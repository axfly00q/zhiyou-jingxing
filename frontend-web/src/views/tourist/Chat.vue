<template>
  <div class="layout">
    <div class="bg-layer"></div>
    <div class="dust-particles">
      <div v-for="i in 30" :key="i" class="dust"></div>
    </div>
    <!-- 上：数字人画面 -->
    <div class="avatar-pane" :class="{ 'night-mode': isNightMode }">
      <!-- 基础白天背景图 -->
      <div class="bg-day"></div>
      <!-- 梵夜深蓝背景（通过不透明度平滑过渡） -->
      <div class="bg-night"></div>
      <!-- 流体光晕特效层（酥油灯） -->
      <div class="fluid-lights" v-if="isNightMode">
        <div class="butter-lamp lamp-1"></div>
        <div class="butter-lamp lamp-2"></div>
        <div class="butter-lamp lamp-3"></div>
        <div class="butter-lamp lamp-4"></div>
      </div>

      <div class="avatar-glow"></div>
      <Muyu v-if="parkCode === 'lingshan'" :park-code="parkCode" />
      <VrmAvatar
        ref="avatarRef"
        class="vrm-fill"
        :model-url="effectiveModelUrl"
        :audio-url="currentAudioUrl"
        :emotion="currentEmotion"
        :motion="currentMotion"
        :motions="motionsMap"
        @audio-end="resetMotion"
      />
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

      <!-- D2: 景区实时路线图（可折叠，默认展开） -->
      <div v-if="parkCode === 'lingshan' && routeSpots.length" class="map-section">
        <div class="map-toggle" @click="mapExpanded = !mapExpanded">
          <span>🗺 实时路线图</span>
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
          <div class="bubble" :class="{ 'is-pending': m.pending }">
            <div>{{ m.pending ? '正在思考…' : m.content }}</div>
            <div v-if="m.citations && m.citations.length" class="cites">
              出处：<span v-for="(c, idx) in m.citations" :key="idx">「{{ c.title }}」 </span>
            </div>
          </div>
        </div>
      </div>

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
import { chatCheckin, chatText, getAvatarStream, getChatPref, getChatSuggestions, interrupt } from '../../api.js'
import RouteBar from '../../components/RouteBar.vue'
import ParkMap from '../../components/ParkMap.vue'
import VrmAvatar from '../../components/VrmAvatar.vue'
import Muyu from '../../components/Muyu.vue'
import RatingModal from '../../components/RatingModal.vue'
import BadgeModal from '../../components/BadgeModal.vue'
import QuizModal from '../../components/QuizModal.vue'
import ShareCard from '../../components/ShareCard.vue'

// 未上传 VRM 时的 demo 资产（three-vrm 官方示例，CDN）
// 生产环境请到 admin 后台上传自己的 .vrm
const SAMPLE_VRM_URL = 'https://cdn.jsdelivr.net/gh/pixiv/three-vrm@release/packages/three-vrm/examples/models/VRM1_Constraint_Twist_Sample.vrm'

const parkName = sessionStorage.getItem('park_name') || '灵山胜境'
const parkCode = sessionStorage.getItem('park') || 'lingshan'
const mapExpanded = ref(true)

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

function resetMotion() {
  currentMotion.value = avatar.default_motion || 'idle'
  currentEmotion.value = 'neutral'
}

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
// 麦克风音量检测（代替摄像头：说话时让数字人"听"的反馈）
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

  const startGreeting = (text) => {
    push('assistant', text)
    currentEmotion.value = 'joy'
    currentMotion.value = 'wave'
    setTimeout(resetMotion, 4000)
  }

  if (routeData?.narrative) {
    startGreeting(routeData.narrative)
  } else {
    startGreeting(`欢迎来到${parkName}！请问想了解什么？`)
  }

  // 初始化星尘粒子
  const dusts = document.querySelectorAll('.dust')
  dusts.forEach(dust => {
    dust.style.left = Math.random() * 100 + 'vw'
    dust.style.top = Math.random() * 100 + 'vh'
    dust.style.animationDuration = (Math.random() * 20 + 10) + 's'
    dust.style.animationDelay = (Math.random() * -20) + 's'
  })
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
    if (synth && answer) {
      const utt = new SpeechSynthesisUtterance(answer)
      utt.lang = 'zh-CN'
      utt.onend = resetMotion
      utt.onerror = resetMotion
      synth.cancel()
      synth.speak(utt)
    } else if (!r.audio_url) {
      setTimeout(resetMotion, 4000)
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

  const msgIdx = messages.value.length
  messages.value.push({ role: 'assistant', content: '', citations: [], pending: true })
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
          messages.value[msgIdx].pending = false
          messages.value[msgIdx].content = cleanAssistantText(messages.value[msgIdx].content + evt.text)
          nextTick(() => { msgBox.value && (msgBox.value.scrollTop = msgBox.value.scrollHeight) })
        } else if (evt.type === 'done') {
          messages.value[msgIdx].pending = false
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
              utt.lang = 'zh-CN';
              utt.onend = resetMotion;
              utt.onerror = resetMotion;
              synth.cancel(); synth.speak(utt)
            } else {
              setTimeout(resetMotion, 4000)
            }
          }
        }
      }
    }
    setTimeout(_pollPref, 1000)
  } catch (e) {
    if (!messages.value[msgIdx]?.content) {
      messages.value[msgIdx] = { role: 'assistant', content: '抱歉，服务暂时不可用。', citations: [], pending: false }
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
    } else {
      currentAudioUrl.value = ''
      if (synth && narrative) {
        const utt = new SpeechSynthesisUtterance(narrative)
        utt.lang = 'zh-CN'
        utt.onend = resetMotion
        utt.onerror = resetMotion
        synth.cancel()
        synth.speak(utt)
      } else {
        setTimeout(resetMotion, 4000)
      }
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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Noto+Serif+SC:wght@400;700;900&display=swap');
.serif-font { font-family: 'Noto Serif SC', 'Songti SC', 'STSong', serif; }

.layout { display: flex; flex-direction: row; width: 100%; height: 100vh; height: 100dvh; background: #000; overflow: hidden; font-family: 'Inter', system-ui, sans-serif; position: relative; padding: 2.5vh 2.5vw; gap: 2vw; box-sizing: border-box; }

.bg-layer { position: absolute; top: -10%; left: -10%; right: -10%; bottom: -10%; background-image: url('/images/lingshan_bg.png'); background-size: cover; background-position: center top; filter: brightness(0.3) blur(8px) saturate(1.1); z-index: 0; pointer-events: none; }

.dust-particles { position: absolute; inset: 0; z-index: 1; pointer-events: none; }
.dust { position: absolute; width: 2px; height: 2px; background-color: rgba(234, 179, 8, 0.7); border-radius: 50%; box-shadow: 0 0 6px 2px rgba(234, 179, 8, 0.6); animation: floatUp 18s linear infinite; }
@keyframes floatUp { 0% { transform: translateY(0) scale(1); opacity: 0; } 15% { opacity: 1; } 85% { opacity: 0.8; } 100% { transform: translateY(-110vh) scale(0.5); opacity: 0; } }

.avatar-pane { position: relative; flex: 0 0 calc(45% - 1vw); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 24px; box-shadow: 0 10px 40px rgba(0, 0, 0, 0.4); overflow: hidden; z-index: 2; }

.bg-day, .bg-night { position: absolute; inset: 0; transition: opacity 2.5s cubic-bezier(0.4, 0, 0.2, 1); z-index: 0; }
.bg-day { background-image: url('/images/lingshan_arch.png'); background-size: 100% 100%; background-position: center; background-repeat: no-repeat; opacity: 1; }
.night-mode .bg-day { opacity: 0; }
.bg-night { background: linear-gradient(180deg, #050a1f 0%, #0a1b44 50%, #112d6a 100%); opacity: 0; }
.night-mode .bg-night { opacity: 1; }

.fluid-lights { position: absolute; inset: 0; z-index: 1; pointer-events: none; }
.butter-lamp { position: absolute; border-radius: 50%; background: radial-gradient(circle, rgba(255,180,50,0.8) 0%, rgba(255,150,0,0.4) 30%, rgba(255,100,0,0) 70%); opacity: 0; animation: lamp-bloom 3s cubic-bezier(0.2, 0.8, 0.2, 1) forwards, lamp-breathe 4s ease-in-out infinite alternate 3s; }
@keyframes lamp-bloom { 0% { transform: scale(0.3); opacity: 0; } 100% { transform: scale(1); opacity: 1; } }
@keyframes lamp-breathe { 0% { transform: scale(1); opacity: 0.8; } 100% { transform: scale(1.15); opacity: 1; } }
.lamp-1 { bottom: 5%; left: 15%; width: 180px; height: 180px; }
.lamp-2 { bottom: 25%; right: 10%; width: 220px; height: 220px; animation-delay: 0.3s, 3.3s; }
.lamp-3 { top: 35%; left: 5%; width: 140px; height: 140px; animation-delay: 0.6s, 3.6s; }
.lamp-4 { top: 15%; right: 20%; width: 100px; height: 100px; animation-delay: 0.9s, 3.9s; }

.avatar-pane::before { content: ''; position: absolute; inset: 0; background: linear-gradient(180deg, rgba(255,255,255,0.05) 0%, rgba(5,8,12,0.3) 100%); z-index: 1; pointer-events: none; }
.avatar-glow { position: absolute; bottom: 0; left: 50%; transform: translateX(-50%); width: 90%; height: 60%; background: radial-gradient(ellipse at center bottom, rgba(234,179,8,0.3) 0%, rgba(234,179,8,0.1) 40%, rgba(0,0,0,0) 70%); z-index: 1; pointer-events: none; }

.vrm-fill { position: absolute; inset: 0; z-index: 1; }
.top-bar { position: absolute; top: env(safe-area-inset-top, 0); left: 0; right: 0; padding: 16px 20px; display: flex; justify-content: space-between; align-items: center; color: #fff; z-index: 2; pointer-events: none; }
.top-bar .title { font-family: 'Noto Serif SC', serif; font-size: clamp(18px, 3.2vw, 28px); letter-spacing: 1px; text-shadow: 0 2px 4px rgba(0,0,0,0.8); }
.top-bar-right { display: flex; align-items: center; gap: 12px; pointer-events: auto; }
.theme-toggle-btn { pointer-events: auto; background: rgba(255,255,255,0.1); color: #fdf6e3; border: 1px solid rgba(255,255,255,0.15); padding: 8px 16px; border-radius: 999px; font-size: clamp(13px, 2vw, 15px); cursor: pointer; backdrop-filter: blur(12px); transition: all 0.3s; }
.theme-toggle-btn:hover { background: rgba(255,255,255,0.2); }
.top-bar .back { pointer-events: auto; color: #fdf6e3; text-decoration: none; font-size: clamp(13px, 2vw, 15px); background: rgba(255,255,255,0.1); padding: 8px 16px; border-radius: 999px; backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.15); transition: all 0.3s; }
.top-bar .back:hover { background: rgba(255,255,255,0.2); }
.end-tour-btn { pointer-events: auto; background: linear-gradient(135deg, rgba(234, 179, 8, 0.9), rgba(202, 138, 4, 0.9)); color: #111; font-weight: 600; border: none; padding: 8px 20px; border-radius: 999px; font-size: clamp(13px, 2vw, 15px); cursor: pointer; backdrop-filter: blur(12px); transition: all 0.3s; box-shadow: 0 4px 12px rgba(234, 179, 8, 0.2); }
.end-tour-btn:hover { background: linear-gradient(135deg, #facc15, #eab308); transform: translateY(-1px); box-shadow: 0 6px 16px rgba(234, 179, 8, 0.3); }

.interrupt-btn { position: absolute; right: 20px; bottom: 20px; width: clamp(56px, 8vw, 88px); height: clamp(56px, 8vw, 88px); border-radius: 50%; border: 1px solid rgba(255,255,255,0.2); background: rgba(255,255,255,0.1); color: #fff; font-size: clamp(20px, 3.5vw, 32px); cursor: pointer; backdrop-filter: blur(8px); z-index: 2; }

.chat-pane { flex: 1 1 calc(55% - 1vw); min-height: 0; display: flex; flex-direction: column; background: rgba(10, 14, 20, 0.55); backdrop-filter: blur(24px); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 24px; box-shadow: 0 16px 48px rgba(0, 0, 0, 0.5); overflow: hidden; padding-bottom: env(safe-area-inset-bottom, 0); color: #e5e7eb; z-index: 2; position: relative; }

.route-map-container { flex: 0 0 auto; display: flex; flex-direction: column; border-bottom: 1px solid rgba(255,255,255,0.05); overflow-y: auto; }
.messages { flex: 1; min-height: 0; overflow-y: auto; padding: 24px; -webkit-overflow-scrolling: touch; }
.msg { margin: 12px 0; display: flex; }
.msg.user { justify-content: flex-end; }
.bubble { max-width: 82%; padding: 14px 20px; border-radius: 20px; line-height: 1.6; white-space: pre-wrap; font-size: clamp(14px, 2.6vw, 15px); backdrop-filter: blur(12px); box-shadow: 0 4px 16px rgba(0,0,0,0.15); letter-spacing: 0.5px; }
.msg.user .bubble { background: linear-gradient(135deg, rgba(234, 179, 8, 0.15), rgba(234, 179, 8, 0.05)); color: #fdf6e3; border: 1px solid rgba(234, 179, 8, 0.2); border-bottom-right-radius: 6px; }
.msg.assistant .bubble { background: rgba(255,255,255,0.06); color: #f3f4f6; border: 1px solid rgba(255,255,255,0.08); border-bottom-left-radius: 6px; }
.msg.assistant .bubble.is-pending { color: #c8d8ff; opacity: 0.82; animation: thinking-pulse 1.2s ease-in-out infinite; }
.cites { font-size: clamp(11px, 1.8vw, 13px); color: #9ca3af; margin-top: 8px; }

@keyframes thinking-pulse {
  0%, 100% { opacity: 0.68; }
  50% { opacity: 1; }
}

.presets { display: flex; gap: 12px; padding: 12px 24px; overflow-x: auto; scroll-snap-type: x mandatory; -ms-overflow-style: none; scrollbar-width: none; }
.presets::-webkit-scrollbar { display: none; }
.map-section { flex: 0 0 auto; border-bottom: 1px solid rgba(255,255,255,0.05); }
.map-toggle { display: flex; justify-content: space-between; align-items: center; padding: 12px 24px; cursor: pointer; font-size: 14px; color: #d1d5db; background: rgba(255,255,255,0.02); transition: background 0.3s; }
.map-toggle:hover { background: rgba(255,255,255,0.06); color: #f3f4f6; }
.map-arrow { color: #9ca3af; font-size: 11px; }
.chip { flex: 0 0 auto; scroll-snap-align: start; padding: 10px 20px; border: 1px solid rgba(255, 255, 255, 0.1); background: rgba(255, 255, 255, 0.05); color: #d1d5db; border-radius: 999px; font-size: clamp(13px, 2.2vw, 14px); cursor: pointer; white-space: nowrap; transition: all 0.4s ease; backdrop-filter: blur(8px); }
.chip:hover { background: rgba(234, 179, 8, 0.15); color: #fdf6e3; border-color: rgba(234, 179, 8, 0.4); transform: translateY(-1px); box-shadow: 0 4px 12px rgba(234, 179, 8, 0.1); }

.chat-input-area { flex: 0 0 auto; display: flex; flex-direction: column; padding: 12px 24px 24px; }
.answer-mode-tabs { display: flex; gap: 12px; margin-bottom: 12px; padding-left: 4px; }
.mode-tab { display: flex; align-items: center; gap: 6px; font-size: 13px; color: #9ca3af; cursor: pointer; transition: all 0.3s; padding: 6px 16px; border-radius: 999px; border: 1px solid transparent; background: rgba(255,255,255,0.03); }
.mode-tab:hover { color: #d1d5db; background: rgba(255, 255, 255, 0.08); border-color: rgba(255,255,255,0.1); }
.mode-tab.active { color: #fdf6e3; background: rgba(234, 179, 8, 0.15); border-color: rgba(234, 179, 8, 0.3); font-weight: 500; }
.mode-tab .icon { font-size: 14px; }

.input-bar { display: grid; grid-template-columns: auto 1fr auto; gap: 12px; align-items: stretch; }
.input-bar.voice-mode { grid-template-columns: auto 1fr auto; }
.mode-toggle { display: flex; justify-content: center; align-items: center; width: 46px; height: 46px; border-radius: 50%; background: rgba(255,255,255,0.05); color: #eab308; font-size: 20px; cursor: pointer; align-self: center; border: 1px solid rgba(255,255,255,0.1); transition: all 0.3s; }
.mode-toggle:hover { background: rgba(234, 179, 8, 0.1); border-color: rgba(234, 179, 8, 0.3); }
textarea { resize: none; border: 1px solid rgba(255,255,255,0.1); border-radius: 16px; padding: 14px 16px; font-size: clamp(14px, 2.2vw, 15px); font-family: inherit; outline: none; background: rgba(255,255,255,0.03); color: #fff; transition: all 0.3s; line-height: 1.5; }
textarea:focus { border-color: rgba(234, 179, 8, 0.5); background: rgba(255,255,255,0.06); box-shadow: 0 0 0 2px rgba(234, 179, 8, 0.1); }
.btn-col { display: flex; flex-direction: column; gap: 8px; }
.btn { border: none; border-radius: 14px; padding: 0 20px; min-width: clamp(72px, 8vw, 100px); min-height: 48px; font-size: clamp(14px, 2vw, 15px); font-weight: 600; cursor: pointer; transition: all 0.3s; display: flex; align-items: center; justify-content: center; }
.btn.primary { background: linear-gradient(135deg, rgba(234, 179, 8, 0.9), rgba(202, 138, 4, 0.9)); color: #111; box-shadow: 0 4px 12px rgba(234, 179, 8, 0.2); }
.btn.primary:disabled { opacity: 0.4; cursor: not-allowed; background: rgba(255,255,255,0.1); color: #9ca3af; box-shadow: none; }
.btn.primary:not(:disabled):hover { background: linear-gradient(135deg, #facc15, #eab308); transform: translateY(-1px); box-shadow: 0 6px 16px rgba(234, 179, 8, 0.3); }
.btn.ghost { background: transparent; color: #eab308; border: 1px solid rgba(234, 179, 8, 0.3); }
.btn.ghost:active { background: rgba(234, 179, 8, 0.1); }
.voice-btn { border: 1px solid rgba(234, 179, 8, 0.3); border-radius: 16px; background: rgba(234, 179, 8, 0.1); color: #eab308; font-size: clamp(14px, 2.5vw, 18px); cursor: pointer; height: 50px; align-self: center; font-weight: 500; transition: all 0.3s; }
.voice-btn.recording { background: rgba(234, 179, 8, 0.25); color: #fde047; border-color: #eab308; }
.voice-error { margin: 8px 0 0 58px; color: #fca5a5; font-size: 13px; }

@media (max-width: 1024px) and (orientation: portrait) { .layout { flex-direction: column; padding: 1.5vh 3vw; gap: 1.5vh; } .avatar-pane { flex: 0 0 45vh; width: 100%; border-radius: 20px; } .chat-pane { flex: 1 1 auto; width: 100%; border-radius: 20px; } }
</style>
