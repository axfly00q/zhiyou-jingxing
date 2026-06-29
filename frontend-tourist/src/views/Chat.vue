<template>
  <div class="layout">
    <div class="avatar-pane" :class="{ 'night-mode': isNightMode }">
      <!-- 基础白天背景图 -->
      <div class="bg-day"></div>
      <!-- 梵夜：多层CSS夜景（通过不透明度平滑过渡） -->
      <div class="bg-night">
        <!-- 星空层 -->
        <div class="night-stars"></div>
        <!-- 月亮 -->
        <div class="night-moon"></div>
        <!-- 远山轮廓 -->
        <div class="night-mountains"></div>
        <!-- 寺庙建筑轮廓 -->
        <div class="night-temple"></div>
        <!-- 月光倒影光柱 -->
        <div class="night-moonbeam"></div>
      </div>
      <!-- 流体光晕特效层（酥油灯 + 灯笼） -->
      <div class="fluid-lights" v-if="isNightMode">
        <div class="butter-lamp lamp-1"></div>
        <div class="butter-lamp lamp-2"></div>
        <div class="butter-lamp lamp-3"></div>
        <div class="butter-lamp lamp-4"></div>
        <!-- 红灯笼光晕 -->
        <div class="red-lantern rl-1"></div>
        <div class="red-lantern rl-2"></div>
        <div class="red-lantern rl-3"></div>
        <!-- 飘动萤火 -->
        <div class="firefly ff-1"></div>
        <div class="firefly ff-2"></div>
        <div class="firefly ff-3"></div>
        <div class="firefly ff-4"></div>
        <div class="firefly ff-5"></div>
      </div>

      <VrmAvatar
        ref="avatarRef"
        class="vrm-fill"
        :model-url="effectiveModelUrl"
        :audio-url="currentAudioUrl"
        :emotion="currentEmotion"
        :motion="currentMotion"
        :motions="motionsMap"
      />
      <!-- B3: 互动电子木鱼 (等待响应时显示) -->
      <Muyu v-if="loading" :park-code="parkCode" />

      <div class="top-bar">
        <strong class="title">{{ parkName }}</strong>
        <div class="top-bar-right">
          <button class="theme-toggle-btn" @click="isNightMode = !isNightMode">
            {{ isNightMode ? '梵夜 🌙' : '晨雾 🌤️' }}
          </button>
          <button class="end-tour-btn" @click="startEndFlow">结束游览</button>
          <a href="#/preference" class="back">← 重新规划</a>
        </div>
      </div>
      <button class="interrupt-btn" @click="onInterrupt" title="打断播报">⏸</button>
    </div>

    <!-- 下：对话面板 -->
    <div class="chat-pane">
      <!-- B2: 路线进度条（有路线时显示） -->
      <RouteBar
        v-if="routeSpots.length"
        :spots="routeSpots"
        :current-idx="currentSpotIdx"
        :total-minutes="routeTotalMinutes"
        :elapsed-minutes="elapsedMinutes"
        @checkin="handleCheckin"
      />

      <!-- D2: 景区平面地图（可折叠，默认收起） -->
      <div v-if="parkCode === 'lingshan' && routeSpots.length" class="map-section">
        <div class="map-toggle" @click="mapExpanded = !mapExpanded">
          <span>🗺 景区平面图</span>
          <span class="map-arrow">{{ mapExpanded ? '▲' : '▼' }}</span>
        </div>
        <ParkMap
          v-if="mapExpanded"
          :park-code="parkCode"
          :spots="routeSpots"
          :current-idx="currentSpotIdx"
        />
      </div>

      <div class="messages" ref="msgBox">
        <div v-for="(m, i) in messages" :key="i" :class="['msg', m.role]">
          <div class="bubble">
            <div>{{ m.content }}</div>
            <div v-if="m.citations && m.citations.length" class="cites">
              出处：<span v-for="(c, idx) in m.citations" :key="idx">「{{ c.title }}」 </span>
            </div>
          </div>
        </div>
        <div v-if="loading && !messages[messages.length-1]?.content" class="msg assistant"><div class="bubble">正在思考…</div></div>
      </div>

      <!-- 预设问题 chips -->
      <div class="presets">
        <button v-if="arrivalPrompt" class="chip" @click="sendPreset(arrivalPrompt)">{{ arrivalPrompt }}</button>
        <button v-for="(q, i) in presets" :key="i" class="chip" @click="sendPreset(q)">{{ q }}</button>
      </div>

      <div class="chat-input-area">
        <div class="answer-mode-tabs">
          <div :class="['mode-tab', { active: answerMode === 'fast' }]" @click="setAnswerMode('fast')">
            <span class="icon">⚡</span> 精简版 · 5秒内
          </div>
          <div :class="['mode-tab', { active: answerMode === 'detailed' }]" @click="setAnswerMode('detailed')">
            <span class="icon">📖</span> 详细版 · 完整讲解
          </div>
        </div>

        <div class="input-bar" :class="{ 'voice-mode': isVoiceMode }">
          <div class="mode-toggle" @click="isVoiceMode = !isVoiceMode">
            <span>{{ isVoiceMode ? '⌨️' : '🎤' }}</span>
          </div>
          <textarea v-model="input"
                    :placeholder="isVoiceMode ? '语音识别文字会显示在这里…' : '输入问题…'"
                    @keydown.enter.exact.prevent="send" rows="2"></textarea>
          <div class="btn-col">
            <template v-if="!isVoiceMode">
              <button class="btn primary" :disabled="loading || !input.trim()" @click="send">发送</button>
            </template>
            <template v-else>
              <button class="voice-btn" :class="{ recording }"
                      @mousedown="startRec" @mouseup="stopRec"
                      @touchstart.prevent="startRec" @touchend.prevent="stopRec">
                {{ recording ? '🎤·说话中...' : '🎤 按住说话' }}
              </button>
            </template>
          </div>
        </div>
        <div v-if="voiceError" class="voice-error">{{ voiceError }}</div>
      </div>
    </div>

    <!-- 结束游览弹窗组 -->
    <QuizModal
      v-if="showQuiz"
      :spots="quizSpots"
      :session-id="sessionId"
      :park-code="parkCode"
      @complete="onQuizComplete"
      @skip="onQuizSkip"
    />
    <RatingModal
      v-if="showRating"
      :session-id="sessionId"
      :park-code="parkCode"
      :visited-spots="visitedNames"
      :elapsed-minutes="elapsedMinutes"
      @done="onRatingDone"
    />
    <BadgeModal
      v-if="showBadge"
      :badge="pendingBadge"
      @close="showBadge = false"
    />
    <ShareCard
      v-if="showShare"
      :session-id="sessionId"
      :park-code="parkCode"
      :visited-spots="visitedNames"
      :elapsed-minutes="elapsedMinutes"
      @close="showShare = false"
    />
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'
import { chatCheckin, chatText, getAvatarStream, getChatPref, getChatSuggestions, interrupt } from '../api.js'
import RouteBar from '../components/RouteBar.vue'
import ParkMap from '../components/ParkMap.vue'
import VrmAvatar from '../components/VrmAvatar.vue'
import RatingModal from '../components/RatingModal.vue'
import BadgeModal from '../components/BadgeModal.vue'
import QuizModal from '../components/QuizModal.vue'
import ShareCard from '../components/ShareCard.vue'
import Muyu from '../components/Muyu.vue'

// 未上传 VRM 时的 demo 资产（three-vrm 官方示例，CDN）
// 生产环境请到 admin 后台上传自己的 .vrm
const SAMPLE_VRM_URL = 'https://cdn.jsdelivr.net/gh/pixiv/three-vrm@release/packages/three-vrm/examples/models/VRM1_Constraint_Twist_Sample.vrm'

const parkName = sessionStorage.getItem('park_name') || '灵山胜境'
const parkCode = sessionStorage.getItem('park') || 'lingshan'
const mapExpanded = ref(false)

// 日夜模式状态
const isNightMode = ref(false)

// 结束游览弹窗状态
const showQuiz = ref(false)
const showRating = ref(false)
const showBadge = ref(false)
const showShare = ref(false)
const pendingBadge = ref(null)
const quizSpots = ref([])

// 路线状态（从 sessionStorage 加载）
const routeData = JSON.parse(sessionStorage.getItem('route') || 'null')
const routeSpots = ref((routeData?.spots) || [])
const routeTotalMinutes = ref(routeData?.total_minutes || 0)
const currentSpotIdx = ref(0)           // 打卡后才向前推进
const routeStartTime = ref(Date.now())
const elapsedMinutes = ref(0)
let elapsedTimer = null

// 已游览 / 剩余景点名称（用于上下文注入）
const visitedNames = computed(() =>
  routeSpots.value.slice(0, currentSpotIdx.value).map(s => s.name)
)
const remainingNames = computed(() =>
  routeSpots.value.slice(currentSpotIdx.value).map(s => s.name)
)
// 从偏好设置页静态标签初始化
function _initPrefSummary() {
  const stored = sessionStorage.getItem('preferences_summary')
  if (stored) return stored
  const pref = JSON.parse(sessionStorage.getItem('pref') || '{}')
  const labels = { history: '历史人文', nature: '自然风光', architecture: '建筑艺术', family: '亲子', photo: '摄影打卡' }
  return Object.entries(labels).filter(([k]) => (pref[k] || 0) >= 0.6).map(([, v]) => v).join('、') || ''
}
const preferencesSummary = ref(_initPrefSummary())

// 轮询偏好更新（在每次发送消息后延迟调用）
async function _pollPref() {
  try {
    const { preferences_summary } = await getChatPref(sessionId.value)
    if (preferences_summary && preferences_summary !== preferencesSummary.value) {
      preferencesSummary.value = preferences_summary
      sessionStorage.setItem('preferences_summary', preferences_summary)
    }
  } catch (e) { /* 静默失败 */ }
}

// 组装 route_context 上下文（每条消息带过去）
const buildRouteContext = () => {
  if (!routeSpots.value.length) return undefined
  const cur = routeSpots.value[currentSpotIdx.value]
  return {
    current_spot_code: cur?.code || null,
    current_spot_name: cur?.name || null,
    visited_names: visitedNames.value,
    remaining_names: remainingNames.value,
    total_minutes: routeTotalMinutes.value,
    elapsed_minutes: elapsedMinutes.value,
    preferences_summary: preferencesSummary.value || null,
  }
}

const currentRouteSpot = computed(() => routeSpots.value[currentSpotIdx.value] || null)
const arrivalPrompt = computed(() => {
  const spot = currentRouteSpot.value
  return spot ? `我已到达${spot.name}，请用一句话补充一个有趣的小知识或观赏建议。` : ''
})

const ARRIVAL_PATTERNS = [
  /\u6211.*\u5230.*\u4e86/,
  /\u5df2.*\u5230/,
  /\u5df2\u7ecf.*\u5230/,
  /\u5230\u8fbe/,
  /\u62b5\u8fbe/,
  /\u6765\u5230/,
  /\u5230\u4e86/,
  /\u5230\u8fd9\u91cc\u4e86/,
  /\u5230\u8fd9\u4e86/,
]
const ARRIVAL_HINTS = ['\u8fd9\u91cc', '\u8fd9\u513f', '\u8fd9\u4e86', '\u5f53\u524d']

function getCurrentRouteSpot() {
  return currentRouteSpot.value
}

function isArrivalMessage(text) {
  const spot = getCurrentRouteSpot()
  const normalized = String(text || '').trim()
  if (!spot || !normalized) return false

  const hasArrivalIntent = ARRIVAL_PATTERNS.some(pattern => pattern.test(normalized))
  if (!hasArrivalIntent) return false

  const mentionsCurrentSpot = spot.name && normalized.includes(spot.name)
  const mentionsHere = ARRIVAL_HINTS.some(hint => normalized.includes(hint))
  return mentionsCurrentSpot || mentionsHere || normalized.length <= 12
}

function advanceRouteToSpot(spotCode) {
  const prevIdx = currentSpotIdx.value
  const spotIdx = routeSpots.value.findIndex(spot => spot.code === spotCode)
  if (spotIdx < 0 || spotIdx < currentSpotIdx.value) {
    return { advanced: false, prevIdx }
  }
  currentSpotIdx.value = Math.min(spotIdx + 1, routeSpots.value.length)
  return { advanced: currentSpotIdx.value !== prevIdx, prevIdx }
}
// Web Speech API（TTS Tier-3 保底）
const synth = window.speechSynthesis ?? null
const sessionId = ref(crypto.randomUUID().slice(0, 16))
const messages = ref([])
const input = ref('')
const loading = ref(false)
const recording = ref(false)
const isVoiceMode = ref(false)
const voiceError = ref('')
const answerMode = ref(sessionStorage.getItem('answer_mode') || 'fast')
const msgBox = ref(null)
const avatarRef = ref(null)

// VRM 数字人状态
const avatar = reactive({
  code: '',
  name: '',
  model_url: '',
  voice_id: '',
  default_motion: 'idle',
})
const currentAudioUrl = ref('')
const currentEmotion = ref('neutral')
const currentMotion = ref('idle')

// 预设问题（从 hot-questions 接口动态加载，兜底保留静态提示）
const presets = ref(['这里最佳拍照点？', '讲讲历史', '下一站是哪里？', '门票怎么购买？'])

// 最终传给 VRM 的 model URL：优先后台配置，其次 sample
const effectiveModelUrl = computed(() => avatar.model_url || SAMPLE_VRM_URL)

// 预制动作映射（仅在后台配置了 avatar.code 时才预加载；
// sample 模型不带动作，会退化到静态 idle，不影响显示）
const motionsMap = computed(() => {
  if (!avatar.code) return {}
  const base = `/static/avatars/${avatar.code}/motions`
  return {
    idle: `${base}/idle.vrma`,
    wave: `${base}/wave.vrma`,
    explain: `${base}/explain.vrma`,
    think: `${base}/think.vrma`,
    beckon: `${base}/beckon.vrma`,
    bow: `${base}/bow.vrma`,
    clap: `${base}/clap.vrma`,
    goodbye: `${base}/goodbye.vrma`,
    listen: `${base}/listen.vrma`,
    point: `${base}/point.vrma`,
    shrug: `${base}/shrug.vrma`,
  }
})

let mediaRecorder = null
let chunks = []
let browserSpeechRecognition = null
let browserSpeechText = ''
let voiceBaseInput = ''
// 麦克风音量检测（代替摄像头：说话时让数字人“听”的反馈）
let audioCtx = null
let analyser = null
let rmsTimer = 0
let prevMotion = 'idle'

function getSpeechRecognitionCtor() {
  return window.SpeechRecognition || window.webkitSpeechRecognition
}

function applyVoiceTranscript(text) {
  const transcript = String(text || '').trim()
  if (!transcript) return false
  input.value = voiceBaseInput ? `${voiceBaseInput} ${transcript}` : transcript
  return true
}

function startBrowserSpeechRecognition() {
  const SpeechRecognition = getSpeechRecognitionCtor()
  browserSpeechText = ''
  if (!SpeechRecognition) return false

  try {
    const recognition = new SpeechRecognition()
    recognition.lang = 'zh-CN'
    recognition.continuous = false
    recognition.interimResults = true
    recognition.maxAlternatives = 1
    recognition.onresult = (event) => {
      let transcript = ''
      for (let i = 0; i < event.results.length; i++) {
        transcript += event.results[i][0]?.transcript || ''
      }
      browserSpeechText = transcript.trim()
      if (applyVoiceTranscript(browserSpeechText)) {
        voiceError.value = ''
      }
    }
    recognition.onerror = (event) => {
      console.warn('browser speech recognition failed', event?.error || event)
    }
    recognition.onend = () => {
      browserSpeechRecognition = null
    }
    browserSpeechRecognition = recognition
    recognition.start()
    return true
  } catch (e) {
    browserSpeechRecognition = null
    console.warn('browser speech recognition unavailable', e)
    return false
  }
}

function stopBrowserSpeechRecognition() {
  if (!browserSpeechRecognition) return
  try { browserSpeechRecognition.stop() } catch (e) {}
}

function wait(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

onMounted(async () => {
  // 启动已用时间计时器
  if (routeSpots.value.length) {
    elapsedTimer = setInterval(() => {
      elapsedMinutes.value = Math.floor((Date.now() - routeStartTime.value) / 60000)
    }, 30000)
  }

  try {
    const r = await getAvatarStream({ session_id: sessionId.value })
    sessionId.value = r.session_id
    Object.assign(avatar, {
      code: r.avatar_code || '',
      name: r.name || '',
      model_url: r.model_url || '',
      voice_id: r.voice_id || '',
      default_motion: r.default_motion || 'idle',
    })
    currentMotion.value = avatar.default_motion
  } catch (e) {
    console.warn('avatar config load failed', e)
  }

  // 拉取该园区近7天 Top5 热门问题作为预设 chips
  try {
    const hot = await getChatSuggestions(parkCode || undefined, 5)
    if (hot && hot.length) {
      presets.value = hot.map(h => h.question)
    }
  } catch (e) {
    console.warn('chat suggestions load failed', e)
  }

  if (routeData?.narrative) {
    push('assistant', routeData.narrative)
    currentEmotion.value = 'joy'
    currentMotion.value = 'wave'
  } else {
    push('assistant', `欢迎来到${parkName}！请问想了解什么？`)
    currentEmotion.value = 'joy'
    currentMotion.value = 'wave'
  }
})

onUnmounted(() => {
  if (elapsedTimer) clearInterval(elapsedTimer)
})

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

function push(role, content, citations = []) {
  if (role === 'assistant') content = cleanAssistantText(content)
  messages.value.push({ role, content, citations })
  nextTick(() => { msgBox.value && (msgBox.value.scrollTop = msgBox.value.scrollHeight) })
}

function setAnswerMode(mode) {
  answerMode.value = mode
  sessionStorage.setItem('answer_mode', mode)
}

function applyResponse(r) {
  const answer = cleanAssistantText(r.answer)
  push('assistant', answer, r.citations)
  currentEmotion.value = r.emotion || 'neutral'
  currentMotion.value = r.motion || avatar.default_motion || 'idle'
  if (r.new_route) {
    routeSpots.value = r.new_route.spots || []
    routeTotalMinutes.value = r.new_route.total_minutes || 0
    currentSpotIdx.value = 0
    sessionStorage.setItem('route', JSON.stringify(r.new_route))
  }
  if (r.audio_url) {
    const sep = r.audio_url.startsWith('data:') ? '' : (r.audio_url.includes('?') ? '&' : '?')
    currentAudioUrl.value = r.audio_url + (sep ? `${sep}t=${Date.now()}` : '')
  } else {
    currentAudioUrl.value = ''
    // TTS Tier-3：CosyVoice2 与 Tier-2 均不可用时，用浏览器内置 TTS 朗读
    if (synth && answer) {
      const utt = new SpeechSynthesisUtterance(answer)
      utt.lang = 'zh-CN'
      synth.cancel()
      synth.speak(utt)
    }
  }
}

async function send() {
  const text = input.value.trim()
  if (!text || loading.value) return
  synth?.cancel()
  push('user', text)
  input.value = ''

  if (isArrivalMessage(text)) {
    const spot = getCurrentRouteSpot()
    if (spot?.code) {
      await handleCheckin(spot.code)
      return
    }
  }

  loading.value = true

  // 流式占位气泡
  const msgIdx = messages.value.length
  messages.value.push({ role: 'assistant', content: '', citations: [] })
  nextTick(() => { msgBox.value && (msgBox.value.scrollTop = msgBox.value.scrollHeight) })

  try {
    const resp = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId.value,
        message: text,
        avatar_code: avatar.code || undefined,
        park_code: parkCode || undefined,
        route_context: buildRouteContext(),
        answer_mode: answerMode.value,
      }),
    })
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)

    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let sseBuffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      sseBuffer += decoder.decode(value, { stream: true })
      const lines = sseBuffer.split('\n')
      sseBuffer = lines.pop()           // 保留未完整的行

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        let evt
        try { evt = JSON.parse(line.slice(6)) } catch { continue }

        if (evt.type === 'token') {
          messages.value[msgIdx].content = cleanAssistantText(messages.value[msgIdx].content + evt.text)
          nextTick(() => { msgBox.value && (msgBox.value.scrollTop = msgBox.value.scrollHeight) })
        } else if (evt.type === 'done') {
          currentEmotion.value = evt.emotion || 'neutral'
          currentMotion.value = evt.motion || avatar.default_motion || 'idle'
          if (evt.new_route) {
            routeSpots.value = evt.new_route.spots || []
            routeTotalMinutes.value = evt.new_route.total_minutes || 0
            currentSpotIdx.value = 0
            sessionStorage.setItem('route', JSON.stringify(evt.new_route))
          }
          if (evt.audio_url) {
            const sep = evt.audio_url.includes('?') ? '&' : '?'
            currentAudioUrl.value = evt.audio_url + sep + 't=' + Date.now()
          } else {
            currentAudioUrl.value = ''
            const speechText = cleanAssistantText(messages.value[msgIdx].content)
            messages.value[msgIdx].content = speechText
            if (synth && speechText) {
              const utt = new SpeechSynthesisUtterance(speechText)
              utt.lang = 'zh-CN'; synth.cancel(); synth.speak(utt)
            }
          }
        }
      }
    }
    setTimeout(_pollPref, 1000)
  } catch (e) {
    if (!messages.value[msgIdx]?.content) {
      messages.value[msgIdx] = { role: 'assistant', content: '抱歉，服务暂时不可用。', citations: [] }
    }
  } finally {
    loading.value = false
  }
}

// B2: 打卡处理
async function handleCheckin(spotCode) {
  if (loading.value) return
  const routeContext = buildRouteContext()
  const progress = advanceRouteToSpot(spotCode)
  loading.value = true
  try {
    const r = await chatCheckin({
      session_id: sessionId.value,
      spot_code: spotCode,
      park_code: parkCode,
      avatar_code: avatar.code || undefined,
      route_context: routeContext,
      answer_mode: answerMode.value,
    })
    // 展示景点介绍
    const narrative = cleanAssistantText(r.narrative)
    push('assistant', narrative)
    currentEmotion.value = r.emotion || 'joy'
    currentMotion.value = r.motion || 'wave'
    if (r.audio_url) {
      currentAudioUrl.value = r.audio_url + (r.audio_url.includes('?') ? '&' : '?') + 't=' + Date.now()
    }
    // 推进进度
    // 处理成就徽章
    if (r.badge) {
      pendingBadge.value = r.badge
      showBadge.value = true
    }
    // 提示下一站
    if (r.next_spot_name) {
      const walkTip = r.next_walk_minutes ? `，步行约 ${r.next_walk_minutes} 分钟` : ''
      push('assistant', `→ 下一站：${r.next_spot_name}${walkTip}`)
    } else if (currentSpotIdx.value >= routeSpots.value.length) {
      push('assistant', '🎉 路线全部完成！您已游遍所有景点，希望本次游览令您尽兴而归！')
    }
  } catch (e) {
    if (progress.advanced) {
      currentSpotIdx.value = progress.prevIdx
    }
    push('assistant', '打卡失败，请稍后重试。')
  } finally {
    loading.value = false
  }
}

function sendPreset(q) {
  if (loading.value) return
  input.value = q
  send()
}

async function startRec() {
  if (recording.value) return
  voiceError.value = ''
  browserSpeechText = ''
  voiceBaseInput = input.value.trim()
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    mediaRecorder = new MediaRecorder(stream)
    chunks = []
    mediaRecorder.ondataavailable = (e) => chunks.push(e.data)
    mediaRecorder.onstop = uploadAudio
    mediaRecorder.start()
    recording.value = true
    const browserStarted = startBrowserSpeechRecognition()
    if (!browserStarted) {
      voiceError.value = '浏览器语音识别不可用，将使用后端识别。'
    }
    // 启动音量检测，驱动数字人“在听”反馈
    try {
      audioCtx = new (window.AudioContext || window.webkitAudioContext)()
      const src = audioCtx.createMediaStreamSource(stream)
      analyser = audioCtx.createAnalyser()
      analyser.fftSize = 1024
      src.connect(analyser)
      const buf = new Uint8Array(analyser.fftSize)
      prevMotion = currentMotion.value
      rmsTimer = setInterval(() => {
        analyser.getByteTimeDomainData(buf)
        let sum = 0
        for (let i = 0; i < buf.length; i++) {
          const v = (buf[i] - 128) / 128
          sum += v * v
        }
        const rms = Math.sqrt(sum / buf.length)
        if (rms > 0.05) {
          currentEmotion.value = 'joy'
          // 有 listen 动作则用，否则 idle 加微笑
          if (motionsMap.value.listen) currentMotion.value = 'listen'
        }
      }, 100)
    } catch (e) { console.warn('audio analyser init failed', e) }
  } catch (e) {
    alert('无法访问麦克风：' + e.message)
  }
}

function stopRec() {
  if (!recording.value) return
  recording.value = false
  stopBrowserSpeechRecognition()
  try { mediaRecorder?.stop() } catch (e) {}
  if (rmsTimer) { clearInterval(rmsTimer); rmsTimer = 0 }
  if (audioCtx) { try { audioCtx.close() } catch (_) {} audioCtx = null; analyser = null }
  currentMotion.value = prevMotion || avatar.default_motion || 'idle'
}

async function uploadAudio() {
  await wait(600)
  if (applyVoiceTranscript(browserSpeechText)) {
    isVoiceMode.value = false
    voiceError.value = ''
    return
  }

  const blob = new Blob(chunks, { type: 'audio/webm' })
  const fd = new FormData()
  fd.append('session_id', sessionId.value)
  fd.append('audio', blob, 'recording.webm')
  loading.value = true
  try {
    const resp = await fetch('/api/chat/transcribe', { method: 'POST', body: fd })
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    const r = await resp.json()
    const text = String(r?.text || '').trim()
    if (!text) throw new Error('empty transcript')
    input.value = input.value.trim() ? `${input.value.trim()} ${text}` : text
    isVoiceMode.value = false
    voiceError.value = ''
  } catch (e) {
    voiceError.value = '语音识别失败，请再说一次。'
  } finally {
    loading.value = false
  }
}

async function onInterrupt() {
  synth?.cancel()
  try { avatarRef.value?.stop() } catch (e) {}
  try { await interrupt(sessionId.value) } catch (e) {}
}

// 结束游览流程：先测验 → 再评分 → 再分享
function startEndFlow() {
  // 收集已访问景点中有 quiz 的
  const visited = routeSpots.value.slice(0, currentSpotIdx.value)
  const withQuiz = visited.filter(s => s.quiz && s.quiz.length > 0)
  quizSpots.value = withQuiz
  if (withQuiz.length > 0) {
    showQuiz.value = true
  } else {
    showRating.value = true
  }
}

function onQuizComplete() {
  showQuiz.value = false
  showRating.value = true
}

function onQuizSkip() {
  showQuiz.value = false
  showRating.value = true
}

function onRatingDone() {
  showRating.value = false
  showShare.value = true
}
</script>

<style scoped>
/* 竖屏主布局（默认 1080×1920）：上 60vh 数字人，下 40vh 对话 */
.layout {
  display: flex;
  flex-direction: row;
  width: 100%;
  height: 100vh;
  height: 100dvh;
  background: #0f1220;
  overflow: hidden;
}

.avatar-pane {
  position: relative;
  flex: 0 0 45%;
  overflow: hidden;
}

.bg-day, .bg-night {
  position: absolute;
  inset: 0;
  transition: opacity 2.5s cubic-bezier(0.4, 0, 0.2, 1);
  z-index: 0;
}
.bg-day {
  background-image: url('/images/lingshan_arch.png');
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  opacity: 1;
}
.night-mode .bg-day {
  opacity: 0;
}
.bg-night {
  background: linear-gradient(180deg,
    #01030c 0%,
    #050e25 20%,
    #091a40 45%,
    #0f2350 70%,
    #152a50 100%
  );
  opacity: 0;
  overflow: hidden;
}
.night-mode .bg-night {
  opacity: 1;
}

/* 星空 */
.night-stars {
  position: absolute;
  inset: 0;
  background-image:
    radial-gradient(circle, rgba(255,255,255,0.95) 1px, transparent 1px),
    radial-gradient(circle, rgba(255,255,255,0.75) 1px, transparent 1px),
    radial-gradient(circle, rgba(200,210,255,0.65) 1px, transparent 1px),
    radial-gradient(circle, rgba(255,255,255,0.85) 1.5px, transparent 1.5px),
    radial-gradient(circle, rgba(220,220,255,0.5) 1px, transparent 1px);
  background-size: 180px 180px, 280px 280px, 140px 140px, 350px 350px, 220px 220px;
  background-position: 23px 35px, 75px 8px, 145px 75px, 40px 120px, 200px 55px;
  animation: stars-drift 80s linear infinite;
}
@keyframes stars-drift {
  0%   { transform: translateX(0px); }
  100% { transform: translateX(-180px); }
}

/* 月亮 */
.night-moon {
  position: absolute;
  top: 7%;
  right: 16%;
  width: 75px;
  height: 75px;
  border-radius: 50%;
  background: radial-gradient(circle at 38% 38%,
    #fffef5 0%,
    #fffce8 30%,
    #fff3c0 65%,
    #fde68a 90%,
    #fbbf24 100%
  );
  box-shadow:
    0 0 0 4px rgba(253, 230, 138, 0.15),
    0 0 25px 12px rgba(255, 240, 130, 0.30),
    0 0 70px 35px rgba(255, 215, 80, 0.15),
    0 0 140px 70px rgba(255, 200, 50, 0.06);
  animation: moon-glow 7s ease-in-out infinite alternate;
}
@keyframes moon-glow {
  0%   { box-shadow: 0 0 25px 12px rgba(255,240,130,0.30), 0 0 70px 35px rgba(255,215,80,0.15); }
  100% { box-shadow: 0 0 35px 18px rgba(255,248,150,0.45), 0 0 90px 45px rgba(255,225,90,0.22); }
}

/* 远山剪影 */
.night-mountains {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 58%;
  background-color: #060f28;
  clip-path: polygon(
    0% 100%, 0% 60%,
    4% 44%, 10% 30%, 17% 18%,
    24% 26%, 30% 38%,
    37% 22%, 44% 12%,
    50% 8%,
    56% 14%, 63% 26%,
    70% 16%, 77% 6%,
    84% 16%, 91% 30%,
    96% 42%, 100% 50%,
    100% 100%
  );
  opacity: 0.95;
}

/* 寺庙建筑剪影 */
.night-temple {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 65%;
  pointer-events: none;
}

/* 主殿轮廓 */
.night-temple::before {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 52%;
  height: 88%;
  background-color: #04091d;
  clip-path: polygon(
    0% 100%, 0% 78%,
    6% 76%, 6% 70%,
    2% 68%, 14% 60%, 86% 60%, 98% 68%, 94% 70%,
    94% 63%,
    10% 63%, 10% 55%, 90% 55%, 90% 63%,
    88% 61%, 20% 52%, 80% 52%,
    18% 52%, 18% 44%, 82% 44%, 82% 52%,
    80% 50%, 26% 40%, 74% 40%,
    24% 40%, 24% 32%, 76% 32%, 76% 40%,
    73% 38%, 32% 28%, 68% 28%,
    50% 6%,
    100% 78%, 100% 100%
  );
  filter: drop-shadow(0 -4px 16px rgba(255,150,30,0.18)) drop-shadow(0 0 8px rgba(255,120,20,0.12));
  opacity: 0.92;
}

/* 左侧塔楼 */
.night-temple::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 7%;
  width: 13%;
  height: 52%;
  background-color: #04091d;
  clip-path: polygon(
    0% 100%, 0% 72%,
    8% 70%, 8% 60%,
    4% 58%, 16% 52%, 84% 52%, 96% 58%, 92% 60%,
    92% 55%, 15% 55%, 15% 48%, 85% 48%, 85% 55%,
    82% 52%, 22% 44%, 78% 44%,
    20% 44%, 20% 36%, 80% 36%, 80% 44%,
    77% 42%, 50% 8%, 23% 42%,
    100% 72%, 100% 100%
  );
  filter: drop-shadow(0 -3px 12px rgba(255,140,20,0.14));
  opacity: 0.88;
}

/* 月光倒影光柱 */
.night-moonbeam {
  position: absolute;
  top: 12%;
  right: 18%;
  width: 5%;
  height: 50%;
  background: linear-gradient(to bottom,
    rgba(255,252,200,0.0) 0%,
    rgba(255,252,200,0.06) 20%,
    rgba(255,248,180,0.11) 55%,
    rgba(255,244,160,0.05) 85%,
    rgba(255,240,140,0.0) 100%
  );
  filter: blur(10px);
  animation: moonbeam-shimmer 5s ease-in-out infinite alternate;
}
@keyframes moonbeam-shimmer {
  0%   { opacity: 0.5; transform: scaleX(1); }
  100% { opacity: 1;   transform: scaleX(1.4); }
}

/* 酥油灯光晕特效 */
.fluid-lights {
  position: absolute;
  inset: 0;
  z-index: 1;
  pointer-events: none;
}
.butter-lamp {
  position: absolute;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(255,195,65,0.65) 0%, rgba(255,150,20,0.3) 35%, rgba(255,100,0,0) 70%);
  opacity: 0;
  animation: lamp-bloom 3.5s cubic-bezier(0.2, 0.8, 0.2, 1) forwards, lamp-breathe 4.5s ease-in-out infinite alternate 3.5s;
}

@keyframes lamp-bloom {
  0%   { transform: scale(0.3); opacity: 0; }
  100% { transform: scale(1);   opacity: 1; }
}
@keyframes lamp-breathe {
  0%   { transform: scale(1);    opacity: 0.55; }
  100% { transform: scale(1.18); opacity: 0.85; }
}

.lamp-1 { bottom: 6%;  left: 12%;  width: 160px; height: 160px; }
.lamp-2 { bottom: 24%; right: 8%;  width: 200px; height: 200px; animation-delay: 0.4s, 3.9s; }
.lamp-3 { top: 40%;   left: 4%;   width: 120px; height: 120px; animation-delay: 0.7s, 4.2s; }
.lamp-4 { top: 20%;   right: 24%; width: 88px;  height: 88px;  animation-delay: 1.0s, 4.5s; }

/* 红灯笼光晕 */
.red-lantern {
  position: absolute;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(255,65,35,0.60) 0%, rgba(240,60,20,0.28) 42%, transparent 72%);
  opacity: 0;
  animation: lamp-bloom 2.8s ease-out forwards, lamp-breathe 3.8s ease-in-out infinite alternate 2.8s;
}
.rl-1 { top: 30%; left: 22%;  width: 58px; height: 58px; animation-delay: 1.3s, 4.1s; }
.rl-2 { top: 38%; right: 27%; width: 48px; height: 48px; animation-delay: 1.7s, 4.5s; }
.rl-3 { bottom: 42%; left: 46%; width: 52px; height: 52px; animation-delay: 2.0s, 4.8s; }

/* 飘动萤火 */
.firefly {
  position: absolute;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: rgba(255, 252, 140, 0.95);
  box-shadow: 0 0 6px 3px rgba(255, 245, 80, 0.55);
  opacity: 0;
  animation: firefly-float 9s ease-in-out infinite;
}
.ff-1 { top: 28%; left: 32%;  animation-delay: 0.0s; }
.ff-2 { top: 42%; left: 58%;  animation-delay: 1.8s; }
.ff-3 { top: 58%; left: 28%;  animation-delay: 3.5s; }
.ff-4 { top: 22%; right: 32%; animation-delay: 2.2s; }
.ff-5 { top: 48%; right: 18%; animation-delay: 4.5s; }

@keyframes firefly-float {
  0%   { opacity: 0;   transform: translate(0,    0px)  scale(0.8); }
  12%  { opacity: 0.9; }
  35%  { opacity: 0.7; transform: translate(14px, -22px) scale(1.3); }
  60%  { opacity: 0.85;transform: translate(-9px, -40px) scale(0.9); }
  82%  { opacity: 0.4; transform: translate(6px,  -56px) scale(1.1); }
  100% { opacity: 0;   transform: translate(0,   -72px)  scale(0.7); }
}

.vrm-fill { position: absolute; inset: 0; z-index: 2; }
.top-bar {
  position: absolute;
  top: env(safe-area-inset-top, 0);
  left: 0; right: 0;
  padding: 16px 20px;
  display: flex; justify-content: space-between; align-items: center;
  color: #fff;
  z-index: 3;
  pointer-events: none;
}
.top-bar .title { font-size: clamp(18px, 3.2vw, 28px); letter-spacing: 1px; }
.top-bar-right {
  display: flex; align-items: center; gap: 10px;
  pointer-events: auto;
}
.theme-toggle-btn {
  pointer-events: auto;
  background: rgba(0,0,0,0.25);
  color: #fff;
  border: 1px solid rgba(255,255,255,0.2);
  padding: 8px 14px;
  border-radius: 999px;
  font-size: clamp(13px, 2vw, 18px);
  cursor: pointer;
  backdrop-filter: blur(8px);
  transition: all 0.3s;
}
.theme-toggle-btn:hover { background: rgba(0,0,0,0.4); }

.top-bar .back {
  pointer-events: auto;
  color: #a8c4ff; text-decoration: none;
  font-size: clamp(13px, 2vw, 18px);
  background: rgba(0,0,0,0.25); padding: 8px 14px; border-radius: 999px;
}
.end-tour-btn {
  pointer-events: auto;
  background: rgba(255,160,0,0.85);
  color: #fff;
  border: none;
  padding: 8px 14px;
  border-radius: 999px;
  font-size: clamp(13px, 2vw, 18px);
  cursor: pointer;
  backdrop-filter: blur(8px);
}
.end-tour-btn:active { background: rgba(255,140,0,0.95); }
.interrupt-btn {
  position: absolute;
  right: 20px; bottom: 20px;
  width: clamp(56px, 8vw, 88px);
  height: clamp(56px, 8vw, 88px);
  border-radius: 50%;
  border: none;
  background: rgba(255,255,255,0.15);
  color: #fff;
  font-size: clamp(20px, 3.5vw, 32px);
  cursor: pointer;
  backdrop-filter: blur(8px);
  z-index: 2;
}
.interrupt-btn:active { background: rgba(255,255,255,0.3); }

.chat-pane {
  flex: 1 1 55%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 0;
  box-shadow: -6px 0 20px rgba(0,0,0,0.25);
  padding-bottom: env(safe-area-inset-bottom, 0);
}

.messages {
  flex: 1; min-height: 0;
  overflow-y: auto;
  padding: 16px 18px;
  -webkit-overflow-scrolling: touch;
}
.msg { margin: 8px 0; display: flex; }
.msg.user { justify-content: flex-end; }
.bubble {
  max-width: 82%;
  padding: 12px 16px;
  border-radius: 14px;
  line-height: 1.55;
  white-space: pre-wrap;
  font-size: clamp(15px, 2.6vw, 20px);
}
.msg.user .bubble { background: #2c7be5; color: #fff; border-bottom-right-radius: 4px; }
.msg.assistant .bubble { background: #f0f2f7; color: #222; border-bottom-left-radius: 4px; }
.cites { font-size: clamp(11px, 1.8vw, 14px); color: #888; margin-top: 6px; }

.presets {
  display: flex;
  gap: 10px;
  padding: 8px 16px 4px;
  overflow-x: auto;
  scroll-snap-type: x mandatory;
  -ms-overflow-style: none;
  scrollbar-width: none;
}
.presets::-webkit-scrollbar { display: none; }
.map-section { flex: 0 0 auto; border-bottom: 1px solid #eee; }
.map-toggle { display: flex; justify-content: space-between; align-items: center; padding: 6px 14px; cursor: pointer; font-size: 13px; color: #555; background: #f8f9fb; user-select: none; }
.map-toggle:hover { background: #eef2f9; }
.map-arrow { color: #999; font-size: 11px; }
.chip {
  flex: 0 0 auto;
  scroll-snap-align: start;
  padding: 10px 16px;
  border: 1px solid #d6e1f5;
  background: #f4f8ff;
  color: #2c7be5;
  border-radius: 999px;
  font-size: clamp(13px, 2.2vw, 17px);
  cursor: pointer;
  white-space: nowrap;
}
.chip:active { background: #e2ecff; }

.chat-input-area {
  flex: 0 0 auto;
  display: flex;
  flex-direction: column;
  padding: 10px 14px 14px;
  border-top: 1px solid #eef0f5;
  background: #fff;
}
.answer-mode-tabs {
  display: flex;
  gap: 16px;
  margin-bottom: 8px;
  padding-left: 4px;
}
.mode-tab {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #888;
  cursor: pointer;
  transition: all 0.2s;
  padding: 4px 8px;
  border-radius: 6px;
}
.mode-tab:hover {
  color: #555;
  background: #f4f8ff;
}
.mode-tab.active {
  color: #2c7be5;
  background: rgba(44,123,229,0.1);
  font-weight: 500;
}
.mode-tab .icon { font-size: 13px; }

.presets {
  display: flex;
  gap: 10px;
  padding: 8px 16px 4px;
  overflow-x: auto;
  scroll-snap-type: x mandatory;
  -ms-overflow-style: none;
  scrollbar-width: none;
}
.presets::-webkit-scrollbar { display: none; }
.map-section { flex: 0 0 auto; border-bottom: 1px solid #eee; }
.map-toggle { display: flex; justify-content: space-between; align-items: center; padding: 6px 14px; cursor: pointer; font-size: 13px; color: #555; background: #f8f9fb; user-select: none; }
.map-toggle:hover { background: #eef2f9; }
.map-arrow { color: #999; font-size: 11px; }
.chip {
  flex: 0 0 auto;
  scroll-snap-align: start;
  padding: 10px 16px;
  border: 1px solid #d6e1f5;
  background: #f4f8ff;
  color: #2c7be5;
  border-radius: 999px;
  font-size: clamp(13px, 2.2vw, 17px);
  cursor: pointer;
  white-space: nowrap;
}
.chip:active { background: #e2ecff; }

.input-bar {
  flex: 0 0 auto;
  padding: 10px 14px 14px;
  border-top: 1px solid #eef0f5;
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 10px;
  align-items: stretch;
}
.input-bar.voice-mode {
  grid-template-columns: auto 1fr auto;
}
.mode-toggle {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: #f4f8ff;
  color: #2c7be5;
  font-size: 20px;
  cursor: pointer;
  align-self: center;
}
.mode-toggle:active { background: #e2ecff; }
textarea {
  resize: none;
  border: 1px solid #ddd;
  border-radius: 10px;
  padding: 10px 12px;
  font-size: clamp(13px, 2.2vw, 18px);
  font-family: inherit;
  outline: none;
}
textarea:focus { border-color: #2c7be5; }
.btn-col { display: flex; flex-direction: column; gap: 6px; }
.btn {
  border: none;
  border-radius: 10px;
  padding: 0 14px;
  min-width: clamp(56px, 8vw, 88px);
  min-height: 40px;
  font-size: clamp(12px, 2vw, 16px);
  cursor: pointer;
}
.btn.primary { background: #2c7be5; color: #fff; }
.btn.primary:disabled { background: #a8c0e8; cursor: not-allowed; }
.btn.ghost { background: #fff; color: #2c7be5; border: 1px solid #2c7be5; }
.btn.ghost:active { background: #f4f8ff; }
.voice-btn {
  border: none;
  border-radius: 10px;
  background: #f4f8ff;
  color: #2c7be5;
  font-size: clamp(14px, 2.5vw, 18px);
  cursor: pointer;
  height: 44px;
  align-self: center;
  border: 1px solid #2c7be5;
}
.voice-btn.recording { background: #e2ecff; color: #1a5bb8; border-color: #1a5bb8; }
.voice-error { margin: 8px 0 0 58px; color: #dc2626; font-size: 13px; }


/* 横屏 / 宽屏（开发机调试）：恢复左右双栏 */
@media (orientation: landscape) and (min-width: 1024px) {
  .layout { flex-direction: row; }
  .avatar-pane { flex: 1 1 50%; min-width: 0; }
  .chat-pane { flex: 1 1 50%; border-radius: 0; box-shadow: none; min-width: 0; overflow: hidden; }
  .top-bar { color: #fff; }
}
</style>
