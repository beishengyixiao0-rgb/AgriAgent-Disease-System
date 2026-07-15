<template>
  <div class="weather-badge" :class="{ loading: status === 'loading' }" :title="badgeTitle">
    <template v-if="status === 'success'">
      <span class="weather-icon">{{ weather.icon }}</span>
      <span>{{ weather.city }}</span>
      <i />
      <strong>{{ weather.temperature }}°C</strong>
      <i />
      <span>{{ weather.weatherText }}</span>
    </template>

    <template v-else-if="status === 'loading'">
      <span class="weather-icon">🌦️</span>
      <span>正在获取当地天气…</span>
    </template>

    <template v-else>
      <span class="weather-icon">🌿</span>
      <span>AgriAgent 智慧农业</span>
    </template>
  </div>
</template>

<script setup>
import { getCurrentWeather } from '@/api/weather'
import { computed, onMounted, ref } from 'vue'

const status = ref('loading')
const weather = ref({})

const badgeTitle = computed(() => {
  if (status.value !== 'success') return ''
  return `天气更新时间：${new Date(weather.value.updatedAt).toLocaleString('zh-CN')}`
})

onMounted(async () => {
  try {
    weather.value = await getCurrentWeather()
    status.value = 'success'
  } catch (error) {
    console.warn('[首页天气获取失败]', error)
    status.value = 'error'
  }
})
</script>

<style scoped>
.weather-badge {
  display: inline-flex;
  min-height: 34px;
  align-items: center;
  gap: 7px;
  padding: 7px 14px;
  border: 1px solid #d1fae5;
  border-radius: 999px;
  background: #ecfdf5;
  color: #15803d;
  font-size: 12px;
  font-weight: 600;
  box-shadow: 0 5px 16px rgba(22, 101, 52, 0.06);
}

.weather-badge i {
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: #86efac;
}

.weather-icon {
  font-size: 15px;
}

.weather-badge.loading {
  color: #4b7c5a;
}

.weather-badge.loading .weather-icon {
  animation: weather-pulse 1.4s ease-in-out infinite;
}

@keyframes weather-pulse {
  50% { opacity: 0.45; transform: translateY(-1px); }
}
</style>
