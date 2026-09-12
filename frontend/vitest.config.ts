import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
      'monaco-editor': resolve(__dirname, 'tests/__mocks__/monaco-editor.ts'),
      '@monaco-editor/loader': resolve(__dirname, 'tests/__mocks__/monaco-editor-loader.ts'),
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./tests/__mocks__/setup.ts'],
  },
})
