<template>
  <view class="home">
    <view class="hero card">
      <view class="title">智游景行 · 数字人导览</view>
      <view class="subtitle">让 AI 数字人陪您游遍灵山胜境</view>
      <view class="park-row">
        <view v-for="p in parks" :key="p.code" class="park" @click="select(p)">
          <view class="park-name">{{ p.name }}</view>
          <view class="park-desc">{{ p.code === 'lingshan' ? '东方佛国 · 太湖明珠' : '江南第一厅堂 · 三大名石之冠' }}</view>
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

function select(p) {
  uni.setStorageSync('park', p.code)
  uni.setStorageSync('park_name', p.name)
  uni.navigateTo({ url: '/pages/preferences/index' })
}
</script>

<style scoped>
.home { min-height: 100vh; padding: 60px 20px; display: flex; justify-content: center; background-color: #f8f9fa; }
.hero { max-width: 900px; width: 100%; text-align: center; padding: 50px 30px; }
.title { font-size: 24px; font-weight: bold; margin-bottom: 10px; color: #333; }
.subtitle { color: #888; margin-bottom: 40px; font-size: 14px; }
.park-row { display: flex; flex-direction: column; gap: 24px; }
.park { background: #f8faff; border: 2px solid #e0e6ed; border-radius: 10px; padding: 30px; transition: 0.2s; }
.park-name { margin: 0 0 10px; color: #2c7be5; font-size: 20px; font-weight: bold; }
.park-desc { margin: 0; color: #666; font-size: 13px; }
</style>
