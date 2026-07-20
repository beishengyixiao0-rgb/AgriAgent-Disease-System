<template>
  <section class="weather-panel" :class="panelRiskClass">
    <div class="weather-heading">
      <div>
        <span class="weather-kicker">{{ copy.kicker }}</span>
        <h4>{{ copy.title }}</h4>
        <p>{{ hasLocation ? locationText : copy.noLocation }}</p>
      </div>
      <span v-if="weatherView.environment_risk_level" class="environment-risk" :class="`environment-${weatherView.environment_risk_level}`">
        <b aria-hidden="true">{{ riskIcon }}</b>
        {{ environmentRiskLabel(weatherView.environment_risk_level) }}
      </span>
    </div>

    <div v-if="weatherView.weather_summary" class="weather-result">
      <div v-if="riskScalePosition !== null" class="risk-scale" :aria-label="environmentRiskLabel(weatherView.environment_risk_level)">
        <div class="risk-track">
          <span :style="{ width: `${riskScalePosition}%` }" />
          <i :style="{ left: `${riskScalePosition}%` }" />
        </div>
        <div class="risk-labels">
          <span v-for="(label, index) in copy.riskScale" :key="label" :class="{ active: index === riskIndex }">{{ label }}</span>
        </div>
      </div>

      <div class="weather-summary">
        <span aria-hidden="true">{{ riskIcon }}</span>
        <strong>{{ weatherView.weather_summary }}</strong>
      </div>

      <div class="weather-metrics">
        <article v-for="metric in metrics" :key="metric.key" class="metric-card" :class="`metric-${metric.tone}`">
          <div class="metric-heading">
            <span aria-hidden="true">{{ metric.icon }}</span>
            <small>{{ metric.label }}</small>
          </div>
          <strong>{{ metric.value }}</strong>
          <div class="metric-track"><i :style="{ width: `${metric.progress}%` }" /></div>
        </article>
      </div>
      <ul v-if="visibleRecommendations.length">
        <li v-for="item in visibleRecommendations" :key="item">{{ item }}</li>
      </ul>
      <small v-if="weatherView.weather_updated_at" class="updated-at">{{ copy.updated }} {{ formatDateTime(weatherView.weather_updated_at) }}</small>
    </div>

    <div v-if="errorMessage" class="location-notice">
      <strong>{{ copy.preciseFailed }}</strong>
      <span>{{ errorMessage }}</span>
    </div>

    <div class="weather-actions">
      <button type="button" class="primary" :disabled="busy" @click="useBrowserPosition">
        {{ busyAction === 'browser' ? copy.locating : (hasLocation ? copy.updateLocation : copy.authorize) }}
      </button>
      <button v-if="hasLocation" type="button" :disabled="busy" @click="refreshWeather">
        {{ busyAction === 'weather' ? copy.refreshing : copy.refresh }}
      </button>
      <button type="button" :disabled="busy" @click="showFallback = !showFallback">
        {{ copy.fallback }}
      </button>
    </div>

    <div v-if="showFallback" class="fallback-panel">
      <div class="fallback-row">
        <div>
          <strong>{{ copy.ipTitle }}</strong>
          <span>{{ copy.ipDesc }}</span>
        </div>
        <button type="button" :disabled="busy" @click="useApproximatePosition">
          {{ busyAction === 'ip' ? copy.locating : copy.useIp }}
        </button>
      </div>

      <form class="manual-form" @submit.prevent="saveManualPosition">
        <strong>{{ copy.manualTitle }}</strong>
        <input v-model.trim="manual.name" type="text" maxlength="255" :placeholder="copy.locationName" />
        <div>
          <input v-model.trim="manual.latitude" inputmode="decimal" :placeholder="copy.latitude" />
          <input v-model.trim="manual.longitude" inputmode="decimal" :placeholder="copy.longitude" />
        </div>
        <button type="submit" :disabled="busy">{{ busyAction === 'manual' ? copy.saving : copy.saveManual }}</button>
      </form>
    </div>
  </section>
</template>

<script setup>
import { getApproximateLocationByIp } from '@/api/weather'
import { refreshTaskWeatherRiskApi, updateTaskLocationApi } from '@/api/history'
import { coordinateLabel, getBrowserLocation } from '@/utils/geolocation'
import { ElMessage } from 'element-plus'
import { computed, reactive, ref } from 'vue'

const props = defineProps({
  task: { type: Object, required: true },
  locale: { type: String, default: 'zh' },
})
const emit = defineEmits(['updated'])

const busyAction = ref('')
const showFallback = ref(false)
const errorMessage = ref('')
const latestWeather = ref({})
const manual = reactive({ name: '', latitude: '', longitude: '' })

const copy = computed(() => props.locale === 'en'
  ? {
      kicker: 'Weather context', title: 'Location and environmental risk', noLocation: 'Add a location to assess weather-related spread risk.', updated: 'Updated',
      authorize: 'Use precise location', updateLocation: 'Update location', locating: 'Locating…', refresh: 'Refresh weather risk', refreshing: 'Refreshing…', fallback: 'Other location options',
      preciseFailed: 'Precise location was not available', ipTitle: 'Approximate network location', ipDesc: 'Less precise. Suitable as a fallback only.', useIp: 'Use approximate location',
      manualTitle: 'Enter coordinates manually', locationName: 'Location name (optional)', latitude: 'Latitude, e.g. 30.52', longitude: 'Longitude, e.g. 114.31', saveManual: 'Save and analyze', saving: 'Saving…',
      invalidCoordinates: 'Enter valid latitude and longitude.', saved: 'Location and weather risk updated', weatherUpdated: 'Weather risk refreshed', unavailable: 'Weather source is temporarily unavailable. The location has still been saved.',
      risks: { low: 'Low environmental risk', moderate: 'Moderate environmental risk', high: 'High environmental risk', critical: 'Critical environmental risk', unavailable: 'Weather unavailable' },
      riskScale: ['Low', 'Moderate', 'High', 'Critical'],
      humidity: 'Avg. humidity', temperature: 'Avg. temp.', precipitationChance: 'Max rain chance', precipitation: '3-day rainfall',
    }
  : {
      kicker: '天气环境', title: '位置与环境风险', noLocation: '补充检测地点后，可结合未来天气判断病害扩散风险。', updated: '更新于',
      authorize: '授权精确定位', updateLocation: '更新位置', locating: '正在定位…', refresh: '重新分析天气', refreshing: '正在分析…', fallback: '其他定位方式',
      preciseFailed: '未能使用精确定位', ipTitle: '使用网络估算位置', ipDesc: '精度较低，仅作为无法授权定位时的降级方案。', useIp: '使用估算位置',
      manualTitle: '手动填写经纬度', locationName: '地点名称（可选）', latitude: '纬度，例如 30.52', longitude: '经度，例如 114.31', saveManual: '保存并分析', saving: '正在保存…',
      invalidCoordinates: '请输入有效的经纬度。', saved: '位置和天气风险已更新', weatherUpdated: '天气风险已刷新', unavailable: '天气源暂不可用，但位置已经保存，可稍后重试。',
      risks: { low: '低环境风险', moderate: '中等环境风险', high: '高环境风险', critical: '严重环境风险', unavailable: '天气不可用' },
      riskScale: ['低风险', '中等', '高风险', '严重'],
      humidity: '平均湿度', temperature: '平均气温', precipitationChance: '最高降雨概率', precipitation: '三日降水量',
    })

const busy = computed(() => Boolean(busyAction.value))
const weatherView = computed(() => ({ ...props.task, ...latestWeather.value }))
const hiddenRecommendations = new Set([
  '结合检测结果和问卷严重程度确定处理优先级。',
  '记录处理日期和复查结果，必要时在历史记录中更新治疗状态。',
])
const visibleRecommendations = computed(() => (weatherView.value.weather_recommendations || [])
  .filter((item) => !hiddenRecommendations.has(String(item).trim())))
const hasLocation = computed(() => Number.isFinite(Number(weatherView.value.latitude)) && Number.isFinite(Number(weatherView.value.longitude)))
const locationText = computed(() => weatherView.value.location_name || coordinateLabel(weatherView.value.latitude, weatherView.value.longitude, props.locale))
const riskLevels = ['low', 'moderate', 'high', 'critical']
const riskIndex = computed(() => riskLevels.indexOf(weatherView.value.environment_risk_level))
const riskScalePosition = computed(() => riskIndex.value < 0 ? null : (riskIndex.value / (riskLevels.length - 1)) * 100)
const panelRiskClass = computed(() => `weather-risk-${weatherView.value.environment_risk_level || 'unavailable'}`)
const riskIcon = computed(() => ({ low: '✓', moderate: '!', high: '⚠', critical: '⚠', unavailable: '—' }[weatherView.value.environment_risk_level] || '—'))

function clamp(value, min = 0, max = 100) {
  return Math.min(max, Math.max(min, value))
}

function metricVisual(key, rawValue) {
  if (rawValue === null || rawValue === undefined || rawValue === '') return { progress: 0, tone: 'muted' }
  const value = Number(rawValue)
  if (!Number.isFinite(value)) return { progress: 0, tone: 'muted' }
  if (key === 'avg_humidity') return { progress: clamp(value), tone: value >= 85 ? 'high' : value >= 75 ? 'moderate' : 'low' }
  if (key === 'avg_temperature') return { progress: clamp(((value + 10) / 50) * 100), tone: 'temperature' }
  if (key === 'max_precipitation_probability') return { progress: clamp(value), tone: value >= 60 ? 'high' : value >= 30 ? 'moderate' : 'low' }
  return { progress: clamp((value / 30) * 100), tone: value >= 20 ? 'high' : value >= 5 ? 'moderate' : 'low' }
}

const metrics = computed(() => {
  const value = weatherView.value.weather_metrics || {}
  return [
    ['avg_humidity', copy.value.humidity, '%', '💧'],
    ['avg_temperature', copy.value.temperature, '°C', '🌡️'],
    ['max_precipitation_probability', copy.value.precipitationChance, '%', '☔'],
    ['total_precipitation', copy.value.precipitation, ' mm', '🌧️'],
  ].map(([key, label, unit, icon]) => {
    const available = value[key] !== undefined && value[key] !== null
    return {
      key,
      label,
      icon,
      value: available ? `${value[key]}${unit}` : '—',
      ...metricVisual(key, available ? value[key] : null),
    }
  })
})

function environmentRiskLabel(value) {
  return copy.value.risks[value] || value
}

function formatDateTime(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return new Intl.DateTimeFormat(props.locale === 'en' ? 'en-US' : 'zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit',
  }).format(date)
}

async function persistLocation(location, source) {
  const response = await updateTaskLocationApi(props.task.id, {
    latitude: Number(location.latitude),
    longitude: Number(location.longitude),
    location_name: location.city || location.name || coordinateLabel(location.latitude, location.longitude, props.locale),
    location_source: source,
  })
  latestWeather.value = response || {}
  emit('updated', response)
  ElMessage.success(copy.value.saved)
  if (response?.environment_risk_level === 'unavailable') ElMessage.warning(copy.value.unavailable)
}

async function useBrowserPosition() {
  busyAction.value = 'browser'
  errorMessage.value = ''
  try {
    const location = await getBrowserLocation()
    await persistLocation(location, 'browser')
  } catch (error) {
    errorMessage.value = error?.message || String(error)
    showFallback.value = true
  } finally {
    busyAction.value = ''
  }
}

async function useApproximatePosition() {
  busyAction.value = 'ip'
  errorMessage.value = ''
  try {
    await persistLocation(await getApproximateLocationByIp(), 'other')
  } catch (error) {
    errorMessage.value = error?.message || String(error)
  } finally {
    busyAction.value = ''
  }
}

async function saveManualPosition() {
  const latitude = Number(manual.latitude)
  const longitude = Number(manual.longitude)
  if (!Number.isFinite(latitude) || !Number.isFinite(longitude) || latitude < -90 || latitude > 90 || longitude < -180 || longitude > 180) {
    ElMessage.warning(copy.value.invalidCoordinates)
    return
  }
  busyAction.value = 'manual'
  errorMessage.value = ''
  try {
    await persistLocation({ latitude, longitude, name: manual.name }, 'manual')
  } catch (error) {
    errorMessage.value = error?.response?.data?.detail || error?.message || String(error)
  } finally {
    busyAction.value = ''
  }
}

async function refreshWeather() {
  busyAction.value = 'weather'
  errorMessage.value = ''
  try {
    const response = await refreshTaskWeatherRiskApi(props.task.id)
    latestWeather.value = response || {}
    emit('updated', response)
    ElMessage.success(copy.value.weatherUpdated)
    if (response?.environment_risk_level === 'unavailable') ElMessage.warning(copy.value.unavailable)
  } catch (error) {
    errorMessage.value = error?.response?.data?.detail || error?.message || String(error)
  } finally {
    busyAction.value = ''
  }
}
</script>

<style scoped>
.weather-panel { --risk-color: #7c8780; margin-top: 18px; padding: 16px; border: 1px solid #dbe8df; border-radius: 15px; background: linear-gradient(145deg, #f8fcf9, #fff); transition: border-color .2s ease, background .2s ease; }
.weather-risk-low { --risk-color: #1b9a57; background: linear-gradient(145deg, #f2fbf5, #fff 62%); }
.weather-risk-moderate { --risk-color: #d79a22; background: linear-gradient(145deg, #fffaf0, #fff 62%); }
.weather-risk-high { --risk-color: #e46d25; background: linear-gradient(145deg, #fff6ef, #fff 62%); }
.weather-risk-critical { --risk-color: #dc3f3f; background: linear-gradient(145deg, #fff3f3, #fff 62%); }
.weather-risk-unavailable { --risk-color: #8a948e; }
.weather-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 14px; }
.weather-kicker { display: block; margin-bottom: 4px; color: #277a49; font-size: 11px; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }
.weather-heading h4 { margin: 0; color: #26372d; font-size: 15px; }
.weather-heading p { margin: 4px 0 0; color: #7b887f; font-size: 13px; }
.environment-risk { display: inline-flex; align-items: center; gap: 6px; padding: 5px 9px; border-radius: 999px; white-space: nowrap; font-size: 11px; font-weight: 800; }
.environment-risk b { display: grid; width: 17px; height: 17px; place-items: center; border-radius: 50%; background: rgba(255, 255, 255, .72); font-size: 10px; }
.environment-low { background: #e9f8ef; color: #18854b; }
.environment-moderate { background: #fff6e3; color: #ad730d; }
.environment-high { background: #fff0e7; color: #c45118; }
.environment-critical { background: #fff0f0; color: #c93636; }
.environment-unavailable { background: #f1f3f2; color: #737d77; }
.weather-result { margin-top: 13px; padding: 12px; border-radius: 12px; background: #fff; border: 1px solid #e3ebe5; }
.risk-scale { margin: 3px 4px 15px; }
.risk-track { position: relative; height: 7px; border-radius: 999px; background: linear-gradient(90deg, #ccefd8 0 25%, #f8dda0 25% 50%, #f7b685 50% 75%, #efa0a0 75% 100%); }
.risk-track > span { position: absolute; inset: 0 auto 0 0; border-radius: inherit; background: color-mix(in srgb, var(--risk-color) 70%, transparent); }
.risk-track > i { position: absolute; top: 50%; width: 14px; height: 14px; border: 3px solid #fff; border-radius: 50%; background: var(--risk-color); box-shadow: 0 1px 6px rgba(32, 50, 39, .24); transform: translate(-50%, -50%); }
.risk-labels { display: grid; grid-template-columns: repeat(4, 1fr); margin-top: 7px; color: #8a948e; font-size: 10px; }
.risk-labels span { text-align: center; }
.risk-labels span:first-child { text-align: left; }
.risk-labels span:last-child { text-align: right; }
.risk-labels span.active { color: var(--risk-color); font-weight: 800; }
.weather-summary { display: flex; align-items: flex-start; gap: 9px; padding: 10px 12px; border-radius: 10px; background: color-mix(in srgb, var(--risk-color) 8%, white); color: #34443a; }
.weather-summary > span { display: grid; width: 23px; height: 23px; flex: 0 0 23px; place-items: center; border-radius: 7px; background: var(--risk-color); color: #fff; font-size: 11px; font-weight: 900; }
.weather-summary strong { font-size: 13px; line-height: 1.65; }
.weather-result ul { margin: 9px 0 0; padding-left: 19px; color: #58655d; font-size: 13px; line-height: 1.65; }
.weather-metrics { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; margin-top: 11px; }
.metric-card { --metric-color: #87928b; min-width: 0; padding: 10px; border: 1px solid #e5ebe7; border-radius: 10px; background: #fafcfb; }
.metric-low { --metric-color: #28a662; }
.metric-moderate { --metric-color: #d79a22; }
.metric-high { --metric-color: #df5d35; }
.metric-temperature { --metric-color: #3786cf; }
.metric-muted { --metric-color: #a7afaa; }
.metric-heading { display: flex; align-items: center; gap: 5px; min-width: 0; }
.metric-heading > span { font-size: 14px; }
.metric-heading small { overflow: hidden; color: #7c8880; font-size: 9px; font-weight: 600; text-overflow: ellipsis; white-space: nowrap; }
.metric-card > strong { display: block; margin: 6px 0 8px; color: #2f3e35; font-size: 14px; }
.metric-track { height: 4px; overflow: hidden; border-radius: 999px; background: #e9eeeb; }
.metric-track i { display: block; height: 100%; border-radius: inherit; background: var(--metric-color); transition: width .35s ease; }
.updated-at { display: block; margin-top: 8px; color: #909991; font-size: 11px; }
.location-notice { display: flex; flex-direction: column; gap: 3px; margin-top: 11px; padding: 9px 11px; border-radius: 10px; background: #fff8e8; color: #8d650f; font-size: 12px; }
.weather-actions { display: flex; flex-wrap: wrap; gap: 7px; margin-top: 13px; }
.weather-actions button, .fallback-panel button { border: 1px solid #dce5df; border-radius: 9px; padding: 7px 10px; background: #fff; color: #536158; font-size: 12px; cursor: pointer; }
.weather-actions button.primary { border-color: #1b8a50; background: #1b8a50; color: #fff; }
button:disabled { opacity: .55; cursor: wait; }
.fallback-panel { margin-top: 11px; padding-top: 11px; border-top: 1px solid #e8ede9; }
.fallback-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.fallback-row strong, .fallback-row span { display: block; }
.fallback-row strong, .manual-form > strong { color: #405047; font-size: 13px; }
.fallback-row span { margin-top: 3px; color: #89938c; font-size: 11px; }
.manual-form { display: grid; gap: 7px; margin-top: 12px; }
.manual-form > div { display: grid; grid-template-columns: 1fr 1fr; gap: 7px; }
.manual-form input { box-sizing: border-box; width: 100%; min-width: 0; padding: 8px 9px; border: 1px solid #dce4df; border-radius: 9px; outline: none; color: #34443a; font-size: 12px; }
.manual-form input:focus { border-color: #8cc8a0; }
.manual-form button { justify-self: start; border-color: #b8d9c3; color: #187744; }
@media (max-width: 620px) {
  .weather-heading, .fallback-row { align-items: flex-start; flex-direction: column; }
  .weather-metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .manual-form > div { grid-template-columns: 1fr; }
}
</style>
