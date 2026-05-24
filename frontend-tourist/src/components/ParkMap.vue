<template>
  <div class="map-wrap">
    <div class="map-container" ref="container">
      <img :src="`/maps/${parkCode}.jpg`" class="map-img" @load="onImgLoad" @error="imgError=true" />

      <template v-if="imgLoaded && !imgError">
        <!-- SVG 连线 -->
        <svg class="map-svg" :viewBox="`0 0 ${imgW} ${imgH}`" :width="imgW" :height="imgH">
          <polyline
            v-if="linePoints"
            :points="linePoints"
            fill="none"
            stroke="#2c7be5"
            stroke-width="2"
            stroke-dasharray="6 4"
            opacity="0.7"
          />
        </svg>

        <!-- 景点点位 -->
        <div
          v-for="(spot, i) in validSpots"
          :key="spot.code"
          class="spot-pin"
          :class="pinClass(i)"
          :style="{ left: spot.map_x + '%', top: spot.map_y + '%' }"
          :title="spot.name"
        >
          <div class="pin-dot"></div>
          <div class="pin-label">{{ spot.name }}</div>
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

// SVG polyline 点串：百分比 → 像素
const linePoints = computed(() => {
  if (validSpots.value.length < 2) return ''
  return validSpots.value
    .map(s => `${(s.map_x / 100) * imgW.value},${(s.map_y / 100) * imgH.value}`)
    .join(' ')
})

function pinClass(i) {
  if (i < props.currentIdx) return 'visited'
  if (i === props.currentIdx) return 'current'
  return 'upcoming'
}
</script>

<style scoped>
.map-wrap { width: 100%; overflow: auto; max-height: 220px; }
.map-container { position: relative; display: inline-block; width: 100%; max-width: 480px; }
.map-img { width: 100%; display: block; border-radius: 8px; }
.map-svg { position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; }
.spot-pin { position: absolute; transform: translate(-50%, -50%); text-align: center; cursor: default; }
.pin-dot { width: 12px; height: 12px; border-radius: 50%; margin: 0 auto 2px; border: 2px solid #fff; }
.visited .pin-dot { background: #28a745; }
.current .pin-dot { background: #ff7b00; animation: pulse 1.2s infinite; }
.upcoming .pin-dot { background: rgba(255,255,255,0.7); border-color: #aaa; }
.pin-label { font-size: 10px; white-space: nowrap; background: rgba(0,0,0,.5); color: #fff; padding: 1px 4px; border-radius: 3px; }
.current .pin-label { background: rgba(255,123,0,.85); }
.map-placeholder { padding: 20px; text-align: center; color: #aaa; background: #f5f5f5; border-radius: 8px; }

@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(255,123,0,.6); }
  50% { box-shadow: 0 0 0 6px rgba(255,123,0,0); }
}
</style>
