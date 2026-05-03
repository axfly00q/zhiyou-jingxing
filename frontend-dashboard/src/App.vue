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
      </div>
    </header>
    <div class="grid">
      <!-- KPI -->
      <div class="card kpi">
        <h3>核心指标</h3>
        <div class="kpi-row">
          <div><div class="num">{{ overview.today_sessions }}</div><div class="lbl">今日服务人次</div></div>
          <div><div class="num">{{ overview.today_messages }}</div><div class="lbl">今日对话条数</div></div>
          <div><div class="num">{{ overview.week_sessions }}</div><div class="lbl">本周累计</div></div>
          <div><div class="num">{{ Math.round(overview.avg_latency_ms) }}<small>ms</small></div><div class="lbl">平均响应</div></div>
          <div><div class="num">{{ (overview.satisfaction*100).toFixed(1) }}<small>%</small></div><div class="lbl">满意度</div></div>
        </div>
      </div>
      <!-- 情感趋势 -->
      <div class="card"><h3>情感趋势（近7天）</h3><div ref="trendEl" class="chart"></div></div>
      <!-- 情感分布 -->
      <div class="card"><h3>情感分布</h3><div ref="pieEl" class="chart"></div></div>
      <!-- 热门问答 -->
      <div class="card"><h3>热门问答 Top10</h3><div ref="hotEl" class="chart"></div></div>
      <!-- 热门景点 -->
      <div class="card"><h3>景点热度</h3><div ref="spotEl" class="chart"></div></div>
      <!-- 实时建议流 -->
      <div class="card scroll">
        <h3>最新服务建议</h3>
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

const overview = ref({ today_sessions: 0, today_messages: 0, week_sessions: 0, avg_latency_ms: 0, satisfaction: 0 })
const suggestions = ref([])
const now = ref('')
const selectedDays = ref(7)

const trendEl = ref(), pieEl = ref(), hotEl = ref(), spotEl = ref()
let charts = {}, timer

const dark = { textStyle: { color: '#cbd5e1' } }

async function refresh() {
  now.value = new Date().toLocaleString()
  const [o, t, h, sp, sg] = await Promise.all([
    axios.get('/api/analytics/overview', { params: { days: selectedDays.value } }),
    axios.get('/api/analytics/sentiment-trend', { params: { days: selectedDays.value } }),
    axios.get('/api/analytics/hot-questions', { params: { limit: 10 } }),
    axios.get('/api/analytics/spot-heatmap'),
    axios.get('/api/analytics/suggestions')
  ])
  overview.value = o.data
  suggestions.value = sg.data.slice(0, 6)

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

  const total = t.data.reduce((a, p) => ({
    pos: a.pos + p.pos, neu: a.neu + p.neu, neg: a.neg + p.neg
  }), { pos: 0, neu: 0, neg: 0 })
  charts.pie.setOption({
    ...dark,
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie', radius: ['40%', '70%'],
      label: { color: '#cbd5e1' },
      data: [
        { value: total.pos, name: '正向', itemStyle: { color: '#22c55e' } },
        { value: total.neu, name: '中性', itemStyle: { color: '#94a3b8' } },
        { value: total.neg, name: '负向', itemStyle: { color: '#ef4444' } }
      ]
    }]
  })

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
  charts.trend = echarts.init(trendEl.value, 'dark')
  charts.pie = echarts.init(pieEl.value, 'dark')
  charts.hot = echarts.init(hotEl.value, 'dark')
  charts.spot = echarts.init(spotEl.value, 'dark')
  refresh()
  timer = setInterval(refresh, 15000)
  window.addEventListener('resize', resize)
})

function resize() { Object.values(charts).forEach(c => c?.resize()) }

onUnmounted(() => { clearInterval(timer); window.removeEventListener('resize', resize) })
</script>

<style scoped>
.dash { height: 100vh; padding: 16px; display: flex; flex-direction: column; }
header { display: flex; justify-content: space-between; align-items: center; padding: 0 16px 12px; border-bottom: 1px solid #1f2a44; }
.header-right { display: flex; align-items: center; gap: 16px; }
.days-select { background: #1e293b; color: #cbd5e1; border: 1px solid #334155; border-radius: 6px; padding: 4px 10px; font-size: 13px; cursor: pointer; }
header h1 { margin: 0; font-size: 24px; background: linear-gradient(90deg, #38bdf8, #c084fc); -webkit-background-clip: text; color: transparent; }
.time { color: #64748b; }
.grid {
  flex: 1; display: grid;
  grid-template-columns: 2fr 1fr 1fr;
  grid-template-rows: 1fr 1fr 1fr;
  gap: 12px; margin-top: 12px;
}
.grid .card:nth-child(1) { grid-column: span 3; grid-row: span 1; }
.grid .card:nth-child(2) { grid-column: span 2; }
.grid .card:nth-child(6) { grid-row: span 1; }
.card { background: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 16px; display: flex; flex-direction: column; }
.card h3 { margin: 0 0 12px; font-size: 14px; color: #94a3b8; font-weight: 500; letter-spacing: 1px; }
.chart { flex: 1; min-height: 0; }
.kpi-row { display: grid; grid-template-columns: repeat(5, 1fr); gap: 16px; flex: 1; align-items: center; }
.kpi-row .num { font-size: 36px; color: #38bdf8; font-weight: 700; }
.kpi-row .num small { font-size: 16px; color: #94a3b8; margin-left: 4px; }
.kpi-row .lbl { color: #94a3b8; font-size: 13px; }
.scroll ul { list-style: none; padding: 0; margin: 0; overflow-y: auto; flex: 1; }
.scroll li { padding: 10px 0; border-bottom: 1px dashed #1e293b; }
.scroll li p { margin: 4px 0 0; font-size: 12px; color: #94a3b8; }
.dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; vertical-align: middle; }
.dot.high { background: #ef4444; } .dot.medium { background: #f59e0b; } .dot.low { background: #22c55e; }
</style>
