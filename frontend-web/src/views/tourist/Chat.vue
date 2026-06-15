<template>
  <div class="layout">
    <!-- 上：数字人画面 -->
    <div class="avatar-pane">
      <VrmAvatar
        ref="avatarRef"
        class="vrm-fill"
        :model-url="effectiveModelUrl"
        :audio-url="currentAudioUrl"
        :emotion="currentEmotion"
        :motion="currentMotion"
        :motions="motionsMap"
      />
      <div class="top-bar">
        <strong class="title">{{ parkName }}</strong>
        <div class="top-bar-right">
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

      <!-- 预设问题 chips（静态占位，后续接 /chat/suggestions） -->
      <div class="presets">
        <button v-for="(q, i) in presets" :key="i" class="chip" @click="sendPreset(q)">{{ q }}</button>
      </div>

      <div class="input-bar">
        <textarea v-model="input" placeholder="输入问题，或按住右侧按钮说话…"
                  @keydown.enter.exact.prevent="send" rows="2"></textarea>
        <div class="btn-col">
          <button class="btn primary" :disabled="loading || !input.trim()" @click="send">发送</button>
          <button class="btn ghost"
                  @mousedown="startRec" @mouseup="stopRec"
                  @touchstart.prevent="startRec" @touchend.prevent="stopRec">
            {{ recording ? '🎤·说话中' : '🎤 按住说话' }}
          </button>
        </div>
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
import RatingModal from '../../components/RatingModal.vue'
import BadgeModal from '../../components/BadgeModal.vue'
import QuizModal from '../../components/QuizModal.vue'
import ShareCard from '../../components/ShareCard.vue'

// 未上传 VRM 时的 demo 资产（three-vrm 官方示例，CDN）
// 生产环境请到 admin 后台上传自己的 .vrm
const SAMPLE_VRM_URL = 'https://cdn.jsdelivr.net/gh/pixiv/three-vrm@release/packages/three-vrm/examples/models/VRM1_Constraint_Twist_Sample.vrm'

const parkName = sessionStorage.getItem('park_name') || '灵山胜境'
const parkCode = sessionStorage.getItem('park') || 'lingshan'
const mapExpanded = ref(false)

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
// Web Speech API（TTS Tier-3 保底）
const synth = window.speechSynthesis ?? null
const sessionId = ref(crypto.randomUUID().slice(0, 16))
const messages = ref([])
const input = ref('')
const loading = ref(false)
const recording = ref(false)
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
  }
})

let mediaRecorder = null
let chunks = []
// 麦克风音量检测（代替摄像头：说话时让数字人“听”的反馈）
let audioCtx = null
let analyser = null
let rmsTimer = 0
let prevMotion = 'idle'

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

function push(role, content, citations = []) {
  messages.value.push({ role, content, citations })
  nextTick(() => { msgBox.value && (msgBox.value.scrollTop = msgBox.value.scrollHeight) })
}

function applyResponse(r) {
  push('assistant', r.answer, r.citations)
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
    if (synth && r.answer) {
      const utt = new SpeechSynthesisUtterance(r.answer)
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
          messages.value[msgIdx].content += evt.text
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
            if (synth && messages.value[msgIdx].content) {
              const utt = new SpeechSynthesisUtterance(messages.value[msgIdx].content)
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
  loading.value = true
  try {
    const r = await chatCheckin({
      session_id: sessionId.value,
      spot_code: spotCode,
      park_code: parkCode,
      avatar_code: avatar.code || undefined,
      route_context: buildRouteContext(),
    })
    // 展示景点介绍
    push('assistant', r.narrative)
    currentEmotion.value = r.emotion || 'joy'
    currentMotion.value = r.motion || 'wave'
    if (r.audio_url) {
      currentAudioUrl.value = r.audio_url + (r.audio_url.includes('?') ? '&' : '?') + 't=' + Date.now()
    }
    // 推进进度
    if (currentSpotIdx.value < routeSpots.value.length) {
      currentSpotIdx.value += 1
    }
    // 处理成就徽章
    if (r.badge) {
      pendingBadge.value = r.badge
      showBadge.value = true
    }
    // 提示下一站
    if (r.next_spot_name) {
      const walkTip = r.next_walk_minutes ? `，步行约 ${r.next_walk_minutes} 分钟` : ''
      push('assistant', `→ 下一站：**${r.next_spot_name}**${walkTip}`)
    } else if (currentSpotIdx.value >= routeSpots.value.length) {
      push('assistant', '🎉 路线全部完成！您已游遍所有景点，希望本次游览令您尽兴而归！')
    }
  } catch (e) {
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
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    mediaRecorder = new MediaRecorder(stream)
    chunks = []
    mediaRecorder.ondataavailable = (e) => chunks.push(e.data)
    mediaRecorder.onstop = uploadAudio
    mediaRecorder.start()
    recording.value = true
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
  try { mediaRecorder?.stop() } catch (e) {}
  if (rmsTimer) { clearInterval(rmsTimer); rmsTimer = 0 }
  if (audioCtx) { try { audioCtx.close() } catch (_) {} audioCtx = null; analyser = null }
  currentMotion.value = prevMotion || avatar.default_motion || 'idle'
}

async function uploadAudio() {
  const blob = new Blob(chunks, { type: 'audio/webm' })
  const fd = new FormData()
  fd.append('session_id', sessionId.value)
  if (avatar.code) fd.append('avatar_code', avatar.code)
  fd.append('audio', blob, 'recording.webm')
  loading.value = true
  push('user', '🎤（语音消息）')
  try {
    const resp = await fetch('/api/chat/voice', { method: 'POST', body: fd })
    const r = await resp.json()
    applyResponse(r)
    setTimeout(_pollPref, 1000)
  } catch (e) {
    push('assistant', '语音识别失败。')
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

.layout { display: flex; flex-direction: row; width: 100%; height: 100vh; height: 100dvh; background: #05080c; overflow: hidden; font-family: 'Inter', system-ui, sans-serif; }

.avatar-pane { position: relative; flex: 0 0 45%; background-image: url('/images/lingshan_bg.png'); background-size: cover; background-position: center; overflow: hidden; }
.avatar-pane::before { content: ''; position: absolute; inset: 0; background: rgba(5, 8, 12, 0.4); z-index: 0; }

.vrm-fill { position: absolute; inset: 0; z-index: 1; }
.top-bar { position: absolute; top: env(safe-area-inset-top, 0); left: 0; right: 0; padding: 16px 20px; display: flex; justify-content: space-between; align-items: center; color: #fff; z-index: 2; pointer-events: none; }
.top-bar .title { font-family: 'Noto Serif SC', serif; font-size: clamp(18px, 3.2vw, 28px); letter-spacing: 1px; text-shadow: 0 2px 4px rgba(0,0,0,0.8); }
.top-bar-right { display: flex; align-items: center; gap: 10px; pointer-events: auto; }
.top-bar .back { pointer-events: auto; color: #eab308; text-decoration: none; font-size: clamp(13px, 2vw, 18px); background: rgba(255,255,255,0.08); padding: 8px 14px; border-radius: 999px; backdrop-filter: blur(8px); border: 1px solid rgba(234, 179, 8, 0.3); }
.end-tour-btn { pointer-events: auto; background: linear-gradient(135deg, #eab308 0%, #ca8a04 100%); color: #000; font-weight: 600; border: none; padding: 8px 14px; border-radius: 999px; font-size: clamp(13px, 2vw, 18px); cursor: pointer; backdrop-filter: blur(8px); }

.interrupt-btn { position: absolute; right: 20px; bottom: 20px; width: clamp(56px, 8vw, 88px); height: clamp(56px, 8vw, 88px); border-radius: 50%; border: 1px solid rgba(255,255,255,0.2); background: rgba(255,255,255,0.1); color: #fff; font-size: clamp(20px, 3.5vw, 32px); cursor: pointer; backdrop-filter: blur(8px); z-index: 2; }

.chat-pane { flex: 1 1 55%; min-height: 0; display: flex; flex-direction: column; background: rgba(10, 15, 25, 0.85); backdrop-filter: blur(24px); border-left: 1px solid rgba(255,255,255,0.05); padding-bottom: env(safe-area-inset-bottom, 0); color: #e5e7eb; }

.route-map-container { flex: 0 0 auto; display: flex; flex-direction: column; border-bottom: 1px solid rgba(255,255,255,0.05); overflow-y: auto; }
.messages { flex: 1; min-height: 0; overflow-y: auto; padding: 24px; -webkit-overflow-scrolling: touch; }
.msg { margin: 12px 0; display: flex; }
.msg.user { justify-content: flex-end; }
.bubble { max-width: 82%; padding: 14px 18px; border-radius: 18px; line-height: 1.6; white-space: pre-wrap; font-size: clamp(14px, 2.6vw, 16px); backdrop-filter: blur(12px); box-shadow: 0 4px 12px rgba(0,0,0,0.2); }
.msg.user .bubble { background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); border-bottom-right-radius: 4px; }
.msg.assistant .bubble { background: rgba(255,255,255,0.05); color: #e5e7eb; border: 1px solid rgba(255,255,255,0.1); border-bottom-left-radius: 4px; }
.cites { font-size: clamp(11px, 1.8vw, 13px); color: #9ca3af; margin-top: 8px; }

.presets { display: flex; gap: 12px; padding: 12px 24px; overflow-x: auto; scroll-snap-type: x mandatory; -ms-overflow-style: none; scrollbar-width: none; border-top: 1px solid rgba(255,255,255,0.05); }
.presets::-webkit-scrollbar { display: none; }
.map-section { flex: 0 0 auto; border-bottom: 1px solid rgba(255,255,255,0.05); }
.map-toggle { display: flex; justify-content: space-between; align-items: center; padding: 10px 24px; cursor: pointer; font-size: 14px; color: #d1d5db; background: rgba(255,255,255,0.02); }
.map-arrow { color: #9ca3af; font-size: 11px; }
.chip { flex: 0 0 auto; scroll-snap-align: start; padding: 8px 16px; border: 1px solid rgba(234, 179, 8, 0.3); background: rgba(234, 179, 8, 0.1); color: #eab308; border-radius: 999px; font-size: clamp(13px, 2.2vw, 15px); cursor: pointer; white-space: nowrap; transition: all 0.3s; }
.chip:hover { background: rgba(234, 179, 8, 0.2); }

.input-bar { flex: 0 0 auto; padding: 16px 24px 24px; display: grid; grid-template-columns: 1fr auto; gap: 12px; align-items: stretch; }
textarea { resize: none; border: 1px solid rgba(255,255,255,0.1); border-radius: 16px; padding: 14px; font-size: clamp(14px, 2.2vw, 16px); font-family: inherit; outline: none; background: rgba(0,0,0,0.3); color: #fff; transition: border-color 0.3s; }
textarea:focus { border-color: #10b981; }
.btn-col { display: flex; flex-direction: column; gap: 8px; }
.btn { border: none; border-radius: 12px; padding: 0 16px; min-width: clamp(64px, 8vw, 96px); min-height: 44px; font-size: clamp(13px, 2vw, 15px); font-weight: 500; cursor: pointer; transition: all 0.3s; }
.btn.primary { background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); }
.btn.primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn.primary:not(:disabled):hover { background: rgba(16, 185, 129, 0.25); }
.btn.ghost { background: transparent; color: #eab308; border: 1px solid rgba(234, 179, 8, 0.3); }
.btn.ghost:active { background: rgba(234, 179, 8, 0.1); }

@media (max-width: 1024px) and (orientation: portrait) { .layout { flex-direction: column; } .avatar-pane { flex: 0 0 50vh; } .chat-pane { flex: 1 1 50vh; border-left: none; border-top: 1px solid rgba(255,255,255,0.05); } }
</style>
