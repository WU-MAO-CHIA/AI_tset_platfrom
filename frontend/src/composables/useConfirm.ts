import { createApp, reactive } from 'vue'

export interface ConfirmOptions {
  title: string
  message?: string
  confirmLabel?: string
  danger?: boolean
}

export const confirmState = reactive({
  open: false,
  title: '',
  message: '',
  confirmLabel: '確定',
  danger: false,
})

let pending: ((ok: boolean) => void) | null = null
let mounted = false

export function resolveConfirm(ok: boolean) {
  confirmState.open = false
  pending?.(ok)
  pending = null
}

// 取代 window.confirm()：回傳 Promise<boolean>。對話框第一次使用時才掛載到 body
export async function confirmAction(options: ConfirmOptions): Promise<boolean> {
  if (!mounted) {
    const { default: ConfirmDialog } = await import('../components/ConfirmDialog/index.vue')
    const host = document.createElement('div')
    document.body.appendChild(host)
    createApp(ConfirmDialog).mount(host)
    mounted = true
  }
  pending?.(false)
  Object.assign(confirmState, {
    open: true,
    title: options.title,
    message: options.message ?? '',
    confirmLabel: options.confirmLabel ?? '確定',
    danger: options.danger ?? false,
  })
  return new Promise((resolve) => {
    pending = resolve
  })
}
