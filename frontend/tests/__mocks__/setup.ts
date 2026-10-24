import { vi } from 'vitest'

// Global mock for monaco-editor is handled via alias in vitest.config.ts
// This file ensures mocks are available globally
// jsdom 的 Blob/File 沒有 arrayBuffer()（rfUpload.decodeFileContent 會用到），以 FileReader 補上
if (typeof Blob !== 'undefined' && !Blob.prototype.arrayBuffer) {
  Blob.prototype.arrayBuffer = function (this: Blob): Promise<ArrayBuffer> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = () => resolve(reader.result as ArrayBuffer)
      reader.onerror = () => reject(reader.error)
      reader.readAsArrayBuffer(this)
    })
  }
}
