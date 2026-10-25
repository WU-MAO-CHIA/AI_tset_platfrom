import { describe, it, expect, vi } from 'vitest'
import { confirmAction } from '../../src/composables/useConfirm'

// 對話框在第一次呼叫時才動態載入並掛載，所以等它出現在 DOM 上
const dialogShown = () => vi.waitFor(() => expect(document.body.querySelector('.modal')).not.toBeNull())

describe('confirmAction', () => {
  it('resolves true when the confirm button is pressed', async () => {
    const result = confirmAction({ title: '刪除帳號「a」？', confirmLabel: '刪除', danger: true })
    await dialogShown()
    const buttons = document.body.querySelectorAll<HTMLButtonElement>('.modal-actions button')
    expect(document.body.textContent).toContain('刪除帳號「a」？')
    buttons[1].click()
    expect(await result).toBe(true)
    await vi.waitFor(() => expect(document.body.querySelector('.modal')).toBeNull())
  })

  it('resolves false when cancelled', async () => {
    const result = confirmAction({ title: '確定？' })
    await dialogShown()
    document.body.querySelector<HTMLButtonElement>('.modal-actions .btn-secondary')!.click()
    expect(await result).toBe(false)
  })
})
