<template>
  <ElSelect
    class="env-select"
    :model-value="modelValue ?? NONE"
    :placeholder="placeholder ?? '選擇執行環境'"
    :disabled="disabled"
    data-testid="env-select"
    @update:model-value="onChange"
  >
    <ElOption v-if="defaultLabel" :value="NONE" :label="defaultLabel" />
    <ElOption v-for="env in options" :key="env.id" :value="env.id" :label="env.name">
      <span class="option">
        <span class="name">{{ env.name }}</span>
        <span class="kind">{{ env.kind === 'windows' ? 'Windows' : 'Linux' }}</span>
        <span class="status" :class="`status-${env.status}`">{{ STATUS_LABEL[env.status] }}</span>
      </span>
    </ElOption>
  </ElSelect>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ElOption, ElSelect } from 'element-plus'
import 'element-plus/es/components/select/style/css'
import 'element-plus/es/components/option/style/css'
import { STATUS_LABEL, type EnvironmentKind, type RunnerEnvironment } from '../../services/runnerEnvironmentApi'

// ElSelect 不能以 null 當選項值，「依各案例設定」以空字串代表
const NONE = ''

const props = defineProps<{
  modelValue: string | null | undefined
  environments: RunnerEnvironment[]
  // 只列出這個類型的環境（例如網頁案例只能選 Linux 容器）
  kind?: EnvironmentKind | null
  // 有值時多一個「不指定」選項，選到時回傳 null
  defaultLabel?: string
  placeholder?: string
  disabled?: boolean
}>()

const emit = defineEmits<{ (e: 'update:modelValue', value: string | null): void }>()

const options = computed(() =>
  props.environments.filter((env) => env.enabled && (!props.kind || env.kind === props.kind)),
)

function onChange(value: string) {
  emit('update:modelValue', value === NONE ? null : value)
}
</script>

<style scoped>
.env-select { min-width: 220px; }
.option { display: flex; align-items: center; gap: 8px; }
.name { flex: 1; }
.kind { color: var(--ink-faint); font-size: var(--fs-12); }
.status { font-size: var(--fs-12); color: var(--ink-muted); }
.status-online, .status-local { color: var(--pass); }
.status-busy { color: var(--running); }
.status-offline, .status-unauthorized { color: var(--fail); }
</style>
