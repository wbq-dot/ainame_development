import { request, upload } from '../utils/request'

export const api = {
  health: () => request({ url: '/' }),

  sendRegisterCode: (email) => request({
    url: `/auth/code?email=${encodeURIComponent(email)}`
  }),
  register: (data) => request({ url: '/auth/register', method: 'POST', data }),
  login: (data) => request({ url: '/auth/login', method: 'POST', data }),
  adminLogin: (data) => request({ url: '/auth/admin/login', method: 'POST', data }),
  getAdminBootstrapStatus: () => request({ url: '/admin/bootstrap/status' }),
  bootstrapAdmin: (data) => request({ url: '/admin/bootstrap', method: 'POST', data }),
  generateNames: (data) => request({ url: '/name/generate', method: 'POST', data, auth: true }),
  feedbackNames: (data) => request({ url: '/name/feedback', method: 'POST', data, auth: true }),
  getBalance: () => request({ url: '/credit/balance', auth: true }),

  getPackages: () => request({ url: '/packages/list' }),
  createOrder: (packageId) => request({
    url: '/pay/create_order',
    method: 'POST',
    data: { package_id: packageId },
    auth: true
  }),

  uploadKnowledge: (filePath, knowledgeType = 'general') => upload({
    url: '/knowledge/upload',
    filePath,
    formData: { knowledge_type: knowledgeType }
  }),
  generateLogo: (data) => request({ url: '/logos/generate', method: 'POST', data, auth: true }),

  getAdminUsers: ({ page = 1, pageSize = 20, keyword = '', status = '' }) => {
    const params = [
      `page=${page}`,
      `page_size=${pageSize}`,
      keyword ? `keyword=${encodeURIComponent(keyword)}` : '',
      status ? `status=${encodeURIComponent(status)}` : ''
    ].filter(Boolean).join('&')
    return request({ url: `/admin/users?${params}`, auth: true })
  },
  getAdminPackages: () => request({ url: '/admin/packages', auth: true }),
  updateAdminPackageStatus: (packageId, isActive) => request({
    url: `/admin/packages/${packageId}/status`,
    method: 'PATCH',
    data: { is_active: isActive },
    auth: true
  }),
  adjustUserCredit: (userId, data) => request({
    url: `/admin/users/${userId}/credit-adjustments`,
    method: 'POST',
    data,
    auth: true
  }),
  freezeUser: (userId, reason = '') => request({
    url: `/admin/users/${userId}/freeze`,
    method: 'POST',
    data: { reason: reason || null },
    auth: true
  }),
  unfreezeUser: (userId, reason = '') => request({
    url: `/admin/users/${userId}/unfreeze`,
    method: 'POST',
    data: { reason: reason || null },
    auth: true
  }),
  deleteUser: (userId, reason = '') => request({
    url: `/admin/users/${userId}`,
    method: 'DELETE',
    data: { reason: reason || null },
    auth: true
  })
}
