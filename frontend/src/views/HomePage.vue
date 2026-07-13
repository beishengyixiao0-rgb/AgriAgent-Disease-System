<template>
  <div class="home-page">
    <header class="navbar">
      <div class="logo">
        🌿 <span>AgriAgent</span>
      </div>

      <div class="nav-links">
        <button @click="go('/ai-chat')">AI Agent</button>
        <button @click="go('/data-analysis')">Analytics</button>
        <button @click="go('/history')">History</button>
      </div>
    </header>

    <main class="hero">
      <div class="badge">YOLOv11 + LLM</div>

      <h1>
        Agri<span>Agent</span>
      </h1>

      <p class="subtitle">
        AI-Powered Fruit and Vegetable Disease Diagnosis Assistant
      </p>

      <div class="card-grid">
        <div class="entry-card" @click="go('/ai-chat')">
          <div class="icon">🤖</div>
          <h2>AI Agent</h2>
          <p>
            Upload plant images for instant disease diagnosis and treatment recommendations.
          </p>
        </div>

        <div class="entry-card" @click="go('/data-analysis')">
          <div class="icon">📊</div>
          <h2>Data Analytics</h2>
          <p>
            Explore disease patterns, detection trends, and model performance metrics.
          </p>
        </div>
      </div>

      <button class="history-btn" @click="go('/history')">
        View Detection History →
      </button>

      <div class="features">
        <span>⚡ Real-time Detection</span>
        <span>🛡️ 94.2% Accuracy</span>
        <span>📈 35+ Disease Classes</span>
        <span>🌱 Fruits & Vegetables</span>
      </div>
    </main>

    <footer>
      AgriAgent © 2026 — Smart Farming with Conversational AI
    </footer>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router';

const router = useRouter()

const go = (path) => {
  router.push(path)
}
</script>

<style scoped>
.home-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #fafafa;
}

.navbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 40px;
  border-bottom: 1px solid #e5e7eb;
}

.logo {
  font-size: 20px;
  font-weight: 700;
}

.nav-links {
  display: flex;
  gap: 12px;
}

.nav-links button {
  border: none;
  background: transparent;
  cursor: pointer;
}

.hero {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 40px 20px;
}

.badge {
  background: #ecfdf5;
  color: #15803d;
  border-radius: 999px;
  padding: 8px 16px;
  font-size: 12px;
  font-weight: 600;
}

h1 {
  font-size: 72px;
  margin: 24px 0 12px;
}

h1 span {
  color: #16a34a;
}

.subtitle {
  color: #6b7280;
  font-size: 20px;
  margin-bottom: 40px;
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 20px;
  width: 100%;
  max-width: 900px;
}

.entry-card {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 20px;
  padding: 24px;
  text-align: left;
  cursor: pointer;
  transition: 0.2s;
}

.entry-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 10px 25px rgba(0,0,0,0.08);
}

.icon {
  font-size: 28px;
  margin-bottom: 12px;
}

.history-btn {
  margin-top: 30px;
  border: none;
  background: transparent;
  cursor: pointer;
  color: #6b7280;
}

.features {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 12px;
  margin-top: 40px;
}

.features span {
  background: #f3f4f6;
  padding: 8px 14px;
  border-radius: 999px;
  font-size: 13px;
}

footer {
  border-top: 1px solid #e5e7eb;
  text-align: center;
  padding: 20px;
  color: #6b7280;
  font-size: 13px;
}
</style>