/* Framework-free (Divergence Rule 2): no React, no fetch, no DOM.
   Unit-testable in plain Node. Real fixture coverage — data integrity is
   personal here (GATE B: transliteration widget, beta-code-flavored).

   Deterministic Latin → polytonic Greek:
     letters  a β=b g d e z h(η) q(θ) i k l m n x(ξ) o p r s t u f(φ) c(χ) y(ψ) w(ω)
     breathings BEFORE a letter:  )a → ἀ   (a → ἁ   (r → ῥ
     accents AFTER a letter:      a/ → ά   a\ → ὰ   a= → ᾶ
     iota subscript:              a| → ᾳ   diaeresis: i+ → ϊ
     final sigma is automatic:    logos → λογος (…ς)
   Examples: lo/gos → λόγος · )arch=| → ἀρχῇ · (rh=ma → ῥῆμα · (w=| → ᾧ */

const LETTERS: Record<string, string> = {
  a: 'α', b: 'β', g: 'γ', d: 'δ', e: 'ε', z: 'ζ', h: 'η', q: 'θ', i: 'ι',
  k: 'κ', l: 'λ', m: 'μ', n: 'ν', x: 'ξ', o: 'ο', p: 'π', r: 'ρ', s: 'σ',
  t: 'τ', u: 'υ', f: 'φ', c: 'χ', y: 'ψ', w: 'ω',
  A: 'Α', B: 'Β', G: 'Γ', D: 'Δ', E: 'Ε', Z: 'Ζ', H: 'Η', Q: 'Θ', I: 'Ι',
  K: 'Κ', L: 'Λ', M: 'Μ', N: 'Ν', X: 'Ξ', O: 'Ο', P: 'Π', R: 'Ρ', S: 'Σ',
  T: 'Τ', U: 'Υ', F: 'Φ', C: 'Χ', Y: 'Ψ', W: 'Ω',
}

const SMOOTH = '̓'
const ROUGH = '̔'
const ACUTE = '́'
const GRAVE = '̀'
const CIRCUMFLEX = '͂'
const SUBSCRIPT = 'ͅ'
const DIAERESIS = '̈'

const ACCENT_MARKS: Record<string, string> = {
  '/': ACUTE,
  '\\': GRAVE,
  '=': CIRCUMFLEX,
  '|': SUBSCRIPT,
  '+': DIAERESIS,
}

/** Deterministic transliteration; unknown characters pass through unchanged. */
export function translit(input: string): string {
  let out = ''
  let i = 0
  while (i < input.length) {
    const ch = input[i]
    // breathing marks apply to the NEXT letter
    if (ch === ')' || ch === '(') {
      const next = input[i + 1]
      if (next && LETTERS[next]) {
        let cluster = LETTERS[next] + (ch === ')' ? SMOOTH : ROUGH)
        i += 2
        while (i < input.length && ACCENT_MARKS[input[i]]) {
          cluster += ACCENT_MARKS[input[i]]
          i++
        }
        out += cluster
        continue
      }
      out += ch
      i++
      continue
    }
    if (LETTERS[ch]) {
      let cluster = LETTERS[ch]
      i++
      while (i < input.length && ACCENT_MARKS[input[i]]) {
        cluster += ACCENT_MARKS[input[i]]
        i++
      }
      out += cluster
      continue
    }
    out += ch
    i++
  }
  // word-final sigma (σ before a non-letter or end of text becomes ς)
  out = out.normalize('NFC').replace(/σ(?=$|[^\p{L}\p{M}])/gu, 'ς')
  return out.normalize('NFC')
}
