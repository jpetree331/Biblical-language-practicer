/* Framework-free (Divergence Rule 2): no React, no fetch, no DOM.
   Unit-testable in plain Node.

   Cloze mechanics. Payload stores {text, deletions:[{start,end}]} (codepoint
   offsets into text). Authoring uses [[...]] markup; these functions convert
   both ways and split text into render segments. */

export type Deletion = { start: number; end: number }
export type ClozeSegment = { text: string; deletion: number | null } // index into deletions

/** Normalize deletions: numeric, in-range, sorted, non-overlapping, non-empty. */
export function normalizeDeletions(text: string, deletions: Deletion[]): Deletion[] {
  const cleaned = deletions
    .filter(
      (d) =>
        Number.isInteger(d.start) &&
        Number.isInteger(d.end) &&
        d.start >= 0 &&
        d.end <= text.length &&
        d.start < d.end,
    )
    .sort((a, b) => a.start - b.start)
  const out: Deletion[] = []
  for (const d of cleaned) {
    const prev = out[out.length - 1]
    if (prev && d.start < prev.end) continue // drop overlaps
    out.push({ start: d.start, end: d.end })
  }
  return out
}

/** Split text into segments; each deleted span carries its deletion index. */
export function clozeSplit(text: string, deletions: Deletion[]): ClozeSegment[] {
  const clean = normalizeDeletions(text, deletions)
  const segments: ClozeSegment[] = []
  let cursor = 0
  clean.forEach((d, i) => {
    if (d.start > cursor) segments.push({ text: text.slice(cursor, d.start), deletion: null })
    segments.push({ text: text.slice(d.start, d.end), deletion: i })
    cursor = d.end
  })
  if (cursor < text.length) segments.push({ text: text.slice(cursor), deletion: null })
  return segments
}

/** Parse authoring markup: "the [[quick]] fox" → text + deletions.
 *  Unbalanced markers throw — the editor surfaces the message. */
export function parseClozeMarkup(marked: string): { text: string; deletions: Deletion[] } {
  let text = ''
  const deletions: Deletion[] = []
  let i = 0
  while (i < marked.length) {
    const open = marked.indexOf('[[', i)
    if (open === -1) {
      text += marked.slice(i)
      break
    }
    const close = marked.indexOf(']]', open + 2)
    if (close === -1) throw new Error('unclosed [[ — every [[ needs a matching ]]')
    text += marked.slice(i, open)
    const inner = marked.slice(open + 2, close)
    if (inner.length === 0) throw new Error('empty [[]] deletion')
    deletions.push({ start: text.length, end: text.length + inner.length })
    text += inner
    i = close + 2
  }
  if (deletions.length === 0) throw new Error('mark at least one deletion with [[double brackets]]')
  return { text, deletions }
}

/** Inverse of parseClozeMarkup, for editing an existing card. */
export function toClozeMarkup(text: string, deletions: Deletion[]): string {
  const clean = normalizeDeletions(text, deletions)
  let out = ''
  let cursor = 0
  for (const d of clean) {
    out += text.slice(cursor, d.start) + '[[' + text.slice(d.start, d.end) + ']]'
    cursor = d.end
  }
  return out + text.slice(cursor)
}
