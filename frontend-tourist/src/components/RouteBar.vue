<template>
  <div class="route-bar" v-if="spots && spots.length">
    <!-- 折叠头部 -->
    <div class="route-bar__header" @click="expanded = !expanded">
      <span class="route-bar__icon">🗺</span>
      <span class="route-bar__summary">
        路线：共 {{ spots.length }} 站 &nbsp;·&nbsp;
        已完成 {{ checkedCount }}/{{ spots.length }} 站 &nbsp;·&nbsp;
        剩余约 {{ remainingMinutes }} 分钟
      </span>
      <span class="route-bar__arrow" :class="{ expanded }">▼</span>
    </div>

    <!-- 展开内容：横向滚动的景点 chips -->
    <transition name="slide">
      <div class="route-bar__spots" v-show="expanded">
        <div
          v-for="(spot, idx) in spots"
          :key="spot.code"
          class="route-bar__spot"
          :class="{
            'is-done': idx < currentIdx,
            'is-current': idx === currentIdx,
            'is-future': idx > currentIdx,
          }"
        >
          <div class="spot-index">{{ idx + 1 }}</div>
          <div class="spot-info">
            <div class="spot-name">
              <span v-if="idx < currentIdx">✓ </span>{{ spot.name }}
            </div>
            <div class="spot-meta">~{{ spot.suggested_minutes }}分钟</div>
          </div>
          <!-- 到达按钮：仅对下一个待游览站（currentIdx 对应的站）显示 -->
          <button
            v-if="idx === currentIdx"
            class="checkin-btn"
            @click.stop="$emit('checkin', spot.code)"
          >到这里了</button>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  spots: { type: Array, default: () => [] },
  currentIdx: { type: Number, default: 0 },
  totalMinutes: { type: Number, default: 0 },
  elapsedMinutes: { type: Number, default: 0 },
})

defineEmits(['checkin'])

const expanded = ref(true)

const checkedCount = computed(() => props.currentIdx)
const remainingMinutes = computed(() =>
  Math.max(props.totalMinutes - props.elapsedMinutes, 0)
)
</script>

<style scoped>
.route-bar {
  background: #1a1f35;
  border-bottom: 1px solid rgba(255,255,255,0.08);
  z-index: 10;
  flex-shrink: 0;
}

.route-bar__header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  cursor: pointer;
  user-select: none;
  color: #c8d8ff;
  font-size: clamp(13px, 2vw, 16px);
}
.route-bar__icon { font-size: 16px; }
.route-bar__summary { flex: 1; }
.route-bar__arrow {
  font-size: 12px;
  transition: transform 0.2s;
  opacity: 0.6;
}
.route-bar__arrow.expanded { transform: rotate(180deg); }

.route-bar__spots {
  display: flex;
  gap: 10px;
  padding: 0 16px 12px;
  overflow-x: auto;
  scroll-snap-type: x mandatory;
  -ms-overflow-style: none;
  scrollbar-width: none;
}
.route-bar__spots::-webkit-scrollbar { display: none; }

.route-bar__spot {
  flex: 0 0 auto;
  scroll-snap-align: start;
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 10px;
  padding: 8px 12px;
  min-width: 120px;
  max-width: 180px;
  transition: all 0.2s;
}

.route-bar__spot.is-done {
  opacity: 0.45;
  background: rgba(255,255,255,0.03);
}
.route-bar__spot.is-current {
  border-color: #4d9fff;
  background: rgba(77,159,255,0.18);
  box-shadow: 0 0 8px rgba(77,159,255,0.35);
}
.route-bar__spot.is-future {
  opacity: 0.75;
}

.spot-index {
  width: 22px; height: 22px;
  border-radius: 50%;
  background: rgba(255,255,255,0.15);
  color: #fff;
  font-size: 12px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.is-current .spot-index { background: #4d9fff; }
.is-done .spot-index { background: #52c41a; }

.spot-info { flex: 1; min-width: 0; }
.spot-name {
  color: #e8eeff;
  font-size: clamp(13px, 2vw, 15px);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.is-done .spot-name { color: #8899bb; }
.spot-meta { color: #7a8ab0; font-size: 12px; margin-top: 2px; }

.checkin-btn {
  flex-shrink: 0;
  background: #2c7be5;
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 5px 10px;
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
}
.checkin-btn:active { background: #1a60c8; }

/* 折叠动画 */
.slide-enter-active,
.slide-leave-active { transition: all 0.22s ease; overflow: hidden; }
.slide-enter-from,
.slide-leave-to { max-height: 0; opacity: 0; padding-bottom: 0; }
.slide-enter-to,
.slide-leave-from { max-height: 200px; opacity: 1; }
</style>
