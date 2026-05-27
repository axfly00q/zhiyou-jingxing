<template>
  <div class="dash">
    <header>
      <div class="header-left">
        <h1>智游景行 · 苏州园林游客服务大屏</h1>
        <span class="subtitle">实时数据 · 每 15 秒更新</span>
      </div>
      <div class="header-right">
        <span class="time">{{ now }}</span>
        <button class="fs-btn" @click="toggleFullscreen" :title="isFullscreen ? '退出全屏' : '全屏展示'">{{ isFullscreen ? '⊠' : '⛶' }}</button>
      </div>
    </header>

    <div class="grid">
      <!-- 1. KPI -->
      <div class="card kpi">
        <div class="kpi-row">
          <div class="kpi-item">
            <div class="kpi-icon">👥</div>
            <div class="num">{{ overview.today_sessions }}</div>
            <div class="lbl">今日导览人次</div>
          </div>
          <div class="kpi-item">
            <div class="kpi-icon">📅</div>
            <div class="num">{{ overview.week_sessions }}</div>
            <div class="lbl">近7天累计导览</div>
          </div>
          <div class="kpi-item">
            <div class="kpi-icon">🏆</div>
            <div class="num spot-name">{{ topSpotName }}</div>
            <div class="lbl">最受关注景点</div>
          </div>
          <div class="kpi-item">
            <div class="kpi-icon">{{ peakStatus.icon }}</div>
            <div class="num peak" :class="peakStatus.cls">{{ peakStatus.label }}</div>
            <div class="lbl">当前时段客流</div>
            <div class="peak-tip">{{ peakStatus.tip }}</div>
          </div>
        </div>
      </div>

      <!-- 2. 分时客流 -->
      <div class="card">
        <h3>📊 各时段游客咨询热度（近7天均值）</h3>
        <div class="chart-hint">越高代表当前时段越热闹，可据此安排游览时间</div>
        <div ref="hourlyEl" class="chart"></div>
      </div>

      <!-- 3. 景点热度 -->
      <div class="card">
        <h3>🔥 景点热度排行</h3>
        <div class="chart-hint">游客最常询问的景点</div>
        <div ref="spotEl" class="chart"></div>
      </div>

      <!-- 4. 热门问答 -->
      <div class="card hot-qa">
        <h3>💬 游客最常问的问题 Top 10</h3>
        <div class="chart-hint">以下是大家最关心的问题，可直接向数字人导游提问</div>
        <div ref="hotEl" class="chart"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import axios from 'axios'
import * as echarts from 'echarts'

const overview = ref({ today_sessions: 0, today_messages: 0, week_sessions: 0, avg_latency_ms: 0, satisfaction: 0, today_neg_rate: 0 })
const now = ref('')
const hotEl = ref(), spotEl = ref(), hourlyEl = ref()
const isFullscreen = ref(false)
let charts = {}, timer

// 最热景点名称（来自 spot heatmap 数据）
const topSpotName = ref('—')

// 当前时段状态（基于分时客流数据推断）
const hourlyData = ref([])
const peakStatus = computed(() => {
  const h = new Date().getHours()
  const row = hourlyData.value.find(x => Number(x.hour) === h)
  if (!row || hourlyData.value.length === 0) return { label: '获取中', icon: '⏳', cls: '', tip: '' }
  const counts = hourlyData.value.map(x => x.count)
  const max = Math.max(...counts) || 1
  const ratio = row.count / max
  if (ratio >= 0.7) return { label: '高峰时段', icon: '🔴', cls: 'peak-high', tip: '建议避开主干道，先游偏僻景点' }
  if (ratio >= 0.35) return { label: '一般时段', icon: '🟡', cls: 'peak-mid', tip: '游客适中，正常游览即可' }
  return { label: '较空闲', icon: '🟢', cls: 'peak-low', tip: '当前游客较少，非常适合游览' }
})

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
  const [o, h, sp, hourly] = await Promise.all([
    axios.get('/api/analytics/overview', { params: { days: 7 } }),
    axios.get('/api/analytics/hot-questions', { params: { limit: 10 } }),
    axios.get('/api/analytics/spot-heatmap'),
    axios.get('/api/analytics/hourly-traffic', { params: { days: 7 } }),
  ])
  overview.value = o.data
  hourlyData.value = hourly.data

  // 最热景点
  if (sp.data.length > 0) topSpotName.value = sp.data[0].name

  // 分时客流 —— 高亮当前小时
  const currentHour = new Date().getHours()
  charts.hourly.setOption({
    ...dark,
    tooltip: { trigger: 'axis', formatter: p => `${p[0].name}时<br/>咨询热度：${p[0].value}` },
    xAxis: {
      type: 'category',
      data: hourly.data.map(x => x.hour),
      axisLabel: { color: '#94a3b8', formatter: v => v + '时' }
    },
    yAxis: { type: 'value', axisLabel: { color: '#94a3b8' }, name: '咨询量', nameTextStyle: { color: '#64748b' } },
    series: [{
      type: 'bar',
      data: hourly.data.map(x => ({
        value: x.count,
        itemStyle: {
          color: Number(x.hour) === currentHour
            ? '#f59e0b'
            : { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(56,189,248,0.9)' }, { offset: 1, color: 'rgba(56,189,248,0.2)' }] }
        }
      })),
      markLine: {
        silent: true,
        data: [{ xAxis: String(currentHour), label: { formatter: '▲ 现在', color: '#f59e0b' }, lineStyle: { color: '#f59e0b', type: 'dashed' } }]
      }
    }]
  })

  // 景点热度
  const spotRows = sp.data.slice(0, 10).slice().reverse()
  charts.spot.setOption({
    ...dark,
    tooltip: { formatter: p => `${p.name}<br/>咨询次数：${p.value}` },
    grid: { left: 80, right: 24, top: 8, bottom: 12 },
    xAxis: { type: 'value', axisLabel: { color: '#94a3b8' } },
    yAxis: { type: 'category', data: spotRows.map(x => x.name), axisLabel: { color: '#e2e8f0', fontSize: 12 } },
    series: [{
      type: 'bar',
      data: spotRows.map((x, i) => ({
        value: x.count,
        itemStyle: {
          color: i === spotRows.length - 1
            ? { type: 'linear', x: 0, y: 0, x2: 1, y2: 0, colorStops: [{ offset: 0, color: '#f59e0b' }, { offset: 1, color: '#dc2626' }] }
            : { type: 'linear', x: 0, y: 0, x2: 1, y2: 0, colorStops: [{ offset: 0, color: '#1d4ed8' }, { offset: 1, color: '#38bdf8' }] }
        }
      })),
      label: { show: true, position: 'right', color: '#94a3b8', fontSize: 11, formatter: p => p.value || '' }
    }]
  })

  // 热门问答
  const hot = h.data.slice().reverse()
  charts.hot.setOption({
    ...dark,
    grid: { left: 220, right: 60, top: 8, bottom: 12 },
    tooltip: { formatter: p => `问题：${hot[p.dataIndex]?.question}<br/>被问次数：${p.value}` },
    xAxis: { type: 'value', axisLabel: { color: '#94a3b8' } },
    yAxis: {
      type: 'category',
      data: hot.map(x => x.question.length > 22 ? x.question.slice(0, 22) + '…' : x.question),
      axisLabel: { color: '#e2e8f0', fontSize: 12 }
    },
    series: [{
      type: 'bar',
      data: hot.map(x => x.count),
      itemStyle: { color: { type: 'linear', x: 0, y: 0, x2: 1, y2: 0, colorStops: [{ offset: 0, color: '#4f46e5' }, { offset: 1, color: '#38bdf8' }] } },
      label: { show: true, position: 'right', color: '#94a3b8', fontSize: 11, formatter: p => p.value ? `×${p.value}` : '' }
    }]
  })
}

onMounted(() => {
  charts.hourly = echarts.init(hourlyEl.value, 'dark')
  charts.spot   = echarts.init(spotEl.value, 'dark')
  charts.hot    = echarts.init(hotEl.value, 'dark')
  refresh()
  timer = setInterval(refresh, 15000)
  window.addEventListener('resize', resize)
})

function resize() { Object.values(charts).forEach(c => c?.resize()) }

onUnmounted(() => { clearInterval(timer); window.removeEventListener('resize', resize) })
</script>

<style scoped>
.dash { min-height: 100vh; padding: 16px; display: flex; flex-direction: column; background: #020817; }
header { display: flex; justify-content: space-between; align-items: center; padding: 0 8px 12px; border-bottom: 1px solid #1f2a44; }
.header-left { display: flex; flex-direction: column; gap: 2px; }
.subtitle { font-size: 12px; color: #475569; letter-spacing: 1px; }
.header-right { display: flex; align-items: center; gap: 16px; }
header h1 { margin: 0; font-size: 22px; background: linear-gradient(90deg, #38bdf8, #c084fc); -webkit-background-clip: text; color: transparent; }
.time { color: #64748b; font-size: 13px; }
.fs-btn { background: transparent; border: 1px solid #334155; color: #94a3b8; border-radius: 6px; padding: 4px 10px; font-size: 16px; cursor: pointer; line-height: 1; }
.fs-btn:hover { border-color: #38bdf8; color: #38bdf8; }

.grid {
  flex: 1; display: grid;
  grid-template-columns: 2fr 1fr;
  grid-template-rows: auto minmax(260px, 1fr) minmax(300px, 1fr);
  gap: 12px; margin-top: 12px;
}
/* KPI 占满两列 */
.grid .card:nth-child(1) { grid-column: span 2; }
/* 热门问答占满两列 */
.grid .hot-qa { grid-column: span 2; }

.card { background: #0f172a; border: 1px solid #1e293b; border-radius: 10px; padding: 16px; display: flex; flex-direction: column; }
.card h3 { margin: 0 0 4px; font-size: 14px; color: #94a3b8; font-weight: 500; letter-spacing: 0.5px; }
.chart-hint { font-size: 11px; color: #475569; margin-bottom: 8px; }
.chart { flex: 1; min-height: 0; }

/* KPI */
.kpi { padding: 20px 24px; }
.kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 24px; align-items: start; }
.kpi-item { display: flex; flex-direction: column; align-items: center; text-align: center; gap: 4px; }
.kpi-icon { font-size: 28px; line-height: 1; }
.num { font-size: 38px; color: #38bdf8; font-weight: 700; line-height: 1.1; }
.num.spot-name { font-size: 22px; color: #f59e0b; }
.num.peak { font-size: 20px; font-weight: 600; }
.num.peak-high { color: #ef4444; }
.num.peak-mid  { color: #f59e0b; }
.num.peak-low  { color: #22c55e; }
.lbl { color: #64748b; font-size: 13px; }
.peak-tip { font-size: 11px; color: #475569; margin-top: 2px; max-width: 140px; line-height: 1.4; }
</style>

