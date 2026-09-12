<template>
  <div class="rf-editor" ref="editorContainer" data-testid="rf-editor"></div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as monaco from 'monaco-editor'
import loader from '@monaco-editor/loader'

const props = defineProps<{
  modelValue: string
  readOnly?: boolean
  language?: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

const editorContainer = ref<HTMLElement | null>(null)
let editor: monaco.editor.IStandaloneCodeEditor | null = null
let isEditorReady = false
let ignoreModelChange = false

const language = computed(() => props.language || 'robotframework')

/** Register Robot Framework language with Monaco */
async function registerRobotFrameworkLanguage() {
  if (monaco.languages.getLanguages().some(l => l.id === 'robotframework')) {
    return
  }

  monaco.languages.register({ id: 'robotframework' })

  monaco.languages.setMonarchTokensProvider('robotframework', {
    tokenizer: {
      root: [
        [/^\s*\*\*\*\s*(Settings|Variables|Test Cases|Keywords)\s*\*\*\*/i, 'keyword.section'],
        [/^\s*\[Documentation\]/i, 'keyword.documentation'],
        [/^\s*\[Tags\]/i, 'keyword.tags'],
        [/^\s*\[Setup\]|\[Teardown\]/i, 'keyword.setup'],
        [/^\s*Library\s+/i, 'keyword.library'],
        [/^\s*Resource\s+/i, 'keyword.resource'],
        [/^\s*Variables\s+/i, 'keyword.variables'],
        [/^\s*Test Setup|Test Teardown/i, 'keyword.hook'],
        [/^\s*Suite Setup|Suite Teardown/i, 'keyword.hook'],
        [/^\s*[A-Za-z][\w\s]*\n(?=\s)/, 'entity.name.testcase'],
        [/\$\{[^}]+\}/g, 'variable'],
        [/#.*$/, 'comment'],
        [/^\s*\w.*/, 'keyword.statement'],
      ],
    },
  })

  monaco.languages.setLanguageConfiguration('robotframework', {
    comments: { lineComment: '#' },
    brackets: [
      ['${', '}'],
      ['@{', '}'],
      ['&{', '}'],
      ['[', ']'],
      ['(', ')'],
    ],
    autoClosingPairs: [
      { open: '${', close: '}' },
      { open: '@{', close: '}' },
      { open: '&{', close: '}' },
      { open: '[', close: ']' },
      { open: '(', close: ')' },
      { open: '"', close: '"' },
      { open: "'", close: "'" },
    ],
    surroundingPairs: [
      { open: '${', close: '}' },
      { open: '@{', close: '}' },
      { open: '&{', close: '}' },
    ],
    folding: {
      markers: {
        start: /^\s*\*\*\*\s*(Settings|Variables|Test Cases|Keywords)\s*\*\*\*/i,
        end: /^\s*\*\*\*\s*(Settings|Variables|Test Cases|Keywords)\s*\*\*\*/i,
      },
    },
  })
}

async function initEditor() {
  if (!editorContainer.value || isEditorReady) return

  await loader.init()
  await registerRobotFrameworkLanguage()

  editor = monaco.editor.create(editorContainer.value, {
    value: props.modelValue,
    language: language.value,
    theme: 'vs-dark',
    readOnly: props.readOnly,
    fontSize: 13,
    lineNumbers: 'on',
    minimap: { enabled: false },
    scrollBeyondLastLine: false,
    automaticLayout: true,
    tabSize: 2,
    insertSpaces: true,
    wordWrap: 'on',
    renderLineHighlight: 'line',
  })

  editor.onDidChangeModelContent(() => {
    if (!ignoreModelChange && editor) {
      emit('update:modelValue', editor.getValue())
    }
  })

  isEditorReady = true
}

watch(() => props.modelValue, (newVal) => {
  if (editor && !ignoreModelChange) {
    ignoreModelChange = true
    editor.setValue(newVal)
    ignoreModelChange = false
  }
})

watch(() => props.readOnly, (newVal) => {
  if (editor) {
    editor.updateOptions({ readOnly: newVal })
  }
})

onMounted(() => {
  nextTick(() => initEditor())
})

onUnmounted(() => {
  if (editor) {
    editor.dispose()
    editor = null
    isEditorReady = false
  }
})
</script>

<style scoped>
.rf-editor {
  width: 100%;
  height: 100%;
  min-height: 300px;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  background: #1e1e2e;
}
</style>