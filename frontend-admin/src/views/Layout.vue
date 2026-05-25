<template>
  <div class="layout">
    <aside>
      <div class="logo">智游景行</div>
      <nav>
        <router-link to="/avatars">数字人形象</router-link>
        <router-link to="/knowledge">知识库</router-link>
        <router-link to="/suggestions">服务建议</router-link>
        <router-link to="/analytics">数据概览</router-link>
      </nav>
      <button class="logout" @click="logout">退出</button>
    </aside>
    <main><router-view /></main>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
const router = useRouter()
function logout() { localStorage.removeItem('token'); router.push('/login') }
</script>

<style scoped>
.layout { display: grid; grid-template-columns: 200px 1fr; height: 100vh; }
aside { background: #001529; color: #fff; padding: 20px 0; display: flex; flex-direction: column; }
.logo { font-size: 18px; padding: 0 20px 20px; border-bottom: 1px solid #1f2a3c; }
nav { flex: 1; display: flex; flex-direction: column; margin-top: 14px; }
nav a { color: #c5cdd9; padding: 12px 24px; text-decoration: none; }
nav a:hover, nav a.router-link-active { background: #1890ff; color: #fff; }
.logout { margin: 16px; background: transparent; border: 1px solid #555; color: #ccc; padding: 8px; border-radius: 4px; cursor: pointer; }
main { padding: 24px; overflow: auto; }
</style>
