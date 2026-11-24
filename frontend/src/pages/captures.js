import {api} from '../api/survey.js';
import {heading} from '../components/common/layout.js';
import {table} from '../components/common/table.js';
import {strip} from '../components/common/strip.js';
import {states} from '../constants/enums.js';
import {onForm} from '../hooks/forms.js';
import {canWrite} from '../stores/session.js';
import {h} from '../utils/html.js';

let selected = 'BANK-01';
let campaign = 'NOV21-BENCH';
export async function captures() {
  const segments = await api.segments();
  const chosen = segments.find(x => x.code === selected) || segments[0];
  if (!chosen) return {html:heading('双轮发现清单','先登记区段，再记录两轮独立发现。')};
  const [rows, summary] = await Promise.all([api.captures(chosen.code, campaign), api.summary(chosen.code, campaign)]);
  const pending = rows.filter(x => x.state === 'unverified');
  const form = `<section class="sheet tools"><h2>记录座椅标签</h2><p>${h(chosen.title)} · ${h(campaign)}</p><form id="capture-form">
    <label>巡视轮次<select name="round_code"><option>A</option><option>B</option></select></label><label>座椅编号<input name="asset_code" required placeholder="BANK-01-S099"></label>
    <label>核对状态<select name="state"><option value="verified">标签已核</option><option value="unverified">待核标签</option></select></label>
    <button type="submit">登记发现</button><p role="alert"></p></form>
    ${pending.length ? `<form id="confirm-form"><h3>待核照片</h3><label>座椅标签<select name="id">${pending.map(x => `<option value="${x.id}">${h(x.round_code)} · ${h(x.asset_code)}</option>`).join('')}</select></label><button type="submit">确认实物编号</button><p role="alert"></p></form>` : ''}</section>`;
  return {html:heading('双轮发现清单','独立记录同一物理标签。两个队均发现的座椅进入重合数，待核照片先排除。') +
    `<div class="workarea"><section class="sheet"><h2>发现台账 · ${h(chosen.title)}</h2><form id="filter-form" class="filters">
    <label>区段<select name="segment">${segments.map(x => `<option value="${h(x.code)}" ${chosen.code === x.code ? 'selected' : ''}>${h(x.title)}</option>`).join('')}</select></label>
    <label>巡查批次<input name="campaign" required pattern="[A-Z0-9-]+" value="${h(campaign)}"></label><button type="submit" class="secondary">查询</button><p role="alert"></p></form>
    ${strip(summary)}<div class="tall">${table(['轮次','座椅编号','标签状态'],rows.map(x => [x.round_code,x.asset_code,states[x.state]]))}</div></section>${canWrite()?form:''}</div>`,
    bind(root, refresh) {
      onForm(root.querySelector('#filter-form'), async data => {selected=data.segment; campaign=data.campaign; refresh();});
      onForm(root.querySelector('#capture-form'), async data => {await api.addCapture({...data,segment_code:chosen.code,campaign});refresh();});
      onForm(root.querySelector('#confirm-form'), async data => {await api.confirm(data.id); refresh();});
    }
  };
}
