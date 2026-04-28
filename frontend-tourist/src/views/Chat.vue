<template>
  <div class="layout">
    <!-- 左：数字人画面 -->
    <div class="avatar-pane">
      <iframe v-if="streamUrl" :src="streamUrl" frameborder="0" allow="autoplay; microphone"></iframe>
      <div v-else class="avatar-placeholder">
        <div class="avatar-circle">数字人</div>
        <p>正在连接数字人...（未配置 LiveTalking 时显示此占位图）</p>
      </div>
      <div class="actions">
        <button class="btn ghost" @click="onInterrupt">⏸ 打断</button>
      </div>
    </div>

    <!-- 右：对话气泡 -->
    <div class="chat-pane">
      <div class="head">
        <strong>{{ parkName }}</strong>
        <a href="#/preference" class="back">← 重新规划</a>
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
        <div v-if="loading" class="msg assistant"><div class="bubble">正在思考…</div></div>
      </div>
      <div class="input-bar">
        <textarea v-model="input" placeholder="输入问题，或按住下方按钮说话…"
                  @keydown.enter.exact.prevent="send" rows="2"></textarea>
        <button class="btn" :disabled="loading || !input.trim()" @click="send">发送</button>
        <button class="btn ghost"
                @mousedown="startRec" @mouseup="stopRec"
                @touchstart.prevent="startRec" @touchend.prevent="stopRec">
          {{ recording ? '🎤 录音中…' : '🎤 按住说话' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { nextTick, onMounted, ref } from 'vue'
import { chatText, getAvatarStream, interrupt } from '../api.js'

const parkName = sessionStorage.getItem('park_name') || '苏州园林'
const sessionId = ref(crypto.randomUUID().slice(0, 16))
const streamUrl = ref('')
const messages = ref([])
const input = ref('')
const loading = ref(false)
const recording = ref(false)
const msgBox = ref(null)
let mediaRecorder = null
let chunks = []
let audio = null

onMounted(async () => {
  // 数字人画面
  try {
    const r = await getAvatarStream({ session_id: sessionId.value })
    sessionId.value = r.session_id
    streamUrl.value = r.url
  } catch (e) { /* 占位即可 */ }

  // 路线开场白
  const route = JSON.parse(sessionStorage.getItem('route') || 'null')
  if (route?.narrative) {
    push('assistant', route.narrative)
  } else {
    push('assistant', `欢迎来到${parkName}！请问想了解什么？`)
  }
})

function push(role, content, citations = []) {
  messages.value.push({ role, content, citations })
  nextTick(() => { msgBox.value && (msgBox.value.scrollTop = msgBox.value.scrollHeight) })
}

async function send() {
  const text = input.value.trim()
  if (!text || loading.value) return
  push('user', text)
  input.value = ''
  loading.value = true
  try {
    const r = await chatText({ session_id: sessionId.value, message: text })
    push('assistant', r.answer, r.citations)
    if (r.audio_url) {
      try { audio?.pause() } catch (e) {}
      audio = new Audio(r.audio_url)
      audio.play().catch(() => {})
    }
  } catch (e) {
    push('assistant', '抱歉，服务暂时不可用。')
  } finally {
    loading.value = false
  }
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
  } catch (e) {
    alert('无法访问麦克风：' + e.message)
  }
}

function stopRec() {
  if (!recording.value) return
  recording.value = false
  try { mediaRecorder?.stop() } catch (e) {}
}

async function uploadAudio() {
  const blob = new Blob(chunks, { type: 'audio/webm' })
  const fd = new FormData()
  fd.append('session_id', sessionId.value)
  fd.append('audio', blob, 'recording.webm')
  loading.value = true
  push('user', '🎤（语音消息）')
  try {
    const resp = await fetch('/api/chat/voice', { method: 'POST', body: fd })
    const r = await resp.json()
    push('assistant', r.answer, r.citations)
    if (r.audio_url) { audio = new Audio(r.audio_url); audio.play().catch(() => {}) }
  } catch (e) {
    push('assistant', '语音识别失败。')
  } finally {
    loading.value = false
  }
}

async function onInterrupt() {
  try { audio?.pause() } catch (e) {}
  await interrupt(sessionId.value)
}
</script>

<style scoped>
.layout { display: grid; grid-template-columns: 1fr 1.2fr; height: 100vh; }
.avatar-pane { background: #1a1d2b; display: flex; flex-direction: column; align-items: center; justify-content: center; position: relative; }
.avatar-pane iframe { width: 100%; height: 100%; }
.avatar-placeholder { color: #ccc; text-align: center; }
.avatar-circle { width: 140px; height: 140px; border-radius: 50%; background: linear-gradient(135deg, #2c7be5, #6f42c1); margin: 0 auto 20px; display: flex; align-items: center; justify-content: center; color: #fff; font-size: 18px; }
.actions { position: absolute; bottom: 20px; }
.chat-pane { display: flex; flex-direction: column; background: #fff; }
.head { padding: 14px 20px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; }
.back { color: #2c7be5; text-decoration: none; font-size: 13px; }
.messages { flex: 1; overflow-y: auto; padding: 20px; }
.msg { margin: 10px 0; display: flex; }
.msg.user { justify-content: flex-end; }
.bubble { max-width: 78%; padding: 10px 14px; border-radius: 10px; line-height: 1.6; white-space: pre-wrap; }
.msg.user .bubble { background: #2c7be5; color: #fff; }
.msg.assistant .bubble { background: #f0f2f7; color: #222; }
.cites { font-size: 12px; color: #888; margin-top: 6px; }
.input-bar { padding: 12px 16px; border-top: 1px solid #eee; display: grid; grid-template-columns: 1fr auto auto; gap: 8px; }
textarea { resize: none; border: 1px solid #ddd; border-radius: 6px; padding: 8px; font-size: 14px; }
@media (max-width: 800px) { .layout { grid-template-columns: 1fr; grid-template-rows: 240px 1fr; } }
</style>
