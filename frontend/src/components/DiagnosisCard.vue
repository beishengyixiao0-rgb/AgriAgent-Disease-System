<template>
  <div class="diagnosis-card">
    <div class="diagnosis-header">
      <div>
        <div class="diagnosis-label">Detected Disease</div>
        <h3>{{ item.disease }}</h3>
        <p>{{ item.plant }}</p>
      </div>

      <div class="severity-badge">
        {{ item.severity }}
      </div>
    </div>

    <div class="confidence-section">
      <div class="confidence-row">
        <span>Confidence</span>
        <strong>{{ item.confidence }}%</strong>
      </div>

      <div class="progress-bar">
        <div
          class="progress-fill"
          :style="{ width: item.confidence + '%' }"
        />
      </div>
    </div>

    <div v-if="item.annotatedImage" class="diagnosis-image-section">
      <img
        :src="item.annotatedImage"
        class="diagnosis-image"
        alt="detection result"
      />
    </div>

    <div class="diagnosis-description">
      {{ item.description }}
    </div>

    <div class="treatment-list">
      <div
        v-for="(treatment, idx) in item.treatments"
        :key="idx"
        class="treatment-item"
      >
        ✓ {{ treatment }}
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  item: {
    type: Object,
    required: true,
  },
})
</script>

<style scoped>
/* 把 ChatPage.vue 中 diagnosis-card 相关 CSS 全部剪切到这里 */
.diagnosis-card {
  width: 100%;
  max-width: 520px;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 20px;
  padding: 20px;
  box-shadow: 0 6px 20px rgba(0,0,0,0.06);
}

.diagnosis-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 18px;
}

.diagnosis-label {
  color: #6b7280;
  font-size: 13px;
}

.diagnosis-header h3 {
  margin: 4px 0;
  color: #111827;
}

.diagnosis-header p {
  color: #6b7280;
}

.severity-badge {
  background: #fef2f2;
  color: #dc2626;
  padding: 8px 14px;
  border-radius: 999px;
  height: fit-content;
}

.confidence-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.progress-bar {
  height: 10px;
  background: #e5e7eb;
  border-radius: 999px;
  overflow: hidden;
  margin-bottom: 18px;
}

.progress-fill {
  height: 100%;
  background: #16a34a;
}

.diagnosis-description {
  line-height: 1.7;
  margin-bottom: 18px;
  color: #374151;
}

.treatment-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.treatment-item {
  background: #f0fdf4;
  color: #166534;
  padding: 10px 12px;
  border-radius: 10px;
}

.diagnosis-image-section {
  margin-bottom: 18px;
}

.diagnosis-image {
  width: 100%;
  border-radius: 14px;
  border: 1px solid #e5e7eb;
}
</style>
