<template>
  <div>
    <h2>服务优化建议</h2>
    <p style="color:#666">由情感分析 + LLM 自动从游客负面反馈中提炼，每 30 分钟更新一次。</p>
    <table>
      <thead><tr><th>优先级</th><th>问题摘要</th><th>建议</th><th>状态</th><th>生成时间</th></tr></thead>
      <tbody>
        <tr v-for="s in list" :key="s.id">
          <td><span :class="['badge', s.priority]">{{ s.priority }}</span></td>
          <td>{{ s.title }}</td>
          <td>{{ s.summary }}</td>
          <td>{{ s.status }}</td>
          <td>{{ new Date(s.created_at).toLocaleString() }}</td>
        </tr>
        <tr v-if="!list.length"><td colspan="5" style="text-align:center;color:#999">暂无数据</td></tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import api from '../api.js'
const list = ref([])
onMounted(async () => { list.value = (await api.get('/analytics/suggestions')).data })
</script>
