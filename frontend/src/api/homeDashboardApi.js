import alarmApi from './alarmApi'
import dockStatusApi from './dockStatusApi'
import inspectTaskApi from './inspectTaskApi'
import waylineImageApi from './waylineImageApi'
import authApi from './authApi'
import flightTaskInfoApi from './flightTaskInfoApi'

const SERIES_COLORS = [
  '#20A4F3', // 鲜亮蓝
  '#FF6B6B', // 亮红
  '#7C3AED', // 深紫
  '#16A34A', // 纯绿
  '#F59E0B', // 琥珀橙
  '#0EA5E9', // 青蓝
  '#EF4444', // 鲜红
  '#14B8A6', // 松石绿
  '#8B5CF6', // 紫罗兰
  '#F97316', // 亮橙
  '#22C55E', // 草绿
  '#C026D3' // 品红
]

const DETECT_TYPE_MAP = {
  rail: '铁路',
  contactline: '接触网',
  bridge: '桥梁',
  protected_area: '保护区'
}
const DETECT_TYPE_ALIASES = {
  rail: ['rail', 'railway', 'rail_line', 'rail-line', 'railway_line'],
  contactline: ['contactline', 'contact_line', 'contact-line', 'catenary', 'catenary_line', 'contactwire'],
  bridge: ['bridge', 'bridge_line', 'bridge-line'],
  protected_area: ['protected_area', 'protected-area', 'protectedarea', 'protected', 'protected-zone', 'protectedzone']
}

const HANDLED_STATUSES = new Set([
  'COMPLETED',
  'DONE',
  'FINISHED',
  'RESOLVED',
  'CLOSED',
  'PROCESSED',
  'HANDLED'
])

function normalizeList(res) {
  if (!res) return []
  if (Array.isArray(res)) return res
  if (Array.isArray(res.results)) return res.results
  if (Array.isArray(res.data)) return res.data
  return []
}

function getCount(res) {
  if (!res) return 0
  if (typeof res.count === 'number') return res.count
  // 兼容非分页返回数组
  if (Array.isArray(res)) return res.length
  if (Array.isArray(res.results)) return res.results.length
  return 0
}

function pad2(n) {
  return String(n).padStart(2, '0')
}

function formatDateParam(dateLike) {
  const dt = dateLike instanceof Date ? dateLike : new Date(dateLike)
  return `${dt.getFullYear()}-${pad2(dt.getMonth() + 1)}-${pad2(dt.getDate())}`
}

function startOfDay(d) {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate(), 0, 0, 0, 0)
}

function endOfDay(d) {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate(), 23, 59, 59, 999)
}

function startOfYear(d) {
  return new Date(d.getFullYear(), 0, 1, 0, 0, 0, 0)
}

function endOfYear(d) {
  return new Date(d.getFullYear(), 11, 31, 23, 59, 59, 999)
}

function startOfCalendarMonths(now, months) {
  const m = Number(months)
  const span = Number.isFinite(m) && m > 0 ? m : 1
  // 自然月口径：包含当月在内，共 span 个整月（起点=span-1个月前的1号）
  return new Date(now.getFullYear(), now.getMonth() - (span - 1), 1, 0, 0, 0, 0)
}


function resolveRangeWindow(days) {
  const span = Number(days)
  const safeDays = Number.isFinite(span) && span > 0 ? span : 30
  const now = new Date()
  const end = endOfDay(now)
  const start = startOfDay(new Date(now.getTime() - (safeDays - 1) * 24 * 60 * 60 * 1000))
  return { start, end }
}

function startOfMonth(d) {
  return new Date(d.getFullYear(), d.getMonth(), 1, 0, 0, 0, 0)
}

function endOfMonth(d) {
  return new Date(d.getFullYear(), d.getMonth() + 1, 0, 23, 59, 59, 999)
}

function normalizeStatus(status) {
  return String(status || '').trim().toUpperCase()
}

function resolveDetectTypeKey(alarm) {
  const rawCode = (
    alarm?.category_details?.code ||
    alarm?.category_code ||
    alarm?.detect_type ||
    alarm?.detectType ||
    alarm?.type ||
    ''
  )
  const rawName = (
    alarm?.category_details?.name ||
    alarm?.category_name ||
    alarm?.detect_type_name ||
    ''
  )
  const code = String(rawCode || '').trim().toLowerCase()
  if (code) {
    if (DETECT_TYPE_MAP[code]) return code
    for (const [key, aliases] of Object.entries(DETECT_TYPE_ALIASES)) {
      if (aliases.includes(code)) return key
    }
    const normalizedCode = code.replace(/\s+/g, '')
    if (normalizedCode.includes('铁路')) return 'rail'
    if (normalizedCode.includes('接触网') || normalizedCode.includes('接触线')) return 'contactline'
    if (normalizedCode.includes('桥梁')) return 'bridge'
    if (normalizedCode.includes('保护区')) return 'protected_area'
  }
  const name = String(rawName || '').trim()
  if (name) {
    const normalized = name.replace(/\s+/g, '')
    if (normalized.includes('铁路')) return 'rail'
    if (normalized.includes('接触网') || normalized.includes('接触线')) return 'contactline'
    if (normalized.includes('桥梁')) return 'bridge'
    if (normalized.includes('保护区')) return 'protected_area'
  }
  return null
}

function isHandledStatus(status) {
  return HANDLED_STATUSES.has(normalizeStatus(status))
}


function resolveTaskDockSn(task) {
  const raw =
    task?.dock_sn ||
    task?.dockSn ||
    task?.dock?.dock_sn ||
    task?.dock?.dockSn ||
    task?.sn ||
    task?.device_sn ||
    task?.deviceSn ||
    task?.station_sn ||
    task?.stationSn ||
    task?.airport_sn ||
    task?.airportSn ||
    null
  if (raw === null || raw === undefined) return null
  const normalized = String(raw).trim()
  return normalized || null
}

function resolveDockSn(dock) {
  const raw =
    dock?.dock_sn ||
    dock?.dockSn ||
    dock?.sn ||
    dock?.device_sn ||
    dock?.deviceSn ||
    dock?.station_sn ||
    dock?.stationSn ||
    dock?.airport_sn ||
    dock?.airportSn ||
    null
  if (raw === null || raw === undefined) return null
  const normalized = String(raw).trim()
  return normalized || null
}

function resolveDockName(dock) {
  return (
    dock?.display_name ||
    dock?.dock_name ||
    dock?.dockName ||
    dock?.airport_name ||
    dock?.airportName ||
    dock?.station_name ||
    dock?.stationName ||
    dock?.site_name ||
    dock?.siteName ||
    dock?.name ||
    resolveDockSn(dock) ||
    '未知机场'
  )
}

function resolveWaylineId(alarm) {
  return (
    alarm?.wayline_id ??
    alarm?.wayline?.id ??
    alarm?.wayline?.wayline_id ??
    alarm?.wayline_details?.id ??
    alarm?.wayline_details?.wayline_id ??
    null
  )
}


function calcDiffDays(from, to) {
  const dayMs = 1000 * 60 * 60 * 24
  const a = startOfDay(from).getTime()
  const b = startOfDay(to).getTime()
  return Math.max(Math.floor((b - a) / dayMs), 0)
}

async function countAlarmsInRange(start, end) {
  const res = await alarmApi.getAlarms({
    page_size: 1,
    start_date: formatDateParam(start),
    end_date: formatDateParam(end)
  })
  return getCount(res)
}

async function fetchAllAlarmsByPaging(params) {
  const pageSize = params.page_size || 2000
  let page = 1
  const collected = []
  let hasNext = true
  let totalCount = null

  while (hasNext) {
    const res = await alarmApi.getAlarms({ ...params, page, page_size: pageSize })
    const list = normalizeList(res)
    collected.push(...list)

    if (totalCount === null && res && typeof res.count === 'number') {
      totalCount = res.count
    }

    const hasNextFlag = Boolean(res && res.next)
    const needByCount = totalCount !== null ? collected.length < totalCount : false
    const needBySize = list.length === pageSize
    hasNext = hasNextFlag || needByCount || needBySize

    if (!hasNext) break
    page += 1
  }

  return { collected, totalCount: totalCount ?? collected.length }
}

async function fetchAllFlightTasksByPaging(params) {
  const pageSize = params.page_size || 2000
  let page = 1
  const collected = []
  let hasNext = true
  let totalCount = null

  while (hasNext) {
    const res = await flightTaskInfoApi.getFlightTaskInfos({ ...params, page, page_size: pageSize })
    const list = normalizeList(res)
    collected.push(...list)

    if (totalCount === null && res && typeof res.count === 'number') {
      totalCount = res.count
    }

    const hasNextFlag = Boolean(res && res.next)
    const needByCount = totalCount !== null ? collected.length < totalCount : false
    const needBySize = list.length === pageSize
    hasNext = hasNextFlag || needByCount || needBySize

    if (!hasNext) break
    page += 1
  }

  return { collected, totalCount: totalCount ?? collected.length }
}

function buildDetectTypeSeries(list) {
  const counts = {}
  Object.keys(DETECT_TYPE_MAP).forEach(key => {
    counts[key] = 0
  })

  list.forEach(item => {
    const code = resolveDetectTypeKey(item)
    if (!code || counts[code] === undefined) return
    counts[code] += 1
  })

  const series = Object.entries(DETECT_TYPE_MAP).map(([code, name], idx) => ({
    id: code,
    name,
    value: counts[code] || 0,
    color: SERIES_COLORS[idx % SERIES_COLORS.length]
  }))

  const total = series.reduce((sum, item) => sum + item.value, 0)
  return { total, series }
}

function buildHandleRateSeries(list) {
  const totals = {}
  const handled = {}
  Object.keys(DETECT_TYPE_MAP).forEach(key => {
    totals[key] = 0
    handled[key] = 0
  })

  list.forEach(item => {
    const code = resolveDetectTypeKey(item)
    if (!code || totals[code] === undefined) return
    totals[code] += 1
    const handledFlag =
      item?.handled ??
      item?.is_processed ??
      item?.processed ??
      item?.is_handled ??
      item?.isHandled
    if (handledFlag === true || handledFlag === 1 || handledFlag === '1') {
      handled[code] += 1
    } else if (isHandledStatus(item?.status)) {
      handled[code] += 1
    }
  })

  const series = Object.entries(DETECT_TYPE_MAP).map(([code, name], idx) => {
    const total = totals[code] || 0
    const done = handled[code] || 0
    return {
      id: code,
      name,
      total,
      handled: done,
      rate: total ? Math.round((done / total) * 100) : 0,
      color: SERIES_COLORS[idx % SERIES_COLORS.length]
    }
  })

  const total = Object.values(totals).reduce((sum, item) => sum + item, 0)
  return { total, series }
}


function buildDockTaskStats(dockRes, taskList) {
  const byAirport = []
  const indexBySn = new Map()
  const docks = normalizeList(dockRes)

  docks.forEach(dock => {
    const dockSn = resolveDockSn(dock)
    if (!dockSn || indexBySn.has(dockSn)) return
    const entry = {
      dockSn,
      name: resolveDockName(dock),
      taskCount: 0,
      distanceKm: null,
      durationHours: null
    }
    indexBySn.set(dockSn, entry)
    byAirport.push(entry)
  })

  if (Array.isArray(taskList)) {
    taskList.forEach(task => {
      const dockSn = resolveTaskDockSn(task)
      if (!dockSn) return
      const entry = indexBySn.get(dockSn)
      if (entry) entry.taskCount += 1
    })
  }

  return byAirport
}

export default {
  async getDockSummary() {
    // 机场概览：优先统计接口，缺失时退回列表计算（不提供假数据）
    try {
      const stats = await dockStatusApi.getDockStatistics()
      const total = Number(stats.total_docks ?? stats.total ?? stats.count ?? 0)
      const online = Number(stats.online_docks ?? stats.online ?? stats.online_count ?? 0)
      const offline = Number.isFinite(total) && Number.isFinite(online) ? Math.max(total - online, 0) : 0
      return { total, online, offline, raw: stats }
    } catch (e) {
      const [all, online] = await Promise.all([dockStatusApi.getAllDocks(), dockStatusApi.getOnlineDocks()])
      const total = normalizeList(all).length
      const onlineCount = normalizeList(online).length
      return { total, online: onlineCount, offline: Math.max(total - onlineCount, 0), raw: { all, online } }
    }
  },

  async getRecentAlarms(limit = 5) {
    const res = await alarmApi.getAlarms({
      page_size: limit,
      ordering: '-created_at'
    })
    return normalizeList(res)
  },

  async getAlertStats(days = 30) {
    const now = new Date()
    const end = endOfDay(now)
    const start = startOfDay(new Date(now.getTime() - (days - 1) * 24 * 60 * 60 * 1000))
    const [countRes, listRes] = await Promise.all([
      alarmApi.getAlarms({ page_size: 1, start_date: formatDateParam(start), end_date: formatDateParam(end) }),
      alarmApi.getAlarms({ page_size: 200, ordering: '-created_at', start_date: formatDateParam(start), end_date: formatDateParam(end) })
    ])
    const total = getCount(countRes)
    const list = normalizeList(listRes)
    const byStatus = list.reduce((acc, item) => {
      const key = item?.status || 'UNKNOWN'
      acc[key] = (acc[key] || 0) + 1
      return acc
    }, {})
    return { total, byStatus, window: { start, end } }
  },

  async getDetectTypeStats() {
    const alarmsRes = await fetchAllAlarmsByPaging({ page_size: 20000 })
    const list = alarmsRes.collected || []
    const { total, series } = buildDetectTypeSeries(list)
    return { total, series }
  },

  async getMonthlyDetectTypeStats({ days = 30 } = {}) {
    return this.getDetectTypeStatsByRange({ days })
  },

  async getMonthlyAlarmHandleRateStats({ monthOffset = 0 } = {}) {
    const now = new Date()
    const target = new Date(now.getFullYear(), now.getMonth() - monthOffset, 1)
    const start = startOfMonth(target)
    const end = monthOffset === 0 ? endOfDay(now) : endOfMonth(target)
    const alarmsRes = await fetchAllAlarmsByPaging({
      page_size: 2000,
      ordering: '-created_at',
      start_date: formatDateParam(start),
      end_date: formatDateParam(end)
    })
    const list = alarmsRes.collected || []
    const { total, series } = buildHandleRateSeries(list)
    return { total, series, window: { start, end } }
  },

  async getMonthlyFlightStats({ monthOffset = 0 } = {}) {
    const now = new Date()
    const target = new Date(now.getFullYear(), now.getMonth() - monthOffset, 1)
    const start = startOfMonth(target)
    const end = monthOffset === 0 ? endOfDay(now) : endOfMonth(target)
    const [dockRes, taskRes] = await Promise.all([
      dockStatusApi.getAllDocks(),
      fetchAllFlightTasksByPaging({
        page_size: 2000,
        ordering: '-created_at',
        start_date: formatDateParam(start),
        end_date: formatDateParam(end)
      })
    ])
    const list = taskRes.collected || []
    const totalTasks = typeof taskRes.totalCount === 'number' ? taskRes.totalCount : list.length
    const byAirport = buildDockTaskStats(dockRes, list)
    return {
      totalTasks,
      byAirport,
      distanceKm: null,
      durationHours: null,
      window: { start, end }
    }
  },


  async getDetectTypeStatsByRange({ days = 30 } = {}) {
    const { start, end } = resolveRangeWindow(days)
    const alarmsRes = await fetchAllAlarmsByPaging({
      page_size: 2000,
      ordering: '-created_at',
      start_date: formatDateParam(start),
      end_date: formatDateParam(end)
    })
    const list = alarmsRes.collected || []
    const { total, series } = buildDetectTypeSeries(list)
    return { total, series, window: { start, end } }
  },

  async getAlarmHandleRateStatsByRange({ days = 30 } = {}) {
    const { start, end } = resolveRangeWindow(days)
    const alarmsRes = await fetchAllAlarmsByPaging({
      page_size: 2000,
      ordering: '-created_at',
      start_date: formatDateParam(start),
      end_date: formatDateParam(end)
    })
    const list = alarmsRes.collected || []
    const { total, series } = buildHandleRateSeries(list)
    return { total, series, window: { start, end } }
  },

  async getFlightStatsByRange({ days = 30 } = {}) {
    const { start, end } = resolveRangeWindow(days)
    const [dockRes, taskRes] = await Promise.all([
      dockStatusApi.getAllDocks(),
      fetchAllFlightTasksByPaging({
        page_size: 2000,
        ordering: '-created_at',
        start_date: formatDateParam(start),
        end_date: formatDateParam(end)
      })
    ])
    const list = taskRes.collected || []
    const totalTasks = typeof taskRes.totalCount === 'number' ? taskRes.totalCount : list.length
    const byAirport = buildDockTaskStats(dockRes, list)
    return {
      totalTasks,
      byAirport,
      distanceKm: null,
      durationHours: null,
      window: { start, end }
    }
  },
  async getAlertWaylineStats({ days = 30, months = null, topN = 6 } = {}) {
    const now = new Date()
    const end = endOfDay(now)
    const useCalendarMonths = months !== null && months !== undefined && months !== ''
    const start = useCalendarMonths
      ? startOfCalendarMonths(now, months)
      : startOfDay(new Date(now.getTime() - (days - 1) * 24 * 60 * 60 * 1000))

    const [waylinesRes, countRes, alarmsRes] = await Promise.all([
      alarmApi.getWaylines({ page_size: 20000 }),
      alarmApi.getAlarms({ page_size: 1, start_date: formatDateParam(start), end_date: formatDateParam(end) }),
      fetchAllAlarmsByPaging({
        page_size: 2000,
        ordering: '-created_at',
        start_date: formatDateParam(start),
        end_date: formatDateParam(end)
      })
    ])

    const total = getCount(countRes)

    const waylineList = normalizeList(waylinesRes)
    const waylineNameMap = waylineList.reduce((map, item) => {
      const id = item?.wayline_id ?? item?.id
      if (id !== undefined && id !== null) {
        map[id] = item?.name || `航线${id}`
      }
      return map
    }, {})

    const alarms = alarmsRes?.collected || []
    const countByWayline = new Map()

    for (const alarm of alarms) {
      const id = resolveWaylineId(alarm)
      const key = id === undefined || id === null ? '__UNKNOWN__' : id
      countByWayline.set(key, (countByWayline.get(key) || 0) + 1)
    }

    const allSeries = Array.from(countByWayline.entries()).map(([id, value]) => {
      if (id === '__UNKNOWN__') return { id, name: '未知航线', value }
      const mapped = waylineNameMap[id]
      return { id, name: mapped || `航线${id}`, value }
    })

    allSeries.sort((a, b) => b.value - a.value)

    const top = allSeries.slice(0, Math.max(0, topN))
    const rest = allSeries.slice(Math.max(0, topN))
    const restSum = rest.reduce((sum, item) => sum + item.value, 0)

    const series = top.map((item, idx) => ({
      id: item.id,
      name: item.name,
      value: item.value,
      color: SERIES_COLORS[idx % SERIES_COLORS.length]
    }))

    if (restSum > 0) {
      series.push({
        id: '__OTHER__',
        name: '其他',
        value: restSum,
        color: '#94a3b8'
      })
    }

    return {
      total,
      series,
      window: { start, end }
    }
  },

  async getAiDetectionSlides(limit = 6) {
    // 优先告警图片，其次航线图片库（不构造假图片）
    const slides = []
    const alarmRes = await alarmApi.getAlarms({ page_size: 60, ordering: '-created_at' })
    const alarmList = normalizeList(alarmRes)
    for (const item of alarmList) {
      const url = item?.image_signed_url || item?.image_url
      if (!url) continue
      slides.push({
        id: item.id,
        imageUrl: url,
        title: item.content || '异常检测图片',
        createdAt: item.created_at
      })
      if (slides.length >= limit) break
    }
    if (slides.length >= limit) return slides

    const imgRes = await waylineImageApi.getImages({ page_size: 60, ordering: '-created_at' })
    const imgList = normalizeList(imgRes)
    for (const item of imgList) {
      const url = item?.image_url
      if (!url) continue
      slides.push({
        id: item.id,
        imageUrl: url,
        title: item.title || item.description || '巡检图片',
        createdAt: item.created_at
      })
      if (slides.length >= limit) break
    }
    return slides
  },

  async getRecentInspectTasks(limit = 5) {
    const res = await inspectTaskApi.getInspectTasks({ page_size: limit, ordering: '-created_at' })
    return normalizeList(res)
  },

  async getPersonnelSummary(limit = 5) {
    let userInfo = null
    try {
      const raw = localStorage.getItem('userInfo')
      if (raw) userInfo = JSON.parse(raw)
    } catch (e) {
      userInfo = null
    }

    const isAdmin = userInfo?.role === 'admin'
    if (!isAdmin) {
      // 普通用户：只展示当前用户信息
      const me = await authApi.getCurrentUser()
      return { isAdmin: false, total: 1, users: [me] }
    }

    const res = await authApi.getUsers({ page_size: limit, page: 1 })
    const users = normalizeList(res)
    const total = typeof res?.count === 'number' ? res.count : users.length
    return { isAdmin: true, total, users }
  },

  async getSafetyStats() {
    const now = new Date()

    const baselineDate = new Date(2026, 1, 1, 0, 0, 0, 0)
    const safetyDays = calcDiffDays(baselineDate, now)

    const dayMs = 24 * 60 * 60 * 1000
    const rolling30Start = startOfDay(new Date(now.getTime() - (30 - 1) * dayMs))
    const rolling30End = endOfDay(now)

    const [todayAlarms, monthAlarms, yearAlarms] = await Promise.all([
      countAlarmsInRange(startOfDay(now), endOfDay(now)),
      countAlarmsInRange(rolling30Start, rolling30End),
      countAlarmsInRange(startOfYear(now), endOfYear(now))
    ])

    return {
      safetyDays,
      todayAlarms,
      monthAlarms,
      yearAlarms,
      latestAlarmAt: null
    }
  }
}

