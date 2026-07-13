<template>
  <div class="rive-page" :class="{ 'has-active-route': activeSidebarRoute }">

    <header class="rive-header">
      <h1>灵山胜境数字人导览</h1>
      <p>Rive 模式 · 聊天流与动态组件无缝联动</p>
    </header>

    <div class="main-grid">
      <!-- ── 左侧卡片：展示台 ── -->
      <div class="card avatar-card">
        <div class="avatar-top">
          <div class="stage-circle">
            <div
              class="rive-stage"
              :class="[`pose-${currentAction}`, { reacting: stageReacting }, stageReactionClass]"
            >
              <div class="rive-avatar-frame" :style="avatarRenderStyle">
                <canvas ref="avatarCanvas" class="rive-canvas" width="900" height="900" aria-label="AI数字人展示台"></canvas>
              </div>
              <div v-if="riveStatus !== 'ready'" class="stage-loading">{{ riveStatusLabel }}</div>
            </div>
          </div>
          <div class="avatar-info">
            <div class="avatar-name">{{ activeGuide.name }}</div>
            <div class="avatar-status" id="avatarStatus">
              <div class="status-dot"></div>
              {{ statusText }}
            </div>
          </div>
          <div class="guide-switcher" aria-label="选择讲解员形象">
            <button
              v-for="guide in guides"
              :key="guide.id"
              type="button"
              class="guide-choice"
              :class="{ active: guide.id === activeGuideId }"
              @click="selectGuide(guide.id)"
            >
              <span>{{ guide.name }}</span>
              <small>{{ guide.role }}</small>
            </button>
          </div>
        </div>

        <!-- 下半：路线图 -->
        <div class="avatar-bottom" v-if="activeSidebarRoute" :key="sidebarKey">
          <div class="active-route-header">
            <h3>🗺️ {{ activeSidebarRoute.name }}</h3>
            <span class="live-badge">● 实时导航中</span>
          </div>
          <div class="large-route-container">
            <svg class="zigzag-svg" preserveAspectRatio="none" viewBox="0 0 100 100">
              <polyline class="svg-line-bg" points="15,15 45,40 15,65 45,90" />
              <polyline class="svg-line-active" points="15,15 45,40 15,65 45,90" />
            </svg>
            <div
              v-for="(stop, idx) in activeSidebarRoute.stops.slice(0, 4)"
              :key="idx"
              class="large-node"
              :class="['l' + (idx + 1), { 'active-now': idx === 0 }]"
            >
              <div class="l-dot"></div>
              <div class="l-content">
                <h4>{{ stop.name }}</h4>
                <p>{{ idx === 0 ? '当前位置 · 集合出发' : (stop.transport || '步行') }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ── 右侧卡片：聊天区 ── -->
      <div class="card chat-card">
        <div class="chat-header">
          <div class="title"><span>💬</span> 互动问答</div>
          <span class="answer-mode-status">{{ answerMode === 'fast' ? '⚡ 精简回答' : '📖 详细讲解' }}</span>
        </div>

        <div class="chat-messages" ref="msgBox">
          <!-- 欢迎 + 快捷问题 -->
          <div v-if="!messages.length" class="welcome-area">
            <div class="msg ai"><div class="msg-bubble">👋 您好！我是您的 AI 导览助手慧行。请问您想了解哪些景点，或者需要帮您规划游览路线吗？</div></div>
            <div class="quick-btns">
              <button v-for="q in quickQuestions" :key="q" class="quick-chip" @click="send(q)">{{ q }}</button>
            </div>
          </div>

          <div v-for="(m, i) in messages" :key="i" :class="['msg', m.role]">
            <div class="msg-bubble">
              <div>{{ m.content }}</div>

              <!-- 路线卡片 -->
              <div v-if="m.routeData" class="route-card">
                <div class="route-title">
                  <span>🗺️ {{ m.routeData.name }}</span>
                  <button v-if="!m.routeApplied" class="btn-apply-route" @click="applyRoute(m)">转移至侧边栏</button>
                  <button v-else class="btn-apply-route applied" disabled>✅ 已在左侧展示</button>
                </div>
                <div class="zigzag-container">
                  <svg class="zigzag-svg" preserveAspectRatio="none" viewBox="0 0 100 100">
                    <polyline points="15,10 45,35 15,60 45,85" fill="none" stroke="rgba(212,175,55,0.4)" stroke-width="2" stroke-dasharray="4,4" />
                  </svg>
                  <div v-for="(stop, idx) in m.routeData.stops.slice(0, 4)" :key="idx" class="route-node" :class="'n' + (idx + 1)">
                    <div class="node-dot"></div>
                    <div class="node-content"><h4>{{ stop.name }}</h4><p>{{ stop.transport || '步行' }}</p></div>
                  </div>
                </div>
              </div>

              <div v-if="m.role === 'ai' && m.content" class="msg-actions" aria-label="消息操作">
                <button
                  type="button"
                  class="msg-action-btn"
                  :class="{ active: m.voiceStatus === 'playing' }"
                  :disabled="m.voiceStatus === 'loading'"
                  :title="voiceTitle(m)"
                  @click="playMessageVoice(m)"
                >
                  <span class="action-icon">{{ voiceIcon(m) }}</span>
                  <span class="action-label">{{ voiceLabel(m) }}</span>
                </button>
              </div>
            </div>
          </div>

          <div v-if="loading" class="msg ai"><div class="msg-bubble">正在查找灵山胜境官方资料…</div></div>
        </div>

        <div class="chat-input-area">
          <div class="answer-mode-tabs" aria-label="回答模式">
            <button
              type="button"
              class="mode-tab"
              :class="{ active: answerMode === 'fast' }"
              @click="setAnswerMode('fast')"
            >⚡ 精简版 · 5秒内</button>
            <button
              type="button"
              class="mode-tab"
              :class="{ active: answerMode === 'detailed' }"
              @click="setAnswerMode('detailed')"
            >📖 详细版 · 知识讲解</button>
          </div>
          <div class="input-box">
            <input v-model="inputText" type="text" placeholder="输入您想了解的景点或路线..." @keydown.enter="send()" />
            <button class="btn-voice">🎤</button>
            <button class="btn-send" @click="send()">➤</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Rive, StateMachineInputType } from '@rive-app/canvas'
import { chatText, planRoute, synthesizeChatSpeech } from '../../api.js'

const parkCode = sessionStorage.getItem('park') || 'lingshan'
const sessionId = ref(sessionStorage.getItem('session_id') || `rive-${Date.now()}`)

const guides = [
  {
    id: 'huixing',
    name: '慧行',
    role: '状态讲解员',
    desc: '表情动作完整，适合问答演示',
    assetPath: '/avatar/rive/live-avatar-state-machine.riv',
    renderScale: 1.05,
    renderOffsetY: '3%',
    stateMachine: 'State Machine 1',
    actionMap: {
      idle: 'idle',
      listen: 'hover',
      think: 'thinking',
      speak: 'happy',
      happy: 'happy',
      point: 'happy',
      error: 'sad',
    },
  },
  {
    id: 'huiyuan',
    name: '慧远',
    role: '稳重讲解员',
    desc: '文化感更强，适合正式路线讲解',
    assetPath: '/avatar/rive/mature-guide-avatar.riv',
    renderScale: 1.2,
    renderOffsetY: '6%',
    animation: 'Animation 1',
    actionMap: {},
  },
  {
    id: 'xiaoling',
    name: '小灵',
    role: '亲和助手',
    desc: '年轻友好，适合亲子与游客问答',
    assetPath: '/avatar/rive/friendly-avatar.riv',
    // 此文件的画板留白较多，单独放大可视内容以与其他角色保持一致。
    renderScale: 1.55,
    renderOffsetY: '14%',
    stateMachine: 'State Machine 1',
    actionMap: {
      idle: 'Hover/Select',
      listen: 'Hover/Select',
      think: 'Hover/Select',
      speak: 'Hover/Select',
      happy: 'Hover/Select',
      point: 'Hover/Select',
      error: 'Hover/Select',
    },
  },
]

const messages = ref([])
const inputText = ref('')
const loading = ref(false)
const answerMode = ref(sessionStorage.getItem('rive_answer_mode') || 'fast')
const activeSidebarRoute = ref(null)
const sidebarKey = ref(0)
const msgBox = ref(null)
const avatarCanvas = ref(null)
const activeGuideId = ref(sessionStorage.getItem('rive_guide_id') || guides[0].id)
const riveStatus = ref('loading')
let riveInputs = []
const currentAction = ref('idle')
const stageReacting = ref(false)
const stageReactionClass = ref('')

const activeGuide = computed(() => guides.find(item => item.id === activeGuideId.value) || guides[0])
const avatarRenderStyle = computed(() => ({
  transform: `translateY(${activeGuide.value.renderOffsetY || '0'}) scale(${activeGuide.value.renderScale || 1})`,
}))
const riveStatusLabel = computed(() => {
  if (riveStatus.value === 'ready') return ''
  if (riveStatus.value === 'error') return '形象加载失败'
  return '正在加载形象'
})

const actionLabels = {
  idle: '正在为您讲解',
  listen: '正在倾听',
  think: '正在思考',
  speak: '正在讲解',
  happy: '欢迎游客',
  point: '路线指引中',
  error: '抱歉说明',
}

const statusText = computed(() => {
  if (riveStatus.value === 'loading') return '正在加载形象…'
  if (riveStatus.value === 'error') return '形象加载失败'
  if (loading.value) return '正在思考…'
  if (activeSidebarRoute.value) return '实时导航模式'
  return actionLabels[currentAction.value] || '正在为您讲解'
})

const quickQuestions = ['帮我规划半天路线', '灵山大佛有多高？', '亲子半天怎么安排？', '灵山梵宫今天开放吗？']

const routeParams = ref({
  duration: '半天', mobility: '普通', companions: '大众',
  interests: ['佛教文化'], performances: true, transport: '步行为主'
})

const inputFallbacks = {
  idle: ['idle', 'Idle'],
  listen: ['listen', 'hover', 'Hover/Select'],
  think: ['thinking', 'think', 'Think', 'Hover/Select'],
  speak: ['speak', 'Speak', 'happy', 'Hover/Select'],
  happy: ['happy', 'wave', 'Hover/Select'],
  point: ['point', 'guide', 'happy', 'Hover/Select'],
  error: ['sad', 'error', 'Error', 'Warning'],
}

let riveInstance = null
let activeBooleanInput = null
let actionResetTimer = 0
let reactionTimer = 0
let actionSerial = 0
let voiceAudio = null
let activeVoiceMessage = null
let speechUtterance = null

function setAnswerMode(mode) {
  answerMode.value = mode === 'detailed' ? 'detailed' : 'fast'
  sessionStorage.setItem('rive_answer_mode', answerMode.value)
}

function extractRouteHints(text) {
  if (text.includes('老人') || text.includes('长辈')) {
    routeParams.value.companions = '老人'; routeParams.value.mobility = '少步行'; routeParams.value.transport = '优先观光车'
  }
  if (text.includes('小孩') || text.includes('亲子')) routeParams.value.companions = '亲子'
  if (text.includes('一天') || text.includes('全天')) routeParams.value.duration = '一天'
  if (text.includes('少走') || text.includes('腿脚')) { routeParams.value.mobility = '少步行'; routeParams.value.transport = '优先观光车' }
}

function normalizeName(name) {
  return String(name || '').toLowerCase().replace(/[^a-z0-9]/g, '')
}

function findRiveInput(names) {
  const wanted = names.map(normalizeName).filter(Boolean)
  return riveInputs.find((input) => {
    const current = normalizeName(input?.name)
    return wanted.some((name) => current === name || current.includes(name) || name.includes(current))
  })
}

function clearBooleanInput() {
  if (!activeBooleanInput) return
  try { activeBooleanInput.value = false } catch (e) {}
  activeBooleanInput = null
}

function cleanupRive() {
  clearBooleanInput()
  if (riveInstance) {
    try { riveInstance.cleanup() } catch (e) {}
  }
  riveInstance = null
  riveInputs = []
}

function showStageReaction(action) {
  stageReacting.value = false
  stageReactionClass.value = ''
  window.clearTimeout(reactionTimer)
  requestAnimationFrame(() => {
    stageReactionClass.value = `reaction-${action}`
    stageReacting.value = true
    reactionTimer = window.setTimeout(() => {
      stageReacting.value = false
      stageReactionClass.value = ''
    }, 720)
  })
}

function resolveInputNames(action) {
  const mapped = activeGuide.value.actionMap?.[action]
  return [
    ...(mapped ? [mapped] : []),
    ...(inputFallbacks[action] || inputFallbacks.speak),
  ]
}

function triggerInput(input, action) {
  try {
    if (input.type === StateMachineInputType.Trigger) {
      input.fire()
      return true
    }
    if (input.type === StateMachineInputType.Boolean) {
      clearBooleanInput()
      if (action === 'idle') {
        input.value = false
        return true
      }
      input.value = true
      activeBooleanInput = input
      window.setTimeout(() => {
        if (activeBooleanInput === input) clearBooleanInput()
      }, 900)
      return true
    }
    if (input.type === StateMachineInputType.Number) {
      input.value = action === 'idle' ? 0 : 1
      if (action !== 'idle') {
        window.setTimeout(() => { try { input.value = 0 } catch (e) {} }, 900)
      }
      return true
    }
  } catch (e) {
    return false
  }
  return false
}

function replayAnimationFallback() {
  const guide = activeGuide.value
  if (!riveInstance || !guide.animation) return false
  try {
    riveInstance.stop(guide.animation)
    riveInstance.play(guide.animation)
    return true
  } catch (e) {
    return false
  }
}

function triggerRiveAction(action) {
  currentAction.value = action
  showStageReaction(action)
  if (!riveInstance || riveStatus.value !== 'ready') return

  const input = findRiveInput(resolveInputNames(action))
  if (input && triggerInput(input, action)) return
  replayAnimationFallback()
}

function playResponseAction(action) {
  const safeAction = action || 'speak'
  actionSerial += 1
  window.clearTimeout(actionResetTimer)
  triggerRiveAction(safeAction)
  actionResetTimer = window.setTimeout(() => {
    currentAction.value = 'idle'
    clearBooleanInput()
    if (!riveInstance || riveStatus.value !== 'ready') return
    const input = findRiveInput(resolveInputNames('idle'))
    if (input) triggerInput(input, 'idle')
  }, safeAction === 'error' ? 1500 : 1800)
}

function inferResponseAction(question, answer, res, hasRouteCard) {
  const rawMotion = String(res?.motion || '').toLowerCase()
  const motionMap = {
    wave: 'happy',
    welcome: 'happy',
    explain: 'speak',
    speak: 'speak',
    think: 'think',
    listen: 'listen',
    point: 'point',
    guide: 'point',
    bow: 'happy',
    clap: 'happy',
    shrug: 'error',
    error: 'error',
    sad: 'error',
  }
  if (motionMap[rawMotion]) return motionMap[rawMotion]

  const text = `${question || ''} ${answer || ''}`
  if (/抱歉|暂不可用|无法|失败|错误|稍后|不确定/.test(text)) return 'error'
  if (hasRouteCard || res?.intent === 'route' || /路线|规划|导航|下一站|步行|游览顺序|怎么安排/.test(text)) return 'point'
  if (/欢迎|您好|你好|出发|祝您|很高兴/.test(text)) return 'happy'
  if (/为什么|怎么|历史|文化|介绍|讲讲|多高|开放|资料|根据/.test(text)) return 'speak'
  return 'speak'
}

function loadGuide() {
  const guide = activeGuide.value
  if (!avatarCanvas.value) return
  cleanupRive()
  riveStatus.value = 'loading'
  currentAction.value = 'idle'

  const options = {
    src: guide.assetPath,
    canvas: avatarCanvas.value,
    autoplay: true,
    onLoad: () => {
      try { riveInstance?.resizeDrawingSurfaceToCanvas() } catch (e) {}
      try {
        riveInputs = guide.stateMachine ? (riveInstance?.stateMachineInputs(guide.stateMachine) || []) : []
      } catch (e) {
        riveInputs = []
      }
      riveStatus.value = 'ready'
      triggerRiveAction('idle')
    },
    onLoadError: (error) => {
      console.error('Rive model load failed:', error)
      riveStatus.value = 'error'
    },
  }
  if (guide.stateMachine) options.stateMachines = guide.stateMachine
  if (guide.animation) options.animations = guide.animation

  riveInstance = new Rive(options)
}

function selectGuide(id) {
  if (id === activeGuideId.value) return
  activeGuideId.value = id
  sessionStorage.setItem('rive_guide_id', id)
}

function voiceIcon(message) {
  if (message.voiceStatus === 'loading') return '⏳'
  if (message.voiceStatus === 'playing') return '⏸'
  if (message.voiceStatus === 'readyToPlay') return '▶'
  if (message.voiceStatus === 'error') return '↻'
  return '🔊'
}

function voiceLabel(message) {
  if (message.voiceStatus === 'loading') return '生成中'
  if (message.voiceStatus === 'playing') return '停止'
  if (message.voiceStatus === 'readyToPlay') return '播放'
  if (message.voiceStatus === 'error') return '重试语音'
  return '语音'
}

function voiceTitle(message) {
  if (message.voiceStatus === 'loading') return '正在生成语音'
  if (message.voiceStatus === 'playing') return '停止播放'
  if (message.voiceStatus === 'readyToPlay') return '语音已生成，点击播放'
  if (message.voiceStatus === 'error') return '生成失败，点击重试'
  return '点击生成并播放语音'
}

function stopVoicePlayback() {
  if (voiceAudio) {
    try { voiceAudio.pause() } catch (e) {}
    voiceAudio = null
  }
  if (speechUtterance && window.speechSynthesis) {
    try { window.speechSynthesis.cancel() } catch (e) {}
    speechUtterance = null
  }
  if (activeVoiceMessage && activeVoiceMessage.voiceStatus === 'playing') {
    activeVoiceMessage.voiceStatus = activeVoiceMessage.audioUrl ? 'readyToPlay' : 'ready'
  }
  activeVoiceMessage = null
}

function playBrowserSpeech(message) {
  if (!window.speechSynthesis) throw new Error('speech synthesis unavailable')
  speechUtterance = new SpeechSynthesisUtterance(message.content)
  speechUtterance.lang = 'zh-CN'
  speechUtterance.rate = 0.95
  speechUtterance.pitch = 1
  activeVoiceMessage = message
  message.voiceStatus = 'playing'
  speechUtterance.onend = () => {
    if (activeVoiceMessage === message) message.voiceStatus = 'ready'
    activeVoiceMessage = null
    speechUtterance = null
  }
  speechUtterance.onerror = () => {
    if (activeVoiceMessage === message) message.voiceStatus = 'error'
    activeVoiceMessage = null
    speechUtterance = null
  }
  window.speechSynthesis.speak(speechUtterance)
  playResponseAction('speak')
}

async function playMessageVoice(message) {
  if (!message?.content || message.voiceStatus === 'loading') return
  if (message.voiceStatus === 'playing') {
    stopVoicePlayback()
    return
  }

  stopVoicePlayback()
  message.voiceStatus = 'loading'
  try {
    if (!message.audioUrl) {
      const res = await synthesizeChatSpeech({
        session_id: sessionId.value,
        text: message.content,
      })
      message.audioUrl = res?.audio_url || ''
    }
    if (!message.audioUrl) {
      playBrowserSpeech(message)
      return
    }
    const sep = message.audioUrl.includes('?') ? '&' : '?'
    voiceAudio = new Audio(message.audioUrl + sep + 't=' + Date.now())
    activeVoiceMessage = message
    message.voiceStatus = 'playing'
    voiceAudio.addEventListener('ended', () => {
      if (activeVoiceMessage === message) message.voiceStatus = 'readyToPlay'
      activeVoiceMessage = null
      voiceAudio = null
    }, { once: true })
    voiceAudio.addEventListener('error', () => {
      if (activeVoiceMessage === message) {
        message.voiceStatus = 'error'
        activeVoiceMessage = null
      }
      voiceAudio = null
    }, { once: true })
    try {
      await voiceAudio.play()
      playResponseAction('speak')
    } catch (playError) {
      console.warn('audio play blocked or failed', playError)
      message.voiceStatus = 'readyToPlay'
      activeVoiceMessage = null
      voiceAudio = null
    }
  } catch (e) {
    console.warn('voice synthesis/playback failed', e)
    message.voiceStatus = 'error'
    activeVoiceMessage = null
    voiceAudio = null
  }
}

async function send(text) {
  const q = text ?? inputText.value.trim()
  if (!q || loading.value) return
  inputText.value = ''
  messages.value.push({ role: 'user', content: q })
  loading.value = true
  await scrollBottom()

  try {
    extractRouteHints(q)
    const res = await chatText({
      session_id: sessionId.value,
      park_code: parkCode,
      message: q,
      answer_mode: answerMode.value,
      enable_tts: false,
    })
    const answer = { role: 'ai', content: res.reply || res.answer || res.text || '（无回复）' }
    const isRouteIntent = (res.intent === 'route') || q.includes('路线') || q.includes('规划') || q.includes('怎么玩') || q.includes('怎么安排')
    if (isRouteIntent) {
      try {
        const routeRes = await planRoute(parkCode, routeParams.value)
        if (routeRes && routeRes.spots) {
          answer.routeData = {
            name: routeRes.park + '为您规划的路线',
            stops: routeRes.spots
          }
        } else if (routeRes && routeRes.routes && routeRes.routes[0]) {
          answer.routeData = {
            name: routeRes.routes[0].name || '推荐路线',
            stops: routeRes.routes[0].spots || routeRes.routes[0].stops || []
          }
        }
      } catch (e) { console.warn('路线规划失败', e) }
    }
    messages.value.push(answer)
    playResponseAction(inferResponseAction(q, answer.content, res, Boolean(answer.routeData)))
  } catch (e) {
    console.error('Chat error:', e)
    messages.value.push({ role: 'ai', content: '服务暂不可用，请稍后重试。' })
    playResponseAction('error')
  } finally {
    loading.value = false
    await scrollBottom()
  }
}

async function applyRoute(message) {
  if (!message.routeData || message.routeApplied) return
  const ok = confirm('确定将该路线固定为本次导航路线吗？一旦确认，左侧将进入导航模式。')
  if (!ok) return
  messages.value.forEach(m => { m.routeApplied = false })
  message.routeApplied = true
  activeSidebarRoute.value = message.routeData
  sidebarKey.value++
  setTimeout(async () => {
    messages.value.push({ role: 'ai', content: `好的，我已经将该路线固定在侧边栏了，导航面板会实时更新您的位置。随时可以出发！` })
    playResponseAction('happy')
    await scrollBottom()
  }, 500)
}

async function scrollBottom() {
  await nextTick()
  if (msgBox.value) msgBox.value.scrollTo({ top: msgBox.value.scrollHeight, behavior: 'smooth' })
}

function resizeRive() {
  try { riveInstance?.resizeDrawingSurfaceToCanvas() } catch (e) {}
}

onMounted(() => {
  loadGuide()
  window.addEventListener('resize', resizeRive)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeRive)
  window.clearTimeout(actionResetTimer)
  window.clearTimeout(reactionTimer)
  stopVoicePlayback()
  cleanupRive()
})

watch(activeGuideId, async () => {
  await nextTick()
  loadGuide()
})
</script>

<style scoped>
/* ── 与 chat-design.html 完全一致的样式 ── */
.rive-page {
  background: #0d0f18;
  color: #e2e8f0;
  height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 32px 16px;
  overflow: hidden;
  font-family: 'Inter', system-ui, sans-serif;
}
.rive-header { text-align: center; margin-bottom: 24px; flex-shrink: 0; }
.rive-header h1 { font-size: 24px; font-weight: 600; color: #e2e8f0; letter-spacing: 1px; margin: 0; }
.rive-header p { color: #8b95a5; font-size: 13px; margin-top: 6px; }

.main-grid {
  display: grid;
  grid-template-columns: 420px 1fr;
  gap: 24px;
  width: 100%; max-width: 1100px;
  flex: 1; min-height: 0;
}

/* ── 卡片通用 ── */
.card {
  background: #161926;
  border: 1px solid #2a2f45;
  border-radius: 16px;
  display: flex; flex-direction: column;
  overflow: hidden;
}

/* ── 左侧：展示台 ── */
.avatar-card { position: relative; }
.avatar-top {
  flex: 1; display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  padding: 24px;
  transition: all 0.6s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative; overflow: hidden;
}

.stage-circle {
  width: 320px; height: 320px; border-radius: 50%;
  background: linear-gradient(135deg, #fdfbf7 0%, #f1dfbc 50%, #e2c285 100%);
  box-shadow: inset 0 0 40px rgba(255,255,255,0.5), 0 20px 40px rgba(0,0,0,0.4);
  display: flex; align-items: center; justify-content: center;
  transition: all 0.6s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
  position: relative;
}

.rive-stage {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  display: grid;
  place-items: center;
  position: relative;
  overflow: hidden;
  background: radial-gradient(circle at 50% 48%, rgba(255,255,255,0.42), transparent 54%);
}

.rive-avatar-frame {
  width: 100%;
  height: 100%;
  transform-origin: 50% 100%;
  transition: transform 260ms ease;
}

.rive-canvas {
  width: 100%;
  height: 100%;
  display: block;
  transform-origin: 50% 58%;
  transition: transform 260ms ease, filter 260ms ease;
}

.stage-loading {
  position: absolute;
  inset: auto 24px 34px;
  min-height: 32px;
  display: grid;
  place-items: center;
  border-radius: 999px;
  background: rgba(13,15,24,0.72);
  border: 1px solid rgba(212,175,55,0.25);
  color: #f3e5c8;
  font-size: 12px;
  font-weight: 700;
}

.rive-stage.reacting .rive-canvas { animation: avatarPulse 560ms ease; }
.rive-stage.pose-listen .rive-canvas { transform: translateY(5px) rotate(-1.5deg) scale(1.025); filter: drop-shadow(0 16px 18px rgba(133, 184, 203, 0.18)); }
.rive-stage.pose-think .rive-canvas { transform: translateY(-7px) rotate(1.2deg) scale(1.018); filter: saturate(0.92) drop-shadow(0 18px 18px rgba(201, 170, 93, 0.16)); }
.rive-stage.pose-speak .rive-canvas { transform: translateY(-4px) scale(1.035); filter: contrast(1.04) drop-shadow(0 16px 18px rgba(111, 185, 143, 0.2)); }
.rive-stage.pose-happy .rive-canvas { transform: translateY(-12px) rotate(-1deg) scale(1.045); filter: brightness(1.08) saturate(1.12) drop-shadow(0 20px 20px rgba(201, 170, 93, 0.2)); }
.rive-stage.pose-point .rive-canvas { transform: translateY(-8px) rotate(-2deg) scale(1.04); filter: brightness(1.04) drop-shadow(0 18px 20px rgba(201, 170, 93, 0.22)); }
.rive-stage.pose-error .rive-canvas { transform: translateY(6px) rotate(1.8deg) scale(0.985); filter: saturate(0.78) drop-shadow(0 14px 18px rgba(215, 135, 114, 0.2)); }
.rive-stage.reaction-listen { box-shadow: 0 0 0 1px rgba(133, 184, 203, 0.55) inset, 0 0 34px rgba(133, 184, 203, 0.18); }
.rive-stage.reaction-think { box-shadow: 0 0 0 1px rgba(201, 170, 93, 0.46) inset, 0 0 34px rgba(201, 170, 93, 0.14); }
.rive-stage.reaction-speak .rive-canvas { animation: avatarSpeak 620ms ease; }
.rive-stage.reaction-happy, .rive-stage.reaction-point { box-shadow: 0 0 0 1px rgba(201, 170, 93, 0.55) inset, 0 0 34px rgba(201, 170, 93, 0.2); }
.rive-stage.reaction-error { box-shadow: 0 0 0 1px rgba(215, 135, 114, 0.52) inset, 0 0 34px rgba(215, 135, 114, 0.18); }
.rive-stage.pose-error.reacting .rive-canvas { animation: avatarError 520ms ease; }

@keyframes avatarPulse { 0%, 100% { transform: scale(1); } 45% { transform: scale(1.025); } }
@keyframes avatarSpeak { 0%, 100% { transform: translateY(0) scale(1); } 30% { transform: translateY(-6px) scale(1.018); } 62% { transform: translateY(2px) scale(0.997); } }
@keyframes avatarError { 0%, 100% { transform: translateX(0) rotate(1.8deg) scale(0.985); } 28% { transform: translateX(-8px) rotate(-1.2deg) scale(0.985); } 58% { transform: translateX(7px) rotate(1.6deg) scale(0.985); } }


.avatar-info { margin-top: 24px; text-align: center; transition: all 0.6s; }
.guide-switcher {
  width: min(100%, 360px);
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin-top: 16px;
}
.guide-choice {
  min-height: 54px;
  border: 1px solid #2a2f45;
  border-radius: 10px;
  background: #10131d;
  color: #e2e8f0;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  transition: border-color 0.2s, background 0.2s, transform 0.2s;
}
.guide-choice span { font-size: 14px; font-weight: 700; }
.guide-choice small { font-size: 10px; color: #8b95a5; white-space: nowrap; }
.guide-choice:hover { transform: translateY(-1px); border-color: rgba(212,175,55,0.62); }
.guide-choice.active { border-color: #d4af37; background: rgba(212,175,55,0.14); }

.avatar-name { font-size: 18px; font-weight: 600; margin-bottom: 4px; }
.avatar-status {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 12px; background: #1e2235; border-radius: 100px;
  font-size: 12px; color: #f3e5c8;
}
.status-dot { width: 6px; height: 6px; background: #d4af37; border-radius: 50%; }

/* 激活态 */
.has-active-route .avatar-top { flex: 0.45; padding: 16px; }
.has-active-route .stage-circle { width: 160px; height: 160px; }
.has-active-route .rive-stage { transform: scale(0.98); }
.has-active-route .avatar-info { margin-top: 15px; }
.has-active-route .avatar-name { font-size: 15px; }
.has-active-route .guide-switcher { margin-top: 10px; }
.has-active-route .guide-choice { min-height: 40px; }
.has-active-route .guide-choice small { display: none; }

/* 下半路线图 */
.avatar-bottom {
  flex: 0; opacity: 0; background: rgba(13,15,24,0.6);
  border-top: 1px solid rgba(255,255,255,0.05);
  overflow: hidden; display: flex; flex-direction: column;
  transition: all 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}
.has-active-route .avatar-bottom { flex: 0.55; opacity: 1; }

.active-route-header {
  padding: 16px 20px;
  border-bottom: 1px solid rgba(255,255,255,0.05);
  display: flex; justify-content: space-between; align-items: center;
  background: rgba(212,175,55,0.05);
}
.active-route-header h3 { font-size: 14px; font-weight: 600; color: #d4af37; display: flex; align-items: center; gap: 8px; margin: 0; }
.live-badge {
  font-size: 10px; padding: 2px 6px;
  background: rgba(52,211,153,0.2); color: #34d399;
  border-radius: 4px; border: 1px solid rgba(52,211,153,0.4);
  animation: pulse 2s infinite;
}
@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.5; } }

.large-route-container { flex: 1; position: relative; padding: 20px; }
.zigzag-svg { position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 1; }
.svg-line-bg { stroke: rgba(255,255,255,0.1); stroke-width: 2; fill: none; }
.svg-line-active { stroke: #d4af37; stroke-width: 3; fill: none; stroke-dasharray: 400; stroke-dashoffset: 400; }
.has-active-route .svg-line-active { animation: drawLine 3s ease-in-out forwards; animation-delay: 0.5s; }
@keyframes drawLine { to { stroke-dashoffset: 0; } }

.large-node { position: absolute; display: flex; align-items: center; gap: 16px; opacity: 0; transform: translateY(-50%); }
.has-active-route .large-node { animation: fadeInNode 0.5s forwards; }
@keyframes fadeInNode { to { opacity: 1; } }
.l1 { top: 15%; left: 15%; animation-delay: 0.6s !important; }
.l2 { top: 40%; left: 45%; flex-direction: row-reverse; text-align: right; animation-delay: 1.2s !important; }
.l3 { top: 65%; left: 15%; animation-delay: 1.8s !important; }
.l4 { top: 90%; left: 45%; flex-direction: row-reverse; text-align: right; animation-delay: 2.4s !important; }

.l-dot { width: 16px; height: 16px; background: #161926; border: 3px solid #2a2f45; border-radius: 50%; position: relative; z-index: 2; transition: 0.3s; }
.has-active-route .active-now .l-dot { border-color: #d4af37; background: #f3e5c8; box-shadow: 0 0 15px rgba(212,175,55,0.6); }
.has-active-route .active-now .l-dot::after { content:''; position: absolute; inset: -6px; border: 1px solid #d4af37; border-radius: 50%; animation: ripple 1.5s infinite; }
@keyframes ripple { 0% { transform: scale(0.8); opacity: 1; } 100% { transform: scale(2); opacity: 0; } }
.l-content h4 { font-size: 15px; font-weight: 600; color: #e2e8f0; margin: 0; }
.l-content p { font-size: 12px; color: #8b95a5; margin-top: 4px; }

/* ── 右侧：聊天区 ── */
.chat-card { display: flex; flex-direction: column; }
.chat-header {
  padding: 16px 20px;
  border-bottom: 1px solid #2a2f45;
  display: flex; justify-content: space-between; align-items: center;
}
.title { font-size: 14px; font-weight: 600; display: flex; align-items: center; gap: 8px; }
.answer-mode-status {
  color: #d4af37;
  font-size: 12px;
  font-weight: 700;
}

.chat-messages {
  flex: 1; padding: 20px 20px 40px 20px;
  overflow-y: auto; display: flex; flex-direction: column; gap: 20px;
  scroll-behavior: smooth;
}

.welcome-area { display: flex; flex-direction: column; gap: 12px; }
.quick-btns { display: flex; flex-wrap: wrap; gap: 8px; }
.quick-chip {
  background: #1e2235; border: 1px solid #2a2f45; color: #c8d8ff;
  border-radius: 20px; padding: 6px 14px; font-size: 13px; cursor: pointer; transition: 0.2s;
}
.quick-chip:hover { border-color: #d4af37; color: #f3e5c8; }

.msg { display: flex; flex-direction: column; max-width: 85%; }
.msg.user { align-self: flex-end; align-items: flex-end; }
.msg.ai { align-self: flex-start; align-items: flex-start; }
.msg-bubble { padding: 12px 16px; border-radius: 16px; font-size: 14px; line-height: 1.6; }
.msg.user .msg-bubble { background: #1e2235; border: 1px solid #2a2f45; border-bottom-right-radius: 4px; }
.msg.ai .msg-bubble { background: rgba(212,175,55,0.08); border: 1px solid rgba(212,175,55,0.2); border-bottom-left-radius: 4px; color: #fdfbf7; }
.msg-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid rgba(212,175,55,0.14);
}
.msg-action-btn {
  min-width: 68px;
  height: 30px;
  padding: 0 10px;
  border-radius: 999px;
  border: 1px solid rgba(226,232,240,0.14);
  background: rgba(13,15,24,0.32);
  color: #b8c2d6;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 700;
  transition: border-color 0.18s, color 0.18s, background 0.18s, transform 0.18s;
}
.msg-action-btn:hover:not(:disabled) {
  color: #f3e5c8;
  border-color: rgba(212,175,55,0.55);
  background: rgba(212,175,55,0.12);
  transform: translateY(-1px);
}
.msg-action-btn:disabled {
  cursor: wait;
  opacity: 0.72;
}
.msg-action-btn.active {
  color: #0d0f18;
  background: #d4af37;
  border-color: #d4af37;
}
.action-icon {
  width: 16px;
  text-align: center;
  line-height: 1;
}
.action-label {
  line-height: 1;
  white-space: nowrap;
}

/* 气泡内折线图 */
.route-card {
  margin-top: 12px; background: rgba(13,15,24,0.5);
  border: 1px solid #2a2f45; border-radius: 12px;
  padding: 20px; width: 320px; position: relative;
}
.route-title {
  font-size: 13px; font-weight: 600; color: #d4af37;
  margin-bottom: 20px; display: flex; align-items: center;
  justify-content: space-between; gap: 6px;
}
.btn-apply-route {
  background: #d4af37; color: #000; border: none;
  padding: 4px 10px; border-radius: 6px; font-size: 11px;
  font-weight: bold; cursor: pointer; transition: 0.2s;
}
.btn-apply-route:hover:not(.applied) { filter: brightness(1.1); transform: scale(1.05); }
.btn-apply-route.applied { background: rgba(52,211,153,0.2); color: #34d399; cursor: default; border: 1px solid rgba(52,211,153,0.4); }

.zigzag-container { position: relative; height: 240px; margin-left: 10px; }
.route-node { position: absolute; z-index: 2; display: flex; align-items: center; gap: 12px; transform: translateY(-50%); }
.node-dot { width: 12px; height: 12px; background: #0d0f18; border: 2px solid #d4af37; border-radius: 50%; box-shadow: 0 0 10px rgba(212,175,55,0.3); }
.node-content h4 { font-size: 13px; font-weight: 500; color: #e2e8f0; margin: 0; }
.node-content p { font-size: 11px; color: #8b95a5; margin-top: 2px; }
.n1 { top: 10%; left: 10%; }
.n2 { top: 35%; left: 40%; flex-direction: row-reverse; text-align: right; }
.n3 { top: 60%; left: 10%; }
.n4 { top: 85%; left: 40%; flex-direction: row-reverse; text-align: right; }

/* 输入区 */
.chat-input-area { padding: 16px 20px; border-top: 1px solid #2a2f45; background: #161926; }
.answer-mode-tabs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-bottom: 10px;
}
.mode-tab {
  min-height: 34px;
  border: 1px solid #2a2f45;
  border-radius: 8px;
  background: #10131d;
  color: #8b95a5;
  cursor: pointer;
  font-size: 12px;
  font-weight: 700;
  transition: border-color .2s, background .2s, color .2s;
}
.mode-tab:hover { border-color: rgba(212,175,55,.62); color: #f3e5c8; }
.mode-tab.active { border-color: #d4af37; background: rgba(212,175,55,.14); color: #f3e5c8; }
.input-box {
  display: flex; align-items: center;
  background: #0d0f18; border: 1px solid #2a2f45;
  border-radius: 24px; padding: 4px 4px 4px 16px;
  transition: border-color 0.2s;
}
.input-box:focus-within { border-color: #d4af37; }
.input-box input { flex: 1; background: transparent; border: none; outline: none; color: #e2e8f0; font-size: 14px; }
.input-box input::placeholder { color: #8b95a5; }
.btn-voice {
  width: 36px; height: 36px; border-radius: 50%;
  background: #1e2235; border: none; color: #e2e8f0;
  cursor: pointer; display: flex; align-items: center; justify-content: center;
}
.btn-send {
  width: 36px; height: 36px; border-radius: 50%;
  background: #d4af37; border: none; color: #000;
  font-weight: bold; cursor: pointer; margin-left: 8px;
}
</style>
