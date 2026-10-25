<template>
  <div class="page">
    <div class="page-header">
      <h1>測試案例管理</h1>
      <RouterLink v-if="authStore.isEditor" to="/cases/new" class="btn-primary">建立案例</RouterLink>
    </div>
    <TestCaseList ref="listRef" @select="onSelect" @edit="onEdit" @delete="onDelete" />

    <div v-if="deleteConfirm" class="modal-overlay" @click.self="deleteConfirm = null">
      <div class="modal" role="alertdialog" aria-modal="true">
        <h2>刪除案例「{{ deleteConfirm.name }}」？</h2>
        <p v-if="!affectedChecklists.length" class="muted">刪除後無法復原。</p>
        <div v-if="affectedChecklists.length" class="warning">
          這個案例還在以下清單中，請先從清單移除再刪除：
          <ul>
            <li v-for="cl in affectedChecklists" :key="cl.id">{{ cl.name }}</li>
          </ul>
        </div>
        <div class="modal-actions" v-if="!affectedChecklists.length">
          <button class="btn-secondary" @click="deleteConfirm = null">取消</button>
          <button class="btn-danger" @click="confirmDelete">刪除</button>
        </div>
        <div v-else class="modal-actions">
          <button class="btn-secondary" @click="deleteConfirm = null">關閉</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, RouterLink } from 'vue-router'
import TestCaseList from '../components/TestCaseList/index.vue'
import { caseApi, type TestCaseSummary } from '../services/caseApi'
import { useAuthStore } from '../stores/authStore'

const authStore = useAuthStore()

const router = useRouter()
const listRef = ref<InstanceType<typeof TestCaseList> | null>(null)
const deleteConfirm = ref<TestCaseSummary | null>(null)
const affectedChecklists = ref<Array<{ id: string; name: string }>>([])

function onSelect(c: TestCaseSummary) {
  router.push(`/cases/${c.id}`)
}

function onEdit(c: TestCaseSummary) {
  router.push(`/cases/${c.id}`)
}

function onDelete(c: TestCaseSummary) {
  deleteConfirm.value = c
  affectedChecklists.value = []
}

async function confirmDelete() {
  if (!deleteConfirm.value) return
  try {
    await caseApi.deleteCase(deleteConfirm.value.id, authStore.username ?? '')
    deleteConfirm.value = null
    listRef.value?.load()
  } catch (e: any) {
    const data = JSON.parse(e.message || '{}')
    affectedChecklists.value = data.affected_checklists || []
  }
}
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; gap: 16px; margin-bottom: 24px; }
.warning { color: var(--fail); }
.warning ul { margin: 8px 0 0 20px; color: var(--ink); }
</style>
