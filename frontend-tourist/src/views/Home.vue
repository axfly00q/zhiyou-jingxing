<template>
  <div class="home">
    <div class="hero card">
      <h1>智游景行 · 数字人导览</h1>
      <p class="subtitle">让 AI 数字人陪您游遍苏州园林</p>
      <div class="park-row">
        <div v-for="p in parks" :key="p.code" class="park" @click="select(p)">
          <h3>{{ p.name }}</h3>
          <p>{{ p.code === 'zhuozhengyuan' ? '世界文化遗产 · 中国四大名园' : '江南第一厅堂 · 三大名石之冠' }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { listParks } from '../api.js'

const router = useRouter()
const parks = ref([])

onMounted(async () => { parks.value = await listParks() })

function select(p) {
  sessionStorage.setItem('park', p.code)
  sessionStorage.setItem('park_name', p.name)
  router.push('/preference')
}
</script>

<style scoped>
.home { min-height: 100vh; padding: 60px 20px; display: flex; justify-content: center; }
.hero { max-width: 900px; width: 100%; text-align: center; padding: 50px 30px; }
.subtitle { color: #888; margin-bottom: 40px; }
.park-row { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
.park { background: #f8faff; border: 2px solid transparent; border-radius: 10px; padding: 30px; cursor: pointer; transition: 0.2s; }
.park:hover { border-color: #2c7be5; transform: translateY(-2px); }
.park h3 { margin: 0 0 10px; color: #2c7be5; }
.park p { margin: 0; color: #666; font-size: 13px; }
@media (max-width: 600px) { .park-row { grid-template-columns: 1fr; } }
</style>
