const API_BASE_KEY = 'ainame_api_base_url'
const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8000'

export function getApiBaseUrl() {
  return (uni.getStorageSync(API_BASE_KEY) || DEFAULT_API_BASE_URL).replace(/\/$/, '')
}

export function setApiBaseUrl(value) {
  const url = String(value || '').trim().replace(/\/$/, '')
  if (!/^https?:\/\//i.test(url)) {
    throw new Error('服务地址必须以 http:// 或 https:// 开头')
  }
  uni.setStorageSync(API_BASE_KEY, url)
  return url
}

export { DEFAULT_API_BASE_URL }
