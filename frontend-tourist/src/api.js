import axios from 'axios'

const api = axios.create({ baseURL: '/api', timeout: 60000 })

export const listParks = () => api.get('/route/parks').then(r => r.data)
export const planRoute = (park, pref) => api.post(`/route/${park}/plan`, pref).then(r => r.data)
export const chatText = (payload) => api.post('/chat/text', payload).then(r => r.data)
export const getAvatarStream = (params) => api.get('/chat/avatar-stream', { params }).then(r => r.data)
export const interrupt = (sessionId) => api.post('/chat/interrupt', null, { params: { session_id: sessionId } })
export const getChatSuggestions = (park, limit = 5) => api.get('/chat/suggestions', { params: { park, limit } }).then(r => r.data)
export const getHotQuestions = (limit = 5) => api.get('/analytics/hot-questions', { params: { limit } }).then(r => r.data)

export default api
