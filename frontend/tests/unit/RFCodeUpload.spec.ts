import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import RFCodeUpload from '@/components/RFCodeUpload/index.vue'

describe('RFCodeUpload', () => {
  let wrapper: ReturnType<typeof mount>

  beforeEach(() => {
    wrapper = mount(RFCodeUpload, {
      props: { caseId: 'test-case-id' },
      global: {
        stubs: {
          // No external dependencies
        }
      }
    })
  })

  it('renders upload area with instruction text', () => {
    expect(wrapper.find('[data-testid="rf-upload-input"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('點擊或拖曳上傳 .robot 檔案')
  })

  it('shows error for non-.robot file', async () => {
    const file = new File(['content'], 'test.txt', { type: 'text/plain' })
    const input = wrapper.find('[data-testid="rf-upload-input"]')
    await input.setValue(file)

    expect(wrapper.find('[data-testid="rf-upload-error"]').text()).toContain('只接受 .robot 檔案')
    expect(wrapper.emitted('file-loaded')).toBeUndefined()
  })

  it('shows error for file exceeding 500KB', async () => {
    const largeContent = 'x'.repeat(500 * 1024 + 1)
    const file = new File([largeContent], 'test.robot', { type: 'text/plain' })
    const input = wrapper.find('[data-testid="rf-upload-input"]')
    await input.setValue(file)

    expect(wrapper.find('[data-testid="rf-upload-error"]').text()).toContain('500KB')
    expect(wrapper.emitted('file-loaded')).toBeUndefined()
  })

  it('emits file-loaded with decoded content for valid .robot file', async () => {
    const content = '*** Settings ***\nLibrary    Browser\n\n*** Test Cases ***\nTest\n    Log    Hello'
    const file = new File([content], 'test.robot', { type: 'text/plain' })
    const input = wrapper.find('[data-testid="rf-upload-input"]')
    await input.setValue(file)

    expect(wrapper.find('[data-testid="rf-upload-error"]').exists()).toBe(false)
    expect(wrapper.emitted('file-loaded')?.[0]).toEqual([content])
    expect(wrapper.text()).toContain('test.robot')
  })

  it('clears file and emits file-cleared when clear button clicked', async () => {
    const content = '*** Test ***\nLog    Hello'
    const file = new File([content], 'test.robot', { type: 'text/plain' })
    const input = wrapper.find('[data-testid="rf-upload-input"]')
    await input.setValue(file)

    expect(wrapper.emitted('file-loaded')).toBeTruthy()

    await wrapper.find('[data-testid="rf-upload-clear"]').trigger('click')

    expect(wrapper.emitted('file-cleared')).toBeTruthy()
    expect(wrapper.text()).toContain('點擊或拖曳上傳 .robot 檔案')
  })

  it('handles UTF-8 encoded file', async () => {
    const content = '*** Test Cases ***\n測試中文\n    Log    你好世界'
    const file = new File([content], 'test.robot', { type: 'text/plain' })
    const input = wrapper.find('[data-testid="rf-upload-input"]')
    await input.setValue(file)

    expect(wrapper.emitted('file-loaded')?.[0]).toEqual([content])
  })

  it('does not emit file-loaded when file input is cleared without selection', async () => {
    const input = wrapper.find('[data-testid="rf-upload-input"]')
    await input.setValue(null)

    expect(wrapper.emitted('file-loaded')).toBeUndefined()
  })
})