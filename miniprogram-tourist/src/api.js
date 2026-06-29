const DEFAULT_BASE_URL = 'http://127.0.0.1:8010/api'
const ENV_BASE_URL = import.meta.env && import.meta.env.VITE_API_BASE_URL

function normalizeBaseUrl(url) {
  return String(url || '').replace(/\/+$/, '')
}

export function getApiBaseUrl() {
  let stored = ''
  try {
    stored = uni.getStorageSync('api_base_url')
  } catch (e) {}
  return normalizeBaseUrl(stored || ENV_BASE_URL || DEFAULT_BASE_URL)
}

export const BASE_URL = DEFAULT_BASE_URL

export function buildApiUrl(path) {
  const normalizedPath = String(path || '').startsWith('/') ? path : `/${path}`
  return `${getApiBaseUrl()}${normalizedPath}`
}

function request(options) {
  return new Promise((resolve, reject) => {
    uni.request({
      url: buildApiUrl(options.url),
      method: options.method || 'GET',
      data: options.data,
      header: options.header || {},
      timeout: options.timeout || 60000,
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
        } else {
          reject(res)
        }
      },
      fail: (err) => {
        reject(err)
      }
    })
  })
}

export const listParks = () => request({ url: '/route/parks' })
export const planRoute = (park, pref) => request({ url: `/route/${park}/plan`, method: 'POST', data: pref })
export const chatText = (payload) => request({ url: '/chat/text', method: 'POST', data: payload })
export const chatCheckin = (payload) => request({ url: '/chat/checkin', method: 'POST', data: payload })
export const getAvatarStream = (params) => request({ url: '/chat/avatar-stream', data: params })
export const getChatSuggestions = (park, limit = 5) => request({ url: '/chat/suggestions', data: { park, limit } })
export const getChatPref = (sessionId) => request({ url: `/chat/pref/${sessionId}` })
