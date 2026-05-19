<template>
  <div class="checklists-page">
    <div class="page-header">
      <h1>測試清單</h1>
      <button class="btn-primary" @click="showCreate = true">建立清單</button>
    </div>

    <div v-if="loading" class="loading">載入中...</div>

    <div v-else-if="checklists.length === 0" class="empty-state">
      <p>尚無測試清單</p>
    </div>

    <ul v-else class="checklist-list">
      <li
        v-for="cl in checklists"
        :key="cl.id"
        class="checklist-item"
        @click="$router.push(`/checklists/${cl.id}`)"
      >
        <div class="cl-name">{{ cl.name }}</div>
        <div class="cl-meta">建立者：{{ cl.created_by }}</div>
      </li>
    </ul>

    <div class="pagination" v-if="total > pageSize">
      <button :disabled="page <= 1" @click="page--">上一頁</button>
      <span>第 {{ page }} 頁 / 共 {{ Math.ceil(total / pageSize) }} 頁</span>
      <button :disabled="page * pageSize >= total" @click="page++">下一頁</button>
    </div>

    <div v-if="showCreate" class="modal-overlay" @click.self="showCreate = false">
      <div class="modal">
        <h2>建立測試清單</h2>
        <label>清單名稱</label>
        <input v-model="newName" placeholder="Sprint 1 Tests" />
        <label>建立者</label>
        <input v-model="newCreatedBy" placeholder="tester" />
        <div class="modal-actions">
          <button class="btn-secondary" @click="showCreate = false">取消</button>
          <button class="btn-primary" :disabled="!newName" @click="handleCreate">建立</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { listChecklists, createChecklist, type Checklist } from '../services/checklistApi'
import { useRouter } from 'vue-router'

const router = useRouter()

const checklists = ref<Checklist[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const loading = ref(false)

const showCreate = ref(false)
const newName = ref('')
const newCreatedBy = ref('')

async function fetchChecklists() {
  loading.value = true
  try {
    const data = await listChecklists(page.value, pageSize)
    checklists.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  if (!newName.value) return
  await createChecklist({ name: newName.value, created_by: newCreatedBy.value, case_ids: [] })
  newName.value = ''
  newCreatedBy.value = ''
  showCreate.value = false
  await fetchChecklists()
}

watch(page, fetchChecklists)
onMounted(fetchChecklists)
</script>
