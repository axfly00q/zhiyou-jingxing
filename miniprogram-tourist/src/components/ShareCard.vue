<template>
  <view v-if="visible" class="sc-overlay" @tap.self="close">
    <view class="sc-modal">
      <view class="sc-title">{{ isLingshan ? '保存祈福签文' : '保存游览纪念' }}</view>

      <!-- 加载中 -->
      <view v-if="loading" class="sc-loading">
        <view class="sc-spinner" />
        <text class="sc-loading-text">正在生成专属纪念卡…</text>
      </view>

      <!-- 卡片预览 -->
      <view v-else class="sc-content">
        <!--
          canvas 用于离屏绘制（设为 1px 透明，避免微信不渲染）
          必须保持挂在 DOM 里，canvasToTempFilePath 才能工作
        -->
        <canvas
          type="2d"
          id="shareCardCanvas"
          class="sc-canvas-hidden"
        />

        <!-- 预览图 -->
        <image
          v-if="previewSrc"
          :src="previewSrc"
          class="sc-preview"
          mode="widthFix"
          show-menu-by-longpress
        />
        <view v-else class="sc-no-preview">
          <text>卡片生成失败，请重试</text>
        </view>

        <!-- 操作按钮 -->
        <view class="sc-actions">
          <button class="sc-btn sc-btn-primary" @tap="saveToAlbum" :disabled="saving || !previewSrc">
            {{ saving ? '保存中…' : '📥 保存到相册' }}
          </button>
          <button class="sc-btn sc-btn-share" @tap="shareToFriend" :disabled="saving || !previewSrc">
            📤 分享给好友
          </button>
          <button class="sc-btn sc-btn-ghost" @tap="close">关闭</button>
        </view>

        <text class="sc-tip">长按图片也可直接保存 / 分享</text>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { buildApiUrl } from '../api.js'

const props = defineProps({
  visible:        { type: Boolean, default: false },
  sessionId:      { type: String,  default: '' },
  parkCode:       { type: String,  default: '' },
  parkName:       { type: String,  default: '' },
  visitedSpots:   { type: Array,   default: () => [] },
  elapsedMinutes: { type: Number,  default: 0 },
})
const emit = defineEmits(['close'])

const isLingshan = computed(() => props.parkCode === 'lingshan')

// ─── 本地图片库 ──────────────────────────────────────────
// 禅意/祈福背景（灵山）
const LINGSHAN_BG_LIST = [
  '/static/blessing_anime.png',
  '/static/blessing_real.png',
  '/static/blessing_watercolor.png',
  '/static/blessing_ink.png',
  '/static/blessing_3d.png',
]
// 通用景色背景（其他园区）
const GENERAL_BG_LIST = [
  '/static/lingshan_bg.png',
  '/static/lingshan_arch.png',
  '/static/lingshan_circle.png',
]

function pickRandomBg() {
  const list = isLingshan.value ? LINGSHAN_BG_LIST : GENERAL_BG_LIST
  return list[Math.floor(Math.random() * list.length)]
}
// ─────────────────────────────────────────────────────────

const loading      = ref(false)
const saving       = ref(false)
const previewSrc   = ref('')      // 本地临时路径（用于 image 和 saveImageToPhotosAlbum）
const tempFilePath = ref('')

const now    = new Date()
const dateStr = `${now.getFullYear()}年${now.getMonth()+1}月${now.getDate()}日`

watch(() => props.visible, (v) => {
  if (v) generateCard()
})

// ═══════════════════════════════════════════════════════
// 1. 主流程：生成卡片
// ═══════════════════════════════════════════════════════
async function generateCard() {
  loading.value    = true
  previewSrc.value = ''
  tempFilePath.value = ''

  // ① 尝试后端 Pillow 接口
  let backendBase64 = ''
  try {
    const summaryRes = await uniRequest('/share/summary', {
      session_id:      props.sessionId,
      park_code:       props.parkCode,
      spots:           props.visitedSpots,
      elapsed_minutes: props.elapsedMinutes,
    })
    const cardRes = await uniRequest('/share/card', {
      session_id:      props.sessionId,
      park_code:       props.parkCode,
      spots:           props.visitedSpots,
      elapsed_minutes: props.elapsedMinutes,
      summary:         summaryRes?.summary || '',
    })
    backendBase64 = cardRes?.image_base64 || ''
  } catch (e) {
    console.warn('[ShareCard] backend API failed:', e)
  }

  if (backendBase64) {
    // 后端成功 → 写本地文件
    const localPath = writeBase64ToLocal(backendBase64)
    if (localPath) {
      previewSrc.value   = localPath
      tempFilePath.value = localPath
      loading.value = false
      return
    }
  }

  // ② 降级：Canvas 2D 绘制（以本地图片库做背景）
  const bgPath = pickRandomBg()
  const canvasOk = await drawCanvas(bgPath)
  if (canvasOk) {
    loading.value = false
    return
  }

  // ③ 最终降级：Canvas 失败，直接拿一张本地图片展示
  console.warn('[ShareCard] canvas failed, using raw local image')
  previewSrc.value   = bgPath    // 直接展示图库里的图
  tempFilePath.value = bgPath
  loading.value = false
}

// ═══════════════════════════════════════════════════════
// 2. Canvas 2D 绘制
// ═══════════════════════════════════════════════════════
const CANVAS_W = 630
const CANVAS_H = 420

async function drawCanvas(bgPath) {
  return new Promise((resolve) => {
    uni.createSelectorQuery()
      .select('#shareCardCanvas')
      .fields({ node: true, size: true })
      .exec(async (res) => {
        const canvasNode = res?.[0]?.node
        if (!canvasNode) { resolve(false); return }

        try {
          const dpr = uni.getSystemInfoSync().pixelRatio || 2
          canvasNode.width  = CANVAS_W * dpr
          canvasNode.height = CANVAS_H * dpr
          const ctx = canvasNode.getContext('2d')
          ctx.scale(dpr, dpr)

          // —— 绘制背景图 ——
          const bgDrawn = await drawBgImage(ctx, canvasNode, bgPath)
          if (!bgDrawn) {
            // 图片加载失败 → 用渐变色兜底
            drawGradientBg(ctx, isLingshan.value)
          }

          // —— 白色半透明遮罩（让文字可读）——
          ctx.fillStyle = 'rgba(255,255,255,0.58)'
          ctx.fillRect(0, 0, CANVAS_W, CANVAS_H)

          // —— 圆角边框 ——
          roundRect(ctx, 10, 10, CANVAS_W - 20, CANVAS_H - 20, 10)
          ctx.strokeStyle = isLingshan.value ? 'rgba(120,90,60,0.3)' : 'rgba(60,100,80,0.3)'
          ctx.lineWidth   = 1.5
          ctx.stroke()

          // —— 公园名 ——
          ctx.fillStyle  = isLingshan.value ? '#3b2a1a' : '#1a3a2a'
          ctx.font       = `bold 34px serif`
          ctx.fillText(props.parkName || '灵山胜境', 36, 70)

          // —— 分割线 ——
          ctx.strokeStyle = isLingshan.value ? 'rgba(100,80,60,0.25)' : 'rgba(40,80,60,0.25)'
          ctx.lineWidth   = 1
          ctx.beginPath()
          ctx.moveTo(36, 88); ctx.lineTo(CANVAS_W - 36, 88)
          ctx.stroke()

          // —— 景点列表 ——
          const spots = (props.visitedSpots || []).join(' · ') || '游览中'
          ctx.fillStyle = isLingshan.value ? '#5a4030' : '#2a5040'
          ctx.font      = '20px sans-serif'
          wrapText(ctx, spots, 36, 122, CANVAS_W - 72, 28, 3)

          // —— 时间 & 日期 ——
          ctx.fillStyle = isLingshan.value ? '#9a7a6a' : '#4a7a60'
          ctx.font      = '18px sans-serif'
          ctx.fillText(`游览时长 ${props.elapsedMinutes} 分钟`, 36, CANVAS_H - 56)
          ctx.fillText(dateStr, 36, CANVAS_H - 30)

          // —— 水印 ——
          ctx.fillStyle = 'rgba(100,80,60,0.2)'
          ctx.font      = '14px sans-serif'
          ctx.fillText('智游景行', CANVAS_W - 90, CANVAS_H - 18)

          // —— 导出 ——
          uni.canvasToTempFilePath({
            canvas:   canvasNode,
            fileType: 'png',
            quality:  1,
            success: (r) => {
              previewSrc.value   = r.tempFilePath
              tempFilePath.value = r.tempFilePath
              resolve(true)
            },
            fail: (e) => {
              console.warn('[ShareCard] canvasToTempFilePath failed:', e)
              resolve(false)
            },
          })
        } catch (e) {
          console.warn('[ShareCard] canvas draw error:', e)
          resolve(false)
        }
      })
  })
}

// 把本地图片画进 canvas（返回 Promise<boolean>）
function drawBgImage(ctx, canvasNode, path) {
  return new Promise((resolve) => {
    const img = canvasNode.createImage()
    img.onload  = () => {
      try {
        ctx.drawImage(img, 0, 0, CANVAS_W, CANVAS_H)
        resolve(true)
      } catch (e) {
        resolve(false)
      }
    }
    img.onerror = () => resolve(false)
    img.src = path
  })
}

// 渐变色兜底
function drawGradientBg(ctx, lingshan) {
  const grad = ctx.createLinearGradient(0, 0, CANVAS_W, CANVAS_H)
  if (lingshan) {
    grad.addColorStop(0, '#e8ddd0'); grad.addColorStop(1, '#c8b8a0')
  } else {
    grad.addColorStop(0, '#c9e4ca'); grad.addColorStop(1, '#7bbf8e')
  }
  ctx.fillStyle = grad
  ctx.fillRect(0, 0, CANVAS_W, CANVAS_H)
}

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath()
  ctx.moveTo(x + r, y)
  ctx.lineTo(x + w - r, y); ctx.arcTo(x + w, y, x + w, y + r, r)
  ctx.lineTo(x + w, y + h - r); ctx.arcTo(x + w, y + h, x + w - r, y + h, r)
  ctx.lineTo(x + r, y + h); ctx.arcTo(x, y + h, x, y + h - r, r)
  ctx.lineTo(x, y + r); ctx.arcTo(x, y, x + r, y, r)
  ctx.closePath()
}

function wrapText(ctx, text, x, y, maxW, lineH, maxLines) {
  const chars = text.split('')
  let line = '', lineCount = 0
  for (const ch of chars) {
    const test = line + ch
    if (ctx.measureText(test).width > maxW) {
      if (lineCount >= maxLines - 1) { ctx.fillText(line + '…', x, y + lineCount * lineH); return }
      ctx.fillText(line, x, y + lineCount * lineH)
      line = ch; lineCount++
    } else { line = test }
  }
  if (line) ctx.fillText(line, x, y + lineCount * lineH)
}

// ═══════════════════════════════════════════════════════
// 3. 保存到相册
// ═══════════════════════════════════════════════════════
async function saveToAlbum() {
  if (!tempFilePath.value || saving.value) return
  saving.value = true
  try {
    await new Promise((resolve, reject) => {
      uni.saveImageToPhotosAlbum({
        filePath: tempFilePath.value,
        success:  resolve,
        fail:     reject,
      })
    })
    uni.showToast({ title: '已保存到相册 🎉', icon: 'success', duration: 2000 })
  } catch (e) {
    const msg = String(e?.errMsg || '')
    if (msg.includes('auth') || msg.includes('deny')) {
      uni.showModal({
        title: '需要相册权限', content: '请在设置中开启相册写入权限，才能保存图片',
        confirmText: '去设置',
        success: (r) => { if (r.confirm) uni.openSetting({}) },
      })
    } else {
      uni.showToast({ title: '保存失败，请重试', icon: 'none' })
    }
  } finally {
    saving.value = false
  }
}

// ═══════════════════════════════════════════════════════
// 4. 分享给好友
// ═══════════════════════════════════════════════════════
async function shareToFriend() {
  if (!tempFilePath.value || saving.value) return
  saving.value = true
  try {
    // 先确保已保存到相册（部分接口需要）
    await new Promise((res) => {
      uni.saveImageToPhotosAlbum({ filePath: tempFilePath.value, success: res, fail: res })
    })
    if (typeof wx !== 'undefined' && wx.shareFileMessage) {
      wx.shareFileMessage({
        filePath: tempFilePath.value,
        fileName: isLingshan.value ? '祈福签文.png' : '游览纪念.png',
        success:  () => {},
        fail:     () => {},
      })
    } else {
      uni.showToast({ title: '图片已保存，请从相册分享 📤', icon: 'none', duration: 2500 })
    }
  } catch (e) {
    uni.showToast({ title: '分享失败，请重试', icon: 'none' })
  } finally {
    saving.value = false
  }
}

function close() { emit('close') }

// ═══════════════════════════════════════════════════════
// 工具
// ═══════════════════════════════════════════════════════
function writeBase64ToLocal(base64) {
  try {
    const fsm = uni.getFileSystemManager()
    const path = `${wx.env.USER_DATA_PATH}/share_card_${Date.now()}.png`
    fsm.writeFileSync(path, base64, 'base64')
    return path
  } catch (e) {
    console.warn('[ShareCard] writeBase64 failed:', e)
    return ''
  }
}

function uniRequest(path, data) {
  return new Promise((resolve, reject) => {
    uni.request({
      url:     buildApiUrl(path),
      method:  'POST',
      data,
      timeout: 30000,
      success: (r) => r.statusCode >= 200 && r.statusCode < 300 ? resolve(r.data) : reject(r),
      fail:    reject,
    })
  })
}
</script>

<style scoped>
.sc-overlay {
  position: fixed;
  inset: 0;
  z-index: 9000;
  background: rgba(0, 0, 0, 0.72);
  display: flex;
  align-items: flex-end;
  justify-content: center;
}
.sc-modal {
  width: 100%;
  background: #fff;
  border-radius: 32rpx 32rpx 0 0;
  padding: 44rpx 36rpx 64rpx;
  box-sizing: border-box;
  animation: slideUp 0.28s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}
@keyframes slideUp {
  from { transform: translateY(100%); }
  to   { transform: translateY(0);    }
}
.sc-title {
  font-size: 36rpx;
  font-weight: 700;
  color: #222;
  text-align: center;
  margin-bottom: 32rpx;
  letter-spacing: 2rpx;
}

/* 加载 */
.sc-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20rpx;
  padding: 60rpx 0;
}
.sc-spinner {
  width: 64rpx;
  height: 64rpx;
  border: 4rpx solid #eee;
  border-top-color: #4e8cf5;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.sc-loading-text { font-size: 26rpx; color: #aaa; }

/* Canvas（必须存在于 DOM，但视觉上隐藏） */
.sc-canvas-hidden {
  position: fixed;
  left: -9999px;
  top: -9999px;
  width: 1px;
  height: 1px;
  opacity: 0;
  pointer-events: none;
}

/* 预览图 */
.sc-preview {
  width: 100%;
  border-radius: 20rpx;
  box-shadow: 0 8rpx 32rpx rgba(0,0,0,0.15);
  margin-bottom: 28rpx;
}
.sc-no-preview {
  width: 100%;
  height: 260rpx;
  background: #f5f5f5;
  border-radius: 20rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #bbb;
  font-size: 28rpx;
  margin-bottom: 28rpx;
}

/* 按钮 */
.sc-actions {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}
.sc-btn {
  width: 100%;
  height: 96rpx;
  line-height: 96rpx;
  border-radius: 16rpx;
  font-size: 30rpx;
  font-weight: 600;
  border: none;
  text-align: center;
  transition: opacity 0.15s;
}
.sc-btn[disabled] { opacity: 0.5; }
.sc-btn-primary {
  background: linear-gradient(135deg, #4e8cf5, #2563eb);
  color: #fff;
}
.sc-btn-share {
  background: linear-gradient(135deg, #07c160, #059a49);
  color: #fff;
}
.sc-btn-ghost {
  background: #f5f5f5;
  color: #888;
}
.sc-tip {
  display: block;
  text-align: center;
  font-size: 24rpx;
  color: #bbb;
  margin-top: 20rpx;
}
</style>
