<template>
  <div class="map-wrap">
    <div class="map-container" ref="container">
      <img :src="`/maps/${parkCode}.jpg`" class="map-img" @load="onImgLoad" @error="imgError=true" />

      <template v-if="imgLoaded && !imgError">
        <svg class="map-svg" :viewBox="`0 0 ${imgW} ${imgH}`" :width="imgW" :height="imgH">
          <polyline
            v-if="routeLine"
            :points="routeLine"
            fill="none"
            stroke="rgba(146, 64, 14, 0.45)"
            stroke-width="14"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
          <polyline
            v-if="routeLine"
            :points="routeLine"
            fill="none"
            stroke="#fbbf24"
            stroke-width="7"
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-dasharray="16 10"
          />
          <polyline
            v-if="completedLine"
            :points="completedLine"
            fill="none"
            stroke="#dc2626"
            stroke-width="8"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>

        <div
          v-for="(spot, i) in validSpots"
          :key="spot.code"
          class="spot-pin"
          :class="pinClass(i)"
          :style="{ left: spot.map_x + '%', top: spot.map_y + '%' }"
          :title="spot.name"
        >
          <div class="pin-dot">{{ i + 1 }}</div>
          <div class="pin-label">{{ spot.name }}</div>
        </div>

        <div
          v-if="livePoint"
          class="live-pin"
          :style="{ left: livePoint.map_x + '%', top: livePoint.map_y + '%' }"
          :title="`实时地点：${livePoint.name}`"
        >
          <div class="live-ring"></div>
          <div class="live-core"></div>
          <div class="live-label">实时地点 · {{ livePoint.name }}</div>
        </div>

        <div class="map-legend">
          <span><i class="legend-dot live"></i>实时地点</span>
          <span><i class="legend-line done"></i>已走路线</span>
          <span><i class="legend-line planned"></i>规划路线</span>
        </div>
      </template>

      <div v-if="imgError" class="map-placeholder">地图暂未加载</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  parkCode: { type: String, required: true },
  spots: { type: Array, default: () => [] },         // RouteSpot[]，需有 map_x/map_y
  currentIdx: { type: Number, default: 0 },           // 当前正在游览的景点索引
  realtimeLocation: { type: Object, default: null },  // 可选：{ map_x, map_y, name }
})

const container = ref(null)
const imgLoaded = ref(false)
const imgError = ref(false)
const imgW = ref(1)
const imgH = ref(1)

function onImgLoad(e) {
  imgW.value = e.target.naturalWidth
  imgH.value = e.target.naturalHeight
  imgLoaded.value = true
}

const validSpots = computed(() => props.spots.filter(s => s.map_x != null && s.map_y != null))

const pointString = (spots) =>
  spots
    .map(s => `${(Number(s.map_x) / 100) * imgW.value},${(Number(s.map_y) / 100) * imgH.value}`)
    .join(' ')

const routeLine = computed(() => {
  if (validSpots.value.length < 2) return ''
  return pointString(validSpots.value)
})

const completedLine = computed(() => {
  if (validSpots.value.length < 2 || props.currentIdx <= 0) return ''
  return pointString(validSpots.value.slice(0, Math.min(props.currentIdx + 1, validSpots.value.length)))
})

const livePoint = computed(() => {
  if (props.realtimeLocation?.map_x != null && props.realtimeLocation?.map_y != null) {
    return {
      map_x: Number(props.realtimeLocation.map_x),
      map_y: Number(props.realtimeLocation.map_y),
      name: props.realtimeLocation.name || '当前位置',
    }
  }
  if (!validSpots.value.length) return null
  const idx = Math.min(Math.max(props.currentIdx, 0), validSpots.value.length - 1)
  const spot = validSpots.value[idx]
  return { map_x: Number(spot.map_x), map_y: Number(spot.map_y), name: spot.name }
})

function pinClass(i) {
  if (i < props.currentIdx) return 'visited'
  if (i === props.currentIdx) return 'current'
  return 'upcoming'
}
</script>

<style scoped>
.map-wrap { width: 100%; overflow: auto; max-height: min(54vh, 620px); background: #0b1020; }
.map-container { position: relative; display: block; width: 100%; max-width: 760px; margin: 0 auto; }
.map-img { width: 100%; display: block; border-radius: 0; }
.map-svg { position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; }
.spot-pin { position: absolute; transform: translate(-50%, -50%); text-align: center; cursor: default; z-index: 2; }
.pin-dot {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  margin: 0 auto 3px;
  border: 2px solid #fff;
  display: grid;
  place-items: center;
  color: #fff;
  font-size: 12px;
  font-weight: 800;
  line-height: 1;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.35);
}
.visited .pin-dot { background: #b45309; opacity: 0.88; }
.current .pin-dot { background: #dc2626; animation: pulse 1.2s infinite; }
.upcoming .pin-dot { background: rgba(31, 41, 55, 0.78); border-color: rgba(255,255,255,0.85); }
.pin-label { font-size: 10px; white-space: nowrap; background: rgba(20, 24, 39, .74); color: #fff; padding: 2px 5px; border-radius: 999px; text-shadow: 0 1px 1px rgba(0,0,0,.45); }
.current .pin-label { background: rgba(220, 38, 38, .9); }
.live-pin { position: absolute; z-index: 4; transform: translate(-50%, -50%); pointer-events: none; }
.live-ring {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  border: 2px solid rgba(59, 130, 246, 0.86);
  background: rgba(59, 130, 246, 0.18);
  animation: locatePulse 1.5s ease-out infinite;
}
.live-core {
  position: absolute;
  left: 50%;
  top: 50%;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  background: #2563eb;
  border: 3px solid #fff;
  box-shadow: 0 2px 10px rgba(0,0,0,.35);
}
.live-label {
  position: absolute;
  left: 50%;
  top: 30px;
  transform: translateX(-50%);
  white-space: nowrap;
  background: rgba(15, 23, 42, .88);
  color: #dbeafe;
  border: 1px solid rgba(147, 197, 253, .6);
  border-radius: 999px;
  padding: 4px 8px;
  font-size: 11px;
  box-shadow: 0 4px 12px rgba(0,0,0,.24);
}
.map-legend {
  position: sticky;
  left: 8px;
  bottom: 8px;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  margin: 8px;
  padding: 6px 9px;
  border-radius: 999px;
  background: rgba(15, 23, 42, .82);
  color: #e5e7eb;
  font-size: 11px;
  backdrop-filter: blur(8px);
}
.map-legend span { display: inline-flex; align-items: center; gap: 4px; }
.legend-dot { width: 9px; height: 9px; border-radius: 50%; display: inline-block; }
.legend-dot.live { background: #2563eb; border: 2px solid #bfdbfe; }
.legend-line { width: 18px; height: 4px; border-radius: 999px; display: inline-block; }
.legend-line.done { background: #dc2626; }
.legend-line.planned { background: #fbbf24; }
.map-placeholder { padding: 20px; text-align: center; color: #aaa; background: #f5f5f5; border-radius: 8px; }

@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(234, 179, 8, .6); }
  50% { box-shadow: 0 0 0 6px rgba(234, 179, 8, 0); }
}

@keyframes locatePulse {
  0% { transform: scale(.55); opacity: .95; }
  100% { transform: scale(1.45); opacity: 0; }
}
</style>
