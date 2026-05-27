<template>
  <div class="overlay" @click.self="$emit('close')">
    <div class="card">
      <h2 class="title">保存游览纪念</h2>

      <!-- 加载中 -->
      <div v-if="loading" class="loading-area">
        <div class="spinner" />
        <p>正在生成专属纪念卡…</p>
      </div>

      <!-- 图片显示 -->
      <template v-else>
        <div class="img-wrap">
          <img v-if="cardSrc" :src="cardSrc" class="card-img" alt="游览纪念卡" />
          <!-- html2canvas 降级 DOM -->
          <div v-else ref="canvasDom" class="fallback-card">
            <div class="fc-park">{{ parkDisplayName }}</div>
            <div class="fc-summary">{{ summary }}</div>
            <div class="fc-spots">{{ visitedSpots.join(' · ') }}</div>
            <div class="fc-time">游览时长 {{ elapsedMinutes }} 分钟</div>
            <div class="fc-date">{{ dateStr }}</div>
          </div>
        </div>

        <div class="action-row">
          <button class="btn primary" @click="download">💾 保存图片</button>
          <button class="btn ghost" @click="$emit('close')">关闭</button>
        </div>
        <p class="tip">长按图片可直接分享给好友</p>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getSummary, getShareCard } from '../api.js'

const props = defineProps({
  sessionId: String,
  parkCode: String,
  visitedSpots: { type: Array, default: () => [] },
  elapsedMinutes: { type: Number, default: 0 },
})
defineEmits(['close'])

const PARK_NAMES = { zhuozhengyuan: '拙政园', liuyuan: '留园' }
const parkDisplayName = computed(() => PARK_NAMES[props.parkCode] || props.parkCode || '园林')

const loading = ref(true)
const cardSrc = ref('')    // base64 PNG from Pillow
const summary = ref('')
const canvasDom = ref(null)

const now = new Date()
const dateStr = `${now.getFullYear()}年${now.getMonth()+1}月${now.getDate()}日`

onMounted(async () => {
  // 1. 获取 LLM 摘要
  try {
    const r = await getSummary({
      session_id: props.sessionId,
      park_code: props.parkCode,
      spots: props.visitedSpots,
      elapsed_minutes: props.elapsedMinutes,
    })
    summary.value = r.summary || `畅游${parkDisplayName.value}，流连忘返`
  } catch (e) {
    summary.value = `畅游${parkDisplayName.value}，流连忘返`
  }

  // 2. 尝试 Pillow 生成分享卡
  try {
    const r = await getShareCard({
      session_id: props.sessionId,
      park_code: props.parkCode,
      spots: props.visitedSpots,
      elapsed_minutes: props.elapsedMinutes,
      summary: summary.value,
    })
    if (r.image_base64) {
      cardSrc.value = `data:image/png;base64,${r.image_base64}`
    }
  } catch (e) {
    console.warn('Pillow share card failed, falling back to html2canvas', e)
  }

  // 3. 若 Pillow 失败，用 html2canvas 降级
  if (!cardSrc.value) {
    try {
      const html2canvas = (await import('html2canvas')).default
      await new Promise(r => setTimeout(r, 100)) // wait for DOM
      if (canvasDom.value) {
        const canvas = await html2canvas(canvasDom.value, { scale: 2, useCORS: true })
        cardSrc.value = canvas.toDataURL('image/png')
      }
    } catch (e) {
      console.warn('html2canvas failed', e)
    }
  }

  loading.value = false
})

function download() {
  if (!cardSrc.value) return
  const a = document.createElement('a')
  a.href = cardSrc.value
  a.download = `${parkDisplayName.value}_游览纪念.png`
  a.click()
}
</script>

<style scoped>
.overlay {
  position: fixed; inset: 0; z-index: 1000;
  background: rgba(0,0,0,0.7);
  display: flex; align-items: center; justify-content: center;
  padding: 20px;
}
.card {
  background: #fff;
  border-radius: 20px;
  padding: 24px 20px;
  width: 100%; max-width: 420px;
  display: flex; flex-direction: column; align-items: center; gap: 16px;
  animation: slideUp 0.3s ease;
}
@keyframes slideUp {
  from { transform: translateY(40px); opacity: 0; }
  to   { transform: translateY(0);    opacity: 1; }
}
.title { font-size: 20px; font-weight: 700; color: #222; margin: 0; }
.loading-area {
  display: flex; flex-direction: column; align-items: center; gap: 14px;
  padding: 40px 0; color: #888;
}
.spinner {
  width: 40px; height: 40px;
  border: 3px solid #eee;
  border-top-color: #2c7be5;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.img-wrap { width: 100%; }
.card-img { width: 100%; border-radius: 12px; box-shadow: 0 4px 16px rgba(0,0,0,0.1); }

/* 降级 DOM 卡片 */
.fallback-card {
  width: 100%;
  background: linear-gradient(135deg, #1a3a2a 0%, #2d6a4f 100%);
  border-radius: 12px;
  padding: 28px 24px;
  color: #fff;
  font-family: 'Noto Serif SC', serif;
  box-sizing: border-box;
}
.fc-park { font-size: 26px; font-weight: 700; margin-bottom: 10px; letter-spacing: 2px; }
.fc-summary { font-size: 16px; line-height: 1.6; margin-bottom: 14px; color: #b7e4c7; }
.fc-spots { font-size: 13px; color: #95d5b2; margin-bottom: 8px; }
.fc-time { font-size: 13px; color: #ccc; }
.fc-date { font-size: 13px; color: #aaa; margin-top: 4px; }

.action-row { display: flex; gap: 12px; width: 100%; }
.btn {
  flex: 1; padding: 13px; border-radius: 12px; border: none;
  font-size: 16px; font-weight: 600; cursor: pointer;
}
.btn.primary { background: #2c7be5; color: #fff; }
.btn.ghost { background: #fff; color: #888; border: 1px solid #ddd; }
.tip { font-size: 13px; color: #aaa; margin: 0; }
</style>
