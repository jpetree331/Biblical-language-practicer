import { useState } from 'react'
import { CARD_TYPES, cardType } from '../config/cardTypes'
import type { Card } from '../api'
import { Modal } from './Modal'

/* Generic card editor — fully driven by the card-type registry
   (Divergence Rule 1: zero per-type branching here). */

export function CardEditor({
  card,
  onSave,
  onClose,
}: {
  /** Existing card to edit, or null to create. */
  card: Card | null
  onSave: (cardTypeKey: string, payload: Record<string, unknown>) => Promise<void>
  onClose: () => void
}) {
  const [typeKey, setTypeKey] = useState(card?.card_type ?? 'basic')
  const spec = cardType(typeKey)
  const [values, setValues] = useState<Record<string, string>>(() =>
    card ? cardType(card.card_type).toFields(card.payload) : {},
  )
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const switchType = (key: string) => {
    setTypeKey(key)
    setValues({})
    setError(null)
  }

  const save = async () => {
    let payload: Record<string, unknown>
    try {
      payload = spec.fromFields(values)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      return
    }
    setBusy(true)
    try {
      await onSave(typeKey, payload)
      onClose()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal title={card ? 'Edit card' : 'New card'} onClose={onClose}>
      {!card && (
        <label className="field">
          <span>Card type</span>
          <select value={typeKey} onChange={(e) => switchType(e.target.value)}>
            {Object.values(CARD_TYPES).map((t) => (
              <option key={t.key} value={t.key}>
                {t.label}
              </option>
            ))}
          </select>
        </label>
      )}
      {spec.fields.map((f) => (
        <label key={f.name} className="field">
          <span>
            {f.label}
            {f.required ? ' *' : ''}
          </span>
          {f.kind === 'textarea' ? (
            <textarea
              rows={3}
              value={values[f.name] ?? ''}
              placeholder={f.placeholder}
              onChange={(e) => setValues((v) => ({ ...v, [f.name]: e.target.value }))}
            />
          ) : (
            <input
              value={values[f.name] ?? ''}
              placeholder={f.placeholder}
              onChange={(e) => setValues((v) => ({ ...v, [f.name]: e.target.value }))}
            />
          )}
          {f.help ? <span className="muted">{f.help}</span> : null}
        </label>
      ))}
      {error && <p className="form-error">{error}</p>}
      <div className="actions">
        <button onClick={onClose}>Cancel</button>
        <button className="primary" onClick={save} disabled={busy}>
          {card ? 'Save' : 'Add card'}
        </button>
      </div>
    </Modal>
  )
}
