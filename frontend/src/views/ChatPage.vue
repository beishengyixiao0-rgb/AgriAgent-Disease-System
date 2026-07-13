<template>
  <div class="chat-page">
    <aside class="sidebar">
      <router-link to="/" class="brand">
        🌿 AgriAgent
      </router-link>

      <button
        class="new-chat"
        @click="startNewDiagnosis"
      >
        + New Diagnosis
      </button>

      <div class="sidebar-section-title">Recent Diagnoses</div>

      <div class="session-list">
        <div
          v-for="(session,index) in sessions"
          :key="index"
          class="session-item"
        >
          {{ session }}
        </div>
      </div>
      <div class="sidebar-bottom">
        <div class="sidebar-section-title">Navigation</div>

        <router-link to="/ai-chat" class="nav-item" active-class="nav-item-active">
          🤖 AI Diagnosis
        </router-link>

        <router-link to="/data-analysis" class="nav-item" active-class="nav-item-active">
          📊 Data Analysis
        </router-link>

        <router-link to="/history" class="nav-item" active-class="nav-item-active">
          🕒 History Analysis
        </router-link>
      </div>
    </aside>

    <main class="main-area">
      <header class="topbar">
        <span>Plant Disease Diagnosis</span>
        <span class="model-status">🟢 Model Ready</span>
      </header>

      <div class="messages">
        <div v-if="messages.length === 0" class="welcome-panel">
          <div class="welcome-icon">🌿</div>

          <h1>Plant Disease Diagnosis</h1>

          <p class="welcome-desc">
            Upload a photo or describe your plant symptoms<br>
            to get instant AI diagnosis and treatment recommendations.
          </p>

          <div class="suggestions-grid">
            <div
              class="suggestion-card"
              @click="useSuggestion('What disease is affecting my tomato leaf?')"
            >
              What disease is affecting my tomato leaf?
            </div>

            <div
              class="suggestion-card"
              @click="useSuggestion('How to treat grape black rot?')"
            >
              How to treat grape black rot?
            </div>

            <div
              class="suggestion-card"
              @click="useSuggestion('Why are my pepper leaves turning yellow?')"
            >
              Why are my pepper leaves turning yellow?
            </div>

            <div
              class="suggestion-card"
              @click="useSuggestion('Identify disease in my strawberry plant.')"
            >
              Identify disease in my strawberry plant.
            </div>
          </div>

          <button class="upload-btn" @click="openFilePicker">
            📷 Upload plant image
          </button>
        </div>
        <div v-else class="chat-messages">
          <div
            v-for="(item, index) in messages"
            :key="index"
            :class="['message-row', item.role]"
          >
            <div class="message-avatar">
              {{ item.role === 'assistant' ? '🌿' : 'You' }}
            </div>

            <div v-if="item.type === 'image'" class="image-message">
              <img :src="item.imageUrl" class="chat-image" alt="uploaded image" />
            </div>

            <DiagnosisCard
              v-else-if="item.type === 'diagnosis'"
              :item="item"
            />

            <div v-else class="message-bubble">
              {{ item.content }}
            </div>
          </div>
          <div ref="messageEndRef" class="message-end-anchor"></div>
        </div>
      </div>

      <div class="chat-footer">
        <input
          ref="fileInput"
          type="file"
          accept="image/*"
          style="display:none"
          @change="handleImageUpload"
        />

        <div v-if="selectedImage" class="image-preview-bar">
          <img :src="selectedImage" class="preview-image" alt="preview" />
          <span>Image ready for diagnosis</span>
        </div>

        <div class="input-wrapper">
          <button class="image-btn" @click="openFilePicker">📷</button>

          <textarea
            v-model="message"
            placeholder="Describe symptoms or upload a plant photo..."
            @keydown.enter.exact.prevent="sendMessage"
          />

          <button class="send-btn" @click="sendMessage">
            ➤
          </button>
        </div>

        <div class="input-tip">
          Press Enter to send • Supports JPEG, PNG, WebP
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { nextTick, ref } from 'vue'

import DiagnosisCard from '@/components/DiagnosisCard.vue'

const message = ref('')
const messages = ref([])

const fileInput = ref(null)
const selectedImage = ref('')

const messageEndRef = ref(null)

const scrollToBottom = async () => {
  await nextTick()

  messageEndRef.value?.scrollIntoView({
    behavior: 'smooth',
    block: 'end',
  })
}

const openFilePicker = () => {
  fileInput.value?.click()
}

const handleImageUpload = (event) => {
  const file = event.target.files?.[0]

  if (!file) return

  selectedImage.value = URL.createObjectURL(file)

  messages.value.push({
    role: 'user',
    type: 'image',
    imageUrl: selectedImage.value,
    content: file.name,
  })

  scrollToBottom()

  window.setTimeout(() => {
    messages.value.push({
      role: 'assistant',
      type: 'diagnosis',
      disease: 'Tomato Late Blight',
      plant: 'Tomato',
      severity: 'High',
      confidence: 94.2,
      annotatedImage: selectedImage.value,
      description:
        'The uploaded image shows symptoms consistent with Tomato Late Blight, including dark lesions and leaf deterioration.',
      treatments: [
        'Remove infected leaves',
        'Apply fungicide treatment',
        'Improve air circulation',
      ],
    })
    scrollToBottom()
    selectedImage.value = ''
  }, 600)
}

const sendMessage = () => {
  const content = message.value.trim()

  if (!content) return

  messages.value.push({
    role: 'user',
    content,
  })

  scrollToBottom()

  message.value = ''

  window.setTimeout(() => {
    messages.value.push({
      role: 'assistant',
      content: 'Thanks for the details. Please upload a clear image of the affected leaf so I can provide a more accurate diagnosis.',
    })
    scrollToBottom()
  }, 600)
}

const useSuggestion = (text) => {
  message.value = text
  sendMessage()
}

const startNewDiagnosis = () => {
  messages.value = []
  selectedImage.value = ''
  message.value = ''
}

const sessions = ref([
  'Tomato leaf disease',
  'Grape black rot',
  'Pepper diagnosis'
])

</script>

<style scoped>
.chat-page {
  display: flex;
  height: 100vh;
  background: #fafafa;
}

.sidebar {
  width: 260px;
  background: white;
  border-right: 1px solid #e5e7eb;
  padding: 20px;
  display: flex;
  flex-direction: column;
  height: 100vh;
  box-shadow: 2px 0 12px rgba(0,0,0,0.04);
}

.brand {
  font-size: 20px;
  font-weight: 700;
  color: #16a34a;
  margin-bottom: 24px;
  text-decoration: none;
  display: block;
}

.new-chat {
  background: #16a34a;
  color: white;
  border: none;
  border-radius: 10px;
  padding: 12px;
  cursor: pointer;
  margin-bottom: 24px;
  font-weight: 600;
  transition: all 0.2s ease;
}

.new-chat:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(22,163,74,0.25);
}

.session-list {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.session-item {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 14px;
  margin-bottom: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  background: #ffffff;
}

.session-item:hover {
  background: #f9fafb;
  border-color: #16a34a;
}

.sidebar-bottom {
  margin-top: auto;
  padding-top: 24px;
  border-top: 1px solid #e5e7eb;
}

.sidebar-section-title {
  font-size: 12px;
  font-weight: 700;
  color: #9ca3af;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 12px;
}

.nav-item {
  display: block;
  text-decoration: none;
  padding: 12px 14px;
  border-radius: 10px;
  color: #374151;
  margin-bottom: 8px;
  transition: all 0.2s ease;
  font-weight: 500;
}

.nav-item:hover {
  background: #f3f4f6;
}

.nav-item-active {
  background: #ecfdf5;
  color: #16a34a;
  font-weight: 600;
  border: 1px solid #bbf7d0;
}

.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.topbar {
  padding: 18px 24px;
  border-bottom: 1px solid #e5e7eb;
  font-weight: 600;
  background: white;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.model-status {
  font-size: 13px;
  color: #6b7280;
  font-weight: 600;
}

.messages {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 40px;
}

.welcome-panel {
  width: 100%;
  max-width: 820px;
  min-height: 100%;
  margin: auto;
  text-align: center;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.welcome-icon {
  font-size: 72px;
  margin-bottom: 20px;
}

.welcome-panel h1 {
  font-size: 42px;
  margin-bottom: 16px;
  color: #1f2937;
}

.welcome-desc {
  color: #6b7280;
  font-size: 18px;
  line-height: 1.7;
  margin-bottom: 36px;
}

.suggestions-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 32px;
}

.suggestion-card {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 16px;
  padding: 18px;
  text-align: left;
  cursor: pointer;
  transition: all 0.2s ease;
}

.suggestion-card:hover {
  transform: translateY(-2px);
  border-color: #16a34a;
}

.upload-btn {
  border: 1px solid #16a34a;
  color: #16a34a;
  background: white;
  border-radius: 14px;
  padding: 14px 24px;
  font-size: 16px;
  cursor: pointer;
}

.chat-footer {
  padding: 18px 24px;
  border-top: 1px solid #e5e7eb;
  background: white;
}

.input-wrapper {
  display: flex;
  align-items: center;
  gap: 12px;
  border: 1px solid #e5e7eb;
  border-radius: 22px;
  padding: 12px 16px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.05);
}

.image-btn {
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 22px;
}

.input-wrapper textarea {
  flex: 1;
  border: none;
  resize: none;
  outline: none;
  min-height: 30px;
  font-size: 15px;
}

.input-wrapper .send-btn {
  width: 46px;
  height: 46px;
  border-radius: 50%;
  border: none;
  background: #16a34a;
  color: white;
  cursor: pointer;
}

.input-tip {
  text-align: center;
  margin-top: 10px;
  font-size: 13px;
  color: #9ca3af;
}

.chat-messages {
  width: 100%;
  max-width: 900px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding-bottom: 40px;
}

.message-end-anchor {
  width: 100%;
  height: 1px;
  flex-shrink: 0;
}

.message-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.message-row.user {
  flex-direction: row-reverse;
}

.message-avatar {
  width: 42px;
  height: 42px;
  flex-shrink: 0;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #ecfdf5;
  color: #15803d;
  font-size: 13px;
  font-weight: 700;
}

.message-row.user .message-avatar {
  background: #f3f4f6;
  color: #374151;
}

.message-bubble {
  max-width: 70%;
  padding: 14px 18px;
  border: 1px solid #e5e7eb;
  border-radius: 18px;
  background: white;
  color: #374151;
  line-height: 1.6;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.04);
}

.message-row.user .message-bubble {
  background: #16a34a;
  border-color: #16a34a;
  color: white;
}

.image-preview-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  padding: 10px 14px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #f9fafb;
}

.preview-image {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  object-fit: cover;
  border: 1px solid #e5e7eb;
}

.image-message {
  max-width: 420px;
  padding: 8px;
  background: white;
  border-radius: 18px;
  border: 1px solid #e5e7eb;
  box-shadow: 0 2px 10px rgba(0,0,0,.04);
}

.chat-image {
  width: 100%;
  border-radius: 16px;
  border: 1px solid #e5e7eb;
}

.input-wrapper textarea {
  max-height: 120px;
  overflow-y: auto;
}

</style>
