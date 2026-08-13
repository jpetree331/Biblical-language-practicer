import { useState } from 'react'
import { api } from '../api'
import { basicCardsFromCsv } from '../lib/csv'
import { navigate } from '../hooks/useHashRoute'

type Preview = {
  deck_name: string
  topic: string
  counts: Record<string, number>
  total: number
  with_fsrs_state: number
  warnings: string[]
}

/** Parse-then-confirm import. JSON (canonical, carries FSRS state) or CSV
 *  (basic cards only — converted to the canonical shape client-side). */
export function ImportPage() {
  const [raw, setRaw] = useState('')
  const [csvName, setCsvName] = useState('')
  const [doc, setDoc] = useState<Record<string, unknown> | null>(null)
  const [preview, setPreview] = useState<Preview | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [localWarnings, setLocalWarnings] = useState<string[]>([])

  const looksLikeJson = raw.trimStart().startsWith('{')

  const onFile = async (file: File) => {
    setRaw(await file.text())
    if (!csvName) setCsvName(file.name.replace(/\.(csv|json)$/i, ''))
    setPreview(null)
    setDoc(null)
  }

  const buildDoc = (): Record<string, unknown> => {
    if (looksLikeJson) {
      setLocalWarnings([])
      return JSON.parse(raw) as Record<string, unknown>
    }
    const { cards, warnings } = basicCardsFromCsv(raw)
    setLocalWarnings(warnings)
    if (!csvName.trim()) throw new Error('CSV import needs a deck name')
    return {
      format: 'scriptorium-deck@1',
      deck: { name: csvName.trim(), topic: 'general', config: {} },
      cards: cards.map((payload) => ({ card_type: 'basic', payload, source: null, state: null })),
    }
  }

  const runPreview = async () => {
    setError(null)
    setBusy(true)
    try {
      const data = buildDoc()
      setDoc(data)
      setPreview(await api.post<Preview>('/api/import', { data, mode: 'preview' }))
    } catch (e) {
      setPreview(null)
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  const commit = async () => {
    if (!doc) return
    setBusy(true)
    try {
      const result = await api.post<Preview & { deck_id: string }>('/api/import', {
        data: doc,
        mode: 'commit',
      })
      navigate(`/deck/${result.deck_id}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <h1>Import a deck</h1>
      <p className="muted">
        JSON exports restore everything including review schedule. CSV makes basic cards:
        columns <code>front,back,hint</code> (header optional).
      </p>
      <div className="card-surface" style={{ marginBottom: 'var(--sp-5)' }}>
        <label className="field">
          <span>File</span>
          <input
            type="file"
            accept=".json,.csv,text/csv,application/json"
            onChange={(e) => e.target.files?.[0] && void onFile(e.target.files[0])}
          />
        </label>
        <label className="field">
          <span>…or paste here</span>
          <textarea
            rows={8}
            value={raw}
            onChange={(e) => {
              setRaw(e.target.value)
              setPreview(null)
            }}
          />
        </label>
        {!looksLikeJson && raw.trim() && (
          <label className="field">
            <span>Deck name (for CSV) *</span>
            <input value={csvName} onChange={(e) => setCsvName(e.target.value)} />
          </label>
        )}
        <div className="actions">
          <button className="primary" onClick={runPreview} disabled={!raw.trim() || busy}>
            Preview
          </button>
        </div>
      </div>

      {error && <p className="form-error">{error}</p>}

      {preview && (
        <div className="card-surface">
          <h2>Will create</h2>
          <p>
            Deck <strong>{preview.deck_name}</strong> <span className="tag">{preview.topic}</span>{' '}
            with <strong>{preview.total}</strong> cards
            {preview.with_fsrs_state > 0
              ? ` (${preview.with_fsrs_state} keep their review schedule)`
              : ''}
            :
          </p>
          <ul>
            {Object.entries(preview.counts).map(([t, n]) => (
              <li key={t}>
                {n} × {t}
              </li>
            ))}
          </ul>
          {[...localWarnings, ...preview.warnings].length > 0 && (
            <>
              <h3>Warnings</h3>
              <ul className="muted">
                {[...localWarnings, ...preview.warnings].map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            </>
          )}
          <div className="actions">
            <button onClick={() => setPreview(null)}>Cancel</button>
            <button className="primary" onClick={commit} disabled={busy || preview.total === 0}>
              Import {preview.total} cards
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
