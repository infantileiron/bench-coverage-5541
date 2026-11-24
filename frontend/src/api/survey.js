import {send} from './client.js';
export const api = {
  login: data => send('/auth/login', data),
  segments: input => send('/segments', input),
  captures: (code, campaign) => send(`/captures?${new URLSearchParams({segment_code:code, campaign})}`),
  summary: (code, campaign) => send(`/captures/summary?${new URLSearchParams({segment_code:code, campaign})}`),
  addCapture: input => send('/captures', input),
  confirm: id => send(`/captures/${id}/verify`, {}),
  analyses: input => send('/analyses', input),
  analysis: id => send(`/analyses/${id}`),
  publish: (id, note) => send(`/analyses/${id}/publish`, {note}),
  export: id => send(`/analyses/${id}/export`, undefined, true),
  samplingPlans: input => send('/sampling/plans', input),
  samplingPlan: id => send(`/sampling/plans/${id}`),
  rerunSampling: (id, input) => send(`/sampling/plans/${id}/rerun`, input),
  submitRecount: (id, code, input) => send(`/sampling/plans/${id}/segments/${code}/recount`, input),
  markBlocked: (id, code, input) => send(`/sampling/plans/${id}/segments/${code}/blocked`, input),
};
