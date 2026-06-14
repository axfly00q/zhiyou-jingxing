<template>
  <view class="page">
    <view class="card">
      <view class="header-title">{{ parkName }} · 偏好引导</view>
      <view class="hint">调整你的兴趣，AI 将为你定制游览路线</view>

      <view class="row">
        <text class="label">游览时长(分钟)</text>
        <slider class="slider" min="30" max="240" step="15" :value="pref.duration_min" @change="(e) => pref.duration_min = e.detail.value" show-value/>
      </view>

      <view class="constraints">
        <label class="checkbox-label">
          <checkbox :checked="pref.wheelchair" @click="pref.wheelchair = !pref.wheelchair" color="#2c7be5" style="transform:scale(0.8)"/> 🦽 需要无障碍通道
        </label>
        <label class="checkbox-label">
          <checkbox :checked="pref.children" @click="pref.children = !pref.children" color="#2c7be5" style="transform:scale(0.8)"/> 🧒 携带儿童
        </label>
        <label class="checkbox-label">
          <checkbox :checked="pref.rush" @click="pref.rush = !pref.rush" color="#2c7be5" style="transform:scale(0.8)"/> ⚡ 时间紧张(跳过次要景点)
        </label>
      </view>

      <view class="presets">
        <view class="preset-title">快速选择</view>
        <view class="preset-cards">
          <view class="preset-card" @click="applyPreset('family')"><text>🧒 亲子家庭\n<text class="small">90 分钟</text></text></view>
          <view class="preset-card" @click="applyPreset('photo')"><text>📷 摄影发烧友\n<text class="small">120 分钟</text></text></view>
          <view class="preset-card" @click="applyPreset('history')"><text>🏛 历史深度游\n<text class="small">180 分钟</text></text></view>
        </view>
      </view>

      <button class="btn" :disabled="loading" @click="submit">
        {{ loading ? '规划中...' : '生成专属路线' }}
      </button>

      <view v-if="route" class="result">
        <view class="result-title">{{ route.park }} · 推荐路线（约 {{ route.total_minutes }} 分钟）</view>
        <view class="narrative">{{ route.narrative }}</view>
        <button class="btn-chat" @click="goChat">让数字人为我讲解 →</button>
      </view>
    </view>
  </view>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { planRoute } from '../../api'

const parkName = ref('灵山胜境')
const parkCode = ref('lingshan')
const pref = reactive({ history: 0.5, nature: 0.5, architecture: 0.5, family: 0.5, photo: 0.5, duration_min: 90, wheelchair: false, children: false, rush: false })

const PRESETS = {
  family:  { duration_min: 90,  children: true,  wheelchair: false, rush: false },
  photo:   { duration_min: 120, children: false, wheelchair: false, rush: false },
  history: { duration_min: 180, children: false, wheelchair: false, rush: false },
}

function applyPreset(name) {
  Object.assign(pref, PRESETS[name])
}

const route = ref(null)
const loading = ref(false)

onMounted(() => {
  const name = uni.getStorageSync('park_name')
  const code = uni.getStorageSync('park')
  if (name) parkName.value = name
  if (code) parkCode.value = code
})

async function submit() {
  loading.value = true
  try {
    const res = await planRoute(parkCode.value, pref)
    route.value = res
    uni.setStorageSync('route', JSON.stringify(res))
    uni.setStorageSync('pref', JSON.stringify(pref))
  } catch (err) {
    uni.showToast({ title: '规划失败', icon: 'error' })
  } finally {
    loading.value = false
  }
}

function goChat() {
  uni.navigateTo({ url: '/pages/chat/index' })
}
</script>

<style scoped>
.page { min-height: 100vh; padding: 20px; display: flex; justify-content: center; background-color: #f8f9fa; }
.card { width: 100%; background: white; padding: 20px; border-radius: 12px; }
.header-title { font-size: 22px; font-weight: bold; margin-bottom: 5px; color: #333; }
.hint { color: #888; font-size: 13px; margin-bottom: 20px; }
.row { margin: 14px 0; }
.label { color: #444; font-size: 14px; margin-bottom: 5px; display: block; }
.slider { margin: 10px 0; }
.constraints { display: flex; flex-direction: column; gap: 12px; margin: 20px 0; }
.checkbox-label { display: flex; align-items: center; font-size: 14px; color: #444; }
.presets { margin: 20px 0; }
.preset-title { color: #888; font-size: 13px; margin-bottom: 10px; }
.preset-cards { display: flex; gap: 10px; }
.preset-card { flex: 1; padding: 15px 5px; border: 1px solid #dde; border-radius: 8px; text-align: center; font-size: 13px; background: #f8f9ff; }
.preset-card .small { color: #888; font-size: 11px; display: block; margin-top: 5px; }
.btn { background: #2c7be5; color: white; border-radius: 8px; margin-top: 20px; font-size: 16px; }
.btn-chat { background: #00c853; color: white; border-radius: 8px; margin-top: 15px; font-size: 16px; }
.result { margin-top: 30px; padding-top: 20px; border-top: 1px dashed #ddd; }
.result-title { font-size: 16px; font-weight: bold; color: #333; margin-bottom: 10px; }
.narrative { background: #f0f7ff; padding: 12px; border-radius: 6px; color: #2c5599; font-size: 14px; line-height: 1.6; }
</style>
