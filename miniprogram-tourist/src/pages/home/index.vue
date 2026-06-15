<template>
  <view class="home-container">
    <!-- 背景层 -->
    <image class="bg-image" src="/static/lingshan_bg.png" mode="aspectFill" />
    <view class="bg-overlay" />

    <!-- 浮尘粒子 -->
    <view class="particles">
      <view v-for="n in 16" :key="n" class="dust" :style="dustStyle(n)" />
    </view>

    <!-- 主面板 -->
    <view class="hero-panel fade-in-up">
      <view class="oriental-badge">
        <view class="badge-dot" />
        <text class="badge-text">DESTINATION</text>
      </view>

      <text class="hero-title">选择您的朝圣之旅</text>
      <text class="hero-subtitle">让专属 AI 数字人陪您游遍大江南北的绝美胜境</text>

      <view class="park-row">
        <view
          v-for="p in parks"
          :key="p.code"
          class="park-card"
          :class="{ 'park-card--active': activeCard === p.code }"
          @touchstart="activeCard = p.code"
          @touchend="activeCard = ''"
          @tap="select(p)"
        >
          <text class="park-name">{{ p.name }}</text>
          <text class="park-desc">{{ p.code === 'lingshan' ? '东方佛国 · 太湖明珠' : '江南第一厅堂 · 三大名石之冠' }}</text>
          <view class="card-glow" />
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue'

const parks = ref([
  { code: 'lingshan', name: '灵山胜境' }
])

const activeCard = ref('')

function dustStyle(n) {
  const seed = n * 137.508
  const left = (seed % 100).toFixed(1)
  const delay = (n * 1.3 % 20).toFixed(1)
  const duration = (10 + n * 1.7 % 15).toFixed(1)
  const size = n % 2 === 0 ? '4rpx' : '3rpx'
  return `left:${left}%;animation-delay:-${delay}s;animation-duration:${duration}s;width:${size};height:${size};top:100%`
}

function select(p) {
  uni.setStorageSync('park', p.code)
  uni.setStorageSync('park_name', p.name)
  uni.navigateTo({ url: '/pages/preferences/index' })
}
</script>

<style scoped>
/* ── 容器 ── */
.home-container {
  min-height: 100vh;
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  overflow: hidden;
  background-color: #05080c;
  padding: 60rpx 40rpx;
  box-sizing: border-box;
}

/* ── 背景 ── */
.bg-image {
  position: absolute;
  top: 0; left: 0;
  width: 100%; height: 100%;
  z-index: 0;
}
.bg-overlay {
  position: absolute;
  top: 0; left: 0;
  width: 100%; height: 100%;
  background: rgba(2, 5, 10, 0.72);
  z-index: 1;
}

/* ── 浮尘粒子 ── */
.particles {
  position: absolute;
  top: 0; left: 0;
  width: 100%; height: 100%;
  z-index: 2;
  pointer-events: none;
  overflow: hidden;
}
.dust {
  position: absolute;
  background: rgba(234, 179, 8, 0.55);
  border-radius: 50%;
  box-shadow: 0 0 8rpx rgba(234, 179, 8, 0.9);
  animation: floatUp linear infinite;
}
@keyframes floatUp {
  0%   { transform: translateY(0) scale(1); opacity: 0; }
  15%  { opacity: 1; }
  85%  { opacity: 0.9; }
  100% { transform: translateY(-110vh) scale(1.6); opacity: 0; }
}

/* ── 主面板 ── */
.hero-panel {
  position: relative;
  z-index: 10;
  width: 100%;
  max-width: 680rpx;
  text-align: center;
  padding: 70rpx 48rpx 60rpx;
  background: rgba(10, 15, 25, 0.55);
  border: 1rpx solid rgba(255, 255, 255, 0.10);
  border-radius: 40rpx;
  box-shadow: 0 40rpx 80rpx rgba(0, 0, 0, 0.55);
  /* backdrop-filter 在新版微信中支持 */
  backdrop-filter: blur(24rpx);
  display: flex;
  flex-direction: column;
  align-items: center;
}

/* ── 徽章 ── */
.oriental-badge {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 36rpx;
}
.badge-dot {
  width: 12rpx; height: 12rpx;
  background: #eab308;
  border-radius: 50%;
  margin-right: 14rpx;
  box-shadow: 0 0 10rpx rgba(234, 179, 8, 0.8);
}
.badge-text {
  font-size: 22rpx;
  letter-spacing: 8rpx;
  color: #eab308;
  font-weight: 600;
}

/* ── 标题 ── */
.hero-title {
  font-size: 52rpx;
  font-weight: 700;
  color: #f3f4f6;
  margin-bottom: 20rpx;
  display: block;
  /* 微信小程序中衬线字体用 STSong / Songti SC 系统字体 */
  font-family: 'STSong', 'Songti SC', 'SimSun', serif;
  letter-spacing: 2rpx;
  text-shadow: 0 0 30rpx rgba(255,255,255,0.15);
}

/* ── 副标题 ── */
.hero-subtitle {
  font-size: 26rpx;
  color: #9ca3af;
  margin-bottom: 70rpx;
  display: block;
  letter-spacing: 2rpx;
  line-height: 1.7;
}

/* ── 景区卡片列表 ── */
.park-row {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 0;
}

/* ── 景区卡片 ── */
.park-card {
  position: relative;
  background: rgba(255, 255, 255, 0.04);
  border: 1rpx solid rgba(255, 255, 255, 0.10);
  border-radius: 24rpx;
  padding: 44rpx 36rpx;
  margin-bottom: 28rpx;
  overflow: hidden;
  transition: all 0.3s ease;
}
.park-card:last-child { margin-bottom: 0; }

.park-card--active {
  background: rgba(255, 255, 255, 0.09);
  border-color: rgba(234, 179, 8, 0.5);
  transform: scale(0.98);
}
.park-card--active .card-glow {
  opacity: 1;
}

.park-name {
  display: block;
  font-size: 40rpx;
  font-weight: 700;
  color: #f3f4f6;
  margin-bottom: 16rpx;
  font-family: 'STSong', 'Songti SC', 'SimSun', serif;
}
.park-desc {
  display: block;
  font-size: 24rpx;
  color: #9ca3af;
  letter-spacing: 2rpx;
}

.card-glow {
  position: absolute;
  top: 0; left: 0;
  width: 100%; height: 100%;
  border-radius: 24rpx;
  box-shadow: inset 0 0 40rpx rgba(234, 179, 8, 0.18);
  opacity: 0;
  transition: opacity 0.3s ease;
  pointer-events: none;
}

/* ── 进场动画 ── */
.fade-in-up {
  animation: fadeInUp 0.9s cubic-bezier(0.2, 0.8, 0.2, 1) forwards;
  opacity: 0;
  transform: translateY(40rpx);
}
@keyframes fadeInUp {
  to { opacity: 1; transform: translateY(0); }
}
</style>
