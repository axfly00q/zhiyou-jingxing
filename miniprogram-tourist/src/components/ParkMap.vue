<template>
  <view class="map-wrap">
    <view class="map-container" :style="{ width: '100%', position: 'relative' }">
      <image
        :src="'/static/maps/' + parkCode + '.jpg'"
        class="map-img"
        mode="widthFix"
        @error="imgError = true"
      />

      <template v-if="!imgError">
        <!-- 路线景点标注 -->
        <view
          v-for="(spot, i) in spotsWithXY"
          :key="spot.code"
          class="spot-pin"
          :class="pinClass(i)"
          :style="{ left: spot._x + '%', top: spot._y + '%' }"
        >
          <view class="pin-dot"></view>
          <view class="pin-label">{{ spot.name }}</view>
        </view>

        <!-- GPS 当前位置蓝点 -->
        <view v-if="gpsPos" class="gps-dot" :style="{ left: gpsPos.x + '%', top: gpsPos.y + '%' }">
          <view class="gps-ring"></view>
          <view class="gps-center"></view>
        </view>
      </template>

      <view v-if="imgError" class="map-placeholder">地图暂未加载</view>
    </view>
  </view>
</template>

<script setup>
import { ref, computed } from 'vue'

// 各景区地图四角经纬度边界（高德坐标，E/N）
const PARK_BOUNDS = {
  lingshan: {
    tl: { lng: 120.0931, lat: 31.4312 }, // 左上（西北）
    tr: { lng: 120.1028, lat: 31.4285 }, // 右上（东北）
    bl: { lng: 120.0926, lat: 31.4243 }, // 左下（西南）
    br: { lng: 120.1032, lat: 31.4239 }, // 右下（东南）
  },
}

// 各景区景点 GPS 坐标（用于无 map_x/map_y 时自动换算）
const SPOT_GPS = {
  lingshan: {
    sheng_jing_men_lou:   { lng: 120.0970, lat: 31.4251 },
    jiu_long_guan_yu:     { lng: 120.0962, lat: 31.4264 },
    da_fo_bao_fo_jiao:    { lng: 120.0950, lat: 31.4299 },
    fan_gong:             { lng: 120.1024, lat: 31.4282 },
    wu_yin_tan_cheng:     { lng: 120.1005, lat: 31.4253 },
  },
}

const props = defineProps({
  parkCode: { type: String, required: true },
  spots:    { type: Array,  default: () => [] },
  currentIdx: { type: Number, default: 0 },
  currentLat: { type: Number, default: null },
  currentLng: { type: Number, default: null },
})

const imgError = ref(false)

/** GPS (lng, lat) → 图片上的百分比坐标 {x, y}，出界返回 null */
function gpsToXY(lng, lat) {
  const b = PARK_BOUNDS[props.parkCode]
  if (!b) return null
  const lngLeft  = (b.tl.lng + b.bl.lng) / 2
  const lngRight = (b.tr.lng + b.br.lng) / 2
  const latTop   = (b.tl.lat + b.tr.lat) / 2
  const latBot   = (b.bl.lat + b.br.lat) / 2
  const x = (lng - lngLeft)  / (lngRight - lngLeft) * 100
  const y = (latTop - lat)   / (latTop   - latBot)  * 100
  if (x < -8 || x > 108 || y < -8 || y > 108) return null
  return { x: Math.max(1, Math.min(99, x)), y: Math.max(1, Math.min(99, y)) }
}

/** 景点列表，自动补齐 _x/_y（优先 map_x/map_y，其次 GPS 换算，最后跳过） */
const spotsWithXY = computed(() => {
  const gpsMap = SPOT_GPS[props.parkCode] || {}
  return props.spots
    .map(s => {
      if (s.map_x != null && s.map_y != null) {
        return { ...s, _x: s.map_x, _y: s.map_y }
      }
      const g = gpsMap[s.code]
      if (g) {
        const pos = gpsToXY(g.lng, g.lat)
        if (pos) return { ...s, _x: pos.x, _y: pos.y }
      }
      return null
    })
    .filter(Boolean)
})

/** 当前 GPS 位置在图上的坐标 */
const gpsPos = computed(() => {
  if (props.currentLat == null || props.currentLng == null) return null
  return gpsToXY(props.currentLng, props.currentLat)
})

function pinClass(i) {
  if (i < props.currentIdx) return 'visited'
  if (i === props.currentIdx) return 'current'
  return 'upcoming'
}
</script>

<style scoped>
.map-wrap { width: 100%; overflow: auto; height: 100%; max-height: 24vh; background-color: #f0f0f0; }
.map-container { display: inline-block; width: 100%; position: relative; }
.map-img { width: 100%; display: block; border-radius: 8px; }

/* 景点图钉 */
.spot-pin { position: absolute; transform: translate(-50%, -50%); text-align: center; }
.pin-dot { width: 12px; height: 12px; border-radius: 50%; margin: 0 auto 2px; border: 2px solid #fff; }
.visited .pin-dot { background: #28a745; }
.current .pin-dot { background: #ff7b00; box-shadow: 0 0 6px rgba(255,123,0,0.8); }
.upcoming .pin-dot { background: rgba(255,255,255,0.7); border-color: #aaa; }
.pin-label { font-size: 10px; white-space: nowrap; background: rgba(0,0,0,.5); color: #fff; padding: 2px 4px; border-radius: 3px; }
.current .pin-label { background: rgba(255,123,0,.85); }

/* GPS 蓝点 */
.gps-dot { position: absolute; transform: translate(-50%, -50%); z-index: 20; width: 12px; height: 12px; }
.gps-center {
  width: 12px; height: 12px;
  background: #007AFF;
  border-radius: 50%;
  border: 2px solid #fff;
  box-shadow: 0 0 4px rgba(0,122,255,0.9);
  position: relative; z-index: 2;
}
.gps-ring {
  position: absolute;
  top: 50%; left: 50%;
  width: 32px; height: 32px;
  margin: -16px 0 0 -16px;
  border-radius: 50%;
  background: rgba(0,122,255,0.2);
  animation: gps-pulse 2s ease-out infinite;
}
@keyframes gps-pulse {
  0%   { transform: scale(0.3); opacity: 1; }
  100% { transform: scale(1);   opacity: 0; }
}

.map-placeholder { padding: 20px; text-align: center; color: #aaa; background: #f5f5f5; border-radius: 8px; }
</style>
