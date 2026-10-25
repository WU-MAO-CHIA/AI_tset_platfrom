<template>
  <div v-if="state.open" class="modal-overlay" @click.self="answer(false)" @keydown.esc="answer(false)">
    <div class="modal" role="alertdialog" aria-modal="true" :aria-labelledby="titleId">
      <h2 :id="titleId">{{ state.title }}</h2>
      <p v-if="state.message" class="message">{{ state.message }}</p>
      <div class="modal-actions">
        <button ref="cancelBtn" class="btn-secondary" @click="answer(false)">取消</button>
        <button :class="state.danger ? 'btn-danger' : 'btn-primary'" @click="answer(true)">{{ state.confirmLabel }}</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { confirmState as state, resolveConfirm as answer } from '../../composables/useConfirm'

const titleId = 'confirm-dialog-title'
const cancelBtn = ref<HTMLButtonElement | null>(null)

// 開啟時把焦點放在「取消」，避免誤按 Enter 直接執行破壞性動作
watch(
  () => state.open,
  async (open) => {
    if (open) {
      await nextTick()
      cancelBtn.value?.focus()
    }
  },
)
</script>

<style scoped>
.message { color: var(--ink-muted); white-space: pre-line; }
</style>
