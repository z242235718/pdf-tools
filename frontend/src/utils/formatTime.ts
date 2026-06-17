export function formatTime(iso: string | null): string {
  if (!iso) return '-'
  // Backend sends naive UTC datetime strings (no 'Z' suffix),
  // so append 'Z' to force UTC interpretation before converting.
  const d = new Date(iso + 'Z')
  return d.toLocaleString('zh-CN', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })
}
