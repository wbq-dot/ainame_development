const ACCESS_TOKEN_KEY = 'ainame_access_token'
const REFRESH_TOKEN_KEY = 'ainame_refresh_token'
const USER_KEY = 'ainame_user'

export function getAccessToken() {
  return uni.getStorageSync(ACCESS_TOKEN_KEY) || ''
}

export function getRefreshToken() {
  return uni.getStorageSync(REFRESH_TOKEN_KEY) || ''
}

export function setAccessToken(token) {
  uni.setStorageSync(ACCESS_TOKEN_KEY, token)
}

export function getUser() {
  return uni.getStorageSync(USER_KEY) || null
}

export function saveLogin(data) {
  uni.setStorageSync(ACCESS_TOKEN_KEY, data.access_token)
  uni.setStorageSync(REFRESH_TOKEN_KEY, data.refresh_token)
  uni.setStorageSync(USER_KEY, data.user)
}

export function clearLogin() {
  uni.removeStorageSync(ACCESS_TOKEN_KEY)
  uni.removeStorageSync(REFRESH_TOKEN_KEY)
  uni.removeStorageSync(USER_KEY)
}

export function isLoggedIn() {
  return Boolean(getAccessToken())
}

export function goLogin() {
  uni.navigateTo({ url: '/pages/auth/login' })
}

export function requireLogin() {
  if (isLoggedIn()) return true
  uni.showModal({
    title: '需要登录',
    content: '此功能需要登录后使用。',
    confirmText: '去登录',
    success: ({ confirm }) => {
      if (confirm) goLogin()
    }
  })
  return false
}
