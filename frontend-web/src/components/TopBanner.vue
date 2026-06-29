<template>
  <nav class="top-nav fade-in-down">
    <div class="nav-left">
      <div class="logo-box">
        <span class="logo-icon">✧</span>
        <span v-if="showTitle" class="logo-text">{{ title }}</span>
      </div>
    </div>

    <div class="nav-center">
      <slot name="center"></slot>
    </div>

    <div class="nav-right">
      <div class="status-indicator">
        <span class="dot pulse-glow"></span>
        <span class="tech-text">{{ statusText }}</span>
      </div>
    </div>
  </nav>
</template>

<script setup>
defineProps({
  showTitle: {
    type: Boolean,
    default: true
  },
  title: {
    type: String,
    default: '灵山胜境'
  },
  statusText: {
    type: String,
    default: '大模型核心引擎运行中'
  }
})
</script>

<style scoped>
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

.nav-center {
  display: flex;
  justify-content: center;
  flex: 1;
}

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
</style>
