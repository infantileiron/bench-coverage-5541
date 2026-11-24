import {api} from '../api/survey.js';
import {heading} from '../components/common/layout.js';
import {states} from '../constants/enums.js';
import {onForm} from '../hooks/forms.js';
import {canWrite} from '../stores/session.js';
import {h} from '../utils/html.js';

export async function analyze() {
  const runs = await api.analyses();
  return {html:heading('漏查估算','每个区段分别估计总量、漏查和方差。区段封闭性、独立性和标签证据须先核准。') +
      `<div class="workarea reverse"><section class="sheet"><h2>新建补巡估算</h2>${canWrite()?`
      <form id="analysis-form"><label>补巡单标题<input name="title" required value="午班补巡排序"></label>
      <label>巡查批次<input name="campaign" required value="NOV21-BENCH"></label>
      <label>最低重合数<input name="min_overlap" type="number" min="3" max="200" value="5" required></label>
      <label class="check"><input name="verified_independence" type="checkbox">已确认两轮独立清点</label>
      <button type="submit">锁定双轮清单并估算</button><p role="alert"></p></form>`:'<p>观察员可查看已运行的估算。</p>'}</section>
      <section class="sheet"><h2>以往估算</h2><ul class="runs">${runs.map(x => `<li><a href="#reports/${x.id}">${h(x.title)}</a><span>${h(states[x.status])}</span></li>`).join('')||'<li>首次运行后会出现记录。</li>'}</ul></section></div>`,
    bind(root){onForm(root.querySelector('#analysis-form'),async data=>{
      const run=await api.analyses({...data,min_overlap:Number(data.min_overlap),verified_independence:data.verified_independence==='on'});
      location.hash=`reports/${run.id}`;
    });}
  };
}
