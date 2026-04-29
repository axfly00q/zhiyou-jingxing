<template>
  <div>
    <h2>数字人形象管理</h2>
    <p style="color:#666;font-size:13px;margin:6px 0 14px">
      数字人采用 VRM 浏览器渲染方案，可上传 <code>.vrm</code> 模型文件与 <code>.vrma</code> 动作文件。
    </p>
    <button class="btn" @click="show=true">+ 新增形象</button>

    <table style="margin-top:16px">
      <thead>
        <tr>
          <th>编号</th><th>名称</th><th>音色</th><th>默认</th>
          <th>VRM 模型</th><th>描述</th><th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="a in list" :key="a.id">
          <td>{{ a.code }}</td>
          <td>{{ a.name }}</td>
          <td>{{ a.voice_id }}</td>
          <td>{{ a.is_default ? '✅' : '' }}</td>
          <td>
            <span v-if="a.model_url" style="color:#28a745">已上传</span>
            <span v-else style="color:#dc3545">未上传</span>
          </td>
          <td>{{ a.description }}</td>
          <td>
            <input :ref="el => fileRefs[a.code] = el" type="file" accept=".vrm"
                   style="display:none" @change="onPickVrm($event, a)" />
            <button class="btn" @click="pickVrm(a)" style="margin-right:6px">
              {{ uploading === a.code ? '上传中…' : '上传 VRM' }}
            </button>
            <input :ref="el => motionRefs[a.code] = el" type="file" accept=".vrma"
                   style="display:none" @change="onPickMotion($event, a)" />
            <button class="btn" @click="pickMotion(a)" style="margin-right:6px;background:#6c757d">
              动作
            </button>
            <button class="btn danger" @click="del(a)">删除</button>
          </td>
        </tr>
        <tr v-if="!list.length"><td colspan="7" style="text-align:center;color:#999">暂无数据</td></tr>
      </tbody>
    </table>

    <div v-if="show" class="modal">
      <div class="modal-box">
        <h3>新增形象</h3>
        <div class="row"><label>编号(code)</label><input v-model="form.code" placeholder="英文+下划线，如 guzhuang_female_01" /></div>
        <div class="row"><label>名称</label><input v-model="form.name" /></div>
        <div class="row"><label>音色 ID</label><input v-model="form.voice_id" /></div>
        <div class="row"><label>预览图 URL</label><input v-model="form.preview_url" /></div>
        <div class="row">
          <label>默认动作</label>
          <select v-model="form.default_motion">
            <option value="idle">idle（待机）</option>
            <option value="wave">wave（招手）</option>
            <option value="explain">explain（讲解）</option>
            <option value="think">think（思考）</option>
          </select>
        </div>
        <div class="row"><label>描述</label><textarea v-model="form.description"></textarea></div>
        <div class="row"><label>设为默认</label><input type="checkbox" v-model="form.is_default" /></div>
        <p style="color:#888;font-size:12px;margin-top:6px">
          ✱ 创建后请在列表里点击「上传 VRM」上传模型文件。
        </p>
        <div style="text-align:right;margin-top:12px">
          <button class="btn" @click="show=false" style="background:#999;margin-right:8px">取消</button>
          <button class="btn" @click="save">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import api from '../api.js'

const list = ref([])
const show = ref(false)
const uploading = ref('')
const fileRefs = reactive({})
const motionRefs = reactive({})

const _empty = () => ({
  code: '', name: '', voice_id: '', preview_url: '', description: '',
  is_default: false, model_type: 'vrm', default_motion: 'idle',
})
const form = reactive(_empty())

async function load() { list.value = (await api.get('/admin/avatars')).data }

async function save() {
  if (!form.code || !form.name || !form.voice_id) {
    alert('请填写编号、名称、音色 ID')
    return
  }
  await api.post('/admin/avatars', { ...form })
  show.value = false
  Object.assign(form, _empty())
  load()
}

async function del(a) {
  if (!confirm(`删除「${a.name}」？`)) return
  await api.delete(`/admin/avatars/${a.id}`)
  load()
}

function pickVrm(a) {
  const el = fileRefs[a.code]
  if (el) el.click()
}

async function onPickVrm(ev, a) {
  const file = ev.target.files && ev.target.files[0]
  if (!file) return
  if (file.size > 50 * 1024 * 1024) { alert('文件不能超过 50MB'); ev.target.value = ''; return }
  const fd = new FormData()
  fd.append('file', file, file.name)
  uploading.value = a.code
  try {
    const r = await api.post(`/admin/avatars/${a.code}/upload-vrm`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000,
    })
    alert(`上传成功，URL: ${r.data.model_url}`)
    load()
  } catch (e) {
    alert('上传失败：' + (e.response?.data?.detail || e.message))
  } finally {
    uploading.value = ''
    ev.target.value = ''
  }
}

function pickMotion(a) {
  const el = motionRefs[a.code]
  if (el) el.click()
}

async function onPickMotion(ev, a) {
  const file = ev.target.files && ev.target.files[0]
  if (!file) return
  const name = prompt('动作名称（仅小写字母/数字/下划线，如 idle / wave / explain / think）',
                      'idle')
  if (!name) { ev.target.value = ''; return }
  const fd = new FormData()
  fd.append('file', file, file.name)
  try {
    const r = await api.post(
      `/admin/avatars/${a.code}/upload-motion?name=${encodeURIComponent(name)}`,
      fd, { headers: { 'Content-Type': 'multipart/form-data' }, timeout: 120000 })
    alert(`动作 ${name} 上传成功`)
  } catch (e) {
    alert('上传失败：' + (e.response?.data?.detail || e.message))
  } finally {
    ev.target.value = ''
  }
}

onMounted(load)
</script>

<style scoped>
.modal { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; }
.modal-box { background: #fff; border-radius: 8px; padding: 24px; width: 520px; }
.row { display: grid; grid-template-columns: 110px 1fr; gap: 10px; margin: 10px 0; align-items: center; }
.row input, .row textarea, .row select { width: 100%; }
</style>
