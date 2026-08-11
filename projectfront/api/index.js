import { request, upload } from '../utils/request'

export const api = {
  health: () => request({ url: '/' }),

  sendRegisterCode: (email) => request({
    url: `/auth/code?email=${encodeURIComponent(email)}`
  }),
  register: (data) => request({ url: '/auth/register', method: 'POST', data }),
  login: (data) => request({ url: '/auth/login', method: 'POST', data }),
  adminLogin: (data) => request({ url: '/auth/admin/login', method: 'POST', data }),
  changePassword: (data) => request({ url: '/account/password', method: 'PATCH', data, auth: true }),
  sendEmailChangeCode: (newEmail) => request({
    url: '/account/email-change/code',
    method: 'POST',
    data: { new_email: newEmail },
    auth: true
  }),
  changeEmail: (data) => request({ url: '/account/email', method: 'PATCH', data, auth: true }),
  deleteAccount: () => request({ url: '/account', method: 'DELETE', auth: true }),
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
  getOrders: ({ page = 1, pageSize = 20 } = {}) => request({
    url: `/pay/orders?page=${page}&page_size=${pageSize}`,
    auth: true
  }),
  getOrder: (orderNo) => request({ url: `/pay/orders/${encodeURIComponent(orderNo)}`, auth: true }),
  requestRefund: (orderNo, reason) => request({
    url: `/pay/orders/${encodeURIComponent(orderNo)}/refunds`,
    method: 'POST',
    data: { reason },
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
  }),
  getAdminRefunds: ({ page = 1, pageSize = 20, keyword = '', status = '' }) => {
    const params = [
      `page=${page}`,
      `page_size=${pageSize}`,
      keyword ? `keyword=${encodeURIComponent(keyword)}` : '',
      status ? `status=${encodeURIComponent(status)}` : ''
    ].filter(Boolean).join('&')
    return request({ url: `/admin/refunds?${params}`, auth: true })
  },
  approveRefund: (refundNo, reason = '') => request({
    url: `/admin/refunds/${encodeURIComponent(refundNo)}/approve`,
    method: 'POST',
    data: { reason: reason || null },
    auth: true
  }),
  rejectRefund: (refundNo, reason) => request({
    url: `/admin/refunds/${encodeURIComponent(refundNo)}/reject`,
    method: 'POST',
    data: { reason },
    auth: true
  }),
  retryRefund: (refundNo) => request({
    url: `/admin/refunds/${encodeURIComponent(refundNo)}/retry`,
    method: 'POST',
    auth: true
  })
}
