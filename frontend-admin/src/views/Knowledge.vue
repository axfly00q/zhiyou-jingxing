<template>
  <div>
    <h2>知识库管理</h2>
    <p style="color:#666">上传 PDF / Markdown / TXT，文件保存到 orchestrator 后由部署手册中的脚本入 Dify。</p>
    <input type="file" @change="upload" />
    <p v-if="msg" style="color:#2c7be5">{{ msg }}</p>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import api from '../api.js'
const msg = ref('')
async function upload(e) {
  const f = e.target.files[0]; if (!f) return
  const fd = new FormData(); fd.append('file', f)
  const r = await api.post('/admin/knowledge/upload', fd)
  msg.value = `上传成功：${r.data.saved_as}`
}
</script>
