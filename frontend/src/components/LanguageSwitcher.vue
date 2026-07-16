<template>
  <div class="language-switcher" role="group" :aria-label="tr('language.switch')">
    <button
      v-for="option in options"
      :key="option.value"
      type="button"
      :class="{ active: localeStore.locale === option.value }"
      :disabled="saving"
      @click="changeLanguage(option.value)"
    >
      {{ tr(option.key) }}
    </button>
  </div>
</template>

<script setup>
import { useLocaleStore } from '@/stores/locale'
import { t } from '@/utils/i18n'
import { ElMessage } from 'element-plus'
import { ref } from 'vue'

const localeStore = useLocaleStore()
const saving = ref(false)
const options = [
  { value: 'zh', key: 'language.zh' },
  { value: 'en', key: 'language.en' },
]
const tr = (key) => t(key, localeStore.locale)

const changeLanguage = async (locale) => {
  if (saving.value || locale === localeStore.locale) return
  saving.value = true
  try {
    await localeStore.setLocale(locale)
    ElMessage.success(t('language.changed', locale))
  } catch (error) {
    ElMessage.error(tr('language.failed'))
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.language-switcher {
  display: inline-flex;
  align-items: center;
  padding: 3px;
  border: 1px solid #dfe7e2;
  border-radius: 999px;
  background: #f5f8f6;
}

button {
  min-width: 38px;
  padding: 5px 9px;
  border: 0;
  border-radius: 999px;
  color: #66746c;
  background: transparent;
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
}

button.active {
  color: #fff;
  background: #169b62;
  box-shadow: 0 2px 7px rgba(22, 155, 98, 0.22);
}

button:disabled { cursor: wait; }
</style>
