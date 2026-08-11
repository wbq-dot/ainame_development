import { getApiBaseUrl } from './config'
import { clearLogin, getAccessToken, getRefreshToken, setAccessToken } from './auth'

let refreshTask = null

function normalizeError(data, statusCode) {
  if (data && Array.isArray(data.detail)) {
    return data.detail.map((item) => item.msg).join('；')
  }
  if (data && typeof data.detail === 'string') return data.detail
  if (data && typeof data.message === 'string') return data.message
  return `请求失败（${statusCode || '网络异常'}）`
}

function refreshAccessToken() {
  if (refreshTask) return refreshTask
  refreshTask = new Promise((resolve, reject) => {
    const refreshToken = getRefreshToken()
    if (!refreshToken) {
      reject(new Error('登录已失效，请重新登录'))
      return
    }
    uni.request({
      url: `${getApiBaseUrl()}/auth/refresh`,
      method: 'POST',
      timeout: 30000,
      header: { Authorization: `Bearer ${refreshToken}` },
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300 && res.data.access_token) {
          setAccessToken(res.data.access_token)
          resolve(res.data.access_token)
        } else {
          reject(new Error(normalizeError(res.data, res.statusCode)))
        }
      },
      fail: () => reject(new Error('刷新登录状态失败'))
    })
  }).finally(() => {
    refreshTask = null
  })
  return refreshTask
}

export function request({ url, method = 'GET', data, auth = false, header = {}, retried = false }) {
  return new Promise((resolve, reject) => {
    const token = getAccessToken()
    if (auth && !token) {
      reject(new Error('请先登录'))
      return
    }

    uni.request({
      url: `${getApiBaseUrl()}${url}`,
      method,
      data,
      timeout: 180000,
      header: {
        'Content-Type': 'application/json',
        ...(auth ? { Authorization: `Bearer ${token}` } : {}),
        ...header
      },
      success: async (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
          return
        }
        if (auth && !retried && res.statusCode === 401 && getRefreshToken()) {
          try {
            await refreshAccessToken()
            resolve(await request({ url, method, data, auth, header, retried: true }))
            return
          } catch (error) {
            clearLogin()
            reject(new Error('登录已失效，请重新登录'))
            return
          }
        }
        if (auth && res.statusCode === 423) {
          clearLogin()
          reject(new Error('账号已被冻结，请联系管理员'))
          return
        }
        if (auth && res.statusCode === 401) clearLogin()
        reject(new Error(normalizeError(res.data, res.statusCode)))
      },
      fail: (error) => {
        reject(new Error(error.errMsg || '无法连接后端，请检查服务地址和后端状态'))
      }
    })
  })
}

export function upload({ url, filePath, name = 'file', formData = {}, auth = true, retried = false }) {
  return new Promise((resolve, reject) => {
    const token = getAccessToken()
    if (auth && !token) {
      reject(new Error('请先登录'))
      return
    }
    uni.uploadFile({
      url: `${getApiBaseUrl()}${url}`,
      filePath,
      name,
      formData,
      timeout: 180000,
      header: auth ? { Authorization: `Bearer ${token}` } : {},
      success: async (res) => {
        let data = res.data
        try {
          data = typeof res.data === 'string' ? JSON.parse(res.data) : res.data
        } catch (error) {
          reject(new Error('后端返回了无法解析的数据'))
          return
        }
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(data)
          return
        }
        if (auth && !retried && res.statusCode === 401 && getRefreshToken()) {
          try {
            await refreshAccessToken()
            resolve(await upload({ url, filePath, name, formData, auth, retried: true }))
            return
          } catch (error) {
            clearLogin()
            reject(new Error('登录已失效，请重新登录'))
            return
          }
        }
        if (auth && res.statusCode === 423) {
          clearLogin()
          reject(new Error('账号已被冻结，请联系管理员'))
          return
        }
        if (auth && res.statusCode === 401) clearLogin()
        reject(new Error(normalizeError(data, res.statusCode)))
      },
      fail: (error) => reject(new Error(error.errMsg || '文件上传失败'))
    })
  })
}

export function download({ url, auth = true }) {
  return new Promise((resolve, reject) => {
    const token = getAccessToken()
    if (auth && !token) { reject(new Error('请先登录')); return }
    uni.downloadFile({
      url: `${getApiBaseUrl()}${url}`,
      timeout: 180000,
      header: auth ? { Authorization: `Bearer ${token}` } : {},
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) resolve(res.tempFilePath)
        else reject(new Error(`下载失败（${res.statusCode}）`))
      },
      fail: (error) => reject(new Error(error.errMsg || '文件下载失败'))
    })
  })
}
