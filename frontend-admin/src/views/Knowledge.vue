<template>
  <div>
    <h2>知识库管理</h2>
    <p style="color:#666;font-size:13px;margin:6px 0 14px">
      上传 PDF / Markdown / TXT，自动同步到 Dify 知识库（需在 <code>.env</code> 配置 <code>DIFY_DATASET_ID</code>）。
    </p>

    <div class="upload-bar">
      <input type="file" ref="fileInput" accept=".md,.txt,.pdf" @change="upload" style="display:none" />
      <button class="btn" @click="fileInput.click()" :disabled="uploading">
        {{ uploading ? '上传中…' : '+ 上传文件' }}
      </button>
    </div>

    <div v-if="msg" :class="['notice', msgType]">{{ msg }}</div>

    <h3 style="margin:20px 0 8px;font-size:15px">已上传文件</h3>
    <table v-if="files.length">
      <thead>
        <tr><th>文件名</th><th>大小</th><th>上传时间</th></tr>
      </thead>
      <tbody>
        <tr v-for="f in files" :key="f.name">
          <td>{{ f.name }}</td>
          <td>{{ formatSize(f.size) }}</td>
          <td>{{ new Date(f.updated_at).toLocaleString() }}</td>
        </tr>
      </tbody>
    </table>
    <p v-else style="color:#999;font-size:13px">暂无已上传文件</p>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import api from '../api.js'

const files = ref([])
const msg = ref('')
const msgType = ref('info')
const uploading = ref(false)
const fileInput = ref(null)

async function loadList() {
  try { files.value = (await api.get('/admin/knowledge/list')).data } catch {}
}

async function upload(e) {
  const f = e.target.files[0]; if (!f) return
  uploading.value = true; msg.value = ''; msgType.value = 'info'
  const fd = new FormData(); fd.append('file', f)
  try {
    const r = (await api.post('/admin/knowledge/upload', fd)).data
    if (r.synced) {
      msg.value = `✅ 「${r.saved_as}」已上传并同步到 Dify（文档 ID：${r.document_id}）`
      msgType.value = 'success'
    } else {
      msg.value = `⚠️ 「${r.saved_as}」已保存，Dify 同步失败：${r.error || '未知原因'}`
      msgType.value = 'warn'
    }
    await loadList()
  } catch (e) {
    msg.value = '❌ 上传失败：' + (e.response?.data?.detail || e.message)
    msgType.value = 'error'
  } finally {
    uploading.value = false
    if (fileInput.value) fileInput.value.value = ''
  }
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}

onMounted(loadList)
</script>

<style scoped>
.upload-bar { margin-bottom: 12px; }
.notice { padding: 10px 14px; border-radius: 6px; font-size: 13px; margin: 8px 0 4px; }
.notice.success { background: #e6f9ed; color: #1a7a3c; }
.notice.warn    { background: #fff8e1; color: #856404; }
.notice.error   { background: #fdecea; color: #b71c1c; }
.notice.info    { background: #e0f0ff; color: #1d6fa4; }
</style>

