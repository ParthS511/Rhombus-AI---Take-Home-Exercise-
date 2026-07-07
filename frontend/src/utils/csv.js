export function parseCsvHeader(text) {
  const firstLine = text.split(/\r?\n/).find((line) => line.trim())
  if (!firstLine) return []
  return firstLine
    .split(',')
    .map((item) => item.trim().replace(/^"|"$/g, ''))
    .filter(Boolean)
}

export function splitColumns(value) {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}
