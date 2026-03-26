#!/usr/bin/env node

const axios = require('axios')

const DEFAULTS = {
  sn: '1581F8HGX255D00A0DK8',
  baseUrl: process.env.API_BASE_URL || process.env.VUE_APP_API_BASE_URL || 'http://127.0.0.1:8000/api/v1',
  token: process.env.API_TOKEN || '',
  count: 60,
  intervalMs: 1000,
  startLongitude: 116.39139,
  startLatitude: 39.9075,
  startAltitude: 85,
  stepLongitude: 0.00008,
  stepLatitude: 0.00004,
  stepAltitude: 0.15,
  batteryStart: 96,
  batteryStep: 0.08,
  headingStart: 0,
  headingStep: 6,
  pitch: -2,
  roll: 1,
  timeoutMs: 10000,
  payloadMode: 'full'
}

function printHelp() {
  console.log(`
用法:
  node scripts/insert-drone-positions.cjs [options]

常用示例:
  node scripts/insert-drone-positions.cjs --token YOUR_TOKEN
  node scripts/insert-drone-positions.cjs --base-url http://127.0.0.1:8000/api/v1 --token YOUR_TOKEN --count 120 --interval-ms 500
  node scripts/insert-drone-positions.cjs --count 0 --interval-ms 1000

参数:
  --sn                 无人机 SN，默认 ${DEFAULTS.sn}
  --base-url           API 基地址，默认 ${DEFAULTS.baseUrl}
  --token              Token 认证，可不传
  --count              发送条数，默认 ${DEFAULTS.count}；传 0 表示持续发送
  --interval-ms        发送间隔毫秒，默认 ${DEFAULTS.intervalMs}
  --start-longitude    起始经度，默认 ${DEFAULTS.startLongitude}
  --start-latitude     起始纬度，默认 ${DEFAULTS.startLatitude}
  --start-altitude     起始高度，默认 ${DEFAULTS.startAltitude}
  --step-longitude     每条经度增量，默认 ${DEFAULTS.stepLongitude}
  --step-latitude      每条纬度增量，默认 ${DEFAULTS.stepLatitude}
  --step-altitude      每条高度增量，默认 ${DEFAULTS.stepAltitude}
  --battery-start      起始电量，默认 ${DEFAULTS.batteryStart}
  --battery-step       每条电量下降值，默认 ${DEFAULTS.batteryStep}
  --heading-start      起始航向角(度)，默认 ${DEFAULTS.headingStart}
  --heading-step       每条航向变化(度)，默认 ${DEFAULTS.headingStep}
  --pitch              俯仰角(度)，默认 ${DEFAULTS.pitch}
  --roll               横滚角(度)，默认 ${DEFAULTS.roll}
  --payload-mode       full 或 raw，默认 ${DEFAULTS.payloadMode}
  --help               显示帮助
`)
}

function parseArgs(argv) {
  const options = { ...DEFAULTS }

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i]

    if (arg === '--help' || arg === '-h') {
      options.help = true
      continue
    }

    if (!arg.startsWith('--')) {
      continue
    }

    const key = arg.slice(2)
    const next = argv[i + 1]

    if (next === undefined || next.startsWith('--')) {
      throw new Error(`参数 ${arg} 缺少值`)
    }

    i += 1

    switch (key) {
      case 'sn':
        options.sn = next
        break
      case 'base-url':
        options.baseUrl = next
        break
      case 'token':
        options.token = next
        break
      case 'count':
        options.count = Number(next)
        break
      case 'interval-ms':
        options.intervalMs = Number(next)
        break
      case 'start-longitude':
        options.startLongitude = Number(next)
        break
      case 'start-latitude':
        options.startLatitude = Number(next)
        break
      case 'start-altitude':
        options.startAltitude = Number(next)
        break
      case 'step-longitude':
        options.stepLongitude = Number(next)
        break
      case 'step-latitude':
        options.stepLatitude = Number(next)
        break
      case 'step-altitude':
        options.stepAltitude = Number(next)
        break
      case 'battery-start':
        options.batteryStart = Number(next)
        break
      case 'battery-step':
        options.batteryStep = Number(next)
        break
      case 'heading-start':
        options.headingStart = Number(next)
        break
      case 'heading-step':
        options.headingStep = Number(next)
        break
      case 'pitch':
        options.pitch = Number(next)
        break
      case 'roll':
        options.roll = Number(next)
        break
      case 'payload-mode':
        options.payloadMode = next
        break
      default:
        throw new Error(`不支持的参数: ${arg}`)
    }
  }

  validateOptions(options)
  return options
}

function validateOptions(options) {
  const numericKeys = [
    'count',
    'intervalMs',
    'startLongitude',
    'startLatitude',
    'startAltitude',
    'stepLongitude',
    'stepLatitude',
    'stepAltitude',
    'batteryStart',
    'batteryStep',
    'headingStart',
    'headingStep',
    'pitch',
    'roll'
  ]

  numericKeys.forEach(key => {
    if (!Number.isFinite(options[key])) {
      throw new Error(`参数 ${key} 不是有效数字`)
    }
  })

  if (!options.sn) {
    throw new Error('sn 不能为空')
  }

  if (options.count < 0) {
    throw new Error('count 不能小于 0')
  }

  if (options.intervalMs <= 0) {
    throw new Error('interval-ms 必须大于 0')
  }

  if (!['full', 'raw'].includes(options.payloadMode)) {
    throw new Error('payload-mode 仅支持 full 或 raw')
  }
}

function normalizeBaseUrl(baseUrl) {
  const trimmed = String(baseUrl || '').trim().replace(/\/+$/, '')
  if (!trimmed) {
    throw new Error('base-url 不能为空')
  }
  return /\/api\/v\d+$/i.test(trimmed) ? trimmed : `${trimmed}/api/v1`
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value))
}

function normalizeHeading(value) {
  const normalized = value % 360
  return normalized < 0 ? normalized + 360 : normalized
}

function buildPayload(options, index) {
  const timestamp = new Date(Date.now() + index * options.intervalMs).toISOString()
  const longitude = Number((options.startLongitude + index * options.stepLongitude).toFixed(7))
  const latitude = Number((options.startLatitude + index * options.stepLatitude).toFixed(7))
  const altitude = Number((options.startAltitude + index * options.stepAltitude).toFixed(2))
  const heading = Number(normalizeHeading(options.headingStart + index * options.headingStep).toFixed(2))
  const pitch = Number(options.pitch.toFixed(2))
  const roll = Number(options.roll.toFixed(2))
  const batteryPercent = Number(clamp(options.batteryStart - index * options.batteryStep, 0, 100).toFixed(1))

  const rawPayload = {
    device_sn: options.sn,
    timestamp,
    longitude,
    latitude,
    altitude,
    height: altitude,
    relative_height: altitude,
    heading,
    yaw: heading,
    attitude_head: heading,
    attitude_pitch: pitch,
    attitude_roll: roll,
    battery_percent: batteryPercent
  }

  if (options.payloadMode === 'raw') {
    return {
      device_sn: options.sn,
      timestamp,
      raw_data: JSON.stringify(rawPayload)
    }
  }

  return {
    device_sn: options.sn,
    timestamp,
    longitude,
    latitude,
    altitude,
    heading,
    pitch,
    roll,
    battery_percent: batteryPercent,
    raw_data: JSON.stringify(rawPayload)
  }
}

async function postPosition(api, payload) {
  const response = await api.post('/drone-positions/', payload)
  return response.data
}

async function main() {
  let options

  try {
    options = parseArgs(process.argv.slice(2))
  } catch (error) {
    console.error(`[参数错误] ${error.message}`)
    printHelp()
    process.exit(1)
  }

  if (options.help) {
    printHelp()
    return
  }

  const baseUrl = normalizeBaseUrl(options.baseUrl)
  const headers = {
    'Content-Type': 'application/json'
  }

  if (options.token) {
    headers.Authorization = `Token ${options.token}`
  }

  const api = axios.create({
    baseURL: baseUrl,
    timeout: options.timeoutMs,
    headers
  })

  const infinite = options.count === 0
  let index = 0

  console.log(`[drone-position] 开始发送位置报文`)
  console.log(`[drone-position] baseUrl=${baseUrl}`)
  console.log(`[drone-position] sn=${options.sn}`)
  console.log(`[drone-position] count=${infinite ? 'infinite' : options.count}, intervalMs=${options.intervalMs}, payloadMode=${options.payloadMode}`)

  while (infinite || index < options.count) {
    const payload = buildPayload(options, index)

    try {
      const result = await postPosition(api, payload)
      console.log(
        `[${index + 1}] ok timestamp=${payload.timestamp} lon=${payload.longitude ?? 'raw'} lat=${payload.latitude ?? 'raw'} alt=${payload.altitude ?? 'raw'} result=${JSON.stringify(result)}`
      )
    } catch (error) {
      const message = error.response
        ? `${error.response.status} ${JSON.stringify(error.response.data)}`
        : error.message
      console.error(`[${index + 1}] failed ${message}`)
    }

    index += 1

    if (infinite || index < options.count) {
      await sleep(options.intervalMs)
    }
  }

  console.log('[drone-position] 发送完成')
}

main().catch(error => {
  console.error('[drone-position] 未处理异常', error)
  process.exit(1)
})
