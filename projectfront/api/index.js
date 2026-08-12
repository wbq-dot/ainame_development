import { request, upload, download } from '../utils/request'

export const api = {
  health: () => request({ url: '/' }),

  sendRegisterCode: (email) => request({
    url: `/auth/code?email=${encodeURIComponent(email)}`
  }),
  register: (data) => request({ url: '/auth/register', method: 'POST', data }),
  login: (data) => request({ url: '/auth/login', method: 'POST', data }),
  adminLogin: (data) => request({ url: '/auth/admin/login', method: 'POST', data }),
  getMe: () => request({ url: '/auth/me', auth: true }),
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
  getKnowledgeTask: (taskId) => request({ url: `/knowledge/tasks/${encodeURIComponent(taskId)}`, auth: true }),
  generateLogo: (data) => request({ url: '/logos/generate', method: 'POST', data, auth: true }),

  getCommunityTopics: ({ sort = 'latest', page = 1, pageSize = 20 } = {}) => request({
    url: `/community/topics?sort=${sort}&page=${page}&page_size=${pageSize}`,
    optionalAuth: true
  }),
  createCommunityTopic: (data) => request({ url: '/community/topics', method: 'POST', data, auth: true }),
  addCommunityCandidate: (topicId, data) => request({ url: `/community/topics/${topicId}/candidates`, method: 'POST', data, auth: true }),
  voteCommunityCandidate: (topicId, candidateId) => request({ url: `/community/topics/${topicId}/vote`, method: 'PUT', data: { candidate_id: candidateId }, auth: true }),
  getCommunityComments: (topicId) => request({ url: `/community/topics/${topicId}/comments` }),
  addCommunityComment: (topicId, content) => request({ url: `/community/topics/${topicId}/comments`, method: 'POST', data: { content }, auth: true }),
  reportCommunityContent: (data) => request({ url: '/community/reports', method: 'POST', data, auth: true }),
  getAdminCommunityTopics: ({ status = 'all', page = 1, pageSize = 20 } = {}) => request({ url: `/admin/community/topics?status=${status}&page=${page}&page_size=${pageSize}`, auth: true }),
  setCommunityFeatured: (topicId, isFeatured) => request({ url: `/admin/community/topics/${topicId}/featured`, method: 'PUT', data: { is_featured: isFeatured }, auth: true }),
  moderateCommunityContent: (data) => request({ url: '/admin/community/moderate', method: 'POST', data, auth: true }),
  getAdminCommunityReports: (status = 'pending') => request({ url: `/admin/community/reports?status=${status}`, auth: true }),
  resolveCommunityReport: (reportId, data) => request({ url: `/admin/community/reports/${reportId}/resolve`, method: 'POST', data, auth: true }),

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
  }),

  getExperts: () => request({ url: '/experts' }),
  getExpertTiers: () => request({ url: '/expert-tiers' }),
  getExpertPackages: (expertId = '') => request({
    url: `/expert-packages${expertId ? `?expert_id=${expertId}` : ''}`
  }),
  getExpertPackage: (packageId) => request({ url: `/expert-packages/${packageId}` }),
  getExpertApplication: () => request({ url: '/expert-applications/me', auth: true }),
  submitExpertApplication: (data) => request({ url: '/expert-applications', method: 'POST', data, auth: true }),
  uploadExpertCredential: (filePath) => upload({ url: '/expert-applications/credential', filePath, name: 'credential' }),
  downloadExpertCredential: (profileId) => download({ url: `/expert-applications/${profileId}/credential` }),
  createExpertOrder: (data) => request({ url: '/expert-orders', method: 'POST', data, auth: true }),
  uploadExpertOrderImage: (orderId, filePath) => upload({ url: `/expert-orders/${orderId}/images`, filePath, name: 'image' }),
  getExpertOrderImages: (orderId) => request({ url: `/expert-orders/${orderId}/images`, auth: true }),
  downloadExpertOrderImage: (orderId, attachmentId) => download({ url: `/expert-orders/${orderId}/images/${attachmentId}` }),
  getMyExpertOrders: () => request({ url: '/expert-orders/mine', auth: true }),
  getExpertOrder: (orderId) => request({ url: `/expert-orders/${orderId}`, auth: true }),
  cancelExpertOrder: (orderId) => request({ url: `/expert-orders/${orderId}/cancel`, method: 'POST', auth: true }),
  getExpertOrderPayLink: (orderId) => request({ url: `/expert-orders/${orderId}/pay-link`, method: 'POST', auth: true }),
  confirmExpertOrder: (orderId) => request({ url: `/expert-orders/${orderId}/confirm`, method: 'POST', auth: true }),
  reviseExpertOrder: (orderId, reason) => request({ url: `/expert-orders/${orderId}/revision`, method: 'POST', data: { reason }, auth: true }),
  disputeExpertOrder: (orderId, reason) => request({ url: `/expert-orders/${orderId}/dispute`, method: 'POST', data: { reason }, auth: true }),
  reviewExpertOrder: (orderId, data) => request({ url: `/expert-orders/${orderId}/reviews`, method: 'POST', data, auth: true }),
  getExpertReport: (orderId) => request({ url: `/expert-orders/${orderId}/report`, auth: true }),
  downloadExpertReport: (orderId) => download({ url: `/expert-orders/${orderId}/report/attachment` }),
  getExpertPayStatus: (orderNo) => request({ url: `/expert-pay/status/${orderNo}`, auth: true }),

  getExpertWorkbenchProfile: () => request({ url: '/expert-workbench/profile', auth: true }),
  getWorkbenchPackages: () => request({ url: '/expert-workbench/packages', auth: true }),
  createWorkbenchPackage: (data) => request({ url: '/expert-workbench/packages', method: 'POST', data, auth: true }),
  updateWorkbenchPackage: (packageId, data) => request({ url: `/expert-workbench/packages/${packageId}`, method: 'PUT', data, auth: true }),
  submitWorkbenchPackage: (packageId) => request({ url: `/expert-workbench/packages/${packageId}/submit`, method: 'POST', auth: true }),
  getWorkbenchOrders: () => request({ url: '/expert-workbench/orders', auth: true }),
  acceptWorkbenchOrder: (orderId) => request({ url: `/expert-workbench/orders/${orderId}/accept`, method: 'POST', auth: true }),
  rejectWorkbenchOrder: (orderId) => request({ url: `/expert-workbench/orders/${orderId}/reject`, method: 'POST', auth: true }),
  submitTextExpertReport: (orderId, data) => request({ url: `/expert-workbench/orders/${orderId}/report-text`, method: 'POST', data, auth: true }),
  uploadExpertReport: (orderId, filePath, data) => upload({ url: `/expert-workbench/orders/${orderId}/report`, filePath, name: 'attachment', formData: data }),
  getExpertIncome: () => request({ url: '/expert-workbench/income', auth: true }),
  getExpertSettlements: () => request({ url: '/expert-workbench/settlements', auth: true }),
  createExpertSettlement: (data) => request({ url: '/expert-workbench/settlements', method: 'POST', data, auth: true }),

  getAdminExpertApplications: () => request({ url: '/admin/expert-applications', auth: true }),
  decideExpertApplication: (profileId, decision, note = '', expertLevel = null) => request({ url: `/admin/expert-applications/${profileId}/decision`, method: 'POST', data: { decision, note: note || null, expert_level: expertLevel }, auth: true }),
  getAdminExpertPackages: () => request({ url: '/admin/expert-packages', auth: true }),
  decideExpertPackage: (packageId, decision, note = '') => request({ url: `/admin/expert-packages/${packageId}/decision`, method: 'POST', data: { decision, note: note || null }, auth: true }),
  getAdminExpertOrders: () => request({ url: '/admin/expert-orders', auth: true }),
  resolveExpertOrder: (orderId, data) => request({ url: `/admin/expert-orders/${orderId}/resolve`, method: 'POST', data, auth: true }),
  getAdminExpertSettlements: () => request({ url: '/admin/expert-settlements', auth: true }),
  processExpertSettlement: (requestId, data) => request({ url: `/admin/expert-settlements/${requestId}/process`, method: 'POST', data, auth: true })
}
