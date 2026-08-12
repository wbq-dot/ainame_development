import { developerRequest, publicApiRequest } from '../utils/developer-request'

export const developerApi = {
  sendCode: (email) => developerRequest({ url: `/developer/auth/code?email=${encodeURIComponent(email)}`, auth: false }),
  register: (data) => developerRequest({ url: '/developer/auth/register', method: 'POST', data, auth: false }),
  login: (data) => developerRequest({ url: '/developer/auth/login', method: 'POST', data, auth: false }),
  me: () => developerRequest({ url: '/developer/me' }),
  password: (data) => developerRequest({ url: '/developer/password', method: 'PATCH', data }),
  keys: () => developerRequest({ url: '/developer/keys' }),
  createKey: (name) => developerRequest({ url: '/developer/keys', method: 'POST', data: { name } }),
  renameKey: (id, name) => developerRequest({ url: `/developer/keys/${id}`, method: 'PATCH', data: { name } }),
  revokeKey: (id) => developerRequest({ url: `/developer/keys/${id}/revoke`, method: 'POST' }),
  regenerateKey: (id) => developerRequest({ url: `/developer/keys/${id}/regenerate`, method: 'POST' }),
  wallet: () => developerRequest({ url: '/developer/wallet' }),
  walletLogs: () => developerRequest({ url: '/developer/wallet/logs' }),
  stats: (days = 7) => developerRequest({ url: `/developer/statistics?days=${days}` }),
  growth: () => developerRequest({ url: '/developer/growth' }),
  tasks: () => developerRequest({ url: '/developer/tasks' }),
  task: (id) => developerRequest({ url: `/developer/tasks/${id}` }),
  packages: () => developerRequest({ url: '/developer/billing/packages', auth: false }),
  orders: () => developerRequest({ url: '/developer/billing/orders' }),
  createOrder: (data) => developerRequest({ url: '/developer/billing/orders', method: 'POST', data }),
  refreshOrder: (orderNo) => developerRequest({ url: `/developer/billing/orders/${encodeURIComponent(orderNo)}/refresh`, method: 'POST' }),
  refund: (orderNo, reason) => developerRequest({ url: `/developer/billing/orders/${encodeURIComponent(orderNo)}/refunds`, method: 'POST', data: { reason } }),
  debugName: (data, apiKey, idem) => publicApiRequest({ url: '/openapi/v1/names/generate', method: 'POST', data, apiKey, idempotencyKey: idem }),
  batch: (items, apiKey, idem) => publicApiRequest({ url: '/openapi/v1/batches', method: 'POST', data: { items }, apiKey, idempotencyKey: idem })
}
