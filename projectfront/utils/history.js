import { getUser } from './auth'

const MAX_HISTORY = 30

function historyKey() {
  const user = getUser()
  const userId = user && (user.id || user.user_id)
  return `ainame_naming_history_${userId || 'anonymous'}`
}

export function getNamingHistory() {
  const value = uni.getStorageSync(historyKey())
  return Array.isArray(value) ? value : []
}

export function saveNamingHistory(entry) {
  const history = getNamingHistory()
  const normalized = {
    threadId: entry.threadId,
    category: entry.category,
    requirement: entry.requirement || '',
    names: entry.names || [],
    updatedAt: new Date().toISOString()
  }
  const next = [normalized, ...history.filter((item) => item.threadId !== entry.threadId)].slice(0, MAX_HISTORY)
  uni.setStorageSync(historyKey(), next)
  return next
}

export function removeNamingHistory(threadId) {
  const next = getNamingHistory().filter((item) => item.threadId !== threadId)
  uni.setStorageSync(historyKey(), next)
  return next
}

export function clearNamingHistory() {
  uni.removeStorageSync(historyKey())
}
