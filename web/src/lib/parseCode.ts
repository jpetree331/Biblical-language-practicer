/* Framework-free (Divergence Rule 2): no React, no fetch, no DOM.
   Unit-testable in plain Node.

   Decode MorphGNT parse codes ("V- 3IAI-S--") into readable English.
   Format: 2-char POS + space + 8-char code
   (person, tense, voice, mood, case, number, gender, degree). */

const POS: Record<string, string> = {
  'A-': 'adjective',
  'C-': 'conjunction',
  'D-': 'adverb',
  'I-': 'interjection',
  'N-': 'noun',
  'P-': 'preposition',
  RA: 'definite article',
  RD: 'demonstrative pronoun',
  RI: 'interrogative/indefinite pronoun',
  RP: 'personal pronoun',
  RR: 'relative pronoun',
  'V-': 'verb',
  'X-': 'particle',
}

const PERSON: Record<string, string> = { '1': '1st person', '2': '2nd person', '3': '3rd person' }
const TENSE: Record<string, string> = {
  P: 'present', I: 'imperfect', F: 'future', A: 'aorist', X: 'perfect', Y: 'pluperfect',
}
const VOICE: Record<string, string> = { A: 'active', M: 'middle', P: 'passive' }
const MOOD: Record<string, string> = {
  I: 'indicative', D: 'imperative', S: 'subjunctive', O: 'optative', N: 'infinitive', P: 'participle',
}
const CASE: Record<string, string> = { N: 'nominative', G: 'genitive', D: 'dative', A: 'accusative' }
const NUMBER: Record<string, string> = { S: 'singular', P: 'plural' }
const GENDER: Record<string, string> = { M: 'masculine', F: 'feminine', N: 'neuter' }
const DEGREE: Record<string, string> = { C: 'comparative', S: 'superlative' }

/** "V- 3IAI-S--" → "verb — 3rd person imperfect active indicative singular".
 *  Unknown/malformed codes come back verbatim rather than throwing. */
export function decodeParse(code: string): string {
  const m = code.match(/^(\S{1,2})\s+(\S{8})$/)
  if (!m) return code
  const pos = POS[m[1]]
  if (!pos) return code
  const [person, tense, voice, mood, kase, number, gender, degree] = m[2].split('')
  const parts = [
    PERSON[person],
    TENSE[tense],
    VOICE[voice],
    MOOD[mood],
    CASE[kase],
    NUMBER[number],
    GENDER[gender],
    DEGREE[degree],
  ].filter(Boolean)
  return parts.length ? `${pos} — ${parts.join(' ')}` : pos
}
