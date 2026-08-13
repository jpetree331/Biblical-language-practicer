/* Framework-free (Divergence Rule 2): no React, no fetch, no DOM.
   Unit-testable in plain Node.

   First-letters memory hint: reduce each word to its first letter while
   preserving punctuation and line breaks. Unicode-aware — works for Greek
   (including polytonic) as well as English. */

const WORD_CHAR = /[\p{L}\p{M}\p{N}]/u

/** "In the beginning" → "I t b". Punctuation and newlines survive:
 *  "λόγος, καὶ" → "λ, κ". */
export function firstLetters(text: string): string {
  let out = ''
  let inWord = false
  for (const ch of text) {
    if (WORD_CHAR.test(ch)) {
      if (!inWord) out += ch
      inWord = true
    } else {
      out += ch
      inWord = false
    }
  }
  // collapse runs of spaces introduced by dropped letters, keep newlines
  return out
    .split('\n')
    .map((line) => line.replace(/ {2,}/g, ' ').trimEnd())
    .join('\n')
}
