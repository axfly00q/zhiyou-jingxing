<template>
  <div>
    <h2>服务优化建议</h2>
    <p style="color:#666">由情感分析 + LLM 自动从游客负面反馈中提炼，每 30 分钟更新一次。</p>
    <table>
      <thead><tr><th>优先级</th><th>问题摘要</th><th>建议</th><th>状态</th><th>生成时间</th><th>操作</th></tr></thead>
      <tbody>
        <tr v-for="s in list" :key="s.id">
          <td><span :class="['badge', s.priority]">{{ s.priority }}</span></td>
          <td>{{ s.title }}</td>
          <td>{{ s.summary }}</td>
          <td><span :class="['status', s.status]">{{ statusLabel[s.status] || s.status }}</span></td>
          <td>{{ new Date(s.created_at).toLocaleString() }}</td>
          <td class="actions">
            <button v-if="s.status !== 'open'" @click="setStatus(s, 'open')" class="btn-status open">待处理</button>
            <button v-if="s.status !== 'resolved'" @click="setStatus(s, 'resolved')" class="btn-status resolved">已解决</button>
            <button v-if="s.status !== 'ignored'" @click="setStatus(s, 'ignored')" class="btn-status ignored">已忽略</button>
          </td>
        </tr>
        <tr v-if="!list.length"><td colspan="6" style="text-align:center;color:#999">暂无数据</td></tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import api from '../api.js'

const list = ref([])
const statusLabel = { open: '待处理', resolved: '已解决', ignored: '已忽略' }

onMounted(async () => { list.value = (await api.get('/analytics/suggestions')).data })

async function setStatus(suggestion, status) {
  await api.patch(`/admin/suggestions/${suggestion.id}/status`, { status })
  suggestion.status = status
}
</script>

<style scoped>
.actions { white-space: nowrap; }
.btn-status { border: none; border-radius: 4px; padding: 3px 10px; cursor: pointer; font-size: 12px; margin-right: 4px; }
.btn-status.open { background: #e0f0ff; color: #1d6fa4; }
.btn-status.resolved { background: #e6f9ed; color: #1a7a3c; }
.btn-status.ignored { background: #f5f5f5; color: #888; }
.status { padding: 2px 8px; border-radius: 10px; font-size: 12px; }
.status.open { background: #e0f0ff; color: #1d6fa4; }
.status.resolved { background: #e6f9ed; color: #1a7a3c; }
.status.ignored { background: #f5f5f5; color: #888; }
</style>
