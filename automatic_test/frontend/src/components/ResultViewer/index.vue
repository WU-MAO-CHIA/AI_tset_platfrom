<template>
  <div class="result-viewer">
    <div class="summary-bar">
      <span class="badge pass">通過 {{ passed }}</span>
      <span class="badge fail">失敗 {{ failed }}</span>
      <span class="badge total">總計 {{ results.length }}</span>
    </div>

    <div v-for="result in results" :key="result.id" class="result-card" :class="result.status">
      <div class="result-header">
        <span class="case-id">{{ result.test_case_id }}</span>
        <span class="status-badge" :class="result.status">{{ result.status }}</span>
        <span v-if="result.elapsed_ms != null" class="elapsed">{{ result.elapsed_ms }}ms</span>
      </div>

      <div v-if="result.failure_message" class="failure-msg">
        {{ result.failure_message }}
      </div>

      <div v-if="result.media && result.media.length > 0" class="media-list">
        <template v-for="m in result.media" :key="m.file_path">
          <img
            v-if="m.media_type === 'screenshot' && m.file_path"
            :src="`/api/v1/${m.file_path}`"
            class="screenshot-thumb"
            :alt="`Step ${m.step_index}`"
            @click="openImage(`/api/v1/${m.file_path}`)"
          />
        </template>
      </div>
    </div>

    <div v-if="lightboxSrc" class="lightbox" @click="lightboxSrc = null">
      <img :src="lightboxSrc" class="lightbox-img" alt="Screenshot" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { CaseResultItem } from '../../services/executionApi'

const props = defineProps<{ results: CaseResultItem[] }>()

const lightboxSrc = ref<string | null>(null)

const passed = computed(() => props.results.filter((r) => r.status === 'passed').length)
const failed = computed(() => props.results.filter((r) => r.status !== 'passed').length)

function openImage(src: string) {
  lightboxSrc.value = src
}
</script>
