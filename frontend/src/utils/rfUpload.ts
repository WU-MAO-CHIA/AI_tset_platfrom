export const MAX_FILE_SIZE = 500 * 1024

export const ALLOWED_EXTENSIONS = ['.robot']

export function validateFileExtension(filename: string): boolean {
  const ext = filename.toLowerCase().substring(filename.lastIndexOf('.'))
  return ALLOWED_EXTENSIONS.includes(ext)
}

export function validateFileSize(size: number): boolean {
  return size <= MAX_FILE_SIZE
}

export async function decodeFileContent(file: File): Promise<string> {
  const encodings = ['utf-8', 'utf-8-sig', 'big5', 'gbk']
  const arrayBuffer = await file.arrayBuffer()
  const bytes = new Uint8Array(arrayBuffer)

  for (const encoding of encodings) {
    try {
      const decoder = new TextDecoder(encoding, { fatal: true })
      return decoder.decode(bytes)
    } catch {
      continue
    }
  }
  throw new Error('無法解碼檔案內容，請確認檔案為 UTF-8、Big5 或 GBK 編碼')
}

export function getFileValidationError(file: File): string | null {
  if (!validateFileExtension(file.name)) {
    return '只接受 .robot 檔案'
  }
  if (!validateFileSize(file.size)) {
    return `檔案超過 ${MAX_FILE_SIZE / 1024}KB 限制`
  }
  return null
}