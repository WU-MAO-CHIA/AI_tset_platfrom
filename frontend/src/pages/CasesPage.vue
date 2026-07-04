<template>
  <div class="page">
    <div class="page-header">
      <h1>測試案例管理</h1>
      <RouterLink v-if="authStore.isEditor" to="/cases/new">
        <button class="primary">+ 建立案例</button>
      </RouterLink>
    </div>
    <TestCaseList ref="listRef" @select="onSelect" @edit="onEdit" @delete="onDelete" />

    <div v-if="deleteConfirm" class="modal-overlay">
      <div class="modal">
        <p>確定刪除案例「{{ deleteConfirm.name }}」？</p>
        <div v-if="affectedChecklists.length" class="warning">
          此案例被以下清單引用，無法刪除：
          <ul>
            <li v-for="cl in affectedChecklists" :key="cl.id">{{ cl.name }}</li>
          </ul>
        </div>
        <div class="modal-actions" v-if="!affectedChecklists.length">
          <button @click="confirmDelete">確認刪除</button>
          <button @click="deleteConfirm = null">取消</button>
        </div>
        <button v-else @click="deleteConfirm = null">關閉</button>
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
    await caseApi.deleteCase(deleteConfirm.value.id, 'current_user')
    deleteConfirm.value = null
    listRef.value?.load()
  } catch (e: any) {
    const data = JSON.parse(e.message || '{}')
    affectedChecklists.value = data.affected_checklists || []
  }
}
</script>

<style scoped>
.page { max-width: 1200px; margin: 0 auto; padding: 24px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
h1 { font-size: 22px; }
.primary { background: #4f46e5; color: white; padding: 8px 20px; border: none; border-radius: 4px; cursor: pointer; }
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; }
.modal { background: white; padding: 24px; border-radius: 8px; min-width: 300px; }
.warning { color: #dc2626; margin: 12px 0; }
.modal-actions { display: flex; gap: 12px; margin-top: 16px; }
</style>
