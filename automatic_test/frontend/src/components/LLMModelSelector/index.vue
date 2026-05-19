<template>
  <div class="llm-model-selector">
    <label>AI 模型</label>
    <select :value="modelValue" @change="emit('update:modelValue', ($event.target as HTMLSelectElement).value)" :disabled="loading">
      <option v-if="loading" value="">載入中...</option>
      <option v-for="model in models" :key="model.id" :value="model.id">
        {{ model.name }}
        <template v-if="model.requires_setup"> (需設定 API Key)</template>
      </option>
    </select>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import apiClient from '../../services/apiClient'

interface LLMModel {
  id: string
  name: string
  provider: string
  requires_setup?: boolean
}

defineProps<{ modelValue: string }>()
const emit = defineEmits<{ (e: 'update:modelValue', value: string): void }>()

const models = ref<LLMModel[]>([])
const loading = ref(false)

onMounted(async () => {
  loading.value = true
  try {
    const res = await apiClient.get<{ models: LLMModel[]; default: string }>('/llm-models')
    models.value = res.data.models
  } finally {
    loading.value = false
  }
})
</script>
