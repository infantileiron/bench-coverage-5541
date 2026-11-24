import {api} from '../api/survey.js';
import {heading} from '../components/common/layout.js';
import {metrics} from '../components/common/metrics.js';
import {table} from '../components/common/table.js';
import {states, samplingStates} from '../constants/enums.js';
import {onForm} from '../hooks/forms.js';
import {session} from '../stores/session.js';
import {h} from '../utils/html.js';

export async function reports(id) {
  const list = await api.analyses();
  const run = id || list.length ? await api.analysis(id || list[0].id) : null;
  const plans = await api.samplingPlans();
  const latestPlan = plans.length ? await api.samplingPlan(plans[0].id) : null;
  const sidebar = `<aside class="sheet"><h2>补巡单</h2><ul class="runs">${list.map(x => `<li><a href="#reports/${x.id}">${h(x.title)}</a><span>${h(states[x.status])}</span></li>`).join('') || '<li>暂无补巡单。</li>'}</ul></aside>`;
  const samplingPanel = latestPlan?.result ? `<section class="sheet" style="margin-bottom:1.25rem">
      <h2>整批复点抽样 · ${h(latestPlan.title)}</h2><p class="state">${h(samplingStates[latestPlan.status])}</p>
      ${metrics(latestPlan.result.metrics)}<p class="decision">${h(latestPlan.result.summary)}</p>
      <h3>缺测影响</h3><ul class="notes">${latestPlan.result.missing_impact.map(x => `<li>${h(x)}</li>`).join('')}</ul>
      <p><a href="#sampling/${latestPlan.id}">进入复点抽样查看分层结果与对账明细</a></p></section>` : '';
  let content = '<div class="empty">先在 <a href="#analyze">漏查估算</a> 锁定双轮记录快照。</div>';
  if (run) {
    const output = run.result;
    content = `<h2>${h(run.title)}</h2><p class="state">${h(states[run.status])}</p>`;
    if (output) {
      const rows = output.rows;
      const columns = ['区段','A 轮','B 轮','重合','合并实见','估计总量','估计漏查','估计方差','建议'];
      content += `${metrics(output.metrics)}<p class="decision">${h(output.summary)}</p>
        <h3>按区段的实见与漏查</h3><div class="tall">${table(columns, rows.map(row => columns.map(key => row[key])))}</div>
        <ul class="notes">${output.notes.map(note => `<li>${h(note)}</li>`).join('')}</ul>
        ${run.note ? `<p class="signed">签核意见 · ${h(run.note)}</p>` : ''}<button class="secondary" id="export">下载补巡派发表</button><p id="export-error" role="alert"></p>`;
      if (session()?.role === 'manager' && run.status === 'completed') content += `<form id="publish-form"><label>签核意见<input name="note" required minlength="3"></label><button type="submit">签核派发</button><p role="alert"></p></form>`;
    } else {
      content += `<p>${h(run.note || 'Worker 正在读取锁定的双轮记录快照，页面将自动刷新。')}</p>`;
    }
  }
  return {
    html:heading('补巡派发','核对优先补巡范围。巡查领班签核后将派发表交给当班队伍。') + `<div class="workarea"> <div>${samplingPanel}<section class="sheet" id="report">${content}</section></div>${sidebar}</div>`,
    bind(root, refresh, signal) {
      if (run && ['queued','running'].includes(run.status)) {
        const timer = setTimeout(refresh, 900);
        signal.addEventListener('abort', () => clearTimeout(timer));
      }
      root.querySelector('#export')?.addEventListener('click', async () => {
        try {
          const url = URL.createObjectURL(await api.export(run.id));
          const link = document.createElement('a');
          link.href = url;
          link.download = `bench-plan-${run.id}.csv`;
          link.click();
          setTimeout(() => URL.revokeObjectURL(url), 1000);
        } catch (error) { root.querySelector('#export-error').textContent = error.message; }
      });
      onForm(root.querySelector('#publish-form'), async data => { await api.publish(run.id, data.note); refresh(); });
    }
  };
}
