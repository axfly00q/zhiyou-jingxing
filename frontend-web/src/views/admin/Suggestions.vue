<template>
  <div class="suggestions-page">
    <h2>服务优化建议</h2>
    <p style="color:#666; margin-bottom:20px;">由情感分析 + LLM 自动从游客负面反馈中提炼，每 30 分钟更新一次。</p>

    <div v-if="!list.length" style="text-align:center;color:#999;padding:40px 0;">暂无数据</div>

    <div class="card-grid" v-else>
      <div v-for="s in list" :key="s.id" class="suggestion-card">
        <div class="card-header">
          <span :class="['badge', s.priority]">{{ s.priority }}</span>
          <span class="title">{{ s.title }}</span>
          <span :class="['status', s.status]">{{ statusLabel[s.status] || s.status }}</span>
        </div>
        <div class="card-body">
          <p class="summary">{{ s.summary }}</p>
        </div>
        <div class="card-footer">
          <span class="time">{{ new Date(s.created_at).toLocaleString() }}</span>
          <div class="actions">
            <button v-if="s.status !== 'open'" @click="setStatus(s, 'open')" class="btn-status open">待处理</button>
            <button v-if="s.status !== 'resolved'" @click="setStatus(s, 'resolved')" class="btn-status resolved">已解决</button>
            <button v-if="s.status !== 'ignored'" @click="setStatus(s, 'ignored')" class="btn-status ignored">已忽略</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import api from '../../api.js'

const list = ref([])
const statusLabel = { open: '待处理', resolved: '已解决', ignored: '已忽略' }

onMounted(async () => { list.value = (await api.get('/analytics/suggestions')).data })

async function setStatus(suggestion, status) {
  try {
    await api.patch(`/admin/suggestions/${suggestion.id}/status`, { status })
    suggestion.status = status
  } catch (e) {
    alert('更新失败: ' + (e.response?.data?.detail || e.message))
  }
}
</script>

<style scoped>
.suggestions-page {
  padding-bottom: 40px;
}
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 16px;
}
.suggestion-card {
  background: #1e1e1e;
  border: 1px solid #333;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  flex-direction: column;
}
.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}
.card-header .title {
  flex: 1;
  font-weight: 600;
  font-size: 15px;
  color: #eee;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.card-body {
  flex: 1;
  margin-bottom: 16px;
}
.card-body .summary {
  color: #aaa;
  font-size: 13px;
  line-height: 1.5;
  margin: 0;
}
.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-top: 1px solid #333;
  padding-top: 12px;
}
.card-footer .time {
  color: #666;
  font-size: 12px;
}
.actions {
  display: flex;
  gap: 6px;
}
.btn-status { border: none; border-radius: 4px; padding: 4px 10px; cursor: pointer; font-size: 12px; }
.btn-status.open { background: #1d6fa420; color: #5dade2; border: 1px solid #1d6fa4; }
.btn-status.resolved { background: #1a7a3c20; color: #58d68d; border: 1px solid #1a7a3c; }
.btn-status.ignored { background: #ffffff10; color: #aaa; border: 1px solid #555; }
.btn-status:hover { filter: brightness(1.2); }

.status { padding: 2px 8px; border-radius: 10px; font-size: 12px; }
.status.open { background: #1d6fa4; color: #fff; }
.status.resolved { background: #1a7a3c; color: #fff; }
.status.ignored { background: #444; color: #aaa; }

.badge { padding: 2px 6px; border-radius: 4px; font-size: 12px; font-weight: bold; }
.badge.high { background: #dc3545; color: #fff; }
.badge.medium { background: #fd7e14; color: #fff; }
.badge.low { background: #6c757d; color: #fff; }
</style>
