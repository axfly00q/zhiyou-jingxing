<template>
  <view class="chat-container">
    <!-- 路线进度条 -->
    <RouteBar
      v-if="routeSpots.length"
      :spots="routeSpots"
      :current-idx="currentSpotIdx"
      :total-minutes="routeTotalMinutes"
      :elapsed-minutes="elapsedMinutes"
      :force-collapse="!isMapCollapsed"
      @checkin="handleCheckin"
    />

    <!-- 顶部：地图区域 -->
    <view class="map-section" :class="{ 'collapsed': isMapCollapsed }">
      <view class="map-wrapper" v-show="!isMapCollapsed">
        <ParkMap
          v-if="parkCode === 'lingshan' || parkCode === 'zhuozheng'"
          :park-code="parkCode"
          :spots="routeSpots"
          :current-idx="currentSpotIdx"
          :current-lat="currentLat"
          :current-lng="currentLng"
        />
      </view>
      <!-- 折叠时的简易摘要 / 展开时的折叠按钮 -->
      <view class="map-controller" @click="toggleMap">
        <text class="location-summary" v-if="isMapCollapsed">
          📍 {{ locationType || '定位中...' }}
          <text v-if="distToNext !== null"> · 距下一站 {{ distToNext }}m</text>
          <text> (点击展开地图)</text>
        </text>
        <text class="collapse-btn" v-else>收起地图 🔼</text>
      </view>
    </view>

    <!-- 中部：AI 数字人区域 (展开态) -->
    <view class="avatar-section" v-if="!isAvatarShrinked">
      <view class="avatar-wrapper" @click="toggleAvatar">
        <image 
          class="avatar-image" 
          src="https://media.giphy.com/media/3o7TKSjRrfIPjeiVyM/giphy.gif" 
          mode="aspectFit"
        ></image>
        <view class="avatar-hint">点击数字人缩小，腾出聊天空间</view>
      </view>
    </view>

    <!-- 悬浮球模式：全屏可拖拽区域 -->
    <movable-area class="movable-area" v-if="isAvatarShrinked">
      <movable-view 
        class="movable-avatar" 
        direction="all" 
        :x="screenWidth" 
        :y="50"
        @click="toggleAvatar"
      >
        <image class="avatar-image-small" src="https://media.giphy.com/media/3o7TKSjRrfIPjeiVyM/giphy.gif" mode="aspectFill"></image>
      </movable-view>
    </movable-area>

    <!-- 底部：聊天记录区 -->
    <view class="chat-section">
      <scroll-view class="chat-scroll" scroll-y :scroll-into-view="'msg-' + (messages.length - 1)">
        <view class="message-list">
          <view v-for="(m, i) in messages" :key="i" :class="['message', m.role]" :id="'msg-' + i">
            <text :class="{ thinking: m.content === '正在思考…' }">{{ m.content }}</text>
          </view>
        </view>
        <view class="bottom-padding"></view>
      </scroll-view>
      
      <!-- 输入区域 -->
      <view class="input-area">
        <input class="chat-input" placeholder="问问我关于景点的故事吧..." v-model="input" @confirm="send" />
        <button class="send-btn" @click="send" :disabled="loading">发送</button>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import locationManager from '../../utils/locationManager'
import { BASE_URL, chatCheckin } from '../../api'
import RouteBar from '../../components/RouteBar.vue'
import ParkMap from '../../components/ParkMap.vue'

const parkName = ref('灵山胜境')
const parkCode = ref('lingshan')
const sessionId = ref(Math.random().toString(36).substring(2, 15))
const loading = ref(false)
const input = ref('')
const messages = ref([])

// 路线数据状态
const routeSpots = ref([])
const routeTotalMinutes = ref(0)
const currentSpotIdx = ref(0)
const routeStartTime = ref(Date.now())
const elapsedMinutes = ref(0)
let elapsedTimer = null

// 状态控制
const isMapCollapsed = ref(false)
const isAvatarShrinked = ref(false)
const screenWidth = ref(300)

// 定位数据
const currentLat = ref(null)
const currentLng = ref(null)
const locationType = ref('')
const lastMessageId = ref('msg-2')

// 到下一景点的距离（米），null 表示无定位或无路线
const distToNext = computed(() => {
  if (currentLat.value == null || currentLng.value == null) return null
  const next = routeSpots.value[currentSpotIdx.value]
  if (!next) return null
  // 需要景点有 GPS 坐标（lat/lng 字段）
  if (next.lat == null || next.lng == null) return null
  return haversine(currentLat.value, currentLng.value, next.lat, next.lng)
})

function haversine(lat1, lng1, lat2, lng2) {
  const R = 6371000
  const dLat = (lat2 - lat1) * Math.PI / 180
  const dLng = (lng2 - lng1) * Math.PI / 180
  const a = Math.sin(dLat / 2) ** 2
    + Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * Math.sin(dLng / 2) ** 2
  return Math.round(R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a)))
}

const toggleMap = () => {
  isMapCollapsed.value = !isMapCollapsed.value
  // 展开地图时自动缩小数字人，避免内容超出屏幕
  if (!isMapCollapsed.value) {
    isAvatarShrinked.value = true
  }
}

const toggleAvatar = () => {
  isAvatarShrinked.value = !isAvatarShrinked.value
}

onMounted(() => {
  const sysInfo = uni.getSystemInfoSync()
  screenWidth.value = sysInfo.windowWidth - 100 // 默认靠右侧
  
  const pName = uni.getStorageSync('park_name')
  const pCode = uni.getStorageSync('park')
  if (pName) parkName.value = pName
  if (pCode) parkCode.value = pCode

  const routeStr = uni.getStorageSync('route')
  let narrative = ''
  if (routeStr) {
    try { 
      const routeData = JSON.parse(routeStr)
      narrative = routeData.narrative 
      routeSpots.value = routeData.spots || []
      routeTotalMinutes.value = routeData.total_minutes || 0
    } catch (e) {}
  }

  // 启动已用时间计时器
  if (routeSpots.value.length) {
    elapsedTimer = setInterval(() => {
      elapsedMinutes.value = Math.floor((Date.now() - routeStartTime.value) / 60000)
    }, 30000)
  }
  
  if (narrative) {
    messages.value.push({ role: 'assistant', content: narrative })
  } else {
    messages.value.push({ role: 'assistant', content: `欢迎来到${parkName.value}！请问想了解什么？` })
  }

  locationManager.onLocationUpdate((res) => {
    currentLat.value = res.latitude
    currentLng.value = res.longitude
    locationType.value = res.type
  })
  locationManager.start()
})

onUnmounted(() => {
  locationManager.stop()
})

async function send() {
  const text = input.value.trim()
  if (!text || loading.value) return
  messages.value.push({ role: 'user', content: text })
  input.value = ''
  loading.value = true

  const msgIdx = messages.value.length
  messages.value.push({ role: 'assistant', content: '正在思考…' })

  uni.request({
    url: `${BASE_URL}/chat/stream`,
    method: 'POST',
    timeout: 60000,
    data: {
      session_id: sessionId.value,
      message: text,
      park_code: parkCode.value
    },
    success: (res) => {
      // 解析完整 SSE 响应，拼接所有 token
      let fullText = ''
      const raw = typeof res.data === 'string' ? res.data : ''
      for (const line of raw.split('\n')) {
        if (!line.startsWith('data: ')) continue
        try {
          const evt = JSON.parse(line.slice(6))
          if (evt.type === 'token' && evt.text) fullText += evt.text
        } catch {}
      }
      messages.value[msgIdx].content = fullText || '（暂无回复，请稍后重试）'
      loading.value = false
    },
    fail: () => {
      messages.value[msgIdx].content = '（网络不稳定，请稍后重试）'
      loading.value = false
    }
  })
}

// 打卡处理
async function handleCheckin(spotCode) {
  if (loading.value) return
  loading.value = true

  // 立即推进进度条，给游客即时反馈
  if (currentSpotIdx.value < routeSpots.value.length) {
    currentSpotIdx.value += 1
  }
  // 立即显示思考占位，减少等待焦虑
  const msgIdx = messages.value.length
  messages.value.push({ role: 'assistant', content: '正在思考…' })

  try {
    const res = await chatCheckin({
      session_id: sessionId.value,
      spot_code: spotCode,
      park_code: parkCode.value,
    })

    // 用实际内容替换占位
    messages.value[msgIdx].content = res.narrative

    if (res.next_spot_name) {
      const walkTip = res.next_walk_minutes ? `，步行约 ${res.next_walk_minutes} 分钟` : ''
      messages.value.push({ role: 'assistant', content: `→ 下一站：${res.next_spot_name}${walkTip}` })
    } else if (currentSpotIdx.value >= routeSpots.value.length) {
      messages.value.push({ role: 'assistant', content: '🎉 路线全部完成！您已游遍所有景点，希望本次游览令您尽兴而归！' })
    }
  } catch (e) {
    messages.value[msgIdx].content = '打卡失败，请稍后重试。'
    // 回滚进度
    if (currentSpotIdx.value > 0) currentSpotIdx.value -= 1
  } finally {
    loading.value = false
  }
}
</script>

<style>
/* 整个页面基于 Flex 竖向排列 */
.chat-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  width: 100vw;
  background-color: #f2f2f2;
  overflow: hidden;
  position: relative;
}

/* === 地图区域 === */
.map-section {
  width: 100%;
  flex: 0 0 auto;
  height: 28vh;         /* 固定高度，微信小程序里 max-height 可能不可靠 */
  transition: height 0.3s ease;
  background-color: #fff;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  z-index: 10;
}
.map-section.collapsed {
  height: 40px;
}
.map-wrapper {
  flex: 1;
  min-height: 0;
  width: 100%;
  overflow: hidden;
}
.map-view {
  width: 100%;
  height: 100%;
}
.map-controller {
  height: 40px;
  background-color: rgba(255, 255, 255, 0.95);
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid #eee;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}
.collapse-btn, .location-summary {
  font-size: 13px;
  color: #555;
}

/* === 数字人区域 (展开态) === */
.avatar-section {
  width: 100%;
  height: 35vh;
  display: flex;
  justify-content: center;
  align-items: flex-end; /* 底部对齐 */
  background: linear-gradient(180deg, #d4fc79 0%, #96e6a1 100%);
  position: relative;
  z-index: 5;
}

.avatar-wrapper {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  align-items: center;
}

.avatar-image {
  width: 80%;
  height: 80%;
}

.avatar-hint {
  font-size: 12px;
  color: rgba(0,0,0,0.5);
  margin-bottom: 10px;
}

/* === 悬浮球拖拽区域 === */
.movable-area {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: 100;
  pointer-events: none; /* 让下方的元素可以被点击 */
}

.movable-avatar {
  width: 80px;
  height: 80px;
  border-radius: 40px;
  background: #fff;
  box-shadow: 0 4px 12px rgba(0,0,0,0.2);
  pointer-events: auto; /* 恢复自身的点击和拖拽事件 */
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.avatar-image-small {
  width: 100%;
  height: 100%;
  transform: scale(1.5) translateY(10px); /* 放大特写 */
}

/* === 聊天区域 === */
.chat-section {
  flex: 1; /* 最核心：吃掉所有剩余空间，自动伸缩 */
  background-color: #f2f2f2;
  display: flex;
  flex-direction: column;
  min-height: 0; /* 必须，防止 flex 撑破屏幕 */
}

.chat-scroll {
  flex: 1;
  padding: 15px;
  box-sizing: border-box;
}

.message-list {
  display: flex;
  flex-direction: column;
}

.message {
  margin-bottom: 15px;
  max-width: 80%;
}
.message text {
  display: inline-block;
  padding: 10px 15px;
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.4;
}

.message.system {
  align-self: center;
  max-width: 90%;
}
.message.system text {
  background-color: rgba(0,0,0,0.05);
  color: #666;
  font-size: 12px;
}

.message.user {
  align-self: flex-end;
}
.message.user text {
  background-color: #007AFF;
  color: white;
  border-bottom-right-radius: 0;
}

.message.ai,
.message.assistant {
  align-self: flex-start;
}
.message.ai text,
.message.assistant text {
  background-color: white;
  color: #333;
  border-bottom-left-radius: 0;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

/* 正在思考动画 */
.message.assistant .thinking {
  color: #999;
  font-style: italic;
  animation: blink 1.2s ease-in-out infinite;
}
@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.bottom-padding {
  height: 20px;
}

/* 输入框 */
.input-area {
  height: 60px;
  background-color: white;
  display: flex;
  align-items: center;
  padding: 0 15px;
  box-shadow: 0 -2px 5px rgba(0,0,0,0.02);
  padding-bottom: env(safe-area-inset-bottom);
}
.chat-input {
  flex: 1;
  height: 36px;
  background-color: #f5f5f5;
  border-radius: 18px;
  padding: 0 15px;
  font-size: 14px;
}
.send-btn {
  margin-left: 10px;
  background-color: #007AFF;
  color: white;
  font-size: 14px;
  height: 36px;
  line-height: 36px;
  border-radius: 18px;
  padding: 0 15px;
}
</style>
