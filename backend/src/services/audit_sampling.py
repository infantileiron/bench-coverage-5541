"""审计抽样复点：分层抽签、现场回传对账与整批漏查推算。

抽签按岸线（bank）分层、层内不放回简单随机抽样，使用固定随机种子保证可复算；
漏查按抽中概率（Horvitz–Thompson，pi = n_h / N_h）放大到整批。
抽中却进不去（blocked）或对账挂起（suspended）的区段保留在样本内、不剔不换，
其造成的缺测会收窄可估计范围；算不出上限时 result 中明确标注 None 与原因。
"""
from math import sqrt

from fastapi import HTTPException
from sqlalchemy import select

from src.constants.enums import RecountState, SamplingStatus
from src.models.entities import Capture, RecountReturn, SamplingPlan, Segment
from src.services import business as svc

# t 分布单侧分位数（自由度 1..30，末行为正态 z），列对应置信水平
T_TABLE = {
    0.80: [1.376, 1.061, 0.978, 0.941, 0.920, 0.906, 0.896, 0.889, 0.883, 0.879,
           0.876, 0.873, 0.870, 0.868, 0.866, 0.865, 0.863, 0.862, 0.861, 0.860,
           0.859, 0.858, 0.858, 0.857, 0.856, 0.856, 0.855, 0.855, 0.854, 0.854],
    0.90: [3.078, 1.886, 1.638, 1.533, 1.476, 1.440, 1.415, 1.397, 1.383, 1.372,
           1.363, 1.356, 1.350, 1.345, 1.341, 1.337, 1.333, 1.330, 1.328, 1.325,
           1.323, 1.321, 1.319, 1.318, 1.316, 1.315, 1.314, 1.313, 1.311, 1.310],
    0.95: [6.314, 2.920, 2.353, 2.132, 2.015, 1.943, 1.895, 1.860, 1.833, 1.812,
           1.796, 1.782, 1.771, 1.761, 1.753, 1.746, 1.740, 1.734, 1.729, 1.725,
           1.721, 1.717, 1.714, 1.711, 1.708, 1.706, 1.703, 1.701, 1.699, 1.697],
    0.99: [31.821, 6.965, 4.541, 3.747, 3.365, 3.143, 2.998, 2.896, 2.821, 2.764,
           2.718, 2.681, 2.650, 2.624, 2.602, 2.583, 2.567, 2.552, 2.539, 2.528,
           2.518, 2.508, 2.500, 2.492, 2.485, 2.479, 2.473, 2.467, 2.462, 2.457],
}
Z_VALUE = {0.80: 0.842, 0.90: 1.282, 0.95: 1.645, 0.99: 2.326}
GRID = sorted(T_TABLE)


def t_quantile(confidence, df):
    """单侧 t 分位数；置信档位之间线性插值，df>30 用正态近似，df<=0 不可估。"""
    if df <= 0:
        return None
    column = Z_VALUE if df > 30 else {level: T_TABLE[level][df - 1] for level in GRID}
    if confidence in column:
        return column[confidence]
    level = min(GRID, key=lambda value: abs(value - confidence))
    return column[level]


def draw_stratum(codes, size, seed):
    """固定种子的不放回简单随机抽样，返回排序后的区段编号，便于对账复算。"""
    import random
    if size > len(codes):
        raise HTTPException(422, f'抽签数量 {size} 超过该岸线区段数 {len(codes)}')
    rng = random.Random(seed)
    return sorted(rng.sample(sorted(codes), size))


def locked_assets(db, campaign, segment_code):
    rows = db.scalars(select(Capture).where(
        Capture.campaign == campaign,
        Capture.segment_code == segment_code,
        Capture.state == 'verified'))
    return sorted({row.asset_code for row in rows})


def create_plan(db, data, user):
    segments = db.scalars(select(Segment).order_by(Segment.code)).all()
    if not segments:
        raise HTTPException(422, '请先登记巡查区段')
    by_bank = {}
    for seg in segments:
        by_bank.setdefault(seg.bank, []).append(seg.code)
    unknown = set(data.sample_sizes) - set(by_bank)
    if unknown:
        raise HTTPException(422, f'岸线不在底册中：{"、".join(sorted(unknown))}')

    locked, strata = {}, []
    for bank in sorted(by_bank):
        codes = by_bank[bank]
        size = data.sample_sizes.get(bank, 0)
        chosen = draw_stratum(codes, size, data.seed) if size else []
        for code in codes:
            assets = locked_assets(db, data.campaign, code)
            if not assets:
                raise HTTPException(422, f'{code} 在批次 {data.campaign} 没有已核编号，无法锁定实见清单')
            locked[code] = assets
        strata.append({'bank': bank, 'population_size': len(codes), 'sample_size': size,
                       'sample_codes': chosen, 'all_codes': sorted(codes)})

    plan = SamplingPlan(title=data.title, campaign=data.campaign, status=SamplingStatus.DRAFT,
                        seed=data.seed, confidence=data.confidence,
                        locked_snapshot=locked, strata=strata, result=None,
                        author_id=user.id, note='')
    db.add(plan)
    db.flush()
    svc.audit(db, user, 'sampling_create', plan.id)
    db.commit()
    return svc.record(plan)


def get_plan(db, plan_id):
    plan = db.get(SamplingPlan, plan_id)
    if not plan:
        raise HTTPException(404, '找不到抽样复点批次')
    return plan


def rerun(db, plan_id, data, user):
    """重跑抽签：保留已抽中区段，只允许向更大样本量扩充，不替换、不剔除。"""
    plan = db.scalar(select(SamplingPlan).where(SamplingPlan.id == plan_id).with_for_update())
    if not plan:
        raise HTTPException(404, '找不到抽样复点批次')
    seed = data.seed if data.seed is not None else plan.seed
    new_strata = []
    for stratum in plan.strata:
        bank = stratum['bank']
        if bank not in data.sample_sizes:
            raise HTTPException(422, f'缺少岸线 {bank} 的抽签数量')
        size = data.sample_sizes[bank]
        previous = set(stratum['sample_codes'])
        if size < len(previous):
            raise HTTPException(422, f'{bank} 新样本量 {size} 小于已抽中 {len(previous)} 段，重跑不得改换已抽中区段')
        full = draw_stratum(stratum['all_codes'], size, seed)
        dropped = previous - set(full)
        if dropped:
            raise HTTPException(409, f'重跑会丢失已抽中区段：{"、".join(sorted(dropped))}')
        new_strata.append({**stratum, 'sample_size': size, 'sample_codes': full})
    plan.strata = new_strata
    plan.seed = seed
    plan.result = None
    plan.status = SamplingStatus.DRAFT
    plan.note = ''
    current_codes = {code for stratum in new_strata for code in stratum['sample_codes']}
    # 防御性清理：新样本之外的旧回传不得再参与对账（正常扩充不会产生此类行）
    stale = db.scalars(select(RecountReturn).where(RecountReturn.plan_id == plan_id)).all()
    for row in stale:
        if row.segment_code not in current_codes:
            db.delete(row)
    svc.audit(db, user, 'sampling_rerun', plan.id)
    db.commit()
    return recompute(db, plan)


def _returns_map(db, plan_id):
    rows = db.scalars(select(RecountReturn).where(RecountReturn.plan_id == plan_id))
    return {row.segment_code: row for row in rows}


def _segment_titles(db):
    return {seg.code: seg.title for seg in db.scalars(select(Segment))}


def submit_return(db, plan_id, segment_code, data, user):
    plan = db.scalar(select(SamplingPlan).where(SamplingPlan.id == plan_id).with_for_update())
    if not plan:
        raise HTTPException(404, '找不到抽样复点批次')
    chosen = {code for stratum in plan.strata for code in stratum['sample_codes']}
    if segment_code not in chosen:
        raise HTTPException(422, '该区段不在抽样样本内，现场回传须与抽样批次对账')
    if db.scalar(select(RecountReturn.id).where(
            RecountReturn.plan_id == plan_id, RecountReturn.segment_code == segment_code)):
        raise HTTPException(409, '该区段已回传，复点结果以首次对账为准')

    locked = plan.locked_snapshot.get(segment_code, [])
    new_found = sorted(set(data.asset_codes) - set(locked))
    missing = sorted(set(locked) - set(data.asset_codes))
    if data.total_found != len(data.asset_codes):
        raise HTTPException(422, f'复点总数 {data.total_found} 与回传编号数 {len(data.asset_codes)} 不一致')

    # 复点少于原先实见编号 → 挂起该段；新增编号属于现场补出的漏查，计入本次漏查
    state = RecountState.SUSPENDED if missing else RecountState.COUNTED
    row = RecountReturn(plan_id=plan_id, segment_code=segment_code, state=state,
                        total_found=data.total_found, asset_codes=data.asset_codes,
                        missing_locked=missing, reason=data.reason, reporter=data.reporter)
    db.add(row)
    svc.audit(db, user, f'recount_{state}', f'{plan_id}/{segment_code}')
    db.commit()
    return recompute(db, plan)


def mark_blocked(db, plan_id, segment_code, data, user):
    """抽中却进不去：区段留在样本里，不另抽替代段。"""
    plan = db.scalar(select(SamplingPlan).where(SamplingPlan.id == plan_id).with_for_update())
    if not plan:
        raise HTTPException(404, '找不到抽样复点批次')
    chosen = {code for stratum in plan.strata for code in stratum['sample_codes']}
    if segment_code not in chosen:
        raise HTTPException(422, '该区段不在抽样样本内')
    existing = db.scalar(select(RecountReturn).where(
        RecountReturn.plan_id == plan_id, RecountReturn.segment_code == segment_code))
    if existing:
        raise HTTPException(409, '该区段已有现场结论，不能再标记进不去')
    db.add(RecountReturn(plan_id=plan_id, segment_code=segment_code, state=RecountState.BLOCKED,
                         total_found=None, asset_codes=[], missing_locked=[],
                         reason=data.reason, reporter=data.reporter))
    svc.audit(db, user, 'recount_blocked', f'{plan_id}/{segment_code}')
    db.commit()
    return recompute(db, plan)


def recompute(db, plan):
    """依据最新回传重算整批漏查；缺测导致算不出上限时返回 None 并写明原因。"""
    returns = _returns_map(db, plan.id)
    titles = _segment_titles(db)
    rows, stratum_rows = [], []
    point_sum = var_sum = upper_sum = 0.0
    blocked_segments, suspended_segments, nonestimable = [], [], []

    for stratum in plan.strata:
        bank, n_h, n_capital = stratum['bank'], stratum['sample_size'], stratum['population_size']
        members, answered = [], []
        blocked, suspended = [], []
        if n_h == 0:
            stratum_rows.append({'岸线': bank, '层区段数': n_capital, '抽中段数': 0,
                                 '有效复点段': 0, '进不去段': 0, '挂起段': 0, '抽中概率': None,
                                 '层漏查估计': None, '层方差': None, '漏查上限': None,
                                 '说明': '该岸线未抽中任何区段，层总量与上限无法估计'})
            nonestimable.append(bank)
            continue
        for code in stratum['sample_codes']:
            locked_count = len(plan.locked_snapshot.get(code, []))
            row = returns.get(code)
            state = row.state if row else RecountState.PENDING
            missed = None
            if state == RecountState.COUNTED:
                missed = max(0, row.total_found - locked_count)
                answered.append((code, missed))
            elif state == RecountState.BLOCKED:
                blocked.append(code)
            elif state == RecountState.SUSPENDED:
                suspended.append(code)
            members.append({'segment_code': code, '区段': titles.get(code, code), '岸线': bank,
                            '锁定实见': locked_count, '复点状态': state,
                            '复点总数': row.total_found if row else None,
                            '本次漏查': missed,
                            '新增编号': (sorted(set(row.asset_codes) - set(plan.locked_snapshot.get(code, [])))
                                       if row and state == RecountState.COUNTED else []),
                            '缺测原因': (row.reason if state == RecountState.BLOCKED else
                                       ('复点缺少锁定编号 ' + '、'.join(row.missing_locked)
                                        if state == RecountState.SUSPENDED else ''))})
        r_h = len(answered)
        blocked_segments.extend(blocked)
        suspended_segments.extend(suspended)
        base = {'岸线': bank, '层区段数': n_capital, '抽中段数': n_h,
                '有效复点段': r_h, '进不去段': len(blocked), '挂起段': len(suspended)}

        if r_h == 0:
            stratum_rows.append({**base, '层漏查估计': None, '层方差': None,
                                 '漏查上限': None, '抽中概率': round(n_h / n_capital, 4),
                                 '说明': '该岸线没有可用于推算的复点段，层总量与上限均无法估计'})
            nonestimable.append(bank)
            continue

        # 有缺测时仅有效复点段参与推算，等效抽中概率按有效样本量 r_h 放大
        effective_n = r_h if (blocked or suspended) else n_h
        pi = effective_n / n_capital
        mean_m = sum(value for _, value in answered) / r_h
        s2 = sum((value - mean_m) ** 2 for _, value in answered) / (r_h - 1) if r_h > 1 else 0.0
        point = n_capital * mean_m
        fpc = max(0.0, 1 - effective_n / n_capital)
        variance = (n_capital ** 2) * (s2 / effective_n) * fpc
        t_value = t_quantile(plan.confidence, r_h - 1)
        upper = point + t_value * sqrt(variance) if t_value is not None else None
        point_sum += point
        var_sum += variance
        if upper is not None:
            upper_sum += upper
        else:
            nonestimable.append(bank)
        caveat = []
        if blocked:
            caveat.append(f"{len(blocked)} 段进不去保留在样本内")
        if suspended:
            caveat.append(f"{len(suspended)} 段对账挂起")
        if r_h == 1:
            caveat.append('仅 1 个有效段，自由度为 0，层内方差与单侧上限无法估计，整批上限同步不可计算')
        stratum_rows.append({**base, '抽中概率': round(pi, 4),
                             '层漏查估计': round(point, 2), '层方差': round(variance, 2),
                             '漏查上限': round(upper, 2) if upper is not None else None,
                             '说明': '；'.join(caveat) if caveat else '本层样本完整'})
        rows.extend(members)

    # 跨层：上限只有在每个层都可估时才能合计，否则明说算不出
    overall_upper = round(upper_sum, 2) if not nonestimable else None
    affected = sorted(blocked_segments + suspended_segments)
    metrics = {
        '岸线数': len(plan.strata),
        '区段总数': sum(s['population_size'] for s in plan.strata),
        '抽中样本段': sum(s['sample_size'] for s in plan.strata),
        '已复点段': sum(1 for row in rows if row['复点状态'] == RecountState.COUNTED),
        '进不去段': len(blocked_segments),
        '对账挂起段': len(suspended_segments),
        '整批漏查点估计': round(point_sum, 2),
        '整批漏查方差': round(var_sum, 2),
        f'漏查上限({round(plan.confidence * 100)}% 单侧)': overall_upper,
    }
    missing_impact = []
    if affected:
        missing_impact.append('抽中却进不去或对账挂起的区段保留在样本内、不剔不换，'
                              '其漏查不参与点估计与方差：' + '、'.join(titles.get(c, c) for c in affected))
    if nonestimable:
        missing_impact.append('岸线 ' + '、'.join(sorted(set(nonestimable))) +
                              ' 无有效复点段，该层漏查与上限无法估计，整批上限不可计算。')
    elif affected:
        missing_impact.append('整批上限仅覆盖有效复点段所在层，未含缺测段本身的漏查，属偏乐观口径。')
    else:
        missing_impact.append('样本段全部完成复点，缺测影响为零，上限按各层方差合计后取单侧 t 分位。')

    notes = [
        '先锁定各段在抽样批次中的已核实见编号，再按岸线分层、层内不放回抽签；随机种子固定可复算。',
        '层内抽中概率 pi = 有效样本量 / 层区段数，漏查按 Horvitz–Thompson 放大到整批。',
        '重跑抽签保留已抽中区段，只向更大样本量扩充；现场回传与锁定编号对账，缺少原实见编号即挂起，新增编号计为补出的漏查。',
    ]
    pending_count = sum(1 for row in rows if row['复点状态'] == RecountState.PENDING)
    result = {
        'metrics': metrics,
        'summary': (f'整批漏查点估计约 {point_sum:.2f} 处。'
                    + (f'单侧 {plan.confidence:.0%} 上限 {overall_upper:.2f} 处。'
                       if overall_upper is not None else '受缺测影响，整批漏查上限无法计算。')),
        'strata_rows': stratum_rows,
        'rows': rows,
        'missing_impact': missing_impact,
        'notes': notes,
    }
    plan.result = result
    plan.status = SamplingStatus.ESTIMATED if not pending_count and not nonestimable else SamplingStatus.INCONCLUSIVE
    return plan


def list_plans(db):
    return [svc.record(item) for item in
            db.scalars(select(SamplingPlan).order_by(SamplingPlan.id.desc()))]
