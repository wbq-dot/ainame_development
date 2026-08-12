const ACCESS = 'ainame_developer_access'
const REFRESH = 'ainame_developer_refresh'
const PROFILE = 'ainame_developer_profile'

export const getDeveloperAccess = () => uni.getStorageSync(ACCESS) || ''
export const getDeveloperRefresh = () => uni.getStorageSync(REFRESH) || ''
export const getDeveloper = () => uni.getStorageSync(PROFILE) || null
export function saveDeveloperLogin(data) {
  uni.setStorageSync(ACCESS, data.access_token)
  uni.setStorageSync(REFRESH, data.refresh_token)
  uni.setStorageSync(PROFILE, data.developer)
}
export function setDeveloperAccess(token) { uni.setStorageSync(ACCESS, token) }
export function setDeveloper(profile) { uni.setStorageSync(PROFILE, profile) }
export function clearDeveloperLogin() {
  uni.removeStorageSync(ACCESS); uni.removeStorageSync(REFRESH); uni.removeStorageSync(PROFILE)
}
