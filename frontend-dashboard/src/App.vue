<template>
  <div class="dash">
    <header>
      <h1>智游景行 · 苏州园林导览数据大屏</h1>
      <div class="header-right">
        <select v-model="selectedDays" @change="refresh" class="days-select">
          <option :value="7">近7天</option>
          <option :value="30">近30天</option>
          <option :value="90">近90天</option>
        </select>
        <span class="time">{{ now }}</span>
        <button class="fs-btn" @click="toggleFullscreen" :title="isFullscreen ? '退出全屏' : '全屏展示'">{{ isFullscreen ? '⊠' : '⛶' }}</button>
      </div>
    </header>
    <div class="grid">
      <!-- 1. KPI -->
      <div class="card kpi">
        <h3>核心指标</h3>
        <div class="kpi-row">
          <div><div class="num">{{ overview.today_sessions }}</div><div class="lbl">今日服务人次</div></div>
          <div><div class="num">{{ overview.today_messages }}</div><div class="lbl">今日对话条数</div></div>
          <div><div class="num">{{ overview.week_sessions }}</div><div class="lbl">本周累计</div></div>
          <div><div class="num">{{ (overview.satisfaction*100).toFixed(1) }}<small>%</small></div><div class="lbl">满意度</div></div>
          <div>
            <div class="num" :class="{ 'neg-high': overview.today_neg_rate > 0.2 }">
              {{ (overview.today_neg_rate*100).toFixed(1) }}<small>%</small>
            </div>
            <div class="lbl">今日负面率</div>
          </div>
        </div>
      </div>
      <!-- 2. 分时客流 -->
      <div class="card"><h3>分时客流分布（近{{ selectedDays }}天均值）</h3><div ref="hourlyEl" class="chart"></div></div>
      <!-- 3. 数字人偏好 -->
      <div class="card"><h3>数字人选择偏好</h3><div ref="avatarEl" class="chart"></div></div>
      <!-- 4. 情感趋势 -->
      <div class="card"><h3>情感趋势（近{{ selectedDays }}天）</h3><div ref="trendEl" class="chart"></div></div>
      <!-- 5. 问题分类 -->
      <div class="card"><h3>问题分类占比</h3><div ref="catEl" class="chart"></div></div>
      <!-- 6. 热门问答 -->
      <div class="card"><h3>热门问答 Top10</h3><div ref="hotEl" class="chart"></div></div>
      <!-- 7. 景点热度 -->
      <div class="card"><h3>景点热度</h3><div ref="spotEl" class="chart"></div></div>
      <!-- 8. 最新服务建议 -->
      <div class="card scroll">
        <h3>最新服务建议</h3>
        <div class="neg-alert" v-if="overview.today_neg_rate > 0.2">
          ⚠ 今日负面率偏高（{{ (overview.today_neg_rate*100).toFixed(0) }}%），建议及时关注游客体验
        </div>
        <ul>
          <li v-for="s in suggestions" :key="s.id">
            <span :class="['dot', s.priority]"></span>
            <strong>{{ s.title }}</strong>
            <p>{{ s.summary }}</p>
          </li>
          <li v-if="!suggestions.length" style="color:#888">暂无建议</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import axios from 'axios'
import * as echarts from 'echarts'

const overview = ref({ today_sessions: 0, today_messages: 0, week_sessions: 0, avg_latency_ms: 0, satisfaction: 0, today_neg_rate: 0 })
const suggestions = ref([])
const now = ref('')
const selectedDays = ref(7)

const trendEl = ref(), hotEl = ref(), spotEl = ref()
const hourlyEl = ref(), avatarEl = ref(), catEl = ref()
const isFullscreen = ref(false)
let charts = {}, timer

function toggleFullscreen() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen().catch(() => {})
    isFullscreen.value = true
  } else {
    document.exitFullscreen()
    isFullscreen.value = false
  }
}

const dark = { textStyle: { color: '#cbd5e1' } }

async function refresh() {
  now.value = new Date().toLocaleString()
  const [o, t, h, sp, sg, hourly, cat, avatar] = await Promise.all([
    axios.get('/api/analytics/overview', { params: { days: selectedDays.value } }),
    axios.get('/api/analytics/sentiment-trend', { params: { days: selectedDays.value } }),
    axios.get('/api/analytics/hot-questions', { params: { limit: 10 } }),
    axios.get('/api/analytics/spot-heatmap'),
    axios.get('/api/analytics/suggestions'),
    axios.get('/api/analytics/hourly-traffic', { params: { days: selectedDays.value } }),
    axios.get('/api/analytics/question-categories', { params: { days: selectedDays.value } }),
    axios.get('/api/analytics/avatar-preference', { params: { days: selectedDays.value } }),
  ])
  overview.value = o.data
  suggestions.value = sg.data.slice(0, 6)

  // 分时客流
  charts.hourly.setOption({
    ...dark,
    tooltip: { trigger: 'axis', formatter: p => `${p[0].name}时<br/>访客消息: ${p[0].value}` },
    xAxis: { type: 'category', data: hourly.data.map(x => x.hour), axisLabel: { color: '#94a3b8', formatter: v => v + '时' } },
    yAxis: { type: 'value', axisLabel: { color: '#94a3b8' } },
    series: [{
      type: 'line', smooth: true,
      areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(56,189,248,0.45)' }, { offset: 1, color: 'rgba(56,189,248,0)' }] } },
      lineStyle: { color: '#38bdf8' }, itemStyle: { color: '#38bdf8' },
      data: hourly.data.map(x => x.count)
    }]
  })

  // 数字人偏好
  const avRows = avatar.data.slice().reverse()
  charts.avatar.setOption({
    ...dark,
    tooltip: {},
    grid: { left: 80, right: 20, top: 10, bottom: 20 },
    xAxis: { type: 'value', axisLabel: { color: '#94a3b8' } },
    yAxis: { type: 'category', data: avRows.map(x => x.name), axisLabel: { color: '#cbd5e1' } },
    series: [{ type: 'bar', data: avRows.map(x => x.count), itemStyle: { color: '#c084fc' } }]
  })

  // 情感趋势
  charts.trend.setOption({
    ...dark,
    legend: { textStyle: { color: '#cbd5e1' } },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: t.data.map(p => p.date), axisLabel: { color: '#94a3b8' } },
    yAxis: { type: 'value', axisLabel: { color: '#94a3b8' } },
    series: [
      { name: '正向', type: 'line', smooth: true, color: '#22c55e', data: t.data.map(p => p.pos) },
      { name: '中性', type: 'line', smooth: true, color: '#94a3b8', data: t.data.map(p => p.neu) },
      { name: '负向', type: 'line', smooth: true, color: '#ef4444', data: t.data.map(p => p.neg) }
    ]
  })

  // 问题分类
  charts.cat.setOption({
    ...dark,
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie', radius: ['38%', '68%'],
      label: { color: '#cbd5e1', fontSize: 11 },
      data: cat.data.length
        ? cat.data.map(x => ({ value: x.count, name: x.label }))
        : [{ value: 1, name: '暂无数据', itemStyle: { color: '#1e293b' } }]
    }]
  })

  // 热门问答
  const hot = h.data.slice().reverse()
  charts.hot.setOption({
    ...dark,
    grid: { left: 180, right: 20, top: 10, bottom: 20 },
    tooltip: {},
    xAxis: { type: 'value', axisLabel: { color: '#94a3b8' } },
    yAxis: {
      type: 'category', data: hot.map(x => x.question.length > 18 ? x.question.slice(0, 18) + '…' : x.question),
      axisLabel: { color: '#cbd5e1' }
    },
    series: [{ type: 'bar', data: hot.map(x => x.count), itemStyle: { color: '#2c7be5' } }]
  })

  // 景点热度
  charts.spot.setOption({
    ...dark,
    tooltip: {},
    xAxis: { type: 'category', data: sp.data.slice(0, 8).map(x => x.name), axisLabel: { color: '#cbd5e1', rotate: 30 } },
    yAxis: { type: 'value', axisLabel: { color: '#94a3b8' } },
    series: [{
      type: 'bar', data: sp.data.slice(0, 8).map(x => x.count),
      itemStyle: {
        color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
                 colorStops: [{ offset: 0, color: '#f59e0b' }, { offset: 1, color: '#dc2626' }] }
      }
    }]
  })
}

onMounted(() => {
  charts.hourly = echarts.init(hourlyEl.value, 'dark')
  charts.avatar = echarts.init(avatarEl.value, 'dark')
  charts.trend  = echarts.init(trendEl.value, 'dark')
  charts.cat    = echarts.init(catEl.value, 'dark')
  charts.hot    = echarts.init(hotEl.value, 'dark')
  charts.spot   = echarts.init(spotEl.value, 'dark')
  refresh()
  timer = setInterval(refresh, 15000)
  window.addEventListener('resize', resize)
})

function resize() { Object.values(charts).forEach(c => c?.resize()) }

onUnmounted(() => { clearInterval(timer); window.removeEventListener('resize', resize) })
</script>

<style scoped>
.dash { min-height: 100vh; padding: 16px; display: flex; flex-direction: column; }
header { display: flex; justify-content: space-between; align-items: center; padding: 0 16px 12px; border-bottom: 1px solid #1f2a44; }
.header-right { display: flex; align-items: center; gap: 16px; }
.days-select { background: #1e293b; color: #cbd5e1; border: 1px solid #334155; border-radius: 6px; padding: 4px 10px; font-size: 13px; cursor: pointer; }
header h1 { margin: 0; font-size: 24px; background: linear-gradient(90deg, #38bdf8, #c084fc); -webkit-background-clip: text; color: transparent; }
.time { color: #64748b; }
.fs-btn { background: transparent; border: 1px solid #334155; color: #94a3b8; border-radius: 6px; padding: 4px 10px; font-size: 16px; cursor: pointer; line-height: 1; }
.fs-btn:hover { border-color: #38bdf8; color: #38bdf8; }
.grid {
  flex: 1; display: grid;
  grid-template-columns: 2fr 1fr 1fr;
  grid-template-rows: auto repeat(3, minmax(240px, 1fr));
  gap: 12px; margin-top: 12px;
}
.grid .card:nth-child(1) { grid-column: span 3; }
.grid .card:nth-child(2) { grid-column: span 2; }
.grid .card:nth-child(4) { grid-column: span 2; }
.grid .card:nth-child(6) { grid-column: span 2; }
.card { background: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 16px; display: flex; flex-direction: column; }
.card h3 { margin: 0 0 12px; font-size: 14px; color: #94a3b8; font-weight: 500; letter-spacing: 1px; }
.chart { flex: 1; min-height: 0; }
.kpi-row { display: grid; grid-template-columns: repeat(5, 1fr); gap: 16px; flex: 1; align-items: center; }
.kpi-row .num { font-size: 36px; color: #38bdf8; font-weight: 700; }
.kpi-row .num small { font-size: 16px; color: #94a3b8; margin-left: 4px; }
.kpi-row .num.neg-high { color: #ef4444; }
.kpi-row .lbl { color: #94a3b8; font-size: 13px; }
.neg-alert { background: rgba(239,68,68,0.15); border: 1px solid #ef4444; color: #fca5a5; border-radius: 6px; padding: 8px 12px; margin-bottom: 10px; font-size: 13px; }
.scroll ul { list-style: none; padding: 0; margin: 0; overflow-y: auto; flex: 1; }
.scroll li { padding: 10px 0; border-bottom: 1px dashed #1e293b; }
.scroll li p { margin: 4px 0 0; font-size: 12px; color: #94a3b8; }
.dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; vertical-align: middle; }
.dot.high { background: #ef4444; } .dot.medium { background: #f59e0b; } .dot.low { background: #22c55e; }
</style>

