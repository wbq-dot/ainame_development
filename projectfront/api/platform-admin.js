import { request } from '../utils/request'

export const platformAdminApi = {
  developers: (status = '', keyword = '') => request({ url: `/admin/platform/developers?status=${status}&keyword=${encodeURIComponent(keyword)}`, auth: true }),
  freeze: (id, reason) => request({ url: `/admin/platform/developers/${id}/freeze`, method: 'POST', data: { reason }, auth: true }),
  unfreeze: (id, reason) => request({ url: `/admin/platform/developers/${id}/unfreeze`, method: 'POST', data: { reason }, auth: true }),
  developerKeys: (id) => request({ url: `/admin/platform/developers/${id}/keys`, auth: true }),
  revokeKey: (id, reason) => request({ url: `/admin/platform/keys/${id}/revoke`, method: 'POST', data: { reason }, auth: true }),
  packages: () => request({ url: '/admin/platform/packages', auth: true }),
  savePackage: (data, id = null) => request({ url: id ? `/admin/platform/packages/${id}` : '/admin/platform/packages', method: id ? 'PUT' : 'POST', data, auth: true }),
  packageStatus: (id, active, reason) => request({ url: `/admin/platform/packages/${id}/status`, method: 'PATCH', data: { is_active: active, reason }, auth: true }),
  campaigns: () => request({ url: '/admin/platform/campaigns', auth: true }),
  saveCampaign: (data, id = null) => request({ url: id ? `/admin/platform/campaigns/${id}` : '/admin/platform/campaigns', method: id ? 'PUT' : 'POST', data, auth: true }),
  referrals: (status = '') => request({ url: `/admin/platform/referrals?status=${status}`, auth: true }),
  invalidateReward: (id, reason) => request({ url: `/admin/platform/referrals/${id}/invalidate`, method: 'POST', data: { reason }, auth: true }),
  calls: (status = '') => request({ url: `/admin/platform/calls?status=${status}`, auth: true }),
  refunds: (status = '') => request({ url: `/admin/platform/refunds?status=${status}`, auth: true }),
  reviewRefund: (no, approve, note) => request({ url: `/admin/platform/refunds/${encodeURIComponent(no)}/review`, method: 'POST', data: { approve, note }, auth: true }),
  tasks: (type = '', status = '') => request({ url: `/admin/platform/tasks?task_type=${type}&status=${status}`, auth: true }),
  task: (no) => request({ url: `/admin/platform/tasks/${no}`, auth: true }),
  retryTask: (no, reason) => request({ url: `/admin/platform/tasks/${no}/retry`, method: 'POST', data: { reason }, auth: true }),
  stats: () => request({ url: '/admin/platform/statistics', auth: true })
}
