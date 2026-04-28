<template>
  <div>
    <h2>数字人形象管理</h2>
    <button class="btn" @click="show=true">+ 新增形象</button>

    <table style="margin-top:16px">
      <thead><tr><th>编号</th><th>名称</th><th>音色</th><th>默认</th><th>描述</th><th>操作</th></tr></thead>
      <tbody>
        <tr v-for="a in list" :key="a.id">
          <td>{{ a.code }}</td><td>{{ a.name }}</td><td>{{ a.voice_id }}</td>
          <td>{{ a.is_default ? '✅' : '' }}</td><td>{{ a.description }}</td>
          <td><button class="btn danger" @click="del(a)">删除</button></td>
        </tr>
        <tr v-if="!list.length"><td colspan="6" style="text-align:center;color:#999">暂无数据</td></tr>
      </tbody>
    </table>

    <div v-if="show" class="modal">
      <div class="modal-box">
        <h3>新增形象</h3>
        <div class="row"><label>编号(code)</label><input v-model="form.code" /></div>
        <div class="row"><label>名称</label><input v-model="form.name" /></div>
        <div class="row"><label>音色 ID</label><input v-model="form.voice_id" /></div>
        <div class="row"><label>预览图 URL</label><input v-model="form.preview_url" /></div>
        <div class="row"><label>描述</label><textarea v-model="form.description"></textarea></div>
        <div class="row"><label>设为默认</label><input type="checkbox" v-model="form.is_default" /></div>
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
const form = reactive({ code: '', name: '', voice_id: '', preview_url: '', description: '', is_default: false })

async function load() { list.value = (await api.get('/admin/avatars')).data }
async function save() {
  await api.post('/admin/avatars', { ...form })
  show.value = false
  Object.assign(form, { code: '', name: '', voice_id: '', preview_url: '', description: '', is_default: false })
  load()
}
async function del(a) {
  if (!confirm(`删除「${a.name}」？`)) return
  await api.delete(`/admin/avatars/${a.id}`)
  load()
}
onMounted(load)
</script>

<style scoped>
.modal { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; }
.modal-box { background: #fff; border-radius: 8px; padding: 24px; width: 500px; }
.row { display: grid; grid-template-columns: 110px 1fr; gap: 10px; margin: 10px 0; align-items: center; }
.row input, .row textarea { width: 100%; }
</style>
