<template>
  <div class="home">
    <div class="hero card">
      <h1>智游景行 · 数字人导览</h1>
      <p class="subtitle">让 AI 数字人陪您游遍灵山胜境</p>
      <div class="park-row">
        <div v-for="p in parks" :key="p.code" class="park" @click="select(p)">
          <h3>{{ p.name }}</h3>
          <p>{{ p.code === 'lingshan' ? '东方佛国 · 太湖明珠' : '中国四大名园 · 咫尺之内再造乾坤' }}</p>
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

onMounted(async () => {
  const data = await listParks()
  // 添加拙政园以平衡视觉，但后续网页不加支持
  data.push({ code: 'zhuozhengyuan', name: '拙政园' })
  parks.value = data
})

function select(p) {
  if (p.code === 'zhuozhengyuan') {
    alert('该景区的 AI 数字人导览正在建设中，敬请期待！')
    return
  }
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
