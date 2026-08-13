/* Framework-free (Divergence Rule 2): no React, no fetch, no DOM.
   Unit-testable in plain Node.

   Minimal RFC-4180 CSV for deck import/export. CSV carries basic cards only
   (the JSON format is canonical and carries everything). */

export function parseCsv(text: string): string[][] {
  const rows: string[][] = []
  let row: string[] = []
  let field = ''
  let inQuotes = false
  let i = 0
  const src = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n')
  while (i < src.length) {
    const ch = src[i]
    if (inQuotes) {
      if (ch === '"') {
        if (src[i + 1] === '"') {
          field += '"'
          i += 2
          continue
        }
        inQuotes = false
        i++
        continue
      }
      field += ch
      i++
    } else if (ch === '"') {
      inQuotes = true
      i++
    } else if (ch === ',') {
      row.push(field)
      field = ''
      i++
    } else if (ch === '\n') {
      row.push(field)
      field = ''
      rows.push(row)
      row = []
      i++
    } else {
      field += ch
      i++
    }
  }
  if (field !== '' || row.length > 0) {
    row.push(field)
    rows.push(row)
  }
  return rows.filter((r) => !(r.length === 1 && r[0].trim() === ''))
}

export function toCsvRow(fields: string[]): string {
  return fields
    .map((f) => (/[",\n]/.test(f) ? '"' + f.replace(/"/g, '""') + '"' : f))
    .join(',')
}

export type CsvCards = {
  cards: { front: string; back: string; hint?: string }[]
  warnings: string[]
}

/** CSV → basic-card payloads. Header row (front,back[,hint]) is optional and
 *  detected case-insensitively. Rows missing front or back are skipped with a
 *  warning, never silently. */
export function basicCardsFromCsv(text: string): CsvCards {
  const rows = parseCsv(text)
  const warnings: string[] = []
  if (rows.length === 0) return { cards: [], warnings: ['no rows found'] }

  let start = 0
  const head = rows[0].map((c) => c.trim().toLowerCase())
  if (head[0] === 'front' && head[1] === 'back') start = 1

  const cards: CsvCards['cards'] = []
  for (let r = start; r < rows.length; r++) {
    const [front = '', back = '', hint = ''] = rows[r].map((c) => c.trim())
    if (!front || !back) {
      warnings.push(`row ${r + 1} skipped: needs both front and back`)
      continue
    }
    cards.push(hint ? { front, back, hint } : { front, back })
  }
  return { cards, warnings }
}
