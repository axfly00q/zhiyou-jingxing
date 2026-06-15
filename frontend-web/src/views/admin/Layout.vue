<template>
  <div class="admin-layout">
    <div class="bg-layer"></div>
    <aside class="glass-sidebar">
      <div class="logo">
        <span class="serif-font">灵山智脑</span>
        <div class="logo-sub">SYSTEM ADMIN</div>
      </div>
      <nav>
        <div class="nav-section">SUPERVISION</div>
        <router-link to="/dashboard" class="dashboard-link">
          <span class="icon">🖥</span> 灵山智脑大屏
        </router-link>
        
        <div class="nav-section mt-4">MANAGEMENT</div>
        <router-link to="/admin/avatars">
          <span class="icon">🎭</span> 数字人形象
        </router-link>
        <router-link to="/admin/knowledge">
          <span class="icon">📚</span> 知识库
        </router-link>
        <router-link to="/admin/suggestions">
          <span class="icon">💡</span> 服务建议
        </router-link>
        <router-link to="/admin/analytics">
          <span class="icon">📊</span> 数据概览
        </router-link>
      </nav>
      <button class="logout-btn" @click="logout">
        <span class="icon">🚪</span> 退出系统
      </button>
    </aside>
    <main class="admin-main">
      <div class="main-glass-container fade-in-up">
        <router-view />
      </div>
    </main>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
const router = useRouter()
function logout() { 
  localStorage.removeItem('token')
  localStorage.removeItem('role')
  router.push('/login') 
}
</script>

<!-- 这个是仅针对当前布局框架的局部样式 -->
<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Noto+Serif+SC:wght@400;700;900&display=swap');

.serif-font { font-family: 'Noto Serif SC', 'Songti SC', 'STSong', serif; }

.admin-layout {
  display: flex;
  height: 100vh;
  width: 100%;
  background-color: #1a120b;
  color: #e5e7eb;
  font-family: 'Inter', system-ui, sans-serif;
  overflow: hidden;
  position: relative;
}

.bg-layer {
  position: absolute;
  inset: -5%;
  background-image: url('/images/lingshan_bg.png');
  background-size: cover;
  background-position: center;
  filter: brightness(0.18) sepia(0.6) hue-rotate(-20deg) contrast(1.1) blur(10px);
  z-index: 0;
}

.glass-sidebar {
  position: relative;
  z-index: 10;
  width: 260px;
  display: flex;
  flex-direction: column;
  background: rgba(30, 20, 15, 0.6);
  backdrop-filter: blur(24px);
  border-right: 1px solid rgba(255, 255, 255, 0.05);
  box-shadow: 5px 0 30px rgba(0,0,0,0.5);
}

.logo {
  padding: 32px 24px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  text-align: center;
}

.logo .serif-font {
  font-size: 28px;
  background: linear-gradient(135deg, #eab308 0%, #ca8a04 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: 2px;
}

.logo-sub {
  font-size: 10px;
  color: #9ca3af;
  letter-spacing: 4px;
  margin-top: 6px;
}

nav {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 24px 16px;
  overflow-y: auto;
}

.nav-section {
  font-size: 11px;
  color: #6b7280;
  letter-spacing: 2px;
  margin-bottom: 12px;
  padding-left: 12px;
}

.mt-4 {
  margin-top: 32px;
}

nav a {
  display: flex;
  align-items: center;
  color: #d1d5db;
  padding: 12px 16px;
  text-decoration: none;
  border-radius: 12px;
  margin-bottom: 8px;
  font-size: 14px;
  transition: all 0.3s;
  border: 1px solid transparent;
}

nav a .icon {
  margin-right: 12px;
  font-size: 16px;
}

nav a:hover {
  background: rgba(255, 255, 255, 0.05);
  color: #fff;
}

nav a.router-link-active {
  background: rgba(234, 179, 8, 0.1);
  color: #eab308;
  border-color: rgba(234, 179, 8, 0.3);
  box-shadow: inset 0 0 12px rgba(234, 179, 8, 0.1);
}

.dashboard-link {
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(16, 185, 129, 0.02) 100%);
  border: 1px solid rgba(16, 185, 129, 0.3) !important;
  color: #10b981 !important;
}
.dashboard-link:hover {
  background: rgba(16, 185, 129, 0.2) !important;
}

.logout-btn {
  margin: 24px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #9ca3af;
  padding: 12px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}

.logout-btn:hover {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
  border-color: rgba(239, 68, 68, 0.3);
}

.admin-main {
  position: relative;
  z-index: 10;
  flex: 1;
  padding: 32px;
  overflow-y: auto;
}

.main-glass-container {
  background: rgba(30, 20, 15, 0.65);
  backdrop-filter: blur(24px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 0 30px 60px rgba(0,0,0,0.5);
  border-radius: 24px;
  padding: 32px;
  min-height: calc(100vh - 64px);
}

.fade-in-up {
  animation: fadeInUp 0.6s cubic-bezier(0.2, 0.8, 0.2, 1) forwards;
}
@keyframes fadeInUp {
  0% { opacity: 0; transform: translateY(20px); }
  100% { opacity: 1; transform: translateY(0); }
}
</style>

<!-- 下面这个是不加 scoped 的全局样式，用于暴力穿透并重写子页面的默认白底表单样式 -->
<style>
/* 覆盖原有的丑陋内联样式 */
.admin-main p[style*="color:#666"] { color: #9ca3af !important; }
.admin-main table[style*="margin-top:16px"] { margin-top: 24px !important; }
.admin-main td[style*="text-align:center"] { color: #6b7280 !important; }

.admin-main h2 {
  font-family: 'Noto Serif SC', serif;
  font-size: 32px;
  margin-top: 0;
  margin-bottom: 8px;
  background: linear-gradient(135deg, #fff 0%, #d1d5db 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.admin-main h3 {
  color: #e5e7eb;
  font-size: 20px;
  margin-bottom: 16px;
  border-bottom: 1px solid rgba(255,255,255,0.1);
  padding-bottom: 8px;
}

/* 表格全局暗黑美化 */
.admin-main table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  margin-bottom: 24px;
}
.admin-main th {
  background: rgba(255, 255, 255, 0.03);
  color: #9ca3af;
  font-weight: 500;
  text-align: left;
  padding: 16px;
  font-size: 14px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}
.admin-main td {
  padding: 16px;
  color: #d1d5db;
  font-size: 14px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  vertical-align: middle;
}
.admin-main tbody tr { transition: background 0.3s; }
.admin-main tbody tr:hover { background: rgba(255, 255, 255, 0.02); }

/* 按钮全局美化 */
.admin-main .btn {
  background: rgba(255, 255, 255, 0.05);
  color: #d1d5db;
  border: 1px solid rgba(255, 255, 255, 0.1);
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
  font-size: 13px;
}
.admin-main .btn:hover {
  background: rgba(234, 179, 8, 0.15);
  color: #eab308;
  border-color: rgba(234, 179, 8, 0.3);
}
.admin-main .btn.danger {
  color: #ef4444;
}
.admin-main .btn.danger:hover {
  background: rgba(239, 68, 68, 0.15);
  border-color: rgba(239, 68, 68, 0.3);
}

/* 表单全局美化 */
.admin-main .modal {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}
.admin-main .modal-box {
  background: rgba(15, 20, 30, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 20px 40px rgba(0,0,0,0.6);
  border-radius: 16px;
  padding: 32px;
  width: 100%;
  max-width: 500px;
}
.admin-main .row {
  margin-bottom: 16px;
  display: flex;
  flex-direction: column;
}
.admin-main label {
  font-size: 13px;
  color: #9ca3af;
  margin-bottom: 8px;
}
.admin-main input, 
.admin-main textarea, 
.admin-main select {
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #fff;
  padding: 12px;
  border-radius: 8px;
  outline: none;
  font-family: inherit;
  transition: border-color 0.3s;
}
.admin-main input:focus, 
.admin-main textarea:focus, 
.admin-main select:focus {
  border-color: #eab308;
}

/* 一些小调整修正以前写的 inline style 造成的冲突 */
.admin-main .row > button.btn { margin-top: 16px; width: 100%; background: linear-gradient(135deg, #eab308 0%, #ca8a04 100%); color: #000; font-weight: 600; border: none; }
.admin-main .row > button.btn:hover { background: linear-gradient(135deg, #ca8a04 0%, #a16207 100%); color: #000; }
.admin-main .cancel-btn { margin-top: 12px; width: 100%; text-align: center; color: #9ca3af; cursor: pointer; font-size: 14px; transition: color 0.3s; }
.admin-main .cancel-btn:hover { color: #fff; }
</style>
