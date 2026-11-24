import {api} from '../api/survey.js';
import {heading} from '../components/common/layout.js';
import {table} from '../components/common/table.js';
import {onForm} from '../hooks/forms.js';
import {canWrite} from '../stores/session.js';

export async function segments() {
  const rows = await api.segments();
  return {html:heading('巡查区段','按岸段核定座椅范围。两轮之间曾围挡、迁移或更换座椅的区段，进入人工复查。') +
    `<div class="workarea"><section class="sheet"><h2>岸段底册</h2>${table(['区段编号','区段名称','岸线','两轮资产范围'], rows.map(x => [x.code,x.title,x.bank,x.stable?'可比':'有变更']))}</section>` +
    (canWrite() ? `<section class="sheet tools"><h2>增记区段</h2><form id="segment-form"><label>区段编号<input name="code" required placeholder="BANK-05"></label>
     <label>名称<input name="title" required></label><label>岸线<input name="bank" required placeholder="东岸"></label>
     <label>两轮资产范围<select name="stable"><option value="true">边界与资产未变</option><option value="false">观察期有变动</option></select></label>
     <button type="submit">登记区段</button><p role="alert"></p></form></section>` : '') + '</div>',
    bind(root, refresh) {onForm(root.querySelector('#segment-form'), async data => {await api.segments({...data,stable:data.stable==='true'}); refresh();});}
  };
}
