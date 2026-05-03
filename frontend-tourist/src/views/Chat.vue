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
        <a href="#/preference" class="back">← 重新规划</a>
      </div>
      <button class="interrupt-btn" @click="onInterrupt" title="打断播报">⏸</button>
    </div>

    <!-- 下：对话面板 -->
    <div class="chat-pane">
      <div class="messages" ref="msgBox">
        <div v-for="(m, i) in messages" :key="i" :class="['msg', m.role]">
          <div class="bubble">
            <div>{{ m.content }}</div>
            <div v-if="m.citations && m.citations.length" class="cites">
              出处：<span v-for="(c, idx) in m.citations" :key="idx">「{{ c.title }}」 </span>
            </div>
          </div>
        </div>
        <div v-if="loading" class="msg assistant"><div class="bubble">正在思考…</div></div>
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
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { chatText, getAvatarStream, getChatSuggestions, interrupt } from '../api.js'
import VrmAvatar from '../components/VrmAvatar.vue'

// 未上传 VRM 时的 demo 资产（three-vrm 官方示例，CDN）
// 生产环境请到 admin 后台上传自己的 .vrm
const SAMPLE_VRM_URL = 'https://cdn.jsdelivr.net/gh/pixiv/three-vrm@release/packages/three-vrm/examples/models/VRM1_Constraint_Twist_Sample.vrm'

const parkName = sessionStorage.getItem('park_name') || '苏州园林'
const parkCode = sessionStorage.getItem('park_code') || ''
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

  const route = JSON.parse(sessionStorage.getItem('route') || 'null')
  if (route?.narrative) {
    push('assistant', route.narrative)
    currentEmotion.value = 'joy'
    currentMotion.value = 'wave'
  } else {
    push('assistant', `欢迎来到${parkName}！请问想了解什么？`)
    currentEmotion.value = 'joy'
    currentMotion.value = 'wave'
  }
})

function push(role, content, citations = []) {
  messages.value.push({ role, content, citations })
  nextTick(() => { msgBox.value && (msgBox.value.scrollTop = msgBox.value.scrollHeight) })
}

function applyResponse(r) {
  push('assistant', r.answer, r.citations)
  currentEmotion.value = r.emotion || 'neutral'
  currentMotion.value = r.motion || avatar.default_motion || 'idle'
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
  try {
    const r = await chatText({
      session_id: sessionId.value, message: text,
      avatar_code: avatar.code || undefined,
      park_code: parkCode || undefined,
    })
    applyResponse(r)
  } catch (e) {
    push('assistant', '抱歉，服务暂时不可用。')
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
</script>

<style scoped>
/* 竖屏主布局（默认 1080×1920）：上 60vh 数字人，下 40vh 对话 */
.layout {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100vh;
  height: 100dvh;
  background: #0f1220;
  overflow: hidden;
}

.avatar-pane {
  position: relative;
  flex: 0 0 60vh;
  background: linear-gradient(180deg, #1f2233 0%, #2a2e44 100%);
  overflow: hidden;
}
.vrm-fill { position: absolute; inset: 0; }
.top-bar {
  position: absolute;
  top: env(safe-area-inset-top, 0);
  left: 0; right: 0;
  padding: 16px 20px;
  display: flex; justify-content: space-between; align-items: center;
  color: #fff;
  z-index: 2;
  pointer-events: none;
}
.top-bar .title { font-size: clamp(18px, 3.2vw, 28px); letter-spacing: 1px; }
.top-bar .back {
  pointer-events: auto;
  color: #a8c4ff; text-decoration: none;
  font-size: clamp(13px, 2vw, 18px);
  background: rgba(0,0,0,0.25); padding: 8px 14px; border-radius: 999px;
}
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
  flex: 1 1 40vh;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 20px 20px 0 0;
  box-shadow: 0 -6px 20px rgba(0,0,0,0.25);
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
  padding: 10px 14px 14px;
  border-top: 1px solid #eef0f5;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
  align-items: stretch;
}
textarea {
  resize: none;
  border: 1px solid #ddd;
  border-radius: 10px;
  padding: 10px 12px;
  font-size: clamp(15px, 2.6vw, 20px);
  font-family: inherit;
  outline: none;
}
textarea:focus { border-color: #2c7be5; }
.btn-col { display: flex; flex-direction: column; gap: 6px; }
.btn {
  border: none;
  border-radius: 10px;
  padding: 0 18px;
  min-width: clamp(72px, 12vw, 110px);
  min-height: 44px;
  font-size: clamp(14px, 2.4vw, 18px);
  cursor: pointer;
}
.btn.primary { background: #2c7be5; color: #fff; }
.btn.primary:disabled { background: #a8c0e8; cursor: not-allowed; }
.btn.ghost { background: #fff; color: #2c7be5; border: 1px solid #2c7be5; }
.btn.ghost:active { background: #f4f8ff; }

/* 横屏 / 宽屏（开发机调试）：恢复左右双栏 */
@media (orientation: landscape) and (min-width: 1024px) {
  .layout { flex-direction: row; }
  .avatar-pane { flex: 1 1 50%; }
  .chat-pane { flex: 1 1 50%; border-radius: 0; box-shadow: none; }
  .top-bar { color: #fff; }
}
</style>
