
<template>
  <div class="alarm-stats-page">
    <div class="page-atmosphere"></div>

    <header class="page-header glass-panel">
      <div class="title-block">
        <p class="page-kicker">Security Command View</p>
        <h1 class="page-title">告警态势与业务关联分析</h1>
        <p class="page-subtitle">融合系统安全、告警分布、处置效率与飞行业务数据</p>
      </div>

      <div class="header-controls">
        <label class="control-label">统计范围</label>
        <select v-model="rangeKey" class="range-select" @change="loadDashboard">
          <option v-for="opt in rangeOptions" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </option>
        </select>
        <button class="refresh-btn" type="button" :disabled="loading" @click="loadDashboard">
          刷新
        </button>
        <span class="updated-time">更新时间：{{ lastUpdatedText }}</span>
      </div>
    </header>

    <div v-if="loading" class="state-block loading-block">
      <div class="loading-spinner"></div>
      <p>正在加载多维度告警看板...</p>
    </div>

    <main v-else class="dashboard-body">
      <div v-if="error" class="state-block error-block">{{ error }}</div>

      <section class="kpi-grid">
        <article class="kpi-card glass-panel safety-kpi">
          <div class="kpi-title">系统安全等级</div>
          <div class="safety-kpi-main">
            <div class="gauge-wrap">
              <svg viewBox="0 0 120 120" class="safety-gauge">
                <circle class="gauge-track" cx="60" cy="60" r="42" />
                <circle
                  class="gauge-progress"
                  cx="60"
                  cy="60"
                  r="42"
                  :stroke="safetyGradeColor"
                  :stroke-dasharray="`${(safetyScore / 100) * gaugeCircumference} ${gaugeCircumference}`"
                />
                <text x="60" y="58" text-anchor="middle" class="gauge-grade">{{ safetyGrade }}</text>
                <text x="60" y="76" text-anchor="middle" class="gauge-score">{{ safetyScore }}</text>
              </svg>
            </div>
            <div class="safety-kpi-meta">
              <div class="big-number">{{ safetyStats.safetyDays }}<span>天</span></div>
              <p class="meta-note">{{ safetyGradeDesc }}</p>
            </div>
          </div>
        </article>

        <article class="kpi-card glass-panel">
          <div class="kpi-title">告警概览</div>
          <div class="big-number accent">{{ formatNumber(totalAlarms) }}<span>条</span></div>
          <div class="mini-stats">
            <div class="mini-item">
              <span>今日异常</span>
              <b>{{ formatNumber(safetyStats.todayAlarms) }}</b>
            </div>
            <div class="mini-item">
              <span>近30天</span>
              <b>{{ formatNumber(safetyStats.monthAlarms) }}</b>
            </div>
            <div class="mini-item">
              <span>本年累计</span>
              <b>{{ formatNumber(safetyStats.yearAlarms) }}</b>
            </div>
          </div>
        </article>

        <article class="kpi-card glass-panel">
          <div class="kpi-title">处置效率</div>
          <div class="big-number success">{{ formatRate(overallHandleRate) }}<span>%</span></div>
          <div class="mini-stats">
            <div class="mini-item">
              <span>已办</span>
              <b>{{ formatNumber(handledTotal) }}</b>
            </div>
            <div class="mini-item">
              <span>待办</span>
              <b>{{ formatNumber(pendingTotal) }}</b>
            </div>
            <div class="mini-item">
              <span>统计总量</span>
              <b>{{ formatNumber(handledTotal + pendingTotal) }}</b>
            </div>
          </div>
        </article>

        <article class="kpi-card glass-panel">
          <div class="kpi-title">飞行运营</div>
          <div class="flight-metrics">
            <div class="metric-row">
              <span>总里程</span>
              <b>{{ formatMetric(flightStats.distanceKm, 'km') }}</b>
            </div>
            <div class="metric-row">
              <span>总时长</span>
              <b>{{ formatMetric(flightStats.durationHours, 'h') }}</b>
            </div>
            <div class="metric-row">
              <span>任务数</span>
              <b>{{ formatNumber(flightStats.totalTasks) }}</b>
            </div>
          </div>
        </article>

        <article class="kpi-card glass-panel">
          <div class="kpi-title">飞行风险密度</div>
          <div class="big-number warn">
            <template v-if="alarmDensityPer100Km !== null">
              {{ alarmDensityPer100Km.toFixed(2) }}
            </template>
            <template v-else>--</template>
            <span>条 / 百公里</span>
          </div>
          <div class="meta-note">用于衡量飞行任务密度下的告警风险暴露程度</div>
        </article>
      </section>

      <section class="middle-grid">
        <article class="trend-panel glass-panel">
          <div class="panel-header">
            <div>
              <h3>告警趋势主视图</h3>
            </div>
            <div class="trend-type-legend">
              <span v-for="item in trendTypeLegend" :key="`trend-legend-${item.id}`" class="trend-type-chip">
                <i class="chip-dot" :style="{ background: item.color }"></i>
                <em>{{ item.name }}</em>
              </span>
            </div>
          </div>

          <div v-if="lineChart.series.length" class="trend-chart-wrap">
            <div class="y-axis">
              <span v-for="tick in lineTicks" :key="`tick-${tick}`">{{ tick }}</span>
            </div>

            <div class="chart-main">
              <svg class="trend-svg" :viewBox="`0 0 ${chart.width} ${chart.height}`" preserveAspectRatio="none">
                <g class="grid-layer">
                  <line
                    v-for="(line, idx) in lineGrid"
                    :key="`grid-${idx}`"
                    :x1="chart.paddingX"
                    :y1="line"
                    :x2="chart.width - chart.paddingX"
                    :y2="line"
                  />
                </g>

                <g class="series-layer" v-for="series in lineChart.series" :key="series.id">
                  <path :d="getLinePath(series.data)" :stroke="series.color" class="series-path" />
                  <g v-for="point in getLinePoints(series.data)" :key="`${series.id}-${point.index}`" class="point-node">
                    <circle
                      class="series-point"
                      :cx="point.x"
                      :cy="point.y"
                      r="4.5"
                      :fill="series.color"
                    />
                    <circle
                      class="series-hit"
                      :cx="point.x"
                      :cy="point.y"
                      r="11"
                      fill="transparent"
                      @mouseenter="handlePointHover($event, series, point)"
                      @mouseleave="hideTooltip"
                      @click="handlePointClick(series, point.index)"
                    />
                  </g>
                </g>
              </svg>

              <div class="x-axis">
                <span v-for="m in lineChart.categories" :key="m">{{ m }}</span>
              </div>
            </div>
          </div>

          <div v-else class="empty-hint">暂无趋势数据</div>
        </article>

        <aside class="health-panel glass-panel">
          <div class="panel-header">
            <div>
              <h3>安全状态墙</h3>
              <p>今日/近30天/本年异常综合评估</p>
            </div>
          </div>

          <div class="safety-wall">
            <div v-for="item in safetyWall" :key="item.label" class="wall-item" :class="item.level">
              <div class="wall-label">{{ item.label }}</div>
              <div class="wall-value">{{ item.value }}</div>
              <div class="wall-state">{{ item.state }}</div>
            </div>
          </div>

          <div class="wayline-rank">
            <h4>航线告警排行</h4>
            <div v-if="waylineRanking.length" class="rank-list">
              <div v-for="item in waylineRanking" :key="item.id" class="rank-item">
                <span class="dot" :style="{ background: item.color || '#38bdf8' }"></span>
                <span class="name" :title="item.name">{{ item.name }}</span>
                <span class="value">{{ formatNumber(item.value) }}</span>
              </div>
            </div>
            <div v-else class="empty-sub">暂无航线统计</div>
          </div>
        </aside>
      </section>

      <section class="bottom-grid">
        <article class="bottom-card glass-panel">
          <div class="panel-header small">
            <div>
              <h3>处置效率分析</h3>
              <p>待办 vs 已办 + 平均处置时长</p>
            </div>
          </div>

          <div class="stack-bars" v-if="handlingRows.length">
            <div v-for="row in handlingRows" :key="row.id" class="stack-row">
              <div class="row-label" :title="row.name">{{ row.name }}</div>
              <div class="row-bar">
                <div
                  class="bar-handled"
                  :style="{ width: `${row.handledPct}%` }"
                  @mouseenter="showTooltip($event, `${row.name} · 已办`, [`${row.handled} 条`, `占比 ${row.handledPct.toFixed(1)}%`])"
                  @mouseleave="hideTooltip"
                ></div>
                <div
                  class="bar-pending"
                  :style="{ width: `${row.pendingPct}%` }"
                  @mouseenter="showTooltip($event, `${row.name} · 待办`, [`${row.pending} 条`, `占比 ${row.pendingPct.toFixed(1)}%`])"
                  @mouseleave="hideTooltip"
                ></div>
              </div>
              <div class="row-meta">{{ row.handled }}/{{ row.total }} · {{ row.rate }}%</div>
            </div>
          </div>
          <div v-else class="empty-sub">暂无处置率统计</div>

          <div class="duration-panel">
            <h4>平均处置时长（小时）</h4>
            <div v-if="handleDurationRows.length" class="duration-list">
              <div v-for="row in handleDurationRows" :key="`dur-${row.id}`" class="duration-row">
                <span class="duration-name">{{ row.name }}</span>
                <div class="duration-bar">
                  <i :style="{ width: `${row.width}%` }"></i>
                </div>
                <span class="duration-value">{{ row.display }}</span>
              </div>
            </div>
            <div v-else class="empty-sub">暂无可计算的处置时长</div>
          </div>
        </article>
        <article class="bottom-card glass-panel">
          <div class="panel-header small">
            <div>
              <h3>告警深度分析</h3>
              <p>类型结构 + 时段高发分布</p>
            </div>
          </div>

          <div class="donut-zone">
            <DonutRing :series="detectTypeLegend" total-label="总告警" :total-value="totalAlarms" />
            <div class="type-legend">
              <div v-for="item in detectTypeLegend" :key="`type-${item.id}`" class="legend-row">
                <span class="dot" :style="{ background: item.color || '#38bdf8' }"></span>
                <span class="name" :title="item.name">{{ item.name }}</span>
                <span class="value">{{ formatNumber(item.value) }}</span>
              </div>
            </div>
          </div>

          <div class="hourly-panel">
            <h4>告警时段分布（24小时）</h4>
            <div v-if="hourlyDistribution.length" class="hourly-chart">
              <div
                v-for="item in hourlyDistribution"
                :key="`hour-${item.hour}`"
                class="hour-item"
                @mouseenter="showTooltip($event, `${item.label}`, [`告警 ${item.value} 条`])"
                @mouseleave="hideTooltip"
              >
                <div class="hour-track">
                  <div class="hour-fill" :style="{ height: `${item.height}%` }"></div>
                </div>
                <span class="hour-label">{{ item.shortLabel }}</span>
              </div>
            </div>
            <div v-else class="empty-sub">暂无时段分布数据</div>
          </div>
        </article>

        <article class="bottom-card glass-panel">
          <div class="panel-header small">
            <div>
              <h3>飞行与业务关联</h3>
              <p>机场任务、里程、时长与相对风险指数</p>
            </div>
          </div>

          <div v-if="airportRiskRows.length" class="airport-list">
            <div class="airport-head">
              <span>机场</span>
              <span>任务</span>
              <span>里程(km)</span>
              <span>时长(h)</span>
              <span>风险指数</span>
            </div>

            <div v-for="item in airportRiskRows" :key="item.dockSn || item.name" class="airport-row">
              <span :title="item.name">{{ item.name }}</span>
              <span>{{ item.taskCount }}</span>
              <span>{{ item.distanceKm.toFixed(2) }}</span>
              <span>{{ item.durationHours.toFixed(2) }}</span>
              <span class="risk-col">
                <i class="risk-bar"><em :style="{ width: `${item.riskPct}%` }"></em></i>
                <b>{{ item.riskIndex.toFixed(2) }}</b>
              </span>
            </div>
          </div>
          <div v-else class="empty-sub">暂无机场飞行统计</div>
        </article>
      </section>
    </main>

    <div v-if="tooltip.visible" class="chart-tooltip" :style="{ left: `${tooltip.x}px`, top: `${tooltip.y}px` }">
      <div class="tt-title">{{ tooltip.title }}</div>
      <div v-for="(line, idx) in tooltip.lines" :key="`line-${idx}`" class="tt-line">{{ line }}</div>
    </div>

    <div v-if="detailModal.visible" class="modal-overlay" @click.self="closeDetailModal">
      <div class="modal-panel glass-panel">
        <div class="modal-header">
          <h3>{{ detailModal.waylineName }} · {{ detailModal.monthLabel }} 告警详情</h3>
          <button class="modal-close" type="button" @click="closeDetailModal">×</button>
        </div>

        <div class="modal-body">
          <div v-if="detailModal.loading" class="state-block loading-block inner">
            <div class="loading-spinner"></div>
            <p>正在加载详情...</p>
          </div>

          <div v-else-if="!detailModal.alarms.length" class="empty-sub">该月份暂无告警</div>

          <div v-else class="detail-list">
            <div v-for="alarm in detailModal.alarms" :key="alarm.id" class="detail-row">
              <div class="detail-main">
                <div class="detail-title">{{ alarm.content || '未填写描述' }}</div>
                <div class="detail-meta">
                  <span>时间：{{ formatDateTime(alarm.created_at) }}</span>
                  <span>航线：{{ resolveWaylineName(alarm) }}</span>
                  <span>状态：{{ alarm.status || '未知' }}</span>
                </div>
              </div>
              <div class="detail-id">ID {{ alarm.id }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import alarmApi from '@/api/alarmApi'
import homeDashboardApi from '@/api/homeDashboardApi'
import DonutRing from '@/components/dashboard/DonutRing.vue'

const RANGE_OPTIONS = [
  { label: '近30天', value: '30', days: 30 },
  { label: '近90天', value: '90', days: 90 },
  { label: '近365天', value: '365', days: 365 }
]

const SERIES_COLORS = [
  '#22d3ee',
  '#f97316',
  '#a78bfa',
  '#34d399',
  '#f43f5e',
  '#60a5fa',
  '#f59e0b',
  '#4ade80'
]

const HANDLED_STATUS_SET = new Set([
  'COMPLETED',
  'DONE',
  'FINISHED',
  'RESOLVED',
  'CLOSED',
  'PROCESSED',
  'HANDLED'
])

const TYPE_NAME_MAP = {
  rail: '铁路',
  contactline: '接触网',
  bridge: '桥梁',
  protected_area: '保护区'
}

const TYPE_ALIASES = {
  rail: ['rail', 'railway', 'rail_line', 'rail-line', 'railway_line'],
  contactline: ['contactline', 'contact_line', 'contact-line', 'catenary', 'contactwire'],
  bridge: ['bridge', 'bridge_line', 'bridge-line'],
  protected_area: ['protected_area', 'protected-area', 'protectedarea', 'protected', 'protected-zone']
}

const TREND_TYPE_ORDER = ['rail', 'contactline', 'bridge', 'protected_area']
const TREND_TYPE_COLOR_MAP = {
  rail: '#22d3ee',
  contactline: '#f59e0b',
  bridge: '#a78bfa',
  protected_area: '#34d399'
}

export default {
  name: 'AlarmStats',
  components: {
    DonutRing
  },
  data() {
    return {
      rangeKey: '90',
      loading: true,
      error: '',
      lastUpdated: null,

      gaugeCircumference: 2 * Math.PI * 42,
      chart: {
        width: 980,
        height: 320,
        paddingX: 42,
        paddingY: 24
      },

      trendMonths: [],
      rangeAlarms: [],
      trendAlarms: [],
      waylineNameMap: {},

      safetyStats: {
        safetyDays: 0,
        todayAlarms: 0,
        monthAlarms: 0,
        yearAlarms: 0,
        latestAlarmAt: null
      },
      detectTypeStats: {
        total: 0,
        series: [],
        window: null
      },
      handleRateStats: {
        total: 0,
        series: [],
        window: null
      },
      flightStats: {
        totalTasks: 0,
        byAirport: [],
        distanceKm: 0,
        durationHours: 0,
        window: null
      },
      waylineStats: {
        total: 0,
        series: [],
        window: null
      },

      hourlyDistribution: [],
      handleDurationByType: {},
      lineChart: {
        categories: [],
        series: []
      },

      tooltip: {
        visible: false,
        x: 0,
        y: 0,
        title: '',
        lines: []
      },

      detailModal: {
        visible: false,
        loading: false,
        waylineName: '',
        monthLabel: '',
        alarms: []
      }
    }
  },
  computed: {
    rangeOptions() {
      return RANGE_OPTIONS
    },
    selectedDays() {
      const found = RANGE_OPTIONS.find(opt => opt.value === this.rangeKey)
      return found ? found.days : 90
    },
    lastUpdatedText() {
      return this.lastUpdated ? this.formatDateTime(this.lastUpdated) : '--'
    },
    totalAlarms() {
      const total = Number(this.detectTypeStats?.total)
      if (Number.isFinite(total) && total >= 0) return total
      return this.rangeAlarms.length
    },
    handledTotal() {
      return (this.handlingRows || []).reduce((sum, row) => sum + row.handled, 0)
    },
    pendingTotal() {
      return (this.handlingRows || []).reduce((sum, row) => sum + row.pending, 0)
    },
    overallHandleRate() {
      const total = this.handledTotal + this.pendingTotal
      if (!total) return 0
      return (this.handledTotal / total) * 100
    },
    alarmDensityPer100Km() {
      const distance = this.toFiniteNumber(this.flightStats?.distanceKm, 0)
      if (distance <= 0) return null
      return (this.totalAlarms / distance) * 100
    },
    safetyScore() {
      const today = this.toFiniteNumber(this.safetyStats.todayAlarms, 0)
      const month = this.toFiniteNumber(this.safetyStats.monthAlarms, 0)
      const year = this.toFiniteNumber(this.safetyStats.yearAlarms, 0)
      const penalty = Math.min(95, today * 9 + month * 1.4 + year * 0.15)
      const score = Math.max(5, Math.round(100 - penalty))
      return score
    },
    safetyGrade() {
      const score = this.safetyScore
      if (score >= 85) return 'A'
      if (score >= 70) return 'B'
      if (score >= 55) return 'C'
      return 'D'
    },
    safetyGradeColor() {
      if (this.safetyGrade === 'A') return '#22c55e'
      if (this.safetyGrade === 'B') return '#38bdf8'
      if (this.safetyGrade === 'C') return '#f59e0b'
      return '#ef4444'
    },
    safetyGradeDesc() {
      if (this.safetyGrade === 'A') return '风险低，系统运行稳定'
      if (this.safetyGrade === 'B') return '状态良好，建议持续巡检'
      if (this.safetyGrade === 'C') return '风险抬升，建议重点关注'
      return '风险较高，建议立即复核'
    },
    safetyWall() {
      const resolveLevel = (value, low, high) => {
        if (value <= low) return { level: 'good', state: '平稳' }
        if (value <= high) return { level: 'watch', state: '关注' }
        return { level: 'risk', state: '预警' }
      }
      const today = this.toFiniteNumber(this.safetyStats.todayAlarms, 0)
      const month = this.toFiniteNumber(this.safetyStats.monthAlarms, 0)
      const year = this.toFiniteNumber(this.safetyStats.yearAlarms, 0)

      const todayState = resolveLevel(today, 0, 3)
      const monthState = resolveLevel(month, 10, 25)
      const yearState = resolveLevel(year, 60, 180)

      return [
        { label: '今日异常', value: today, ...todayState },
        { label: '近30天异常', value: month, ...monthState },
        { label: '本年异常', value: year, ...yearState }
      ]
    },
    lineMax() {
      const values = (this.lineChart.series || []).flatMap(item => item.data || [])
      const max = Math.max(...values, 1)
      return max
    },
    lineTicks() {
      const max = this.lineMax || 1
      const step = max / 4
      return [4, 3, 2, 1, 0].map(i => Math.round((step * i + Number.EPSILON) * 10) / 10)
    },
    lineGrid() {
      const innerHeight = this.chart.height - this.chart.paddingY * 2
      return [0, 1, 2, 3, 4].map(i => this.chart.paddingY + (innerHeight / 4) * i)
    },
    handlingRows() {
      const rows = Array.isArray(this.handleRateStats?.series) ? this.handleRateStats.series : []
      return rows.map((item, index) => {
        const handled = this.toFiniteNumber(item.handled, 0)
        const total = this.toFiniteNumber(item.total, 0)
        const pending = Math.max(total - handled, 0)
        const handledPct = total > 0 ? (handled / total) * 100 : 0
        const pendingPct = Math.max(100 - handledPct, 0)
        return {
          id: item.id || `type-${index}`,
          name: item.name || item.id || `类型${index + 1}`,
          total,
          handled,
          pending,
          handledPct,
          pendingPct,
          rate: this.toFiniteNumber(item.rate, total > 0 ? (handled / total) * 100 : 0),
          color: item.color || SERIES_COLORS[index % SERIES_COLORS.length]
        }
      })
    },
    handleDurationRows() {
      const rows = this.handlingRows.map(item => {
        const avg = this.handleDurationByType[item.id]
        return {
          id: item.id,
          name: item.name,
          value: Number.isFinite(avg) ? avg : null
        }
      })
      const valid = rows.filter(item => item.value !== null)
      const max = Math.max(...valid.map(item => item.value), 1)
      return rows.map(item => ({
        ...item,
        width: item.value !== null ? (item.value / max) * 100 : 0,
        display: item.value !== null ? item.value.toFixed(2) : '--'
      }))
    },
    detectTypeLegend() {
      return Array.isArray(this.detectTypeStats?.series) ? this.detectTypeStats.series : []
    },
    trendTypeLegend() {
      return TREND_TYPE_ORDER.map(id => ({
        id,
        name: TYPE_NAME_MAP[id] || id,
        color: TREND_TYPE_COLOR_MAP[id] || '#38bdf8'
      }))
    },
    waylineRanking() {
      const list = Array.isArray(this.waylineStats?.series) ? this.waylineStats.series : []
      return list
        .filter(item => item && item.id !== '__OTHER__')
        .map(item => ({
          ...item,
          name: this.resolveWaylineNameById(item.id)
        }))
        .slice(0, 6)
    },
    airportRiskRows() {
      const list = Array.isArray(this.flightStats?.byAirport) ? this.flightStats.byAirport : []
      if (!list.length) return []

      const normalized = list.map(item => {
        const distanceKm = this.toFiniteNumber(item.distanceKm, 0)
        return {
          dockSn: item.dockSn || item.dock_sn || '',
          name: item.name || item.dockSn || item.dock_sn || '未知机场',
          taskCount: this.toFiniteNumber(item.taskCount, 0),
          distanceKm,
          durationHours: this.toFiniteNumber(item.durationHours, 0)
        }
      })

      const avgDistance = normalized.reduce((sum, item) => sum + item.distanceKm, 0) / Math.max(normalized.length, 1)
      const baseRisk = this.toFiniteNumber(this.alarmDensityPer100Km, 0)
      const rows = normalized.map(item => {
        const distanceFactor = avgDistance > 0 ? item.distanceKm / avgDistance : 0
        const riskIndex = baseRisk * (distanceFactor || 0.1)
        return {
          ...item,
          riskIndex
        }
      })

      const maxRisk = Math.max(...rows.map(item => item.riskIndex), 1)
      return rows
        .map(item => ({
          ...item,
          riskPct: (item.riskIndex / maxRisk) * 100
        }))
        .sort((a, b) => b.riskIndex - a.riskIndex)
    }
  },
  mounted() {
    this.loadDashboard()
  },
  methods: {
    async loadDashboard() {
      this.loading = true
      this.error = ''
      this.hideTooltip()
      this.detailModal.visible = false

      try {
        const days = this.selectedDays
        this.initTrendMonths()

        const [
          safetyRes,
          detectRes,
          handleRes,
          flightRes,
          waylineRes,
          waylineListRes,
          rangeAlarms,
          trendAlarms
        ] = await Promise.all([
          homeDashboardApi.getSafetyStats(),
          homeDashboardApi.getDetectTypeStatsByRange({ days }),
          homeDashboardApi.getAlarmHandleRateStatsByRange({ days }),
          homeDashboardApi.getFlightStatsByRange({ days }),
          homeDashboardApi.getAlertWaylineStats({ days, topN: 8 }),
          this.fetchAllWaylinesByPaging(),
          this.fetchAllAlarmsByRange(days),
          this.fetchAllAlarmsByRange(365)
        ])

        const waylineList = Array.isArray(waylineListRes) ? waylineListRes : this.normalizeList(waylineListRes)
        this.waylineNameMap = waylineList.reduce((map, item) => {
          const name = item?.name || ''
          const dbId = item?.id
          const bizId = item?.wayline_id

          if (dbId !== undefined && dbId !== null && String(dbId) !== '') {
            map[String(dbId)] = name || map[String(dbId)] || String(dbId)
          }
          if (bizId !== undefined && bizId !== null && String(bizId) !== '') {
            map[String(bizId)] = name || map[String(bizId)] || String(bizId)
          }
          return map
        }, {})

        this.safetyStats = {
          safetyDays: this.toFiniteNumber(safetyRes?.safetyDays, 0),
          todayAlarms: this.toFiniteNumber(safetyRes?.todayAlarms, 0),
          monthAlarms: this.toFiniteNumber(safetyRes?.monthAlarms, 0),
          yearAlarms: this.toFiniteNumber(safetyRes?.yearAlarms, 0),
          latestAlarmAt: safetyRes?.latestAlarmAt || null
        }

        this.detectTypeStats = {
          total: this.toFiniteNumber(detectRes?.total, 0),
          series: Array.isArray(detectRes?.series) ? detectRes.series : [],
          window: detectRes?.window || null
        }

        this.handleRateStats = {
          total: this.toFiniteNumber(handleRes?.total, 0),
          series: Array.isArray(handleRes?.series) ? handleRes.series : [],
          window: handleRes?.window || null
        }

        this.flightStats = {
          totalTasks: this.toFiniteNumber(flightRes?.totalTasks, 0),
          byAirport: Array.isArray(flightRes?.byAirport) ? flightRes.byAirport : [],
          distanceKm: this.toFiniteNumber(flightRes?.distanceKm, 0),
          durationHours: this.toFiniteNumber(flightRes?.durationHours, 0),
          window: flightRes?.window || null
        }

        this.waylineStats = {
          total: this.toFiniteNumber(waylineRes?.total, 0),
          series: Array.isArray(waylineRes?.series) ? waylineRes.series : [],
          window: waylineRes?.window || null
        }

        this.rangeAlarms = rangeAlarms
        this.trendAlarms = trendAlarms

        this.hourlyDistribution = this.buildHourlyDistribution(rangeAlarms)
        this.handleDurationByType = this.buildHandleDurationByType(rangeAlarms)
        this.lineChart = this.buildTrendLineChart(trendAlarms)

        const latestAt = this.getLatestAlarmTime(rangeAlarms, trendAlarms)
        this.lastUpdated = latestAt || new Date()
      } catch (err) {
        console.error('加载告警大屏失败', err)
        this.error = '加载统计数据失败，请稍后重试'
      } finally {
        this.loading = false
      }
    },

    initTrendMonths() {
      const now = new Date()
      const months = []
      for (let i = 11; i >= 0; i--) {
        const dt = new Date(now.getFullYear(), now.getMonth() - i, 1)
        const start = new Date(dt.getFullYear(), dt.getMonth(), 1, 0, 0, 0, 0)
        const end = new Date(dt.getFullYear(), dt.getMonth() + 1, 0, 23, 59, 59, 999)
        months.push({
          key: `${dt.getFullYear()}-${dt.getMonth()}`,
          label: `${dt.getMonth() + 1}月`,
          fullLabel: `${dt.getFullYear()}年${dt.getMonth() + 1}月`,
          start,
          end
        })
      }
      this.trendMonths = months
    },

    async fetchAllAlarmsByRange(days = 30) {
      const safeDays = Math.max(this.toFiniteNumber(days, 30), 1)
      const now = new Date()
      const end = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59, 999)
      const start = new Date(end.getTime() - (safeDays - 1) * 24 * 60 * 60 * 1000)

      const pageSize = 2000
      let page = 1
      let totalCount = null
      const collected = []
      let loops = 0

      while (loops < 120) {
        loops += 1
        const res = await alarmApi.getAlarms({
          page,
          page_size: pageSize,
          ordering: '-created_at',
          start_date: this.formatDateParam(start),
          end_date: this.formatDateParam(end)
        })

        const list = this.normalizeList(res)
        collected.push(...list)

        if (totalCount === null && typeof res?.count === 'number') {
          totalCount = res.count
        }

        const hasNextFlag = Boolean(res?.next)
        const needByCount = totalCount !== null ? collected.length < totalCount : false
        const needBySize = list.length === pageSize
        if (!(hasNextFlag || needByCount || needBySize)) break
        page += 1
      }

      return collected
    },

    async fetchAllWaylinesByPaging() {
      const pageSize = 200
      let page = 1
      let totalCount = null
      let loops = 0

      const collected = []
      const seenKeys = new Set()

      while (loops < 200) {
        loops += 1
        const res = await alarmApi.getWaylines({
          page,
          page_size: pageSize
        })

        const list = this.normalizeList(res)
        let addedCount = 0
        for (const item of list) {
          const key = String(item?.id ?? item?.wayline_id ?? '')
          if (!key || seenKeys.has(key)) continue
          seenKeys.add(key)
          collected.push(item)
          addedCount += 1
        }

        if (totalCount === null && typeof res?.count === 'number') {
          totalCount = res.count
        }

        const hasNextFlag = Boolean(res?.next)
        const reachedByCount = totalCount !== null ? collected.length >= totalCount : false
        const noProgress = addedCount === 0

        if (reachedByCount || (!hasNextFlag && noProgress)) break
        if (!hasNextFlag && list.length < pageSize) break

        page += 1
      }

      return collected
    },

    buildTrendLineChart(alarms = []) {
      const monthCount = this.trendMonths.length
      if (!monthCount) {
        return { categories: [], series: [] }
      }

      const typeBuckets = TREND_TYPE_ORDER.reduce((acc, key) => {
        acc[key] = Array(monthCount).fill(0)
        return acc
      }, {})

      for (const alarm of alarms) {
        const createdAt = this.parseDate(alarm?.created_at)
        const monthIdx = this.getTrendMonthIndex(createdAt)
        if (monthIdx < 0) continue

        const typeKey = this.resolveDetectTypeKey(alarm)
        if (!typeBuckets[typeKey]) continue
        typeBuckets[typeKey][monthIdx] += 1
      }

      const series = TREND_TYPE_ORDER.map((id, index) => {
        const data = typeBuckets[id] || Array(monthCount).fill(0)
        return {
          id,
          name: TYPE_NAME_MAP[id] || id,
          color: TREND_TYPE_COLOR_MAP[id] || SERIES_COLORS[index % SERIES_COLORS.length],
          data
        }
      })

      return {
        categories: this.trendMonths.map(item => item.label),
        series
      }
    },

    buildHourlyDistribution(alarms = []) {
      const bins = Array.from({ length: 24 }, (_, hour) => ({
        hour,
        label: `${String(hour).padStart(2, '0')}:00 - ${String(hour).padStart(2, '0')}:59`,
        shortLabel: String(hour).padStart(2, '0'),
        value: 0,
        height: 0
      }))

      for (const alarm of alarms) {
        const dt = this.parseDate(alarm?.created_at)
        if (!dt || Number.isNaN(dt.getTime())) continue
        const hour = dt.getHours()
        if (hour >= 0 && hour < 24) bins[hour].value += 1
      }

      const max = Math.max(...bins.map(item => item.value), 1)
      bins.forEach(item => {
        item.height = (item.value / max) * 100
      })
      return bins
    },

    buildHandleDurationByType(alarms = []) {
      const stats = {}
      for (const alarm of alarms) {
        if (!this.isHandledStatus(alarm)) continue

        const createdAt = this.parseDate(alarm?.created_at)
        const updatedAt = this.parseDate(alarm?.updated_at)
        if (!createdAt || !updatedAt) continue
        if (Number.isNaN(createdAt.getTime()) || Number.isNaN(updatedAt.getTime())) continue

        const diffMs = updatedAt.getTime() - createdAt.getTime()
        if (diffMs < 0) continue

        const hours = diffMs / (1000 * 60 * 60)
        if (hours > 720) continue

        const typeKey = this.resolveDetectTypeKey(alarm)
        if (!stats[typeKey]) {
          stats[typeKey] = { sum: 0, count: 0 }
        }
        stats[typeKey].sum += hours
        stats[typeKey].count += 1
      }

      const result = {}
      for (const [key, val] of Object.entries(stats)) {
        if (val.count > 0) {
          result[key] = val.sum / val.count
        }
      }
      return result
    },

    getTrendMonthIndex(date) {
      if (!date || Number.isNaN(date.getTime())) return -1
      return this.trendMonths.findIndex(item => date >= item.start && date <= item.end)
    },

    getLinePath(values = []) {
      if (!Array.isArray(values) || values.length === 0) return ''
      return values
        .map((value, index) => {
          const x = this.getPointX(index)
          const y = this.getPointY(value)
          return `${index === 0 ? 'M' : 'L'} ${x} ${y}`
        })
        .join(' ')
    },

    getLinePoints(values = []) {
      return values.map((value, index) => ({
        index,
        value,
        x: this.getPointX(index),
        y: this.getPointY(value)
      }))
    },

    getPointX(index) {
      const n = Math.max(this.trendMonths.length - 1, 1)
      const innerWidth = this.chart.width - this.chart.paddingX * 2
      return this.chart.paddingX + (innerWidth / n) * index
    },

    getPointY(value) {
      const max = Math.max(this.lineMax, 1)
      const innerHeight = this.chart.height - this.chart.paddingY * 2
      const ratio = this.toFiniteNumber(value, 0) / max
      return this.chart.height - this.chart.paddingY - innerHeight * ratio
    },

    handlePointHover(event, series, point) {
      const month = this.trendMonths[point.index]
      if (!month) return
      this.showTooltip(event, `${series.name} · ${month.fullLabel}`, [`告警 ${point.value} 条`, '点击可查看详情'])
    },

    handlePointClick(series, monthIndex) {
      const month = this.trendMonths[monthIndex]
      if (!month) return
      this.detailModal.loading = true
      this.detailModal.visible = true
      this.detailModal.waylineName = series.name
      this.detailModal.monthLabel = month.fullLabel

      const filtered = this.trendAlarms
        .filter(alarm => {
          const dt = this.parseDate(alarm?.created_at)
          if (!dt || Number.isNaN(dt.getTime())) return false
          if (dt < month.start || dt > month.end) return false
          return this.resolveDetectTypeKey(alarm) === String(series.id)
        })
        .sort((a, b) => {
          const ta = this.parseDate(a?.created_at)?.getTime() || 0
          const tb = this.parseDate(b?.created_at)?.getTime() || 0
          return tb - ta
        })

      this.detailModal.alarms = filtered
      this.detailModal.loading = false
    },

    closeDetailModal() {
      this.detailModal.visible = false
      this.detailModal.loading = false
      this.detailModal.alarms = []
    },

    showTooltip(event, title, lines = []) {
      const x = (event?.clientX || 0) + 14
      const y = (event?.clientY || 0) + 14
      this.tooltip.visible = true
      this.tooltip.x = x
      this.tooltip.y = y
      this.tooltip.title = title
      this.tooltip.lines = lines
    },

    hideTooltip() {
      this.tooltip.visible = false
    },

    resolveWaylineId(alarm) {
      const raw =
        alarm?.wayline_id ??
        alarm?.wayline ??
        alarm?.wayline_details?.id ??
        alarm?.wayline_details?.wayline_id ??
        null
      if (raw === null || raw === undefined || raw === '') return '__UNKNOWN__'
      return String(raw)
    },

    resolveWaylineName(alarm) {
      const id = this.resolveWaylineId(alarm)
      return this.resolveWaylineNameById(id)
    },

    resolveWaylineNameById(id) {
      if (id === '__UNKNOWN__') return '未知航线'
      const key = String(id)
      const mapped = this.waylineNameMap[key]
      if (mapped && String(mapped).trim()) return mapped
      return key
    },

    resolveDetectTypeKey(alarm) {
      const candidates = [
        alarm?.category_details?.code,
        alarm?.category_code,
        alarm?.detect_type,
        alarm?.type,
        alarm?.category_details?.name,
        alarm?.category_name
      ]

      for (const item of candidates) {
        const key = this.matchDetectType(item)
        if (key) return key
      }
      return '__OTHER__'
    },

    matchDetectType(raw) {
      const value = String(raw || '').trim().toLowerCase()
      if (!value) return null

      if (TYPE_NAME_MAP[value]) return value
      for (const [key, aliases] of Object.entries(TYPE_ALIASES)) {
        if (aliases.includes(value)) return key
      }

      const compact = value.replace(/\s+/g, '')
      if (compact.includes('铁路')) return 'rail'
      if (compact.includes('接触网') || compact.includes('接触线')) return 'contactline'
      if (compact.includes('桥梁')) return 'bridge'
      if (compact.includes('保护区')) return 'protected_area'
      return null
    },

    isHandledStatus(alarm) {
      const direct = alarm?.handled ?? alarm?.is_processed ?? alarm?.processed ?? alarm?.is_handled
      if (direct === true || direct === 1 || direct === '1') return true
      const statusText = String(alarm?.status || '').trim().toUpperCase()
      return HANDLED_STATUS_SET.has(statusText)
    },

    getLatestAlarmTime(...alarmGroups) {
      const merged = alarmGroups.flat().filter(Boolean)
      let latest = null
      for (const alarm of merged) {
        const dt = this.parseDate(alarm?.created_at)
        if (!dt || Number.isNaN(dt.getTime())) continue
        if (!latest || dt > latest) latest = dt
      }
      return latest
    },

    normalizeList(res) {
      if (!res) return []
      if (Array.isArray(res)) return res
      if (Array.isArray(res.results)) return res.results
      if (Array.isArray(res.data)) return res.data
      return []
    },

    toFiniteNumber(value, fallback = 0) {
      const numeric = Number(value)
      return Number.isFinite(numeric) ? numeric : fallback
    },

    formatRate(value) {
      const numeric = this.toFiniteNumber(value, 0)
      return numeric.toFixed(1)
    },

    formatMetric(value, unit = '') {
      const numeric = Number(value)
      if (!Number.isFinite(numeric)) return `-- ${unit}`.trim()
      return `${numeric.toFixed(2)} ${unit}`.trim()
    },

    formatNumber(value) {
      const numeric = Number(value)
      if (!Number.isFinite(numeric)) return '--'
      return Math.round(numeric).toLocaleString('zh-CN')
    },

    formatDateParam(date) {
      const dt = this.parseDate(date)
      if (!dt || Number.isNaN(dt.getTime())) return ''
      const pad = num => String(num).padStart(2, '0')
      return `${dt.getFullYear()}-${pad(dt.getMonth() + 1)}-${pad(dt.getDate())}`
    },

    formatDateTime(dateLike) {
      const dt = this.parseDate(dateLike)
      if (!dt || Number.isNaN(dt.getTime())) return '--'
      const pad = num => String(num).padStart(2, '0')
      return `${dt.getFullYear()}-${pad(dt.getMonth() + 1)}-${pad(dt.getDate())} ${pad(dt.getHours())}:${pad(dt.getMinutes())}`
    },

    parseDate(dateLike) {
      if (!dateLike) return null
      if (dateLike instanceof Date) return new Date(dateLike.getTime())
      if (typeof dateLike === 'string') {
        const normalized = dateLike.includes('T') ? dateLike : dateLike.replace(' ', 'T')
        const parsed = new Date(normalized)
        if (!Number.isNaN(parsed.getTime())) return parsed
      }
      const fallback = new Date(dateLike)
      if (Number.isNaN(fallback.getTime())) return null
      return fallback
    }
  }
}
</script>

<style scoped>
.alarm-stats-page {
  --bg-base: #060b17;
  --glass-bg: rgba(11, 19, 36, 0.72);
  --glass-border: rgba(56, 189, 248, 0.28);
  --text-main: #e2e8f0;
  --text-soft: #94a3b8;
  position: relative;
  height: 100%;
  min-height: 100%;
  padding: 20px;
  overflow: auto;
  color: var(--text-main);
  font-family: 'Bahnschrift', 'DIN Alternate', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  background:
    radial-gradient(circle at 10% 0%, rgba(34, 211, 238, 0.15), transparent 40%),
    radial-gradient(circle at 92% 14%, rgba(56, 189, 248, 0.12), transparent 45%),
    radial-gradient(circle at 50% 100%, rgba(99, 102, 241, 0.1), transparent 55%),
    var(--bg-base);
}

.page-atmosphere {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background-image:
    linear-gradient(90deg, rgba(148, 163, 184, 0.06) 1px, transparent 1px),
    linear-gradient(180deg, rgba(148, 163, 184, 0.06) 1px, transparent 1px);
  background-size: 46px 46px;
  mask-image: radial-gradient(circle at 50% 35%, black, transparent 80%);
}

.glass-panel {
  background: linear-gradient(130deg, rgba(17, 25, 45, 0.92), var(--glass-bg));
  border: 1px solid var(--glass-border);
  border-radius: 16px;
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.38), inset 0 0 0 1px rgba(255, 255, 255, 0.03);
  backdrop-filter: blur(8px);
}

.page-header {
  position: relative;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  padding: 18px 20px;
  margin-bottom: 16px;
}

.page-kicker {
  margin: 0;
  color: #67e8f9;
  font-size: 12px;
  letter-spacing: 2px;
  text-transform: uppercase;
}

.page-title {
  margin: 6px 0 0;
  font-size: 30px;
  font-weight: 800;
  letter-spacing: 0.8px;
  color: #ecfeff;
}

.page-subtitle {
  margin: 8px 0 0;
  color: var(--text-soft);
  font-size: 14px;
}

.header-controls {
  display: grid;
  grid-template-columns: auto auto auto;
  grid-template-rows: auto auto;
  align-items: center;
  gap: 8px 10px;
  justify-items: end;
  min-width: 290px;
}

.control-label {
  grid-column: 1 / -1;
  font-size: 12px;
  color: var(--text-soft);
}

.range-select {
  min-width: 120px;
  padding: 8px 10px;
  border-radius: 10px;
  border: 1px solid rgba(125, 211, 252, 0.35);
  background: rgba(8, 15, 30, 0.8);
  color: #e2e8f0;
}

.refresh-btn {
  padding: 8px 14px;
  border: 1px solid rgba(56, 189, 248, 0.5);
  border-radius: 10px;
  color: #dbeafe;
  background: linear-gradient(120deg, rgba(2, 132, 199, 0.3), rgba(14, 116, 144, 0.3));
  cursor: pointer;
}

.refresh-btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.updated-time {
  grid-column: 1 / -1;
  justify-self: end;
  font-size: 12px;
  color: var(--text-soft);
}

.dashboard-body {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.kpi-grid {
  display: grid;
  grid-template-columns: 1.25fr repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.kpi-card {
  padding: 14px;
  min-height: 146px;
}

.kpi-title {
  color: #bae6fd;
  font-size: 13px;
  letter-spacing: 0.5px;
  margin-bottom: 10px;
}

.big-number {
  font-size: 34px;
  font-weight: 800;
  color: #f8fafc;
  text-shadow: 0 0 16px rgba(34, 211, 238, 0.25);
}

.big-number span {
  font-size: 14px;
  margin-left: 6px;
  color: #bfdbfe;
}

.big-number.accent {
  color: #22d3ee;
}

.big-number.success {
  color: #4ade80;
}

.big-number.warn {
  color: #fbbf24;
}

.meta-note {
  margin-top: 10px;
  font-size: 12px;
  color: var(--text-soft);
  line-height: 1.45;
}

.mini-stats {
  display: grid;
  gap: 8px;
  margin-top: 10px;
}

.mini-item {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--text-soft);
}

.mini-item b {
  color: #e2e8f0;
  font-size: 13px;
}

.safety-kpi-main {
  display: flex;
  gap: 10px;
  align-items: center;
}

.safety-gauge {
  width: 110px;
  height: 110px;
}

.gauge-track {
  fill: none;
  stroke: rgba(148, 163, 184, 0.18);
  stroke-width: 10;
}

.gauge-progress {
  fill: none;
  stroke-width: 10;
  stroke-linecap: round;
  transform: rotate(-90deg);
  transform-origin: 60px 60px;
  filter: drop-shadow(0 0 5px rgba(34, 211, 238, 0.6));
}

.gauge-grade {
  fill: #f8fafc;
  font-size: 22px;
  font-weight: 700;
}

.gauge-score {
  fill: #93c5fd;
  font-size: 12px;
}

.safety-kpi-meta {
  flex: 1;
}

.flight-metrics {
  display: grid;
  gap: 8px;
}

.metric-row {
  display: flex;
  justify-content: space-between;
  color: var(--text-soft);
  font-size: 12px;
}

.metric-row b {
  color: #f8fafc;
}

.middle-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 12px;
}

.trend-panel,
.health-panel,
.bottom-card {
  padding: 14px;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.panel-header.small {
  margin-bottom: 12px;
}

.panel-header h3 {
  margin: 0;
  font-size: 17px;
  color: #f0f9ff;
}

.panel-header p {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--text-soft);
}

.trend-type-legend {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.trend-type-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.3);
  background: rgba(15, 23, 42, 0.5);
  color: #cbd5e1;
  font-size: 11px;
}

.trend-type-chip .chip-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  box-shadow: 0 0 6px currentColor;
}

.trend-type-chip em {
  font-style: normal;
}

.trend-chart-wrap {
  display: flex;
  gap: 8px;
}

.y-axis {
  min-width: 45px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  color: #94a3b8;
  font-size: 11px;
  padding: 8px 0 25px;
}

.y-axis span {
  text-align: right;
}

.chart-main {
  flex: 1;
  min-width: 0;
}

.trend-svg {
  width: 100%;
  height: 310px;
}

.grid-layer line {
  stroke: rgba(148, 163, 184, 0.18);
  stroke-dasharray: 4 4;
}

.series-path {
  fill: none;
  stroke-width: 2.5;
  stroke-linecap: round;
  stroke-linejoin: round;
  opacity: 0.9;
}

.series-point {
  pointer-events: none;
  transition: opacity 0.16s ease;
  opacity: 0.95;
}

.series-hit {
  cursor: pointer;
}

.point-node:hover .series-point {
  opacity: 1;
}

.x-axis {
  display: flex;
  justify-content: space-between;
  margin-top: -4px;
  padding: 0 42px;
  color: #94a3b8;
  font-size: 11px;
}

.health-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.safety-wall {
  display: grid;
  gap: 8px;
}

.wall-item {
  border-radius: 12px;
  padding: 10px 12px;
  border: 1px solid transparent;
  background: rgba(15, 23, 42, 0.52);
  display: grid;
  grid-template-columns: 1fr auto auto;
  align-items: center;
  gap: 10px;
}

.wall-item.good {
  border-color: rgba(34, 197, 94, 0.45);
}

.wall-item.watch {
  border-color: rgba(251, 191, 36, 0.45);
}

.wall-item.risk {
  border-color: rgba(239, 68, 68, 0.45);
}

.wall-label {
  color: #cbd5e1;
  font-size: 12px;
}

.wall-value {
  color: #f8fafc;
  font-weight: 700;
}

.wall-state {
  font-size: 12px;
  color: #93c5fd;
}

.wayline-rank h4,
.duration-panel h4,
.hourly-panel h4 {
  margin: 0 0 8px;
  font-size: 13px;
  color: #bae6fd;
}

.rank-list,
.type-legend,
.duration-list {
  display: grid;
  gap: 6px;
}

.rank-item,
.legend-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.dot {
  width: 9px;
  height: 9px;
  border-radius: 999px;
}

.rank-item .name,
.legend-row .name {
  flex: 1;
  color: #cbd5e1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rank-item .value,
.legend-row .value {
  color: #e2e8f0;
  font-weight: 700;
}

.bottom-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.stack-bars {
  display: grid;
  gap: 8px;
}

.stack-row {
  display: grid;
  grid-template-columns: 76px 1fr auto;
  gap: 8px;
  align-items: center;
}

.row-label {
  color: #cbd5e1;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.row-bar {
  height: 12px;
  border-radius: 999px;
  overflow: hidden;
  display: flex;
  background: rgba(148, 163, 184, 0.18);
}

.bar-handled {
  background: linear-gradient(90deg, #10b981, #34d399);
}

.bar-pending {
  background: linear-gradient(90deg, #f59e0b, #f97316);
}

.row-meta {
  color: #9ca3af;
  font-size: 11px;
}

.duration-panel {
  margin-top: 14px;
}

.duration-row {
  display: grid;
  grid-template-columns: 70px 1fr 42px;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.duration-name {
  font-size: 12px;
  color: #cbd5e1;
}

.duration-bar {
  height: 8px;
  border-radius: 999px;
  overflow: hidden;
  background: rgba(99, 102, 241, 0.16);
}

.duration-bar i {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #818cf8, #22d3ee);
}

.duration-value {
  text-align: right;
  font-size: 11px;
  color: #e2e8f0;
}

.donut-zone {
  display: grid;
  grid-template-columns: 160px 1fr;
  gap: 10px;
  align-items: center;
}

.hourly-panel {
  margin-top: 12px;
}

.hourly-chart {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: 6px;
}

.hour-item {
  text-align: center;
}

.hour-track {
  height: 78px;
  display: flex;
  align-items: flex-end;
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.55);
  border: 1px solid rgba(148, 163, 184, 0.2);
  padding: 2px;
}

.hour-fill {
  width: 100%;
  border-radius: 5px;
  background: linear-gradient(180deg, #22d3ee, #6366f1);
}

.hour-label {
  display: block;
  margin-top: 4px;
  font-size: 10px;
  color: #94a3b8;
}

.airport-list {
  width: 100%;
  display: grid;
  gap: 6px;
}

.airport-head,
.airport-row {
  display: grid;
  grid-template-columns: 1.4fr 0.6fr 0.9fr 0.8fr 1.3fr;
  gap: 8px;
  align-items: center;
}

.airport-head {
  font-size: 11px;
  color: #94a3b8;
  padding-bottom: 5px;
  border-bottom: 1px dashed rgba(148, 163, 184, 0.28);
}

.airport-row {
  font-size: 12px;
  color: #cbd5e1;
}

.risk-col {
  display: flex;
  align-items: center;
  gap: 6px;
}

.risk-bar {
  flex: 1;
  height: 8px;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.2);
  overflow: hidden;
}

.risk-bar em {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #fb7185, #f59e0b);
}

.risk-col b {
  min-width: 36px;
  text-align: right;
  color: #f8fafc;
  font-size: 11px;
}

.chart-tooltip {
  position: fixed;
  z-index: 2000;
  min-width: 150px;
  max-width: 280px;
  padding: 8px 10px;
  border-radius: 10px;
  border: 1px solid rgba(56, 189, 248, 0.38);
  background: rgba(9, 14, 27, 0.95);
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.35);
  pointer-events: none;
}

.tt-title {
  font-size: 12px;
  color: #e0f2fe;
  font-weight: 700;
  margin-bottom: 4px;
}

.tt-line {
  font-size: 11px;
  color: #cbd5e1;
  line-height: 1.45;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(2, 6, 23, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1800;
}

.modal-panel {
  width: min(980px, 92vw);
  max-height: 82vh;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.25);
}

.modal-header h3 {
  margin: 0;
  color: #e0f2fe;
  font-size: 18px;
}

.modal-close {
  border: none;
  background: transparent;
  color: #cbd5e1;
  font-size: 24px;
  cursor: pointer;
}

.modal-body {
  padding: 14px 16px;
  overflow: auto;
}

.detail-list {
  display: grid;
  gap: 8px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid rgba(148, 163, 184, 0.25);
  background: rgba(15, 23, 42, 0.45);
}

.detail-title {
  color: #f8fafc;
  font-size: 13px;
  font-weight: 700;
}

.detail-meta {
  margin-top: 5px;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  color: #94a3b8;
  font-size: 11px;
}

.detail-id {
  color: #cbd5e1;
  font-size: 11px;
}

.state-block {
  border-radius: 12px;
  padding: 14px;
  text-align: center;
}

.loading-block {
  color: #cbd5e1;
}

.loading-block.inner {
  padding: 30px 0;
}

.loading-spinner {
  width: 28px;
  height: 28px;
  border-radius: 999px;
  border: 3px solid rgba(56, 189, 248, 0.24);
  border-top-color: #22d3ee;
  margin: 0 auto 10px;
  animation: spin 1s linear infinite;
}

.error-block {
  background: rgba(127, 29, 29, 0.34);
  border: 1px solid rgba(248, 113, 113, 0.45);
  color: #fecaca;
}

.empty-sub,
.empty-hint {
  color: #94a3b8;
  text-align: center;
  padding: 18px 8px;
  font-size: 13px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 1620px) {
  .kpi-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 1280px) {
  .middle-grid {
    grid-template-columns: 1fr;
  }

  .bottom-grid {
    grid-template-columns: 1fr;
  }

  .donut-zone {
    grid-template-columns: 1fr;
    justify-items: center;
  }

  .hourly-chart {
    grid-template-columns: repeat(8, minmax(0, 1fr));
  }
}

@media (max-width: 960px) {
  .page-header {
    flex-direction: column;
    align-items: stretch;
  }

  .header-controls {
    grid-template-columns: 1fr 1fr;
    justify-items: stretch;
  }

  .range-select,
  .refresh-btn {
    width: 100%;
  }

  .updated-time {
    justify-self: start;
  }

  .kpi-grid {
    grid-template-columns: 1fr;
  }

  .airport-head,
  .airport-row {
    grid-template-columns: 1.3fr 0.6fr 0.8fr 0.8fr 1.2fr;
  }
}

@media (max-width: 640px) {
  .alarm-stats-page {
    padding: 12px;
  }

  .page-title {
    font-size: 24px;
  }

  .trend-svg {
    height: 250px;
  }

  .x-axis {
    padding: 0 24px;
    font-size: 10px;
  }

  .hourly-chart {
    grid-template-columns: repeat(6, minmax(0, 1fr));
  }

  .stack-row {
    grid-template-columns: 62px 1fr;
    grid-template-areas:
      'label meta'
      'bar bar';
    row-gap: 4px;
  }

  .row-label {
    grid-area: label;
  }

  .row-meta {
    grid-area: meta;
    text-align: right;
  }

  .row-bar {
    grid-area: bar;
  }

  .detail-row {
    flex-direction: column;
  }
}
</style>
