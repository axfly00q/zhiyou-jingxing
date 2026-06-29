<template>
  <div class="home-container">
    <div class="bg-layer"></div>
    <div class="dust-particles">
      <div v-for="n in 20" :key="n" class="dust"></div>
    </div>

    <TopBanner :show-title="false" style="position: absolute; top: 0; left: 0; right: 0; z-index: 100; padding: 32px 5%;" />

    <div class="hero glass-panel fade-in-up">
      <div class="oriental-badge">DESTINATION</div>
      <h1 class="serif-font">选择您的朝圣之旅</h1>
      <p class="subtitle">让专属 AI 数字人陪您游遍大江南北的绝美胜境</p>

      <p v-if="loadError" style="color:#f87171;font-size:12px;margin-bottom:8px;">API 异常（已用本地数据）：{{ loadError }}</p>
      <div class="park-row">
        <div v-for="p in parks" :key="p.code" class="park-card" @click="select(p)">
          <div class="card-content">
            <h3 class="serif-font">{{ p.name }}</h3>
            <p>{{ p.code === 'lingshan' ? '东方佛国 · 太湖明珠' : '中国四大名园 · 咫尺之内再造乾坤' }}</p>
          </div>
          <div class="glow-border"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { listParks } from '../../api.js'
import TopBanner from '../../components/TopBanner.vue'

const FALLBACK_PARKS = [
  { code: 'lingshan', name: '灵山胜境' },
]

const router = useRouter()
const parks = ref([])
const loadError = ref('')

onMounted(async () => {
  // Add some random initial positions to dusts
  const dusts = document.querySelectorAll('.dust')
  dusts.forEach(dust => {
    dust.style.left = Math.random() * 100 + 'vw'
    dust.style.top = Math.random() * 100 + 'vh'
    dust.style.animationDuration = (Math.random() * 20 + 10) + 's'
    dust.style.animationDelay = (Math.random() * -20) + 's'
  })

  try {
    parks.value = await listParks()
  } catch (e) {
    console.error('[Home] listParks failed:', e)
    loadError.value = e?.message || String(e)
    parks.value = FALLBACK_PARKS
  }

  // 添加拙政园以平衡视觉，但后续网页不加支持
  parks.value.push({ code: 'zhuozhengyuan', name: '拙政园' })
})

function select(p) {
  if (p.code === 'zhuozhengyuan') {
    alert('该景区的 AI 数字人导览正在建设中，敬请期待！')
    return
  }
  sessionStorage.setItem('park', p.code)
  sessionStorage.setItem('park_name', p.name)
  router.push('/tourist/preference')
}
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Noto+Serif+SC:wght@400;700;900&display=swap');

.serif-font { font-family: 'Noto Serif SC', 'Songti SC', 'STSong', serif; }

.home-container {
  min-height: 100vh;
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  overflow: hidden;
  background-color: #05080c;
  font-family: 'Inter', system-ui, sans-serif;
  padding: 20px;
}

.bg-layer {
  position: absolute;
  inset: -5%;
  background-image: url('/images/lingshan_bg.png');
  background-size: cover;
  background-position: center;
  filter: brightness(0.3) contrast(1.1) blur(4px);
  z-index: 0;
}

.dust-particles {
  position: absolute;
  inset: 0;
  z-index: 1;
  pointer-events: none;
}

.dust {
  position: absolute;
  width: 3px; height: 3px;
  background-color: rgba(234, 179, 8, 0.5);
  border-radius: 50%;
  box-shadow: 0 0 8px rgba(234, 179, 8, 0.8);
  animation: floatUp 15s linear infinite;
}

@keyframes floatUp {
  0% { transform: translateY(0) scale(1); opacity: 0; }
  20% { opacity: 1; }
  80% { opacity: 1; }
  100% { transform: translateY(-100vh) scale(1.5); opacity: 0; }
}

.glass-panel {
  position: relative;
  z-index: 10;
  background: rgba(10, 15, 25, 0.6);
  backdrop-filter: blur(24px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 30px 60px rgba(0,0,0,0.5);
  border-radius: 24px;
}

.hero {
  max-width: 800px;
  width: 100%;
  text-align: center;
  padding: 60px 40px;
  color: #fff;
}

.oriental-badge {
  display: inline-block;
  font-size: 12px;
  letter-spacing: 4px;
  color: #eab308;
  margin-bottom: 24px;
  padding-left: 16px;
  position: relative;
}
.oriental-badge::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 6px; height: 6px;
  background: #eab308;
  border-radius: 50%;
}

.hero h1 {
  font-size: 48px;
  font-weight: 700;
  margin: 0 0 16px;
  background: linear-gradient(135deg, #fff 0%, #d1d5db 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.subtitle {
  color: #9ca3af;
  font-size: 16px;
  margin-bottom: 48px;
  letter-spacing: 1px;
}

.park-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.park-card {
  position: relative;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  padding: 32px 24px;
  cursor: pointer;
  transition: all 0.4s ease;
  overflow: hidden;
}

.card-content {
  position: relative;
  z-index: 2;
}

.park-card h3 {
  margin: 0 0 12px;
  color: #f3f4f6;
  font-size: 24px;
  font-weight: 700;
}

.park-card p {
  margin: 0;
  color: #9ca3af;
  font-size: 13px;
  letter-spacing: 1px;
}

.glow-border {
  position: absolute;
  inset: 0;
  border-radius: 16px;
  opacity: 0;
  box-shadow: inset 0 0 20px rgba(234, 179, 8, 0.2);
  transition: opacity 0.4s ease;
  z-index: 1;
}

.park-card:hover {
  transform: translateY(-4px);
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(234, 179, 8, 0.4);
}

.park-card:hover .glow-border {
  opacity: 1;
}

@media (max-width: 600px) {
  .park-row { grid-template-columns: 1fr; }
  .hero h1 { font-size: 36px; }
  .hero { padding: 40px 20px; }
}

.fade-in-up {
  animation: fadeInUp 1s cubic-bezier(0.2, 0.8, 0.2, 1) forwards;
  opacity: 0;
  transform: translateY(30px);
}
@keyframes fadeInUp { to { opacity: 1; transform: translateY(0); } }
</style>
