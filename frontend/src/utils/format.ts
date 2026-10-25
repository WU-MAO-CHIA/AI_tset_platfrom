// 後端時間為 UTC；無時區標記的 ISO 字串一律視為 UTC，再以台北時間顯示
const TIME_ZONE = 'Asia/Taipei'

function parse(iso: string): Date {
  const hasZone = /([zZ]|[+-]\d{2}:?\d{2})$/.test(iso)
  return new Date(hasZone ? iso : `${iso}Z`)
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '-'
  const d = parse(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString('zh-TW', {
    timeZone: TIME_ZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '-'
  const d = parse(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleDateString('zh-TW', { timeZone: TIME_ZONE, year: 'numeric', month: '2-digit', day: '2-digit' })
}
