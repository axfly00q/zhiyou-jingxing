<template>
  <view
    v-if="isLingshan"
    class="muyu-container"
    :style="{ left: posX + 'px', top: posY + 'px' }"
    @tap="knock"
    @touchstart="startDrag"
    @touchmove.stop.prevent="drag"
    @touchend="endDrag"
    @touchcancel="endDrag"
  >
    <view class="muyu-icon" :class="{ knock: isKnocking }">
      <image class="muyu-img" src="/static/muyu.png" mode="aspectFit" />
    </view>
    <view class="muyu-hint">点击积攒功德</view>
    <view class="muyu-popups">
      <text
        v-for="item in popups"
        :key="item.id"
        class="muyu-popup"
        :style="{ left: item.dx + 'px', top: item.dy + 'px' }"
      >
        功德 +1
      </text>
    </view>
  </view>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'

const props = defineProps({
  parkCode: {
    type: String,
    default: '',
  },
})

const isLingshan = computed(() => props.parkCode === 'lingshan')
const posX = ref(260)
const posY = ref(420)
const isKnocking = ref(false)
const popups = ref([])
let popupId = 0
let maxX = 300
let maxY = 600
let touchStart = null
let hasDragged = false

onMounted(() => {
  try {
    const info = uni.getSystemInfoSync()
    maxX = info.windowWidth
    maxY = info.windowHeight
    posX.value = Math.max(16, info.windowWidth - 96)
    posY.value = Math.max(88, info.windowHeight - 220)
  } catch (err) {
    posX.value = 260
    posY.value = 420
  }
})

function getTouch(e) {
  return e?.touches?.[0] || e?.changedTouches?.[0] || null
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max)
}

function startDrag(e) {
  const touch = getTouch(e)
  if (!touch) return
  hasDragged = false
  touchStart = {
    x: touch.clientX,
    y: touch.clientY,
    posX: posX.value,
    posY: posY.value,
  }
}

function drag(e) {
  const touch = getTouch(e)
  if (!touch || !touchStart) return
  const dx = touch.clientX - touchStart.x
  const dy = touch.clientY - touchStart.y
  if (Math.abs(dx) > 3 || Math.abs(dy) > 3) hasDragged = true
  posX.value = clamp(touchStart.posX + dx, 8, Math.max(8, maxX - 100))
  posY.value = clamp(touchStart.posY + dy, 60, Math.max(60, maxY - 150))
}

function endDrag() {
  touchStart = null
  setTimeout(() => {
    hasDragged = false
  }, 180)
}

function knock() {
  if (hasDragged) return
  isKnocking.value = true
  setTimeout(() => {
    isKnocking.value = false
  }, 120)

  const id = ++popupId
  const dx = Math.round(Math.random() * 24 - 8)
  const dy = Math.round(Math.random() * 10 - 4)
  popups.value.push({ id, dx, dy })
  setTimeout(() => {
    popups.value = popups.value.filter(item => item.id !== id)
  }, 900)
}
</script>

<style scoped>
.muyu-container {
  position: fixed;
  width: 92px;
  height: 118px;
  display: flex;
  flex-direction: column;
  align-items: center;
  overflow: visible;
  z-index: 220;
}

.muyu-icon {
  width: 72px;
  height: 72px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 36px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 8px 22px rgba(80, 45, 20, 0.2);
  transition: transform 0.12s ease, box-shadow 0.12s ease;
}

.muyu-icon.knock {
  transform: scale(0.92) translateY(3px);
  box-shadow: 0 4px 14px rgba(80, 45, 20, 0.18);
}

.muyu-img {
  width: 62px;
  height: 62px;
}

.muyu-hint {
  margin-top: 4px;
  padding: 2px 6px;
  color: #7c4a18;
  font-size: 10px;
  line-height: 16px;
  white-space: nowrap;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.84);
  box-shadow: 0 2px 8px rgba(80, 45, 20, 0.12);
}

.muyu-popups {
  position: absolute;
  left: 36px;
  top: 4px;
  pointer-events: none;
}

.muyu-popup {
  position: absolute;
  color: #d97706;
  font-size: 13px;
  font-weight: 700;
  line-height: 18px;
  white-space: nowrap;
  text-shadow: 0 1px 4px rgba(255, 255, 255, 0.9);
  animation: muyuFloat 0.9s ease-out forwards;
}

@keyframes muyuFloat {
  0% {
    opacity: 0;
    transform: translateY(8px) scale(0.86);
  }

  18% {
    opacity: 1;
    transform: translateY(0) scale(1);
  }

  100% {
    opacity: 0;
    transform: translateY(-42px) scale(1.08);
  }
}
</style>
