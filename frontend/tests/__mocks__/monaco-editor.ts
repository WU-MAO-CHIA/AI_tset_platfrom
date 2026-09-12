export const languages = {
  register: vi.fn(),
  getLanguages: vi.fn(() => []),
  setMonarchTokensProvider: vi.fn(),
  setLanguageConfiguration: vi.fn(),
}

export const editor = {
  create: vi.fn(() => ({
    onDidChangeModelContent: vi.fn(),
    setValue: vi.fn(),
    getValue: vi.fn(() => '*** Test ***\nLog    Hello'),
    updateOptions: vi.fn(),
    dispose: vi.fn(),
  })),
}

export default {
  languages,
  editor,
}