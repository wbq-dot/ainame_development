import { getApiBaseUrl } from './config'
import { clearDeveloperLogin, getDeveloperAccess, getDeveloperRefresh, setDeveloperAccess } from './developer-auth'

function errorText(data, status) {
  if (data && Array.isArray(data.detail)) return data.detail.map((item) => item.msg).join('；')
  return (data && (data.detail || data.message)) || `请求失败（${status}）`
}

async function refresh() {
  const token = getDeveloperRefresh()
  if (!token) throw new Error('开发者登录已失效')
  return new Promise((resolve, reject) => uni.request({
    url: `${getApiBaseUrl()}/developer/auth/refresh`, method: 'POST', header: { Authorization: `Bearer ${token}` },
    success: (res) => {
      if (res.statusCode >= 200 && res.statusCode < 300) { setDeveloperAccess(res.data.access_token); resolve(res.data.access_token) }
      else reject(new Error(errorText(res.data, res.statusCode)))
    }, fail: () => reject(new Error('无法刷新开发者登录'))
  }))
}

export function developerRequest({ url, method = 'GET', data, auth = true, retried = false, header = {} }) {
  return new Promise((resolve, reject) => {
    const token = getDeveloperAccess()
    if (auth && !token) { reject(new Error('请先登录开发者账号')); return }
    uni.request({
      url: `${getApiBaseUrl()}${url}`, method, data, timeout: 180000,
      header: { 'Content-Type': 'application/json', ...(auth ? { Authorization: `Bearer ${token}` } : {}), ...header },
      success: async (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) { resolve(res.data); return }
        if (auth && !retried && res.statusCode === 401 && getDeveloperRefresh()) {
          try { await refresh(); resolve(await developerRequest({ url, method, data, auth, retried: true, header })); return }
          catch (error) { clearDeveloperLogin() }
        }
        if (auth && (res.statusCode === 401 || res.statusCode === 423)) clearDeveloperLogin()
        reject(new Error(errorText(res.data, res.statusCode)))
      }, fail: (error) => reject(new Error(error.errMsg || '无法连接后端'))
    })
  })
}

export function publicApiRequest({ url, method = 'GET', data, apiKey, idempotencyKey = '' }) {
  return developerRequest({ url, method, data, auth: false, header: { 'X-API-Key': apiKey, ...(idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {}) } })
}

