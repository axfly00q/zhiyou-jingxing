<template>
  <div class="landing-container">
    <!-- 背景层：底层图片 + 深度压暗 + 颗粒感噪点 -->
    <div class="bg-base"></div>
    <!-- 禅意微尘特效 (CSS Particles) -->
    <div class="dust-particles">
      <div v-for="n in 30" :key="n" class="dust"></div>
    </div>

    <!-- 顶部导航 -->
    <nav class="top-nav fade-in-down">
      <div class="nav-left">
        <div class="logo-box">
          <span class="logo-icon">✧</span>
          <span class="logo-text">灵山胜境</span>
        </div>
      </div>
      
      <div class="nav-center">
        <div class="segmented-control">
          <button 
            :class="['seg-btn', { active: currentTab === 'tourist' }]"
            @click="currentTab = 'tourist'"
          >
            游客 · 灵境
          </button>
          <button 
            :class="['seg-btn', { active: currentTab === 'admin' }]"
            @click="currentTab = 'admin'"
          >
            后台 · 智脑
          </button>
        </div>
      </div>

      <div class="nav-right">
        <div class="status-indicator">
          <span class="dot pulse-glow"></span>
          <span class="tech-text">大模型核心引擎运行中</span>
        </div>
      </div>
    </nav>

    <!-- 主体区域 -->
    <main class="main-content">
      <!-- 左侧：东方画廊 (拱门与圆满) -->
      <div class="gallery-section fade-in-up">
        <!-- 佛龛形主图 (拱门) -->
        <div class="arch-frame">
          <img src="/images/lingshan_arch.png" alt="灵山大佛" class="zoom-img" />
          <div class="arch-overlay"></div>
        </div>
        <!-- 圆满形副图 (圆形) -->
        <div class="circle-frame frame-floating">
          <img src="/images/lingshan_circle.png" alt="梵宫" class="zoom-img" />
        </div>
      </div>

      <!-- 右侧：留白与诗意排版 -->
      <div class="typography-section fade-in-up delay-1">
        <transition name="fade-blur" mode="out-in">
          
          <!-- 游客端界面 -->
          <div v-if="currentTab === 'tourist'" class="content-block" key="tourist">
            <div class="oriental-badge">AI GUIDE</div>
            <h1 class="hero-title serif-font">灵境<br/>智导</h1>
            <p class="hero-subtitle">
              一花一世界，一叶一菩提。<br/>
              面向灵山胜境的专属数字人导览服务，<br/>
              为您带来智能问答、语音伴游与静心开示。
            </p>
            <div class="action-buttons">
              <button class="btn-zen" @click="enterTourist">
                <span class="btn-text">开启智慧导览</span>
                <span class="pulse-ring"></span>
              </button>
            </div>
          </div>

          <!-- 管理后台界面 -->
          <div v-else-if="currentTab === 'admin'" class="content-block admin-block" key="admin">
            <div class="oriental-badge gold">SYSTEM</div>
            <h1 class="hero-title serif-font">灵山<br/>智脑</h1>
            <p class="hero-subtitle">
              景区全域数据监测与数字人知识库管理。<br/>
              洞悉客流，护航胜境。
            </p>
            
            <form class="login-form" @submit.prevent="handleAdminLogin">
              <div class="input-line">
                <input type="text" v-model="adminForm.username" required />
                <label>管理员账号</label>
                <div class="line-focus"></div>
              </div>
              <div class="input-line">
                <input type="password" v-model="adminForm.password" required />
                <label>访问口令</label>
                <div class="line-focus"></div>
              </div>
              <button type="submit" class="btn-solid-gold">进入控制台</button>
            </form>
          </div>

        </transition>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const currentTab = ref('tourist')

const adminForm = ref({
  username: '',
  password: ''
})

const enterTourist = () => {
  localStorage.setItem('token', 'tourist-token')
  localStorage.setItem('role', 'tourist')
  router.push('/tourist')
}

const handleAdminLogin = () => {
  if (adminForm.value.username && adminForm.value.password) {
    localStorage.setItem('token', 'admin-token')
    localStorage.setItem('role', 'admin')
    router.push('/admin')
  } else {
    alert('请输入账号和密码')
  }
}

// 动态生成香火微尘的随机动画参数
onMounted(() => {
  const dusts = document.querySelectorAll('.dust')
  dusts.forEach(dust => {
    dust.style.left = Math.random() * 100 + 'vw'
    dust.style.top = Math.random() * 100 + 'vh'
    dust.style.animationDuration = (Math.random() * 20 + 10) + 's'
    dust.style.animationDelay = (Math.random() * -30) + 's'
  })
})
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Noto+Serif+SC:wght@400;700;900&display=swap');

/* 全局与字体 */
.serif-font {
  font-family: 'Noto Serif SC', 'Songti SC', 'STSong', serif;
}
.sans-font {
  font-family: 'Inter', -apple-system, sans-serif;
}

.landing-container {
  position: relative;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background-color: #05080c;
  color: #e5e7eb;
  font-family: 'Inter', -apple-system, sans-serif;
  display: flex;
  flex-direction: column;
}

/* 沉浸式背景与特效 */
.bg-base {
  position: absolute;
  inset: -5%;
  background-image: url('/images/lingshan_bg.png');
  background-size: cover;
  background-position: center;
  filter: brightness(0.25) contrast(1.1) saturate(0.8) blur(3px);
  z-index: 0;
  transition: filter 1s ease;
}

.dust-particles {
  position: absolute;
  inset: 0;
  z-index: 1;
  pointer-events: none;
  overflow: hidden;
}

.dust {
  position: absolute;
  width: 3px;
  height: 3px;
  background-color: rgba(234, 179, 8, 0.4);
  border-radius: 50%;
  box-shadow: 0 0 10px rgba(234, 179, 8, 0.8);
  animation: floatUp 15s linear infinite;
}

@keyframes floatUp {
  0% { transform: translateY(0) scale(1); opacity: 0; }
  20% { opacity: 1; }
  80% { opacity: 1; }
  100% { transform: translateY(-100vh) scale(1.5); opacity: 0; }
}

/* 顶部导航 */
.top-nav {
  position: relative;
  z-index: 10;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 32px 5%;
  width: 100%;
  box-sizing: border-box;
}

.logo-box {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 20px;
  font-weight: 600;
  letter-spacing: 2px;
  color: #d1d5db;
}
.logo-icon {
  color: #eab308;
}

.segmented-control {
  display: flex;
  gap: 8px;
}

.seg-btn {
  background: transparent;
  border: none;
  color: #9ca3af;
  padding: 8px 24px;
  font-size: 15px;
  letter-spacing: 1px;
  cursor: pointer;
  transition: all 0.4s ease;
  position: relative;
}

.seg-btn::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 0;
  height: 2px;
  background: #eab308;
  transition: width 0.4s ease;
}

.seg-btn:hover { color: #f3f4f6; }
.seg-btn.active { color: #f3f4f6; }
.seg-btn.active::after { width: 100%; }

.status-indicator {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: #9ca3af;
}

.pulse-glow {
  width: 6px;
  height: 6px;
  background-color: #10b981;
  border-radius: 50%;
  box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
  animation: pulse-green 2s infinite;
}

@keyframes pulse-green {
  70% { box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
  100% { box-shadow: 0 0 0 0; }
}

/* 主体布局 */
.main-content {
  position: relative;
  z-index: 10;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12%;
  padding: 0 10%;
  box-sizing: border-box;
}

/* 左侧：东方画廊 */
.gallery-section {
  position: relative;
  width: 400px;
  height: 560px;
}

.arch-frame {
  position: absolute;
  width: 320px;
  height: 480px;
  left: 0;
  bottom: 0;
  /* 拱门遮罩效果 */
  border-radius: 160px 160px 0 0;
  overflow: hidden;
  box-shadow: 0 30px 60px rgba(0,0,0,0.6);
  border: 1px solid rgba(255,255,255,0.05);
}

.arch-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(to bottom, transparent 60%, rgba(5,8,12,0.9));
  pointer-events: none;
}

.circle-frame {
  position: absolute;
  width: 220px;
  height: 220px;
  right: -20px;
  top: 20px;
  border-radius: 50%;
  overflow: hidden;
  box-shadow: 0 20px 40px rgba(0,0,0,0.8);
  border: 4px solid rgba(255,255,255,0.05);
}

.frame-floating {
  animation: floating 6s ease-in-out infinite;
}

@keyframes floating {
  0% { transform: translateY(0); }
  50% { transform: translateY(-15px); }
  100% { transform: translateY(0); }
}

.zoom-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 10s ease;
}
.gallery-section:hover .zoom-img {
  transform: scale(1.1);
}

/* 右侧排版 */
.typography-section {
  flex: 1;
  max-width: 500px;
}

.oriental-badge {
  display: inline-block;
  font-size: 12px;
  letter-spacing: 4px;
  color: #9ca3af;
  margin-bottom: 24px;
  position: relative;
  padding-left: 20px;
}
.oriental-badge::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 8px;
  height: 8px;
  background: #10b981;
  border-radius: 50%;
}
.oriental-badge.gold::before {
  background: #eab308;
}

.hero-title {
  font-size: 86px;
  font-weight: 700;
  line-height: 1.1;
  margin: 0 0 32px 0;
  background: linear-gradient(135deg, #ffffff 0%, #a1a1aa 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  text-shadow: 0 10px 30px rgba(0,0,0,0.5);
}

.hero-subtitle {
  font-size: 18px;
  line-height: 2;
  color: #9ca3af;
  margin-bottom: 48px;
  font-weight: 300;
  letter-spacing: 1px;
}

/* 禅意按钮 */
.action-buttons {
  position: relative;
}

.btn-zen {
  position: relative;
  background: rgba(16, 185, 129, 0.1);
  border: 1px solid rgba(16, 185, 129, 0.3);
  color: #10b981;
  padding: 16px 48px;
  border-radius: 40px;
  font-size: 16px;
  letter-spacing: 2px;
  cursor: pointer;
  overflow: hidden;
  backdrop-filter: blur(10px);
  transition: all 0.4s ease;
}

.btn-zen:hover {
  background: rgba(16, 185, 129, 0.2);
  transform: translateY(-2px);
  box-shadow: 0 10px 30px rgba(16, 185, 129, 0.2);
}

.pulse-ring {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 100%;
  height: 100%;
  border-radius: 40px;
  border: 1px solid rgba(16, 185, 129, 0.5);
  animation: pulse-ring 2s infinite cubic-bezier(0.215, 0.61, 0.355, 1);
}

@keyframes pulse-ring {
  0% { transform: translate(-50%, -50%) scale(1); opacity: 1; }
  100% { transform: translate(-50%, -50%) scale(1.3); opacity: 0; }
}

/* 管理端极简表单 */
.login-form {
  display: flex;
  flex-direction: column;
  gap: 32px;
  max-width: 320px;
}

.input-line {
  position: relative;
}

.input-line input {
  width: 100%;
  background: transparent;
  border: none;
  border-bottom: 1px solid rgba(255,255,255,0.2);
  padding: 12px 0;
  font-size: 16px;
  color: #fff;
  transition: all 0.3s ease;
}

.input-line input:focus {
  outline: none;
  border-color: transparent;
}

.input-line label {
  position: absolute;
  left: 0;
  top: 12px;
  font-size: 16px;
  color: #6b7280;
  pointer-events: none;
  transition: all 0.3s ease;
}

.input-line input:focus ~ label,
.input-line input:valid ~ label {
  top: -20px;
  font-size: 12px;
  color: #eab308;
}

.line-focus {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 0;
  height: 2px;
  background: #eab308;
  transition: width 0.4s ease;
}

.input-line input:focus ~ .line-focus {
  width: 100%;
}

.btn-solid-gold {
  background: linear-gradient(135deg, #eab308 0%, #ca8a04 100%);
  color: #000;
  border: none;
  padding: 16px;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 2px;
  cursor: pointer;
  margin-top: 16px;
  transition: all 0.3s ease;
}

.btn-solid-gold:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 20px rgba(234, 179, 8, 0.3);
}

/* 进场动画 */
.fade-in-up {
  animation: fadeInUp 1.2s cubic-bezier(0.2, 0.8, 0.2, 1) forwards;
  opacity: 0;
  transform: translateY(40px);
}
.fade-in-down {
  animation: fadeInDown 1s cubic-bezier(0.2, 0.8, 0.2, 1) forwards;
  opacity: 0;
  transform: translateY(-20px);
}
.delay-1 { animation-delay: 0.2s; }

@keyframes fadeInUp { to { opacity: 1; transform: translateY(0); } }
@keyframes fadeInDown { to { opacity: 1; transform: translateY(0); } }

/* 切换动画 */
.fade-blur-enter-active,
.fade-blur-leave-active {
  transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}
.fade-blur-enter-from {
  opacity: 0;
  transform: translateY(20px);
  filter: blur(10px);
}
.fade-blur-leave-to {
  opacity: 0;
  transform: translateY(-20px);
  filter: blur(10px);
}
</style>
