<template>
  <div
    ref="containerRef"
    class="muyu-container"
    :style="{ left: pos.x + 'px', top: pos.y + 'px', transform: 'translate(-50%, -50%)' }"
    @mousedown="startDrag"
    @touchstart.passive="startDrag"
  >
    <div class="muyu-icon" @click="knock" :class="{ knock: isKnocking }">
      <img v-if="isLingshan" src="/images/muyu.png" class="muyu-img" draggable="false" />
      <span v-else>🔔</span>
    </div>
    <div class="hint">点击积攒{{ isLingshan ? '功德' : '福气' }}</div>
    <transition-group name="float-up" tag="div" class="popups">
      <div v-for="pop in popups" :key="pop.id" class="popup" :style="{ left: pop.x + 'px', top: pop.y + 'px' }">
        {{ pop.text }}
      </div>
    </transition-group>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  parkCode: String
})

const isLingshan = computed(() => props.parkCode === 'lingshan')
const isKnocking = ref(false)
const popups = ref([])
let idCounter = 0

// 自由拖拽逻辑
const pos = ref({ x: 200, y: 400 }) // 默认安全坐标
const containerRef = ref(null)
let dragging = false
let hasDragged = false
let startOffset = { x: 0, y: 0 }

function startDrag(e) {
  dragging = true
  hasDragged = false
  const clientX = e.touches ? e.touches[0].clientX : e.clientX
  const clientY = e.touches ? e.touches[0].clientY : e.clientY
  startOffset.x = clientX - pos.value.x
  startOffset.y = clientY - pos.value.y
}

function onDrag(e) {
  if (!dragging) return
  hasDragged = true
  const clientX = e.touches ? e.touches[0].clientX : e.clientX
  const clientY = e.touches ? e.touches[0].clientY : e.clientY
  pos.value.x = clientX - startOffset.x
  pos.value.y = clientY - startOffset.y
}

function stopDrag() {
  dragging = false
  // 稍后清除 dragging 状态，防止触发 click
  setTimeout(() => { hasDragged = false }, 50)
}

onMounted(() => {
  if (containerRef.value && containerRef.value.parentElement) {
    const parentRect = containerRef.value.parentElement.getBoundingClientRect()
    pos.value.x = parentRect.width / 2
    pos.value.y = parentRect.height * 0.7
  }

  window.addEventListener('mousemove', onDrag)
  window.addEventListener('mouseup', stopDrag)
  window.addEventListener('touchmove', onDrag, { passive: false })
  window.addEventListener('touchend', stopDrag)
})

onUnmounted(() => {
  window.removeEventListener('mousemove', onDrag)
  window.removeEventListener('mouseup', stopDrag)
  window.removeEventListener('touchmove', onDrag)
  window.removeEventListener('touchend', stopDrag)
})

function knock(e) {
  if (hasDragged) return

  isKnocking.value = true
  setTimeout(() => { isKnocking.value = false }, 100)

  // Random offset for the floating text
  const x = (Math.random() - 0.5) * 60
  const y = (Math.random() - 0.5) * 20

  const text = isLingshan.value ? '功德 +1' : '烦恼 -1'

  const pop = { id: idCounter++, text, x, y }
  popups.value.push(pop)

  // Remove after animation
  setTimeout(() => {
    popups.value = popups.value.filter(p => p.id !== pop.id)
  }, 1000)
}
</script>

<style scoped>
.muyu-container {
  position: absolute;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  align-items: center;
  pointer-events: auto;
  cursor: grab;
}
.muyu-container:active {
  cursor: grabbing;
}
.muyu-icon {
  font-size: clamp(60px, 15vw, 90px);
  cursor: pointer;
  user-select: none;
  transition: transform 0.05s;
  filter: drop-shadow(0 6px 12px rgba(0,0,0,0.5));
}
.muyu-img {
  width: 120px;
  height: 120px;
  object-fit: contain;
  pointer-events: none; /* 避免拖拽时出现浏览器默认拖图行为 */
}
.muyu-icon.knock {
  transform: scale(0.9) translateY(4px);
}
.hint {
  color: #fff;
  font-size: 13px;
  margin-top: -5px;
  background: rgba(0,0,0,0.6);
  padding: 4px 12px;
  border-radius: 20px;
  backdrop-filter: blur(4px);
  pointer-events: none;
  user-select: none;
}
.popups {
  position: absolute;
  top: -20px;
  left: 50%;
  width: 0; height: 0;
  pointer-events: none;
}
.popup {
  position: absolute;
  white-space: nowrap;
  font-size: 22px;
  font-weight: bold;
  color: #ffda44;
  text-shadow: 0 2px 4px rgba(0,0,0,0.6);
  transform: translate(-50%, -100%);
}
.float-up-enter-active, .float-up-leave-active {
  transition: all 1s cubic-bezier(0.25, 0.8, 0.25, 1);
}
.float-up-enter-from {
  opacity: 1;
  transform: translate(-50%, -50%);
}
.float-up-leave-to {
  opacity: 0;
  transform: translate(-50%, -180%);
}
</style>
