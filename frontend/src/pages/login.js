import {api} from '../api/survey.js';
import {onForm} from '../hooks/forms.js';
import {setSession} from '../stores/session.js';
export function login(root, refresh) {
  root.innerHTML = `<main class="login"><section class="fold"><div class="bench-mark" aria-hidden="true"></div>
    <div><p>汀沿巡查 · 滨岸养护</p><h1>公共座椅<br>漏查估算</h1><p>校验两轮独立清点，分配下一班的补巡区段。</p></div></section>
    <section class="sheet signin"><h2>巡查签到</h2><form id="login-form">
    <label>邮箱<input name="email" type="email" value="analyst@tingyan.demo" required autocomplete="username"></label>
    <label>密码<input name="password" type="password" value="BankBench2026!" required autocomplete="current-password"></label>
    <button type="submit">进入清点台账</button><p role="alert"></p></form></section></main>`;
  onForm(root.querySelector('#login-form'), async data => {setSession(await api.login(data)); refresh();});
}
