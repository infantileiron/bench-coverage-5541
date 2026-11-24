import {h} from '../../utils/html.js';
import {roles} from '../../constants/enums.js';
const menu = [['segments','巡查区段'],['captures','双轮发现清单'],['analyze','漏查估算'],['reports','补巡派发'],['sampling','复点抽样']];
export function shell(body, page, user) {
  return `<header class="masthead"><a class="brand" href="#segments">汀沿巡查 <span>滨岸养护</span></a>
    <nav aria-label="业务模块">${menu.map(([link, label]) => `<a href="#${link}" ${page === link ? 'aria-current="page"' : ''}>${h(label)}</a>`).join('')}</nav>
    <div class="identity"><span>${h(roles[user.role])}</span><button class="secondary" id="logout">退出</button></div></header>
    <main>${body}<footer>汀沿巡查 · 公共座椅清点</footer></main>`;
}
export function heading(title, detail) { return `<div class="heading"><h1>${h(title)}</h1><p>${h(detail)}</p></div>`; }
