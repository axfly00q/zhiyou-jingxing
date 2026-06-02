<template>
  <div>
    <h2>知识库管理</h2>
    <p style="color:#666;font-size:13px;margin:6px 0 14px">
      上传文件并选择分类，将自动同步到对应的 Dify 知识库。需在 <code>.env</code> 配置对应的
      <code>DIFY_DATASET_ID_*</code> 变量。
    </p>

    <div class="upload-bar">
      <select v-model="selectedCategory" class="cat-select">
        <option v-for="c in categories" :key="c.value" :value="c.value">{{ c.label }}</option>
      </select>
      <input type="file" ref="fileInput" accept=".md,.txt,.pdf,.docx,.doc" @change="upload" style="display:none" />
      <button class="btn" @click="fileInput.click()" :disabled="uploading">
        {{ uploading ? '上传中…' : '+ 上传文件' }}
      </button>
    </div>

    <div v-if="msg" :class="['notice', msgType]">{{ msg }}</div>

    <h3 style="margin:20px 0 8px;font-size:15px">已上传文件</h3>

    <!-- 按分类分组展示 -->
    <div v-for="cat in categories" :key="cat.value" class="cat-section">
      <template v-if="filesByCategory[cat.value]?.length">
        <div class="cat-header">
          <span class="cat-badge" :class="cat.value">{{ cat.label }}</span>
          <span class="cat-count">{{ filesByCategory[cat.value].length }} 个文件</span>
        </div>
        <table>
          <thead><tr><th>文件名</th><th>大小</th><th>上传时间</th></tr></thead>
          <tbody>
            <tr v-for="f in filesByCategory[cat.value]" :key="f.name + f.category">
              <td>{{ f.name }}</td>
              <td>{{ formatSize(f.size) }}</td>
              <td>{{ new Date(f.updated_at).toLocaleString() }}</td>
            </tr>
          </tbody>
        </table>
      </template>
    </div>

    <p v-if="!files.length" style="color:#999;font-size:13px">暂无已上传文件</p>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '../api.js'

const categories = [
  { value: 'tour_guide',     label: '旅游攻略' },
  { value: 'culture',        label: '苏州文化' },
  { value: 'international',  label: '外籍服务' },
  { value: 'nearby',         label: '周边景点' },
  { value: 'general',        label: '通用' },
]

const files = ref([])
const msg = ref('')
const msgType = ref('info')
const uploading = ref(false)
const fileInput = ref(null)
const selectedCategory = ref('tour_guide')

const filesByCategory = computed(() => {
  const map = {}
  for (const cat of categories) map[cat.value] = []
  for (const f of files.value) {
    const key = f.category || 'general'
    if (!map[key]) map[key] = []
    map[key].push(f)
  }
  return map
})

async function loadList() {
  try { files.value = (await api.get('/admin/knowledge/list')).data } catch {}
}

async function upload(e) {
  const f = e.target.files[0]; if (!f) return
  uploading.value = true; msg.value = ''; msgType.value = 'info'
  const fd = new FormData()
  fd.append('file', f)
  fd.append('category', selectedCategory.value)
  try {
    const r = (await api.post('/admin/knowledge/upload', fd)).data
    const catLabel = categories.find(c => c.value === r.category)?.label || r.category
    if (r.synced) {
      msg.value = `✅ 「${r.saved_as}」已上传到「${catLabel}」并同步到 Dify（ID：${r.document_id}）`
      msgType.value = 'success'
    } else {
      msg.value = `⚠️ 「${r.saved_as}」已保存到「${catLabel}」，Dify 同步失败：${r.error || '未配置'}`
      msgType.value = 'warn'
    }
    await loadList()
  } catch (ex) {
    msg.value = '❌ 上传失败：' + (ex.response?.data?.detail || ex.message)
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
.upload-bar { display:flex; gap:10px; align-items:center; margin-bottom:12px; flex-wrap:wrap; }
.cat-select { padding:6px 10px; border:1px solid #ddd; border-radius:6px; font-size:13px; }
.notice { padding:10px 14px; border-radius:6px; font-size:13px; margin:8px 0 4px; }
.notice.success { background:#e6f9ed; color:#1a7a3c; }
.notice.warn    { background:#fff8e1; color:#856404; }
.notice.error   { background:#fdecea; color:#b71c1c; }
.notice.info    { background:#e0f0ff; color:#1d6fa4; }
.cat-section { margin-bottom:18px; }
.cat-header { display:flex; align-items:center; gap:8px; margin:10px 0 6px; }
.cat-count { font-size:12px; color:#888; }
.cat-badge { display:inline-block; padding:2px 10px; border-radius:12px; font-size:12px; font-weight:600; }
.cat-badge.tour_guide    { background:#dbeafe; color:#1d4ed8; }
.cat-badge.culture       { background:#fce7f3; color:#9d174d; }
.cat-badge.international { background:#dcfce7; color:#166534; }
.cat-badge.nearby        { background:#fef9c3; color:#854d0e; }
.cat-badge.general       { background:#f3f4f6; color:#374151; }
table { width:100%; border-collapse:collapse; font-size:13px; }
th,td { border:1px solid #eee; padding:7px 10px; text-align:left; }
th { background:#f7f8fa; color:#555; }
</style>

