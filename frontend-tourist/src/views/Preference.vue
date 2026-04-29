<template>
  <div class="page">
    <div class="card">
      <h2>{{ parkName }} · 偏好引导</h2>
      <p class="hint">滑动调整你的兴趣，AI 将为你定制游览路线</p>

      <div v-for="(label, key) in PREFS" :key="key" class="row">
        <span class="label">{{ label }}</span>
        <input type="range" min="0" max="1" step="0.1" v-model.number="pref[key]" />
        <span class="val">{{ pref[key].toFixed(1) }}</span>
      </div>

      <div class="row">
        <span class="label">游览时长（分钟）</span>
        <input type="range" min="30" max="240" step="15" v-model.number="pref.duration_min" />
        <span class="val">{{ pref.duration_min }}</span>
      </div>

      <button class="btn" :disabled="loading" @click="submit">
        {{ loading ? '规划中...' : '生成专属路线' }}
      </button>
      <p v-if="errMsg" style="color:#dc3545;margin:8px 0">⚠ {{ errMsg }}</p>

      <div v-if="route" class="result">
        <h3>{{ route.park }} · 推荐路线（约 {{ route.total_minutes }} 分钟）</h3>
        <p class="narrative">{{ route.narrative }}</p>
        <ol>
          <li v-for="s in route.spots" :key="s.code">
            <strong>{{ s.name }}</strong>
            <span class="badge" v-for="t in s.themes" :key="t">{{ THEME_LABEL[t] || t }}</span>
            <div class="hl">{{ s.highlight }}</div>
            <div class="mins">建议停留 {{ s.suggested_minutes }} 分钟</div>
          </li>
        </ol>
        <button class="btn" @click="goChat">让数字人为我讲解 →</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { planRoute } from '../api.js'

const router = useRouter()
const park = sessionStorage.getItem('park') || 'zhuozhengyuan'
const parkName = sessionStorage.getItem('park_name') || '拙政园'

const PREFS = { history: '历史人文', nature: '自然风光', architecture: '建筑艺术', family: '亲子友好', photo: '摄影打卡' }
const THEME_LABEL = { history: '历史', nature: '自然', architecture: '建筑', family: '亲子', photo: '摄影' }

const pref = reactive({ history: 0.5, nature: 0.5, architecture: 0.5, family: 0.5, photo: 0.5, duration_min: 90 })
const route = ref(null)
const loading = ref(false)
const errMsg = ref('')

async function submit() {
  loading.value = true
  errMsg.value = ''
  try {
    route.value = await planRoute(park, pref)
    sessionStorage.setItem('route', JSON.stringify(route.value))
  } catch (e) {
    errMsg.value = e.response?.data?.detail || e.message || '路线规划失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

function goChat() {
  router.push('/chat')
}
</script>

<style scoped>
.page { min-height: 100vh; padding: 30px 20px; display: flex; justify-content: center; }
.card { max-width: 720px; width: 100%; }
.hint { color: #888; margin-top: -8px; }
.row { display: flex; align-items: center; margin: 14px 0; }
.label { width: 130px; color: #444; }
input[type=range] { flex: 1; margin: 0 12px; }
.val { width: 40px; color: #2c7be5; font-weight: 600; }
.result { margin-top: 30px; padding-top: 20px; border-top: 1px dashed #ddd; }
.narrative { background: #f0f7ff; padding: 12px; border-radius: 6px; color: #2c5599; line-height: 1.6; }
ol { padding-left: 22px; }
li { margin: 12px 0; }
.badge { display: inline-block; background: #e8f0fe; color: #2c7be5; padding: 2px 8px; border-radius: 10px; font-size: 12px; margin-left: 6px; }
.hl { color: #555; font-size: 13px; margin: 4px 0; }
.mins { color: #999; font-size: 12px; }
</style>
