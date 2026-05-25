<template>
  <div>
    <div class="page-header">
      <h2>数据概览</h2>
      <div class="toolbar">
        <select v-model="days" @change="load" class="days-sel">
          <option :value="7">近7天</option>
          <option :value="30">近30天</option>
          <option :value="90">近90天</option>
        </select>
        <span class="refresh-time">{{ refreshTime }}</span>
        <button class="btn-refresh" @click="load">刷新</button>
      </div>
    </div>

    <!-- KPI 卡片 -->
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-val">{{ ov.today_sessions }}</div>
        <div class="kpi-lbl">今日服务人次</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-val">{{ ov.today_messages }}</div>
        <div class="kpi-lbl">今日对话条数</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-val">{{ ov.week_sessions }}</div>
        <div class="kpi-lbl">近{{ days }}天累计</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-val">{{ (ov.satisfaction * 100).toFixed(1) }}<small>%</small></div>
        <div class="kpi-lbl">满意度</div>
      </div>
      <div class="kpi-card" :class="{ 'kpi-alert': ov.today_neg_rate > 0.2 }">
        <div class="kpi-val">{{ (ov.today_neg_rate * 100).toFixed(1) }}<small>%</small></div>
        <div class="kpi-lbl">今日负面率</div>
        <div class="kpi-badge" v-if="ov.today_neg_rate > 0.2">⚠ 偏高</div>
      </div>
    </div>

    <!-- 图表区：2列 -->
    <div class="chart-grid">
      <div class="chart-card">
        <div class="chart-title">分时客流分布</div>
        <div ref="hourlyEl" class="chart-box"></div>
      </div>
      <div class="chart-card">
        <div class="chart-title">情感趋势</div>
        <div ref="trendEl" class="chart-box"></div>
      </div>
      <div class="chart-card">
        <div class="chart-title">问题分类占比</div>
        <div ref="catEl" class="chart-box"></div>
      </div>
      <div class="chart-card">
        <div class="chart-title">数字人选择偏好</div>
        <div ref="avatarEl" class="chart-box"></div>
      </div>
      <div class="chart-card">
        <div class="chart-title">热门问答 Top10</div>
        <div ref="hotEl" class="chart-box"></div>
      </div>
      <div class="chart-card">
        <div class="chart-title">景点热度</div>
        <div ref="spotEl" class="chart-box"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import * as echarts from 'echarts'
import api from '../api.js'

const days = ref(7)
const refreshTime = ref('')
const ov = ref({ today_sessions: 0, today_messages: 0, week_sessions: 0, satisfaction: 0, today_neg_rate: 0 })

const hourlyEl = ref(), trendEl = ref(), catEl = ref(), avatarEl = ref(), hotEl = ref(), spotEl = ref()
let charts = {}, timer

async function load() {
  refreshTime.value = new Date().toLocaleString()
  const d = days.value
  const [o, hourly, t, cat, av, h, sp] = await Promise.all([
    api.get('/analytics/overview', { params: { days: d } }),
    api.get('/analytics/hourly-traffic', { params: { days: d } }),
    api.get('/analytics/sentiment-trend', { params: { days: d } }),
    api.get('/analytics/question-categories', { params: { days: d } }),
    api.get('/analytics/avatar-preference', { params: { days: d } }),
    api.get('/analytics/hot-questions', { params: { limit: 10 } }),
    api.get('/analytics/spot-heatmap'),
  ])
  ov.value = o.data

  // 分时客流
  charts.hourly.setOption({
    tooltip: { trigger: 'axis', formatter: p => `${p[0].name}时  访客: ${p[0].value}` },
    grid: { left: 40, right: 16, top: 16, bottom: 24 },
    xAxis: { type: 'category', data: hourly.data.map(x => x.hour), axisLabel: { fontSize: 11, formatter: v => v + '时' } },
    yAxis: { type: 'value', axisLabel: { fontSize: 11 } },
    series: [{
      type: 'line', smooth: true,
      areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(24,144,255,0.35)' }, { offset: 1, color: 'rgba(24,144,255,0)' }] } },
      lineStyle: { color: '#1890ff' }, itemStyle: { color: '#1890ff' },
      data: hourly.data.map(x => x.count)
    }]
  })

  // 情感趋势
  charts.trend.setOption({
    legend: { bottom: 0, itemWidth: 12, textStyle: { fontSize: 11 } },
    tooltip: { trigger: 'axis' },
    grid: { left: 36, right: 16, top: 16, bottom: 40 },
    xAxis: { type: 'category', data: t.data.map(p => p.date), axisLabel: { fontSize: 10, rotate: 30 } },
    yAxis: { type: 'value', axisLabel: { fontSize: 11 } },
    series: [
      { name: '正向', type: 'line', smooth: true, color: '#52c41a', data: t.data.map(p => p.pos) },
      { name: '中性', type: 'line', smooth: true, color: '#8c8c8c', data: t.data.map(p => p.neu) },
      { name: '负向', type: 'line', smooth: true, color: '#ff4d4f', data: t.data.map(p => p.neg) },
    ]
  })

  // 问题分类
  charts.cat.setOption({
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie', radius: ['38%', '65%'], center: ['50%', '50%'],
      label: { fontSize: 11 },
      data: cat.data.length
        ? cat.data.map(x => ({ value: x.count, name: x.label }))
        : [{ value: 1, name: '暂无数据', itemStyle: { color: '#f0f0f0' } }]
    }]
  })

  // 数字人偏好
  const avRows = av.data.slice().reverse()
  charts.avatar.setOption({
    tooltip: {},
    grid: { left: 80, right: 20, top: 10, bottom: 20 },
    xAxis: { type: 'value', axisLabel: { fontSize: 11 } },
    yAxis: { type: 'category', data: avRows.map(x => x.name), axisLabel: { fontSize: 11 } },
    series: [{ type: 'bar', data: avRows.map(x => x.count), itemStyle: { color: '#722ed1' }, barMaxWidth: 24 }]
  })

  // 热门问答
  const hot = h.data.slice().reverse()
  charts.hot.setOption({
    tooltip: {},
    grid: { left: 180, right: 20, top: 8, bottom: 20 },
    xAxis: { type: 'value', axisLabel: { fontSize: 11 } },
    yAxis: { type: 'category', data: hot.map(x => x.question.length > 18 ? x.question.slice(0, 18) + '…' : x.question), axisLabel: { fontSize: 11 } },
    series: [{ type: 'bar', data: hot.map(x => x.count), itemStyle: { color: '#1890ff' }, barMaxWidth: 20 }]
  })

  // 景点热度
  charts.spot.setOption({
    tooltip: {},
    grid: { left: 40, right: 16, top: 16, bottom: 60 },
    xAxis: { type: 'category', data: sp.data.slice(0, 8).map(x => x.name), axisLabel: { fontSize: 11, rotate: 30 } },
    yAxis: { type: 'value', axisLabel: { fontSize: 11 } },
    series: [{ type: 'bar', data: sp.data.slice(0, 8).map(x => x.count), itemStyle: { color: '#fa8c16' }, barMaxWidth: 36 }]
  })
}

function resize() { Object.values(charts).forEach(c => c?.resize()) }

onMounted(() => {
  charts.hourly = echarts.init(hourlyEl.value)
  charts.trend  = echarts.init(trendEl.value)
  charts.cat    = echarts.init(catEl.value)
  charts.avatar = echarts.init(avatarEl.value)
  charts.hot    = echarts.init(hotEl.value)
  charts.spot   = echarts.init(spotEl.value)
  load()
  timer = setInterval(load, 30000)
  window.addEventListener('resize', resize)
})

onUnmounted(() => { clearInterval(timer); window.removeEventListener('resize', resize) })
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h2 { margin: 0; font-size: 20px; }
.toolbar { display: flex; align-items: center; gap: 12px; }
.days-sel { border: 1px solid #d9d9d9; border-radius: 4px; padding: 4px 10px; font-size: 13px; cursor: pointer; }
.refresh-time { font-size: 12px; color: #8c8c8c; }
.btn-refresh { border: 1px solid #1890ff; background: #fff; color: #1890ff; padding: 4px 14px; border-radius: 4px; cursor: pointer; font-size: 13px; }
.btn-refresh:hover { background: #1890ff; color: #fff; }

.kpi-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 16px; margin-bottom: 24px; }
.kpi-card { background: #fff; border: 1px solid #f0f0f0; border-radius: 8px; padding: 20px 16px; text-align: center; position: relative; box-shadow: 0 1px 4px rgba(0,0,0,.06); }
.kpi-card.kpi-alert { border-color: #ffccc7; background: #fff2f0; }
.kpi-val { font-size: 32px; font-weight: 700; color: #1890ff; line-height: 1; }
.kpi-val small { font-size: 14px; color: #8c8c8c; margin-left: 2px; }
.kpi-lbl { margin-top: 8px; font-size: 13px; color: #595959; }
.kpi-badge { position: absolute; top: 8px; right: 8px; background: #ff4d4f; color: #fff; font-size: 11px; padding: 2px 6px; border-radius: 10px; }
.kpi-card.kpi-alert .kpi-val { color: #ff4d4f; }

.chart-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.chart-card { background: #fff; border: 1px solid #f0f0f0; border-radius: 8px; padding: 16px; box-shadow: 0 1px 4px rgba(0,0,0,.06); }
.chart-title { font-size: 14px; font-weight: 500; color: #262626; margin-bottom: 8px; }
.chart-box { height: 240px; }
</style>
