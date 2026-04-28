<template>
  <div class="login-bg">
    <div class="box">
      <h2>智游景行 · 运营后台</h2>
      <input v-model="username" placeholder="用户名" />
      <input v-model="password" type="password" placeholder="密码" @keyup.enter="login" />
      <button class="btn" @click="login" :disabled="loading">登录</button>
      <div class="err" v-if="err">{{ err }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api.js'

const router = useRouter()
const username = ref('admin'), password = ref('admin123'), err = ref(''), loading = ref(false)

async function login() {
  loading.value = true; err.value = ''
  try {
    const r = await api.post('/admin/login', { username: username.value, password: password.value })
    localStorage.setItem('token', r.data.access_token)
    router.push('/')
  } catch (e) {
    err.value = '登录失败：' + (e.response?.data?.detail || e.message)
  } finally { loading.value = false }
}
</script>

<style scoped>
.login-bg { height: 100vh; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, #2c7be5, #6f42c1); }
.box { background: #fff; padding: 40px; border-radius: 10px; width: 320px; }
.box h2 { margin: 0 0 20px; text-align: center; }
.box input { width: 100%; margin: 8px 0; }
.box .btn { width: 100%; margin-top: 12px; padding: 10px; }
.err { color: #e63946; margin-top: 10px; font-size: 13px; }
</style>
