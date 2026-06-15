<template>
  <div class="page-container">
    <div class="bg-layer"></div>
    <div class="dust-particles">
      <div v-for="n in 20" :key="n" class="dust"></div>
    </div>

    <div class="main-content fade-in-up">
      <div class="glass-panel">
        <div class="panel-header">
          <div class="oriental-badge">CUSTOMIZE</div>
          <h2 class="serif-font">{{ parkName }} · 偏好向导</h2>
          <p class="hint">滑动调整您的偏好，AI 将为您定制专属禅意路线</p>
        </div>

        <div class="form-grid">
          <!-- 偏好滑块 -->
          <div class="slider-section">
            <div v-for="(label, key) in PREFS" :key="key" class="slider-row">
              <span class="label">{{ label }}</span>
              <input type="range" min="0" max="1" step="0.1" v-model.number="pref[key]" class="zen-range" />
              <span class="val">{{ pref[key].toFixed(1) }}</span>
            </div>
            
            <div class="slider-row duration-row">
              <span class="label highlight">游览时长 (分钟)</span>
              <input type="range" min="30" max="240" step="15" v-model.number="pref.duration_min" class="zen-range gold" />
              <span class="val highlight">{{ pref.duration_min }}</span>
            </div>
          </div>

          <!-- 约束与快捷选择 -->
          <div class="side-section">
            <div class="constraints">
              <label class="zen-checkbox">
                <input type="checkbox" v-model="pref.wheelchair" />
                <span class="box"></span>
                <span class="text">🦽 需要无障碍通道</span>
              </label>
              <label class="zen-checkbox">
                <input type="checkbox" v-model="pref.children" />
                <span class="box"></span>
                <span class="text">🧒 携带儿童</span>
              </label>
              <label class="zen-checkbox">
                <input type="checkbox" v-model="pref.rush" />
                <span class="box"></span>
                <span class="text">⚡ 时间紧张 (跳过次要景点)</span>
              </label>
            </div>

            <div class="presets">
              <p class="preset-title serif-font">快速场景</p>
              <div class="preset-cards">
                <div class="preset-card" @click="applyPreset('family')">
                  <span class="icon">🧒</span> 亲子游 <small>90分</small>
                </div>
                <div class="preset-card" @click="applyPreset('photo')">
                  <span class="icon">📷</span> 摄影流 <small>120分</small>
                </div>
                <div class="preset-card" @click="applyPreset('history')">
                  <span class="icon">🏛</span> 历史向 <small>180分</small>
                </div>
              </div>
            </div>

            <button class="btn-solid-gold full-width" :disabled="loading" @click="submit">
              {{ loading ? '慧眼演算中...' : '生成专属路线' }}
            </button>
            <p v-if="errMsg" class="error-msg">⚠ {{ errMsg }}</p>
          </div>
        </div>
      </div>

      <!-- 推荐路线结果 (Timeline) -->
      <transition name="fade-slide">
        <div v-if="route" class="glass-panel result-panel">
          <h3 class="serif-font">{{ route.park }} · 推荐路线 <span class="time-tag">约 {{ route.total_minutes }} 分钟</span></h3>
          <p class="narrative">{{ route.narrative }}</p>
          
          <div class="timeline">
            <div v-for="(s, index) in route.spots" :key="s.code" class="timeline-item">
              <div class="timeline-dot"></div>
              <div class="timeline-content">
                <div class="spot-header">
                  <h4>{{ index + 1 }}. {{ s.name }}</h4>
                  <div class="tags">
                    <span class="badge" v-for="t in s.themes" :key="t">{{ THEME_LABEL[t] || t }}</span>
                  </div>
                </div>
                <div class="hl">{{ s.highlight }}</div>
                <div class="mins">建议停留: {{ s.suggested_minutes }} 分钟</div>
              </div>
            </div>
          </div>
          
          <button class="btn-primary full-width mt-4" @click="goChat">开启数字人伴游 →</button>
        </div>
      </transition>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { planRoute } from '../../api.js'

const router = useRouter()
const park = sessionStorage.getItem('park') || 'lingshan'
const parkName = sessionStorage.getItem('park_name') || '灵山胜境'

const PREFS = { history: '历史人文', nature: '自然风光', architecture: '建筑艺术', family: '亲子友好', photo: '摄影打卡' }
const THEME_LABEL = { history: '历史', nature: '自然', architecture: '建筑', family: '亲子', photo: '摄影' }

const pref = reactive({ history: 0.5, nature: 0.5, architecture: 0.5, family: 0.5, photo: 0.5, duration_min: 90, wheelchair: false, children: false, rush: false })

const PRESETS = {
  family:  { family: 0.9, nature: 0.6, history: 0.3, architecture: 0.3, photo: 0.5, duration_min: 90,  children: true,  wheelchair: false, rush: false },
  photo:   { photo: 0.9,  nature: 0.7, architecture: 0.7, history: 0.4, family: 0.2, duration_min: 120, children: false, wheelchair: false, rush: false },
  history: { history: 0.9, architecture: 0.8, nature: 0.4, family: 0.3, photo: 0.5, duration_min: 180, children: false, wheelchair: false, rush: false },
}

function applyPreset(name) { Object.assign(pref, PRESETS[name]) }

const route = ref(null)
const loading = ref(false)
const errMsg = ref('')

async function submit() {
  loading.value = true
  errMsg.value = ''
  try {
    route.value = await planRoute(park, pref)
    sessionStorage.setItem('park', park)
    sessionStorage.setItem('park_name', parkName)
    sessionStorage.setItem('route', JSON.stringify(route.value))
  } catch (e) {
    errMsg.value = e.response?.data?.detail || e.message || '路线规划失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

function goChat() {
  router.push('/tourist/chat')
}

onMounted(() => {
  const dusts = document.querySelectorAll('.dust')
  dusts.forEach(dust => {
    dust.style.left = Math.random() * 100 + 'vw'
    dust.style.top = Math.random() * 100 + 'vh'
    dust.style.animationDuration = (Math.random() * 20 + 10) + 's'
    dust.style.animationDelay = (Math.random() * -20) + 's'
  })
})
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Noto+Serif+SC:wght@400;700;900&display=swap');

.serif-font { font-family: 'Noto Serif SC', 'Songti SC', 'STSong', serif; }

.page-container {
  min-height: 100vh;
  position: relative;
  background-color: #05080c;
  color: #e5e7eb;
  font-family: 'Inter', system-ui, sans-serif;
  overflow-x: hidden;
  overflow-y: auto;
  padding: 60px 20px;
}

.bg-layer {
  position: fixed;
  inset: -5%;
  background-image: url('/images/lingshan_bg.png');
  background-size: cover;
  background-position: center;
  filter: brightness(0.2) contrast(1.2) blur(10px);
  z-index: 0;
}

.dust-particles {
  position: fixed;
  inset: 0;
  z-index: 1;
  pointer-events: none;
}
.dust {
  position: absolute;
  width: 3px; height: 3px;
  background-color: rgba(16, 185, 129, 0.4);
  border-radius: 50%;
  box-shadow: 0 0 10px rgba(16, 185, 129, 0.6);
  animation: floatUp 15s linear infinite;
}
@keyframes floatUp {
  0% { transform: translateY(0) scale(1); opacity: 0; }
  20% { opacity: 1; }
  80% { opacity: 1; }
  100% { transform: translateY(-100vh) scale(1.5); opacity: 0; }
}

.main-content {
  position: relative;
  z-index: 10;
  max-width: 900px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.glass-panel {
  background: rgba(10, 15, 25, 0.6);
  backdrop-filter: blur(24px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 0 30px 60px rgba(0,0,0,0.5);
  border-radius: 24px;
  padding: 40px;
}

.panel-header {
  text-align: center;
  margin-bottom: 48px;
}

.oriental-badge {
  display: inline-block;
  font-size: 12px;
  letter-spacing: 4px;
  color: #10b981;
  margin-bottom: 16px;
  padding-left: 16px;
  position: relative;
}
.oriental-badge::before {
  content: '';
  position: absolute;
  left: 0; top: 50%; transform: translateY(-50%);
  width: 6px; height: 6px;
  background: #10b981;
  border-radius: 50%;
}

.panel-header h2 {
  font-size: 36px;
  margin: 0 0 12px;
  color: #fff;
}
.hint { color: #9ca3af; font-size: 15px; }

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 48px;
}

@media (max-width: 768px) {
  .form-grid { grid-template-columns: 1fr; gap: 32px; }
}

/* Range Sliders */
.slider-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.slider-row {
  display: flex;
  align-items: center;
  gap: 16px;
}

.slider-row .label {
  flex: 0 0 80px;
  font-size: 14px;
  color: #d1d5db;
}
.slider-row .val {
  flex: 0 0 30px;
  font-size: 14px;
  text-align: right;
  color: #10b981;
  font-variant-numeric: tabular-nums;
}

.duration-row {
  margin-top: 16px;
  padding-top: 24px;
  border-top: 1px solid rgba(255,255,255,0.1);
}
.duration-row .highlight { color: #eab308 !important; font-weight: 600; }

.zen-range {
  flex: 1;
  -webkit-appearance: none;
  background: transparent;
}
.zen-range:focus { outline: none; }
.zen-range::-webkit-slider-runnable-track {
  width: 100%;
  height: 4px;
  cursor: pointer;
  background: rgba(255,255,255,0.1);
  border-radius: 2px;
}
.zen-range::-webkit-slider-thumb {
  height: 16px; width: 16px;
  border-radius: 50%;
  background: #10b981;
  cursor: pointer;
  -webkit-appearance: none;
  margin-top: -6px;
  box-shadow: 0 0 10px rgba(16, 185, 129, 0.6);
  transition: transform 0.2s;
}
.zen-range::-webkit-slider-thumb:hover { transform: scale(1.2); }

.zen-range.gold::-webkit-slider-thumb {
  background: #eab308;
  box-shadow: 0 0 10px rgba(234, 179, 8, 0.6);
}

/* Checkboxes */
.constraints {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 32px;
}

.zen-checkbox {
  display: flex;
  align-items: center;
  cursor: pointer;
  group: hover;
}
.zen-checkbox input { display: none; }
.zen-checkbox .box {
  width: 20px; height: 20px;
  border: 1px solid rgba(255,255,255,0.3);
  border-radius: 6px;
  margin-right: 12px;
  display: flex; align-items: center; justify-content: center;
  transition: all 0.3s;
}
.zen-checkbox input:checked + .box {
  background: rgba(16, 185, 129, 0.2);
  border-color: #10b981;
}
.zen-checkbox input:checked + .box::after {
  content: '✓';
  color: #10b981;
  font-size: 14px;
}
.zen-checkbox .text { color: #d1d5db; font-size: 14px; transition: color 0.3s; }
.zen-checkbox:hover .text { color: #fff; }

/* Presets */
.preset-title {
  font-size: 16px;
  color: #eab308;
  margin-bottom: 16px;
  border-bottom: 1px solid rgba(234, 179, 8, 0.2);
  padding-bottom: 8px;
  display: inline-block;
}

.preset-cards {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 32px;
}

.preset-card {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  padding: 12px 16px;
  border-radius: 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 12px;
  color: #d1d5db;
  font-size: 15px;
  transition: all 0.3s;
}
.preset-card:hover {
  background: rgba(255,255,255,0.08);
  border-color: #eab308;
  color: #fff;
}
.preset-card small {
  margin-left: auto;
  color: #9ca3af;
}

/* Buttons */
.full-width { width: 100%; display: block; text-align: center; }
.mt-4 { margin-top: 32px; }

.btn-solid-gold {
  background: linear-gradient(135deg, #eab308 0%, #ca8a04 100%);
  color: #000;
  border: none;
  padding: 16px;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}
.btn-solid-gold:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 10px 20px rgba(234, 179, 8, 0.3); }
.btn-solid-gold:disabled { opacity: 0.6; cursor: not-allowed; filter: grayscale(1); }

.btn-primary {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
  border: 1px solid rgba(16, 185, 129, 0.4);
  padding: 16px;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}
.btn-primary:hover { background: rgba(16, 185, 129, 0.25); transform: translateY(-2px); }

.error-msg { color: #ef4444; margin-top: 12px; font-size: 14px; text-align: center; }

/* Timeline Result */
.result-panel { margin-top: 24px; }
.time-tag {
  font-size: 14px;
  font-weight: normal;
  background: rgba(234, 179, 8, 0.2);
  color: #eab308;
  padding: 4px 12px;
  border-radius: 20px;
  margin-left: 12px;
  vertical-align: middle;
}
.narrative {
  color: #9ca3af;
  line-height: 1.6;
  margin-bottom: 32px;
}

.timeline {
  position: relative;
  padding-left: 24px;
}
.timeline::before {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 2px;
  background: linear-gradient(to bottom, #10b981, rgba(16, 185, 129, 0.1));
}

.timeline-item {
  position: relative;
  margin-bottom: 32px;
}
.timeline-dot {
  position: absolute;
  left: -29px;
  top: 4px;
  width: 12px; height: 12px;
  background: #10b981;
  border-radius: 50%;
  box-shadow: 0 0 10px rgba(16, 185, 129, 0.8);
}

.spot-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 8px;
}
.spot-header h4 {
  margin: 0;
  font-size: 18px;
  color: #f3f4f6;
}
.tags { display: flex; gap: 8px; }
.badge {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
  background: rgba(255,255,255,0.1);
  color: #d1d5db;
  border: 1px solid rgba(255,255,255,0.2);
}

.hl { color: #d1d5db; font-size: 14px; line-height: 1.5; margin-bottom: 8px; }
.mins { font-size: 13px; color: #eab308; }

.fade-in-up { animation: fadeInUp 0.8s cubic-bezier(0.2, 0.8, 0.2, 1) forwards; opacity: 0; transform: translateY(30px); }
.fade-slide-enter-active { transition: all 0.6s ease; }
.fade-slide-enter-from { opacity: 0; transform: translateY(20px); }
@keyframes fadeInUp { to { opacity: 1; transform: translateY(0); } }
</style>
