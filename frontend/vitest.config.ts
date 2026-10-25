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
    // tests/e2e 是 Playwright 測試（npm run test:e2e），不能由 vitest 收集
    include: ['tests/unit/**/*.spec.ts'],
    // element-plus 的元件樣式以 .css 匯入，需交給 vite 處理而不是由 Node 直接載入
    server: { deps: { inline: ['element-plus'] } },
  },
})
