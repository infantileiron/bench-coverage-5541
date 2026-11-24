import {h} from '../../utils/html.js';
export function strip(counts) {
  const values = [['A 轮已核',counts.round_a], ['双轮找到',counts.overlap], ['B 轮已核',counts.round_b]];
  return `<div class="pair-strip">${values.map(([label,value]) => `<span>${h(label)} <b>${h(value)}</b></span>`).join('')}</div>`;
}
