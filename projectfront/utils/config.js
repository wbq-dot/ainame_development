const API_BASE_KEY = 'ainame_api_base_url'
const DEFAULT_API_BASE_URL = 'http://192.168.0.20:8000'
const LEGACY_LOCAL_API_URLS = new Set([
  'http://127.0.0.1:8000',
  'http://localhost:8000'
])

export function getApiBaseUrl() {
  const storedUrl = String(uni.getStorageSync(API_BASE_KEY) || '').trim().replace(/\/$/, '')
  if (!storedUrl || LEGACY_LOCAL_API_URLS.has(storedUrl)) {
    if (storedUrl) {
      uni.setStorageSync(API_BASE_KEY, DEFAULT_API_BASE_URL)
    }
    return DEFAULT_API_BASE_URL
  }
  return storedUrl
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
