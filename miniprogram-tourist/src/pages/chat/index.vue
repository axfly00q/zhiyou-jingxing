<template>
  <view class="chat-container">
    <!-- 路线进度条 -->
    <RouteBar
      v-if="routeSpots.length"
      :spots="routeSpots"
      :current-idx="currentSpotIdx"
      :total-minutes="routeTotalMinutes"
      :elapsed-minutes="elapsedMinutes"
      :force-collapse="!isMapCollapsed"
      @checkin="handleCheckin"
    />

    <!-- 顶部：地图区域 -->
    <view class="map-section" :class="{ 'collapsed': isMapCollapsed }">
      <view class="map-wrapper" v-show="!isMapCollapsed">
        <ParkMap
          v-if="hasMap"
          :park-code="parkCode"
          :spots="routeSpots"
          :current-idx="currentSpotIdx"
          :current-lat="currentLat"
          :current-lng="currentLng"
        />
      </view>
      <!-- 折叠时的简易摘要 / 展开时的折叠按钮 -->
      <view class="map-controller" @click="toggleMap">
        <text class="location-summary" v-if="isMapCollapsed">
          📍 {{ locationType || '定位中...' }}
          <text v-if="distToNext !== null"> · 距下一站 {{ distToNext }}m</text>
          <text> (点击展开地图)</text>
        </text>
        <text class="collapse-btn" v-else>收起地图 🔼</text>
      </view>
    </view>

    <!-- 中部：AI 数字人区域 (展开态) -->
    <view class="avatar-section" v-if="!isAvatarShrinked">
      <view class="avatar-wrapper" @click="toggleAvatar">
        <video
          v-if="!avatarVideoFailed"
          id="avatarVideo"
          :key="avatarVideoKey"
          class="avatar-video"
          :src="currentAvatarVideo"
          :autoplay="true"
          :loop="avatarVideoLoop"
          :muted="true"
          :controls="false"
          :show-center-play-btn="false"
          :show-play-btn="false"
          :enable-progress-gesture="false"
          object-fit="contain"
          @ended="handleAvatarVideoEnded"
          @error="handleAvatarVideoError"
        ></video>
        <view v-else class="avatar-video-placeholder">
          <text>数字人视频待放入</text>
        </view>
        <view class="avatar-hint">{{ avatarStatusText }} · 点击缩小</view>
      </view>
    </view>

    <!-- 悬浮球模式：全屏可拖拽区域 -->
    <movable-area class="movable-area" v-if="isAvatarShrinked">
      <movable-view 
        class="movable-avatar" 
        direction="all" 
        :x="screenWidth" 
        :y="50"
        @click="toggleAvatar"
      >
        <video
          v-if="!avatarVideoFailed"
          id="avatarVideoSmall"
          :key="avatarVideoKey"
          class="avatar-video-small"
          :src="currentAvatarVideo"
          :autoplay="true"
          :loop="avatarVideoLoop"
          :muted="true"
          :controls="false"
          :show-center-play-btn="false"
          :show-play-btn="false"
          :enable-progress-gesture="false"
          object-fit="cover"
          @ended="handleAvatarVideoEnded"
          @error="handleAvatarVideoError"
        ></video>
        <view v-else class="avatar-video-small-placeholder">AI</view>
      </movable-view>
    </movable-area>

    <!-- 底部：聊天记录区 -->
    <view class="chat-section">
      <scroll-view
        class="chat-scroll"
        scroll-y
        enable-flex
        scroll-with-animation
        :scroll-into-view="'msg-' + (messages.length - 1)"
      >
        <view class="message-list">
          <view v-for="(m, i) in messages" :key="i" :class="['message', m.role]" :id="'msg-' + i">
            <text :class="{ thinking: m.content === '正在思考…' }">{{ m.content }}</text>
          </view>
        </view>
        <view class="bottom-padding"></view>
      </scroll-view>
      
      <!-- 输入区域 -->
      <view class="answer-mode-tabs">
        <view
          class="answer-mode-tab"
          :class="{ active: answerMode === 'fast' }"
          @click="answerMode = 'fast'"
        >
          精简版
        </view>
        <view
          class="answer-mode-tab"
          :class="{ active: answerMode === 'detailed' }"
          @click="answerMode = 'detailed'"
        >
          完整版
        </view>
      </view>
      <view class="input-area">
        <view class="mode-toggle" @click="toggleVoiceMode">
          <text>{{ isVoiceMode ? '⌨️' : '🎤' }}</text>
        </view>
        <template v-if="!isVoiceMode">
          <input class="chat-input" placeholder="问问我关于景点的故事吧..." v-model="input" @confirm="send" />
          <button class="send-btn" @click="send" :disabled="loading">发送</button>
        </template>
        <template v-else>
          <button class="voice-btn" :class="{ recording: isRecording }"
                  @touchstart="startRecord" @touchend="stopRecord" @touchcancel="stopRecord">
            {{ isRecording ? '说话中...' : '按住说话' }}
          </button>
        </template>
        <!-- 保存 / 分享按钮 -->
        <view class="share-btn" @tap="showShareCard = true" title="生成纪念卡">
          <text class="share-btn-icon">🖼️</text>
        </view>
      </view>
    </view>

    <Muyu :park-code="parkCode" />
  </view>

  <!-- 分享卡弹层 -->
  <ShareCard
    :visible="showShareCard"
    :session-id="sessionId"
    :park-code="parkCode"
    :park-name="parkName"
    :visited-spots="visitedSpots"
    :elapsed-minutes="elapsedMinutes"
    @close="showShareCard = false"
  />
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import locationManager from '../../utils/locationManager'
import { buildApiUrl, chatCheckin, chatText, getApiBaseUrl } from '../../api'
import RouteBar from '../../components/RouteBar.vue'
import ParkMap from '../../components/ParkMap.vue'
import ShareCard from '../../components/ShareCard.vue'
import Muyu from '../../components/Muyu.vue'

const SESSION_STORAGE_KEY = 'tour_session_id'
const MAP_ENABLED_PARKS = ['lingshan']
const AVATAR_VIDEO_DIR = '/static/avatar-videos'
const AVATAR_VIDEO_MAP = {
  idle: 'idle.mp4',
  listen: 'listen.mp4',
  think: 'think.mp4',
  explain: 'explain.mp4',
  wave: 'wave.mp4',
  point: 'point.mp4',
  beckon: 'beckon.mp4',
  bow: 'bow.mp4',
  clap: 'clap.mp4',
  shrug: 'shrug.mp4',
  goodbye: 'goodbye.mp4',
}
const AVATAR_MOTION_FALLBACKS = {
  idle: 'explain',
  listen: 'explain',
  think: 'explain',
  point: 'explain',
  beckon: 'wave',
  bow: 'wave',
  clap: 'wave',
  shrug: 'wave',
  goodbye: 'wave',
}
const LOOP_MOTIONS = ['idle', 'listen', 'think', 'explain']

const parkName = ref('灵山胜境')
const parkCode = ref('lingshan')
const sessionId = ref(createSessionId())
const loading = ref(false)
const input = ref('')
const messages = ref([])
const answerMode = ref('fast')
const showShareCard = ref(false)   // 控制分享卡弹层

// 已游览景点（从路线 + currentSpotIdx 推导）
const visitedSpots = computed(() =>
  routeSpots.value.slice(0, currentSpotIdx.value).map(s => s.name).filter(Boolean)
)

const isVoiceMode = ref(false)
const isRecording = ref(false)
let recorderManager = null
let recorderStopHandler = null

// 路线数据状态
const routeSpots = ref([])
const routeTotalMinutes = ref(0)
const currentSpotIdx = ref(0)
const routeStartTime = ref(Date.now())
const elapsedMinutes = ref(0)
let elapsedTimer = null
let stopLocationWatch = null

// 状态控制
const isMapCollapsed = ref(false)
const isAvatarShrinked = ref(false)
const screenWidth = ref(300)
const avatarMotion = ref('think')
const avatarVideoKey = ref(0)
const avatarVideoFailed = ref(false)
let avatarIdleTimer = null
let assistantAudio = null

// 定位数据
const currentLat = ref(null)
const currentLng = ref(null)
const locationType = ref('')

const hasMap = computed(() => MAP_ENABLED_PARKS.includes(parkCode.value))
const normalizedAvatarMotion = computed(() => normalizeAvatarMotion(avatarMotion.value))
const avatarVideoLoop = computed(() => LOOP_MOTIONS.includes(normalizedAvatarMotion.value))
const currentAvatarVideo = computed(() => {
  const file = AVATAR_VIDEO_MAP[normalizedAvatarMotion.value] || AVATAR_VIDEO_MAP.idle
  return buildStaticUrl(`${AVATAR_VIDEO_DIR}/${file}`)
})
const avatarStatusText = computed(() => {
  const textMap = {
    idle: '待机',
    listen: '聆听中',
    think: '思考中',
    explain: '讲解中',
    wave: '打招呼',
    point: '指引中',
    beckon: '引导中',
    bow: '致谢',
    clap: '鼓掌',
    shrug: '未听清',
    goodbye: '告别',
  }
  return textMap[normalizedAvatarMotion.value] || '待机'
})

function normalizeAvatarMotion(motion) {
  const key = String(motion || 'idle').trim()
  return AVATAR_VIDEO_MAP[key] ? key : 'idle'
}

function clearAvatarIdleTimer() {
  if (avatarIdleTimer) {
    clearTimeout(avatarIdleTimer)
    avatarIdleTimer = null
  }
}

function scheduleAvatarIdle(ms = 6000) {
  clearAvatarIdleTimer()
  avatarIdleTimer = setTimeout(() => {
    setAvatarMotion('idle')
  }, ms)
}

function setAvatarMotion(motion, options = {}) {
  const nextMotion = normalizeAvatarMotion(motion)
  clearAvatarIdleTimer()
  avatarMotion.value = nextMotion
  avatarVideoFailed.value = false
  avatarVideoKey.value += 1
  if (options.autoIdleMs) {
    scheduleAvatarIdle(options.autoIdleMs)
  }
}

function handleAvatarVideoEnded() {
  if (!avatarVideoLoop.value) {
    setAvatarMotion('idle')
  }
}

function handleAvatarVideoError() {
  const fallback = AVATAR_MOTION_FALLBACKS[normalizedAvatarMotion.value]
  if (fallback) {
    setAvatarMotion(fallback)
    return
  }
  avatarVideoFailed.value = true
}

function buildStaticUrl(url) {
  if (!url) return ''
  if (/^(https?:|data:|wxfile:|blob:)/.test(url)) return url
  const apiBase = getApiBaseUrl().replace(/\/api\/?$/, '')
  const normalizedPath = String(url).startsWith('/') ? url : `/${url}`
  return `${apiBase}${normalizedPath}`
}

function ensureAssistantAudio() {
  if (assistantAudio) return assistantAudio
  assistantAudio = uni.createInnerAudioContext()
  assistantAudio.obeyMuteSwitch = false
  assistantAudio.onEnded(() => setAvatarMotion('idle'))
  assistantAudio.onStop(() => setAvatarMotion('idle'))
  assistantAudio.onError(() => scheduleAvatarIdle(2500))
  return assistantAudio
}

function playAssistantAudio(audioUrl) {
  if (!audioUrl) {
    scheduleAvatarIdle(6500)
    return
  }
  const audio = ensureAssistantAudio()
  try {
    audio.stop()
    audio.src = buildStaticUrl(audioUrl)
    audio.play()
  } catch (e) {
    scheduleAvatarIdle(6500)
  }
}

function cleanAssistantText(text) {
  return String(text ?? '')
    .replace(/```[a-zA-Z0-9_-]*\n?([\s\S]*?)```/g, '$1')
    .replace(/`([^`]*)`/g, '$1')
    .replace(/!\[([^\]]*)\]\([^)]+\)/g, '$1')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/^#{1,6}\s*/gm, '')
    .replace(/\*/g, '')
    .replace(/^\s*精简版\s*[:：]\s*/, '')
    .replace(/[ \t]+/g, ' ')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

function applyAssistantPayload(res, msgIdx, contentKey = 'answer') {
  messages.value[msgIdx].content = cleanAssistantText(res?.[contentKey] || '（暂无回复，请稍后重试）')
  if (res?.new_route) applyNewRoute(res.new_route)
  const nextMotion = res?.motion || 'explain'
  setAvatarMotion(nextMotion)
  playAssistantAudio(res?.audio_url)
}

function createSessionId() {
  const fallback = Math.random().toString(36).substring(2, 15)
  try {
    const stored = uni.getStorageSync(SESSION_STORAGE_KEY)
    if (stored) return stored
    uni.setStorageSync(SESSION_STORAGE_KEY, fallback)
  } catch (e) {}
  return fallback
}

function buildRouteContext() {
  const spots = routeSpots.value || []
  const current = spots[currentSpotIdx.value] || null
  return {
    current_spot_code: current?.code || null,
    current_spot_name: current?.name || null,
    visited_names: spots.slice(0, currentSpotIdx.value).map(s => s.name).filter(Boolean),
    remaining_names: spots.slice(currentSpotIdx.value).map(s => s.name).filter(Boolean),
    total_minutes: routeTotalMinutes.value || 0,
    elapsed_minutes: elapsedMinutes.value || 0,
  }
}

function applyNewRoute(newRoute) {
  if (!newRoute || !Array.isArray(newRoute.spots)) return
  routeSpots.value = newRoute.spots
  routeTotalMinutes.value = newRoute.total_minutes || 0
  currentSpotIdx.value = 0
  routeStartTime.value = Date.now()
  elapsedMinutes.value = 0
  uni.setStorageSync('route', JSON.stringify(newRoute))
}

// 到下一景点的距离（米），null 表示无定位或无路线
const distToNext = computed(() => {
  if (currentLat.value == null || currentLng.value == null) return null
  const next = routeSpots.value[currentSpotIdx.value]
  if (!next) return null
  // 需要景点有 GPS 坐标（lat/lng 字段）
  if (next.lat == null || next.lng == null) return null
  return haversine(currentLat.value, currentLng.value, next.lat, next.lng)
})

function haversine(lat1, lng1, lat2, lng2) {
  const R = 6371000
  const dLat = (lat2 - lat1) * Math.PI / 180
  const dLng = (lng2 - lng1) * Math.PI / 180
  const a = Math.sin(dLat / 2) ** 2
    + Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * Math.sin(dLng / 2) ** 2
  return Math.round(R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a)))
}

const toggleMap = () => {
  isMapCollapsed.value = !isMapCollapsed.value
  // 展开地图时自动缩小数字人，避免内容超出屏幕
  if (!isMapCollapsed.value) {
    isAvatarShrinked.value = true
  }
}

const toggleAvatar = () => {
  isAvatarShrinked.value = !isAvatarShrinked.value
}

onMounted(() => {
  const sysInfo = uni.getSystemInfoSync()
  screenWidth.value = sysInfo.windowWidth - 100 // 默认靠右侧
  
  const pName = uni.getStorageSync('park_name')
  const pCode = uni.getStorageSync('park')
  if (pName) parkName.value = pName
  if (pCode) parkCode.value = pCode

  const routeStr = uni.getStorageSync('route')
  let narrative = ''
  if (routeStr) {
    try { 
      const routeData = JSON.parse(routeStr)
      narrative = routeData.narrative 
      routeSpots.value = routeData.spots || []
      routeTotalMinutes.value = routeData.total_minutes || 0
    } catch (e) {}
  }

  // 启动已用时间计时器
  if (routeSpots.value.length) {
    elapsedTimer = setInterval(() => {
      elapsedMinutes.value = Math.floor((Date.now() - routeStartTime.value) / 60000)
    }, 30000)
  }
  
  if (narrative) {
    messages.value.push({ role: 'assistant', content: cleanAssistantText(narrative) })
  } else {
    messages.value.push({ role: 'assistant', content: `欢迎来到${parkName.value}！请问想了解什么？` })
  }

  stopLocationWatch = locationManager.onLocationUpdate((res) => {
    currentLat.value = res.latitude
    currentLng.value = res.longitude
    locationType.value = res.type
  })
  locationManager.start()

  // 初始化录音管理器
  recorderManager = uni.getRecorderManager()
  recorderStopHandler = (res) => {
    if (!res.tempFilePath) return
    uploadVoice(res.tempFilePath)
  }
  recorderManager.onStop(recorderStopHandler)
})

onUnmounted(() => {
  if (elapsedTimer) {
    clearInterval(elapsedTimer)
    elapsedTimer = null
  }
  if (stopLocationWatch) {
    stopLocationWatch()
    stopLocationWatch = null
  }
  if (recorderManager && recorderStopHandler && typeof recorderManager.offStop === 'function') {
    recorderManager.offStop(recorderStopHandler)
  }
  clearAvatarIdleTimer()
  if (assistantAudio) {
    assistantAudio.destroy()
    assistantAudio = null
  }
  locationManager.stop()
})

const toggleVoiceMode = () => {
  isVoiceMode.value = !isVoiceMode.value
}

const startRecord = () => {
  if (loading.value) return
  isRecording.value = true
  setAvatarMotion('listen')
  recorderManager.start({
    duration: 60000,
    sampleRate: 16000,
    numberOfChannels: 1,
    format: 'aac'
  })
}

const stopRecord = () => {
  if (!isRecording.value) return
  isRecording.value = false
  setAvatarMotion('think')
  recorderManager.stop()
}

async function uploadVoice(tempFilePath) {
  loading.value = true
  uni.uploadFile({
    url: buildApiUrl('/chat/transcribe'),
    filePath: tempFilePath,
    name: 'audio',
    formData: {
      session_id: sessionId.value,
    },
    success: (uploadFileRes) => {
      if (uploadFileRes.statusCode < 200 || uploadFileRes.statusCode >= 300) {
        uni.showToast({ title: '语音识别失败，请重试', icon: 'none' })
        setAvatarMotion('shrug', { autoIdleMs: 2500 })
        loading.value = false
        return
      }
      try {
        const res = JSON.parse(uploadFileRes.data)
        const text = String(res?.text || '').trim()
        if (!text) {
          uni.showToast({ title: '没听清，请再说一次', icon: 'none' })
          setAvatarMotion('shrug', { autoIdleMs: 2500 })
        } else {
          input.value = input.value.trim() ? `${input.value.trim()} ${text}` : text
          isVoiceMode.value = false
          setAvatarMotion('idle')
        }
      } catch (e) {
        uni.showToast({ title: '识别结果解析失败', icon: 'none' })
        setAvatarMotion('shrug', { autoIdleMs: 2500 })
      }
      loading.value = false
    },
    fail: () => {
      uni.showToast({ title: '语音识别失败，请重试', icon: 'none' })
      setAvatarMotion('shrug', { autoIdleMs: 2500 })
      loading.value = false
    }
  })
}

async function send() {
  const text = input.value.trim()
  if (!text || loading.value) return
  messages.value.push({ role: 'user', content: text })
  input.value = ''
  loading.value = true

  const msgIdx = messages.value.length
  messages.value.push({ role: 'assistant', content: '正在思考…' })
  setAvatarMotion('think')

  try {
    const res = await chatText({
      session_id: sessionId.value,
      message: text,
      park_code: parkCode.value,
      route_context: buildRouteContext(),
      answer_mode: answerMode.value,
    })
    applyAssistantPayload(res, msgIdx, 'answer')
  } catch (e) {
    messages.value[msgIdx].content = '（网络不稳定，请稍后重试）'
    setAvatarMotion('shrug', { autoIdleMs: 2500 })
  } finally {
    loading.value = false
  }
}

// 打卡处理
async function handleCheckin(spotCode) {
  if (loading.value) return
  loading.value = true
  const routeContext = buildRouteContext()

  // 立即推进进度条，给游客即时反馈
  if (currentSpotIdx.value < routeSpots.value.length) {
    currentSpotIdx.value += 1
  }
  // 立即显示思考占位，减少等待焦虑
  const msgIdx = messages.value.length
  messages.value.push({ role: 'assistant', content: '正在思考…' })
  setAvatarMotion('think')

  try {
    const res = await chatCheckin({
      session_id: sessionId.value,
      spot_code: spotCode,
      park_code: parkCode.value,
      route_context: routeContext,
    })

    // 用实际内容替换占位
    applyAssistantPayload(res, msgIdx, 'narrative')

    if (res.next_spot_name) {
      const walkTip = res.next_walk_minutes ? `，步行约 ${res.next_walk_minutes} 分钟` : ''
      messages.value.push({ role: 'assistant', content: `→ 下一站：${res.next_spot_name}${walkTip}` })
    } else if (currentSpotIdx.value >= routeSpots.value.length) {
      messages.value.push({ role: 'assistant', content: '🎉 路线全部完成！您已游遍所有景点，希望本次游览令您尽兴而归！' })
    }
  } catch (e) {
    messages.value[msgIdx].content = '打卡失败，请稍后重试。'
    setAvatarMotion('shrug', { autoIdleMs: 2500 })
    // 回滚进度
    if (currentSpotIdx.value > 0) currentSpotIdx.value -= 1
  } finally {
    loading.value = false
  }
}
</script>

<style>
page {
  height: 100%;
  overflow: hidden;
}

/* 整个页面基于 Flex 竖向排列 */
.chat-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  height: 100dvh;
  width: 100vw;
  background-color: #f2f2f2;
  overflow: hidden;
  position: relative;
  box-sizing: border-box;
}

/* === 地图区域 === */
.map-section {
  width: 100%;
  flex: 0 0 auto;
  height: 28vh;         /* 固定高度，微信小程序里 max-height 可能不可靠 */
  transition: height 0.3s ease;
  background-color: #fff;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  z-index: 10;
}
.map-section.collapsed {
  height: 40px;
}
.map-wrapper {
  flex: 1;
  min-height: 0;
  width: 100%;
  overflow: hidden;
}
.map-view {
  width: 100%;
  height: 100%;
}
.map-controller {
  height: 40px;
  background-color: rgba(255, 255, 255, 0.95);
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid #eee;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}
.collapse-btn, .location-summary {
  font-size: 13px;
  color: #555;
}

/* === 数字人区域 (展开态) === */
.avatar-section {
  width: 100%;
  height: 35vh;
  display: flex;
  justify-content: center;
  align-items: flex-end; /* 底部对齐 */
  background: linear-gradient(180deg, #d4fc79 0%, #96e6a1 100%);
  position: relative;
  z-index: 5;
}

.avatar-wrapper {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  align-items: center;
}

.avatar-video {
  width: 80%;
  height: 80%;
  background: transparent;
}

.avatar-video-placeholder {
  width: 80%;
  height: 80%;
  border: 1px dashed rgba(0,0,0,0.18);
  border-radius: 12px;
  color: rgba(0,0,0,0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
}

.avatar-hint {
  font-size: 12px;
  color: rgba(0,0,0,0.5);
  margin-bottom: 10px;
}

/* === 悬浮球拖拽区域 === */
.movable-area {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: 100;
  pointer-events: none; /* 让下方的元素可以被点击 */
}

.movable-avatar {
  width: 80px;
  height: 80px;
  border-radius: 40px;
  background: #fff;
  box-shadow: 0 4px 12px rgba(0,0,0,0.2);
  pointer-events: auto; /* 恢复自身的点击和拖拽事件 */
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.avatar-video-small {
  width: 100%;
  height: 100%;
}

.avatar-video-small-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #2c7be5;
  font-size: 20px;
  font-weight: bold;
}

/* === 聊天区域 === */
.chat-section {
  flex: 1; /* 最核心：吃掉所有剩余空间，自动伸缩 */
  background-color: #f2f2f2;
  display: flex;
  flex-direction: column;
  min-height: 0; /* 必须，防止 flex 撑破屏幕 */
  overflow: hidden;
}

.chat-scroll {
  flex: 1;
  height: 0;
  min-height: 0;
  padding: 15px;
  box-sizing: border-box;
  overflow: hidden;
}

.message-list {
  display: flex;
  flex-direction: column;
}

.message {
  margin-bottom: 15px;
  max-width: 80%;
}
.message text {
  display: inline-block;
  padding: 10px 15px;
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.4;
}

.message.system {
  align-self: center;
  max-width: 90%;
}
.message.system text {
  background-color: rgba(0,0,0,0.05);
  color: #666;
  font-size: 12px;
}

.message.user {
  align-self: flex-end;
}
.message.user text {
  background-color: #007AFF;
  color: white;
  border-bottom-right-radius: 0;
}

.message.ai,
.message.assistant {
  align-self: flex-start;
}
.message.ai text,
.message.assistant text {
  background-color: white;
  color: #333;
  border-bottom-left-radius: 0;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

/* 正在思考动画 */
.message.assistant .thinking {
  color: #999;
  font-style: italic;
  animation: blink 1.2s ease-in-out infinite;
}
@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.bottom-padding {
  height: 12px;
}

/* 输入框 */
.answer-mode-tabs {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  align-self: center;
  gap: 4px;
  padding: 4px;
  margin: 6px 0 0;
  background: #edf2f7;
  border-radius: 999px;
}
.answer-mode-tab {
  min-width: 72px;
  height: 28px;
  line-height: 28px;
  text-align: center;
  border-radius: 999px;
  color: #64748b;
  font-size: 13px;
}
.answer-mode-tab.active {
  background: #007AFF;
  color: #fff;
  font-weight: 600;
  box-shadow: 0 2px 6px rgba(0, 122, 255, 0.24);
}
.input-area {
  flex: 0 0 auto;
  min-height: 60px;
  background-color: white;
  display: flex;
  align-items: center;
  padding: 8px 12px calc(8px + env(safe-area-inset-bottom));
  box-sizing: border-box;
  box-shadow: 0 -2px 5px rgba(0,0,0,0.02);
}
.mode-toggle {
  width: 36px;
  height: 36px;
  display: flex;
  justify-content: center;
  align-items: center;
  background: #f5f5f5;
  border-radius: 18px;
  margin-right: 10px;
  font-size: 18px;
}
.chat-input {
  flex: 1;
  height: 36px;
  background-color: #f5f5f5;
  border-radius: 18px;
  padding: 0 15px;
  font-size: 14px;
}
.send-btn {
  margin-left: 10px;
  background-color: #007AFF;
  color: white;
  font-size: 14px;
  height: 36px;
  line-height: 36px;
  border-radius: 18px;
  padding: 0 15px;
}
.voice-btn {
  flex: 1;
  height: 36px;
  line-height: 36px;
  background-color: #f5f5f5;
  color: #333;
  font-size: 14px;
  border-radius: 18px;
  text-align: center;
  margin: 0;
}
.voice-btn::after {
  border: none;
}
.voice-btn.recording {
  background-color: #e5e5e5;
  color: #666;
}

/* 纪念卡分享按钮 */
.share-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #4e8cf5, #2563eb);
  border-radius: 18px;
  margin-left: 8px;
  flex-shrink: 0;
}
.share-btn-icon {
  font-size: 18px;
  line-height: 1;
}
</style>
