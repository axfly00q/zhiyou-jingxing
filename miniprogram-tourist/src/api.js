export const BASE_URL = 'http://127.0.0.1:8000/api'

function request(options) {
  return new Promise((resolve, reject) => {
    uni.request({
      url: BASE_URL + options.url,
      method: options.method || 'GET',
      data: options.data,
      header: options.header || {},
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
export const chatCheckin = (payload) => request({ url: '/chat/checkin', method: 'POST', data: payload })
export const getAvatarStream = (params) => request({ url: '/chat/avatar-stream', data: params })
export const getChatSuggestions = (park, limit = 5) => request({ url: '/chat/suggestions', data: { park, limit } })
export const getChatPref = (sessionId) => request({ url: `/chat/pref/${sessionId}` })
