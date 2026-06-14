<template>
  <view class="route-bar" v-if="spots && spots.length">
    <view class="route-bar__header" @click="expanded = !expanded">
      <text class="route-bar__icon">🗺</text>
      <text class="route-bar__summary">
        路线：共 {{ spots.length }} 站 · 已完成 {{ checkedCount }}/{{ spots.length }} 站 · 剩余约 {{ remainingMinutes }} 分钟
      </text>
      <text class="route-bar__arrow" :class="{ expanded }">▼</text>
    </view>

    <view class="route-bar__spots-wrap" v-show="expanded">
      <scroll-view class="route-bar__spots" scroll-x>
        <view
          v-for="(spot, idx) in spots"
          :key="spot.code"
          class="route-bar__spot"
          :class="{
            'is-done': idx < currentIdx,
            'is-current': idx === currentIdx,
            'is-future': idx > currentIdx,
          }"
        >
          <view class="spot-index">{{ idx + 1 }}</view>
          <view class="spot-info">
            <view class="spot-name">
              <text v-if="idx < currentIdx">✓ </text>{{ spot.name }}
            </view>
            <view class="spot-meta">~{{ spot.suggested_minutes }}分钟</view>
          </view>
          <button
            v-if="idx === currentIdx"
            class="checkin-btn"
            @click.stop="$emit('checkin', spot.code)"
          >到这里了</button>
        </view>
      </scroll-view>
    </view>
  </view>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  spots: { type: Array, default: () => [] },
  currentIdx: { type: Number, default: 0 },
  totalMinutes: { type: Number, default: 0 },
  elapsedMinutes: { type: Number, default: 0 },
  forceCollapse: { type: Boolean, default: false },
})

defineEmits(['checkin'])

const expanded = ref(false)
watch(() => props.forceCollapse, (v) => { if (v) expanded.value = false })

const checkedCount = computed(() => props.currentIdx)
const remainingMinutes = computed(() => Math.max(props.totalMinutes - props.elapsedMinutes, 0))
</script>

<style scoped>
.route-bar { background: #1a1f35; border-bottom: 1px solid rgba(255,255,255,0.08); z-index: 10; flex-shrink: 0; }
.route-bar__header { display: flex; align-items: center; padding: 10px 16px; color: #c8d8ff; font-size: 14px; }
.route-bar__summary { flex: 1; margin-left: 8px; }
.route-bar__arrow { transition: transform 0.2s; opacity: 0.6; }
.route-bar__arrow.expanded { transform: rotate(180deg); }
.route-bar__spots-wrap { padding: 0 16px 12px; }
.route-bar__spots { white-space: nowrap; width: 100%; }
.route-bar__spot { display: inline-flex; align-items: center; background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1); border-radius: 10px; padding: 8px 12px; margin-right: 10px; transition: all 0.2s; min-width: 140px; }
.is-done { opacity: 0.45; }
.is-current { border-color: #4d9fff; background: rgba(77,159,255,0.18); }
.is-future { opacity: 0.75; }
.spot-index { width: 22px; height: 22px; border-radius: 50%; background: rgba(255,255,255,0.15); color: #fff; font-size: 12px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; margin-right: 8px;}
.is-current .spot-index { background: #4d9fff; }
.is-done .spot-index { background: #52c41a; }
.spot-info { display: flex; flex-direction: column; margin-right: 8px; }
.spot-name { color: #e8eeff; font-size: 14px; }
.spot-meta { color: #7a8ab0; font-size: 12px; }
.checkin-btn { background: #2c7be5; color: #fff; border: none; border-radius: 6px; padding: 0 10px; font-size: 12px; line-height: 24px; margin: 0; }
</style>
