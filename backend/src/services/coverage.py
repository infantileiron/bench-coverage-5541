from collections import defaultdict
from math import ceil


def chapman(n_a, n_b, overlap):
    population = (n_a + 1) * (n_b + 1) / (overlap + 1) - 1
    variance = (n_a + 1) * (n_b + 1) * (n_a - overlap) * (n_b - overlap) / ((overlap + 1)**2 * (overlap + 2))
    return population, variance



def group_captures(records):
    groups = defaultdict(lambda: {'A': set(), 'B': set(), 'unverified': 0})
    for row in records:
        group = groups[row['segment_code']]
        if row['state'] == 'verified':
            group[row['round_code']].add(row['asset_code'])
        else:
            group['unverified'] += 1
    return groups


def capture_counts(group):
    return {
        'round_a': len(group['A']),
        'round_b': len(group['B']),
        'overlap': len(group['A'] & group['B']),
        'seen': len(group['A'] | group['B']),
        'unverified': group['unverified'],
    }


def analyze(records, config):
    observations = group_captures(records)
    rows = []
    for region in config['segments']:
        counts = capture_counts(observations[region['code']])
        n_a, n_b = counts['round_a'], counts['round_b']
        overlap, seen = counts['overlap'], counts['seen']
        reasons = []
        if not config['verified_independence']:
            reasons.append('两轮独立性待确认')
        if not region['stable']:
            reasons.append('观察期有资产变更或围挡')
        if overlap < config['min_overlap']:
            reasons.append('重合数量低于门槛')
        if counts['unverified']:
            reasons.append('存在待核标签')
        population = missed = var = None
        if not reasons:
            population, var = chapman(n_a, n_b, overlap)
            missed = max(0., population - seen)
        rows.append({'区段':region['title'], 'A 轮':n_a, 'B 轮':n_b, '重合':overlap, '合并实见':seen,
                     '估计总量':round(population,2) if population is not None else None,
                     '估计漏查':round(missed,2) if missed is not None else None,
                     '估计方差':round(var,2) if var is not None else None,
                     '建议': '；'.join(reasons) if reasons else f'按约 {ceil(missed)} 处漏查安排补巡'})
    eligible = [row for row in rows if row['估计漏查'] is not None]
    pending = sorted((row for row in rows if row['估计漏查'] is None), key=lambda row: row['区段'])
    eligible.sort(key=lambda row: (-row['估计漏查'], row['区段']))
    summary = f'先补巡 {eligible[0]["区段"]}，该区段估计漏查 {eligible[0]["估计漏查"]:.2f} 处。' if eligible and eligible[0]['估计漏查'] > 0 else '合格区段当前没有由估算触发的补巡。'
    if not eligible:
        summary = '当前所有区段均需先人工核对，暂缓按估算派单。'
    elif pending:
        summary += f' 另有 {len(pending)} 个区段需人工核对。'
    return {'metrics':{'已确认实见':sum(row['合并实见'] for row in rows), '可估算区段':len(eligible),
                       '人工复核区段':len(pending), '可估区段漏查合计': round(sum(row['估计漏查'] for row in eligible),2)},
            'summary':summary,'rows':eligible+pending,
            'notes':['各区段固定资产范围，A、B 轮独立记录同一标签，轮内去重。',
                     '合计仅覆盖有可比观察且重合达标的区段。未估算区段保留在证据中。']}
