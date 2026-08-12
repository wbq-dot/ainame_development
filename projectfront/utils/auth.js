const ACCESS_TOKEN_KEY = 'ainame_access_token'
const REFRESH_TOKEN_KEY = 'ainame_refresh_token'
const USER_KEY = 'ainame_user'
const ADMIN_HOME_URL = '/pages/admin/index'
const ADMIN_LOGIN_URL = '/pages/admin/login'
const ADMIN_CONSOLE_ROUTES = new Set([
  'pages/admin/index',
  'pages/admin/users',
  'pages/admin/refunds',
  'pages/admin/packages',
  'pages/admin/package-form',
  'pages/admin/experts',
  'pages/admin/expert-packages',
  'pages/admin/expert-orders',
  'pages/admin/expert-settlements'
])

let adminRedirecting = false

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

export function setUser(user) {
  uni.setStorageSync(USER_KEY, user)
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

export function isAdminSession() {
  const user = getUser()
  return Boolean(getAccessToken() && user && user.role === 'admin')
}

function currentRoute() {
  if (typeof getCurrentPages !== 'function') return ''
  const pages = getCurrentPages()
  const page = pages.length ? pages[pages.length - 1] : null
  return String((page && (page.route || page.__route__)) || '').replace(/^\//, '')
}

function reLaunchOnce(url) {
  if (adminRedirecting) return
  adminRedirecting = true
  uni.reLaunch({
    url,
    complete: () => {
      setTimeout(() => {
        adminRedirecting = false
      }, 0)
    }
  })
}

export function enforceAdminConsoleRoute() {
  if (!isAdminSession()) return false
  const route = currentRoute()
  if (!route || ADMIN_CONSOLE_ROUTES.has(route)) return false
  reLaunchOnce(ADMIN_HOME_URL)
  return true
}

export function requireAdminSession() {
  if (isAdminSession()) return true
  reLaunchOnce(ADMIN_LOGIN_URL)
  return false
}

export function handleAdminAuthError(error) {
  const message = String((error && error.message) || '')
  const invalidSession = !getAccessToken()
    || message.includes('请先登录')
    || message.includes('登录已失效')
    || message.includes('管理员权限')
    || message.includes('账号已被冻结')
  if (!invalidSession) return false
  clearLogin()
  reLaunchOnce(ADMIN_LOGIN_URL)
  return true
}

export function logoutAdmin() {
  clearLogin()
  reLaunchOnce(ADMIN_LOGIN_URL)
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
