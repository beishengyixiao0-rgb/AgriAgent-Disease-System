<template>
  <section class="video-progress-card" :class="{ failed: progress.status === 'failed' }">
    <div class="progress-header">
      <div class="progress-icon">{{ progress.status === 'failed' ? '!' : '▶' }}</div>
      <div class="progress-title">
        <strong>{{ statusTitle }}</strong>
        <span :title="progress.fileName">{{ progress.fileName || tr('video.task') }}</span>
      </div>
      <span class="status-badge">{{ statusText }}</span>
    </div>

    <div class="progress-track" role="progressbar" :aria-valuenow="displayProgress" aria-valuemin="0" aria-valuemax="100">
      <div
        class="progress-fill"
        :class="{ indeterminate: isIndeterminate }"
        :style="{ width: isIndeterminate ? '36%' : `${displayProgress}%` }"
      />
    </div>

    <div class="progress-meta">
      <span>{{ progress.message || item.content }}</span>
      <strong>{{ displayProgress }}%</strong>
    </div>

    <div class="task-meta">
      <span v-if="formattedSize">{{ tr('video.fileSize', { size: formattedSize }) }}</span>
      <span v-if="progress.taskId">{{ tr('video.taskId', { id: progress.taskId }) }}</span>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { useLocaleStore } from '@/stores/locale'
import { t } from '@/utils/i18n'

const localeStore = useLocaleStore()
const tr = (key, params) => t(key, localeStore.locale, params)

const props = defineProps({
  item: {
    type: Object,
    required: true,
  },
})

const progress = computed(() => props.item.videoProgress || {})
const displayProgress = computed(() => {
  const value = Number(progress.value.progress)
  if (!Number.isFinite(value)) return 0
  return Math.max(0, Math.min(100, Math.round(value)))
})
const statusTitle = computed(() => (
  progress.value.status === 'failed' ? tr('video.failed') : tr('video.processing')
))
const statusText = computed(() => {
  if (progress.value.status === 'failed') return tr('video.statusFailed')
  if (progress.value.status === 'uploading') return tr('video.uploading')
  return tr('video.analyzing')
})
const isIndeterminate = computed(() => (
  displayProgress.value === 0 && progress.value.status !== 'failed'
))
const formattedSize = computed(() => {
  const bytes = Number(progress.value.fileSize)
  if (!Number.isFinite(bytes) || bytes <= 0) return ''
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
})
</script>

<style scoped>
.video-progress-card {
  width: min(100%, 520px);
  padding: 18px;
  border: 1px solid #bbf7d0;
  border-radius: 18px;
  background: linear-gradient(145deg, #ffffff, #f0fdf4);
  box-shadow: 0 6px 20px rgba(22, 101, 52, 0.08);
}

.video-progress-card.failed {
  border-color: #fecaca;
  background: linear-gradient(145deg, #ffffff, #fef2f2);
}

.progress-header {
  display: flex;
  align-items: center;
  gap: 11px;
}

.progress-icon {
  display: grid;
  flex: 0 0 34px;
  height: 34px;
  place-items: center;
  border-radius: 10px;
  background: #16a34a;
  color: white;
  font-size: 13px;
  font-weight: 800;
}

.failed .progress-icon {
  background: #dc2626;
}

.progress-title {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  gap: 3px;
}

.progress-title strong {
  color: #111827;
  font-size: 15px;
}

.progress-title span {
  overflow: hidden;
  color: #6b7280;
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-badge {
  padding: 5px 9px;
  border-radius: 999px;
  background: #dcfce7;
  color: #15803d;
  font-size: 11px;
  font-weight: 700;
}

.failed .status-badge {
  background: #fee2e2;
  color: #b91c1c;
}

.progress-track {
  height: 8px;
  overflow: hidden;
  margin-top: 16px;
  border-radius: 999px;
  background: #e5e7eb;
}

.progress-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #22c55e, #15803d);
  transition: width 0.3s ease;
}

.progress-fill.indeterminate {
  animation: progress-slide 1.3s ease-in-out infinite;
}

@keyframes progress-slide {
  from { transform: translateX(-110%); }
  to { transform: translateX(290%); }
}

.failed .progress-fill {
  background: #ef4444;
}

.progress-meta,
.task-meta {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-top: 9px;
  color: #4b5563;
  font-size: 12px;
}

.progress-meta span {
  min-width: 0;
  overflow-wrap: anywhere;
}

.progress-meta strong {
  flex-shrink: 0;
  color: #166534;
}

.failed .progress-meta strong {
  color: #b91c1c;
}

.task-meta {
  flex-wrap: wrap;
  justify-content: flex-start;
  color: #9ca3af;
  font-size: 11px;
}
</style>
