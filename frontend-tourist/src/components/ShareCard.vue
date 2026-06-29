<template>
  <div class="overlay" @click.self="$emit('close')">
    <div class="card">
      <h2 class="title">{{ parkCode === 'lingshan' ? '保存祈福签文' : '保存游览纪念' }}</h2>

      <!-- 加载中 -->
      <div v-if="loading" class="loading-area">
        <div class="spinner" />
        <p>正在生成专属纪念卡…</p>
      </div>

      <!-- 图片显示 -->
      <template v-else>
        <div class="img-wrap">
          <!-- 图片：移动端长按可保存；桌面端点击可下载 -->
          <img
            v-if="cardSrc"
            :src="cardSrc"
            class="card-img"
            alt="游览纪念卡"
            title="长按图片保存到相册"
            @contextmenu.prevent
          />
          <!-- html2canvas 降级 DOM -->
          <div
            v-else
            ref="canvasDom"
            class="fallback-card"
            :class="{ 'zen-style': parkCode === 'lingshan' }"
            :style="parkCode === 'lingshan'
              ? { backgroundImage: `url(${randomBg})`, backgroundSize: 'cover', backgroundPosition: 'center' }
              : {}"
          >
            <div class="fc-park">{{ parkDisplayName }}</div>
            <div class="fc-summary">{{ summary }}</div>
            <div class="fc-spots">{{ visitedSpots.join(' · ') }}</div>
            <div class="fc-time">游览时长 {{ elapsedMinutes }} 分钟</div>
            <div class="fc-date">{{ dateStr }}</div>
          </div>
        </div>

        <div class="action-row">
          <!-- 移动端：优先调系统分享；桌面：直接下载 -->
          <button class="btn primary" @click="saveOrShare">
            {{ isMobile ? '📲 保存 / 分享' : '💾 保存图片' }}
          </button>
          <button class="btn ghost" @click="$emit('close')">关闭</button>
        </div>

        <!-- 移动端提示 -->
        <p v-if="isMobile" class="tip">👆 长按上方图片可直接保存到相册</p>
        <p v-else class="tip">点击「保存图片」即可下载到本地</p>

        <!-- Toast 提示 -->
        <transition name="toast-fade">
          <div v-if="toastMsg" class="toast">{{ toastMsg }}</div>
        </transition>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getSummary, getShareCard } from '../api.js'

const randomBg = ref('')

const props = defineProps({
  sessionId: String,
  parkCode: String,
  visitedSpots: { type: Array, default: () => [] },
  elapsedMinutes: { type: Number, default: 0 },
})
defineEmits(['close'])

const PARK_NAMES = { lingshan: '灵山胜境', liuyuan: '留园' }
const parkDisplayName = computed(() => PARK_NAMES[props.parkCode] || props.parkCode || '园林')

const loading = ref(true)
const cardSrc = ref('')    // base64 PNG from Pillow
const summary = ref('')
const canvasDom = ref(null)

const now = new Date()
const dateStr = `${now.getFullYear()}年${now.getMonth()+1}月${now.getDate()}日`

onMounted(async () => {
  const bgs = [
    '/images/blessing_anime.png',
    '/images/blessing_real.png',
    '/images/blessing_watercolor.png',
    '/images/blessing_ink.png',
    '/images/blessing_3d.png'
  ]
  randomBg.value = bgs[Math.floor(Math.random() * bgs.length)]

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

// 检测是否移动端
const isMobile = /Android|iPhone|iPad|iPod|Mobile/i.test(
  typeof navigator !== 'undefined' ? navigator.userAgent : ''
)

// Toast
const toastMsg = ref('')
function showToast(msg, ms = 2500) {
  toastMsg.value = msg
  setTimeout(() => { toastMsg.value = '' }, ms)
}

// 保存 / 分享
async function saveOrShare() {
  if (!cardSrc.value) return

  const suffix = props.parkCode === 'lingshan' ? '祈福签文' : '游览纪念'
  const filename = `${parkDisplayName.value}_${suffix}.png`

  // ① 移动端：优先使用 Web Share API（微信内置浏览器也支持）
  if (isMobile && navigator.share) {
    try {
      // 将 base64 转成 File 对象
      const res = await fetch(cardSrc.value)
      const blob = await res.blob()
      const file = new File([blob], filename, { type: 'image/png' })
      if (navigator.canShare && navigator.canShare({ files: [file] })) {
        await navigator.share({ files: [file], title: filename })
        return
      }
    } catch (e) {
      // 用户取消 or 不支持文件分享，继续尝试下载
    }
    // ② 移动端回退：a 标签触发下载（部分安卓支持）
    try {
      const a = document.createElement('a')
      a.href = cardSrc.value
      a.download = filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      showToast('图片已保存，请查看下载记录 📥')
    } catch (_) {
      showToast('请长按上方图片，选择「保存图片」')
    }
    return
  }

  // ③ 桌面端：直接下载
  const a = document.createElement('a')
  a.href = cardSrc.value
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  showToast('图片已下载 ✅')
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
.fallback-card.zen-style {
  background-color: #dfd8cf; /* fallback color */
  color: #3b312b;
  border: 1px solid #c8bdae;
  box-shadow: inset 0 0 20px rgba(0,0,0,0.05);
  position: relative;
}
.fallback-card.zen-style::before {
  content: '';
  position: absolute;
  inset: 0;
  background: rgba(255, 255, 255, 0.65); /* white overlay to ensure text is readable */
  border-radius: 12px;
  z-index: 0;
}
.fallback-card.zen-style > * {
  position: relative;
  z-index: 1;
}
.fc-park { font-size: 26px; font-weight: 700; margin-bottom: 10px; letter-spacing: 2px; }
.fc-summary { font-size: 16px; line-height: 1.6; margin-bottom: 14px; color: #b7e4c7; }
.zen-style .fc-summary { color: #5a4b41; font-weight: 600; }
.fc-spots { font-size: 13px; color: #95d5b2; margin-bottom: 8px; }
.zen-style .fc-spots { color: #857467; }
.fc-time { font-size: 13px; color: #ccc; }
.zen-style .fc-time { color: #9a8a7a; }
.fc-date { font-size: 13px; color: #aaa; margin-top: 4px; }
.zen-style .fc-date { color: #aba094; }

.action-row { display: flex; gap: 12px; width: 100%; }
.btn {
  flex: 1; padding: 13px; border-radius: 12px; border: none;
  font-size: 16px; font-weight: 600; cursor: pointer;
  transition: opacity 0.15s;
}
.btn:active { opacity: 0.8; }
.btn.primary { background: linear-gradient(135deg, #2c7be5, #1a5bbf); color: #fff; }
.btn.ghost { background: #fff; color: #888; border: 1px solid #ddd; }
.tip { font-size: 13px; color: #aaa; margin: 0; }

/* 图片长按样式 */
.card-img { -webkit-user-select: none; user-select: none; }

/* Toast */
.toast {
  position: fixed;
  bottom: 80px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0,0,0,0.75);
  color: #fff;
  font-size: 14px;
  padding: 10px 20px;
  border-radius: 24px;
  white-space: nowrap;
  z-index: 2000;
  pointer-events: none;
}
.toast-fade-enter-active, .toast-fade-leave-active { transition: opacity 0.3s; }
.toast-fade-enter-from, .toast-fade-leave-to { opacity: 0; }
</style>
