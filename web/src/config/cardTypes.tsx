/* Card-type registry, frontend side (twin of service/app/card_types.py).
   Divergence Rule 1: components never branch on card type — everything a
   component needs (editor fields, payload conversion, renderers, sanitizing)
   lives in this registry. Adding a card type = adding an entry. */

import type { ReactNode } from 'react'
import { clozeSplit, normalizeDeletions, parseClozeMarkup, toClozeMarkup } from '../lib/clozeSplit'
import type { Deletion } from '../lib/clozeSplit'
import { firstLetters } from '../lib/firstLetters'
import { safePayload } from '../lib/sanitize'

export type ReviewCtx = { reps: number }

export type FieldSpec = {
  name: string
  label: string
  kind: 'text' | 'textarea'
  required?: boolean
  placeholder?: string
  help?: string
}

export type CardTypeSpec = {
  key: string
  label: string
  fields: FieldSpec[]
  /** Editor form values → payload. Throws with a human message when invalid. */
  fromFields: (values: Record<string, string>) => Record<string, unknown>
  /** Payload → editor form values (for editing an existing card). */
  toFields: (payload: Record<string, unknown>) => Record<string, string>
  /** Defensive-load: any unknown data → a safe payload. */
  sanitize: (raw: unknown) => Record<string, unknown>
  /** One reviewable unit per variant (cloze: one per deletion). */
  variantCount: (payload: Record<string, unknown>) => number
  /** Question side. ctx carries review history (verse graduates on reps). */
  renderFront: (payload: Record<string, unknown>, variant: number, ctx?: ReviewCtx) => ReactNode
  /** Answer side. */
  renderBack: (payload: Record<string, unknown>, variant: number, ctx?: ReviewCtx) => ReactNode
  /** One-line summary for card lists. */
  summarize: (payload: Record<string, unknown>) => string
}

type BasicPayload = { front: string; back: string; hint: string }
type ClozePayload = { text: string; deletions: Deletion[] }

const basic: CardTypeSpec = {
  key: 'basic',
  label: 'Basic (front / back)',
  fields: [
    { name: 'front', label: 'Front', kind: 'textarea', required: true },
    { name: 'back', label: 'Back', kind: 'textarea', required: true },
    { name: 'hint', label: 'Hint (optional)', kind: 'text' },
  ],
  fromFields(values) {
    const front = (values.front ?? '').trim()
    const back = (values.back ?? '').trim()
    if (!front) throw new Error('Front is required')
    if (!back) throw new Error('Back is required')
    const payload: Record<string, unknown> = { front, back }
    const hint = (values.hint ?? '').trim()
    if (hint) payload.hint = hint
    return payload
  },
  toFields(payload) {
    const p = this.sanitize(payload) as BasicPayload
    return { front: p.front, back: p.back, hint: p.hint }
  },
  sanitize(raw) {
    return safePayload<BasicPayload>(
      { defaults: { front: '(missing front)', back: '(missing back)', hint: '' } },
      raw,
    )
  },
  variantCount: () => 1,
  renderFront(payload) {
    const p = this.sanitize(payload) as BasicPayload
    return (
      <div>
        <div className="card-face-text">{p.front}</div>
        {p.hint ? <div className="muted">hint: {p.hint}</div> : null}
      </div>
    )
  },
  renderBack(payload) {
    const p = this.sanitize(payload) as BasicPayload
    return <div className="card-face-text">{p.back}</div>
  },
  summarize(payload) {
    const p = this.sanitize(payload) as BasicPayload
    return `${p.front} → ${p.back}`
  },
}

const cloze: CardTypeSpec = {
  key: 'cloze',
  label: 'Cloze deletion',
  fields: [
    {
      name: 'marked',
      label: 'Text',
      kind: 'textarea',
      required: true,
      placeholder: 'The [[mitochondria]] is the powerhouse of the [[cell]].',
      help: 'Wrap each deletion in [[double brackets]]. Each deletion becomes its own review.',
    },
  ],
  fromFields(values) {
    return parseClozeMarkup(values.marked ?? '')
  },
  toFields(payload) {
    const p = this.sanitize(payload) as ClozePayload
    return { marked: toClozeMarkup(p.text, p.deletions) }
  },
  sanitize(raw) {
    return safePayload<ClozePayload>(
      {
        defaults: { text: '(missing text)', deletions: [] },
        fix(p) {
          const dels = (p.deletions as unknown[]).filter(
            (d): d is Deletion => d !== null && typeof d === 'object',
          )
          return { text: p.text, deletions: normalizeDeletions(p.text, dels) }
        },
      },
      raw,
    )
  },
  variantCount(payload) {
    const p = this.sanitize(payload) as ClozePayload
    return Math.max(1, p.deletions.length)
  },
  renderFront(payload, variant) {
    const p = this.sanitize(payload) as ClozePayload
    return (
      <div className="card-face-text">
        {clozeSplit(p.text, p.deletions).map((seg, i) =>
          seg.deletion === variant ? (
            <span key={i} className="cloze-blank">
              [{'…'}]
            </span>
          ) : (
            <span key={i}>{seg.text}</span>
          ),
        )}
      </div>
    )
  },
  renderBack(payload, variant) {
    const p = this.sanitize(payload) as ClozePayload
    return (
      <div className="card-face-text">
        {clozeSplit(p.text, p.deletions).map((seg, i) =>
          seg.deletion === null ? (
            <span key={i}>{seg.text}</span>
          ) : (
            <span key={i} className={seg.deletion === variant ? 'cloze-reveal' : 'cloze-other'}>
              {seg.text}
            </span>
          ),
        )}
      </div>
    )
  },
  summarize(payload) {
    const p = this.sanitize(payload) as ClozePayload
    return toClozeMarkup(p.text, p.deletions)
  },
}

type VersePayload = {
  reference: string
  translation: string
  text: string
  graduateAfter: number
}

const verse: CardTypeSpec = {
  key: 'verse',
  label: 'Verse memory',
  fields: [
    { name: 'reference', label: 'Reference', kind: 'text', required: true, placeholder: 'John 1:1' },
    { name: 'translation', label: 'Translation', kind: 'text', placeholder: 'KJV' },
    { name: 'text', label: 'Verse text', kind: 'textarea', required: true },
    {
      name: 'graduateAfter',
      label: 'Graduate after N good reviews',
      kind: 'text',
      placeholder: '6',
      help: 'Until then the front shows first-letter hints; after, you recite from the reference alone.',
    },
  ],
  fromFields(values) {
    const reference = (values.reference ?? '').trim()
    const text = (values.text ?? '').trim()
    if (!reference) throw new Error('Reference is required')
    if (!text) throw new Error('Verse text is required')
    const graduateAfter = values.graduateAfter?.trim()
      ? Number.parseInt(values.graduateAfter, 10)
      : 6
    if (!Number.isInteger(graduateAfter) || graduateAfter < 0)
      throw new Error('Graduate after must be a whole number')
    const payload: Record<string, unknown> = { reference, text, graduateAfter }
    const translation = (values.translation ?? '').trim()
    if (translation) payload.translation = translation
    return payload
  },
  toFields(payload) {
    const p = this.sanitize(payload) as VersePayload
    return {
      reference: p.reference,
      translation: p.translation,
      text: p.text,
      graduateAfter: String(p.graduateAfter),
    }
  },
  sanitize(raw) {
    return safePayload<VersePayload>(
      {
        defaults: {
          reference: '(missing reference)',
          translation: '',
          text: '(missing text)',
          graduateAfter: 6,
        },
      },
      raw,
    )
  },
  variantCount: () => 1,
  renderFront(payload, _variant, ctx) {
    const p = this.sanitize(payload) as VersePayload
    const graduated = (ctx?.reps ?? 0) >= p.graduateAfter
    return (
      <div>
        <div className="verse-ref">
          {p.reference}
          {p.translation ? <span className="tag tag-quiet">{p.translation}</span> : null}
        </div>
        {graduated ? (
          <div className="muted">recite from memory</div>
        ) : (
          <div className="card-face-text verse-hint">{firstLetters(p.text)}</div>
        )}
      </div>
    )
  },
  renderBack(payload) {
    const p = this.sanitize(payload) as VersePayload
    return <div className="card-face-text">{p.text}</div>
  },
  summarize(payload) {
    const p = this.sanitize(payload) as VersePayload
    return `${p.reference} — ${p.text.length > 40 ? p.text.slice(0, 40) + '…' : p.text}`
  },
}

export const CARD_TYPES: Record<string, CardTypeSpec> = { basic, cloze, verse }

/** Lookup that never returns undefined — unknown types degrade to a basic
 *  card whose payload sanitizes to placeholders (corrupt rows must not crash). */
export function cardType(key: string): CardTypeSpec {
  return CARD_TYPES[key] ?? basic
}
