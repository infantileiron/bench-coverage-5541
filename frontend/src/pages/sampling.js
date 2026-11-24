import {api} from '../api/survey.js';
import {heading} from '../components/common/layout.js';
import {metrics} from '../components/common/metrics.js';
import {table} from '../components/common/table.js';
import {recountStates, samplingStates} from '../constants/enums.js';
import {onForm} from '../hooks/forms.js';
import {canWrite} from '../stores/session.js';
import {h} from '../utils/html.js';

function bankOptions(segments, selected = {}) {
  const banks = [...new Set(segments.map(x => x.bank))].sort();
  return banks.map(bank => {
    const total = segments.filter(x => x.bank === bank).length;
    return `<label>${h(bank)}（共 ${total} 段）<input name="size-${h(bank)}" type="number" min="1" max="${total}"
      value="${selected[bank] ?? 1}" required></label>`;
  }).join('');
}

function sizesFrom(form) {
  const sizes = {};
  for (const [name, value] of new FormData(form).entries()) {
    if (name.startsWith('size-')) sizes[name.slice(5)] = Number(value);
  }
  return sizes;
}

export async function sampling(id) {
  const [plans, segments] = await Promise.all([api.samplingPlans(), api.segments()]);
  const current = id || plans.length ? await api.samplingPlan(id || plans[0].id) : null;
  const sidebar = `<aside class="sheet"><h2>抽样批次</h2><ul class="runs">${
    plans.map(x => `<li><a href="#sampling/${x.id}">${h(x.title)}</a><span>${h(samplingStates[x.status])}</span></li>`).join('')
    || '<li>还没有抽样批次。</li>'}</ul></aside>`;

  const creator = canWrite() ? `<section class="sheet tools"><h2>新建分层抽样</h2>
    <form id="plan-form"><label>批次标题<input name="title" required value="复点抽样 · 全数核对"></label>
    <label>巡查批次<input name="campaign" required pattern="[A-Z0-9-]+" value="NOV21-BENCH"></label>
    <fieldset><legend>按岸线抽签数量（层内不放回）</legend><div class="filters">${bankOptions(segments)}</div></fieldset>
    <label>单侧置信水平<select name="confidence">
      <option value="0.9" selected>90%</option><option value="0.95">95%</option><option value="0.8">80%</option><option value="0.99">99%</option>
    </select></label>
    <label>随机种子（固定后抽签可复算）<input name="seed" type="number" min="0" max="4294967295" value="20261124" required></label>
    <button type="submit">锁定实见编号并抽签</button><p role="alert"></p></form></section>` : '';

  let detail = '<div class="empty">先锁定各段实见编号，再按两岸分开抽签。</div>';
  if (current) {
    detail = `<h2>${h(current.title)}</h2><p class="state">${h(samplingStates[current.status])} · 批次 ${h(current.campaign)} · 种子 ${h(current.seed)}</p>`;
    if (canWrite()) {
      const previous = Object.fromEntries(current.strata.map(s => [s.bank, s.sample_size]));
      detail += `<details class="sheet tools" style="margin-bottom:1rem"><summary>重跑抽签（已抽中区段不替换）</summary>
        <form id="rerun-form" style="margin-top:.8rem"><fieldset><legend>新的每岸样本量（不得小于已抽中数）</legend>
        <div class="filters">${bankOptions(segments, previous)}</div></fieldset>
        <label>新随机种子（留空沿用原种子）<input name="seed" type="number" min="0" max="4294967295" placeholder="留空沿用 ${h(current.seed)}"></label>
        <button type="submit" class="secondary">重跑抽签</button><p role="alert"></p></form></details>`;
    }
    detail += `<h3>分层抽签结果</h3>${table(
      ['岸线', '层区段数', '抽中段数', '有效复点段', '进不去段', '挂起段', '抽中概率', '层漏查估计', '层方差', '漏查上限', '说明'],
      current.result ? current.result.strata_rows.map(s => ['岸线', '层区段数', '抽中段数', '有效复点段', '进不去段', '挂起段', '抽中概率', '层漏查估计', '层方差', '漏查上限', '说明'].map(k => s[k] ?? '无法计算'))
        : current.strata.map(s => [s.bank, s.population_size, s.sample_size, '—', '—', '—', (s.sample_size / s.population_size).toFixed(4), '—', '—', '—', s.sample_codes.join('、')]))}`;

    if (current.result) {
      const output = current.result;
      detail += `${metrics(output.metrics)}<p class="decision">${h(output.summary)}</p>`;
      detail += `<h3>整批漏查与缺测影响</h3><ul class="notes">${output.missing_impact.map(x => `<li>${h(x)}</li>`).join('')}</ul>`;
      const segColumns = ['区段', '岸线', '锁定实见', '复点状态', '复点总数', '本次漏查', '新增编号', '缺测原因'];
      detail += `<h3>样本段回传对账</h3>${table(segColumns, output.rows.map(r => segColumns.map(k => Array.isArray(r[k]) ? r[k].join('、') || '—' : (r[k] ?? '—')))}`;
      detail += `<ul class="notes">${output.notes.map(x => `<li>${h(x)}</li>`).join('')}</ul>`;
    }

    const pending = current.result ? current.result.rows.filter(r => r['复点状态'] === 'pending') : [];
    if (canWrite() && pending.length) {
      detail += `<section class="sheet tools"><h2>现场回传</h2>
        <form id="recount-form"><label>抽中区段<select name="segment_code">${
          pending.map(r => `<option value="${h(r.segment_code)}">${h(r['区段'])}（锁定实见 ${r['锁定实见']} 个）</option>`).join('')
        }</select></label>
        <label>复点编号（逗号或换行分隔；缺少原锁定编号将挂起该段，新增编号计为补出的漏查）<textarea name="asset_codes" rows="4" required placeholder="BANK-01-S001, BANK-01-S002"></textarea></label>
        <label>回传人<input name="reporter" required minlength="2" placeholder="午班养护员姓名"></label>
        <label>备注（可选）<input name="reason" maxlength="400"></label>
        <button type="submit">提交复点并对账</button><p role="alert"></p></form>
        <form id="blocked-form" style="margin-top:1rem"><h3>抽中却进不去</h3>
        <label>区段<select name="segment_code">${
          pending.map(r => `<option value="${h(r.segment_code)}">${h(r['区段'])}</option>`).join('')
        }</select></label><label>原因（区段保留在样本内，不另抽替代）<input name="reason" required minlength="3" placeholder="围挡封闭、钥匙未交接等"></label>
        <label>上报人<input name="reporter" required minlength="2"></label>
        <button type="submit" class="secondary">标记进不去</button><p role="alert"></p></form></section>`;
    }
  }

  return {
    html: heading('复点抽样', '两轮巡查后锁定各段实见编号，按两岸分层抽签全数复点，按抽中概率推算整批漏查；缺测影响与可算上限在此明示。')
      + `<div class="workarea"><section class="sheet" id="sampling-detail">${detail}</section><div>${creator}${sidebar}</div></div>`,
    bind(root, refresh) {
      onForm(root.querySelector('#plan-form'), async data => {
        const sample_sizes = sizesFrom(data);
        const run = await api.samplingPlans({
          title: data.title, campaign: data.campaign, sample_sizes,
          confidence: Number(data.confidence), seed: Number(data.seed),
        });
        location.hash = `sampling/${run.id}`;
      });
      onForm(root.querySelector('#rerun-form'), async data => {
        const payload = {sample_sizes: sizesFrom(data)};
        if (data.seed !== '') payload.seed = Number(data.seed);
        const run = await api.rerunSampling(current.id, payload);
        location.hash = `sampling/${run.id}`;
      });
      onForm(root.querySelector('#recount-form'), async data => {
        const asset_codes = data.asset_codes.split(/[\s,，;；]+/).map(x => x.trim().toUpperCase()).filter(Boolean);
        await api.submitRecount(current.id, data.segment_code, {
          total_found: asset_codes.length, asset_codes, reason: data.reason || '', reporter: data.reporter,
        });
        refresh();
      });
      onForm(root.querySelector('#blocked-form'), async data => {
        await api.markBlocked(current.id, data.segment_code, {reason: data.reason, reporter: data.reporter});
        refresh();
      });
    }
  };
}
