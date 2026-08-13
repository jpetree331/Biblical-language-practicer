import { useEffect, useState } from 'react'
import { api } from '../api'
import type { Deck } from '../api'
import { navigate } from '../hooks/useHashRoute'

export function DecksPage() {
  const [decks, setDecks] = useState<Deck[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)
  const [name, setName] = useState('')
  const [topic, setTopic] = useState('')

  const load = () => {
    api
      .get<Deck[]>('/api/decks')
      .then(setDecks)
      .catch((e) => setError(String(e)))
  }
  useEffect(load, [])

  const create = async () => {
    if (!name.trim()) return
    await api.post<Deck>('/api/decks', { name: name.trim(), topic: topic.trim() || 'general' })
    setName('')
    setTopic('')
    setCreating(false)
    load()
  }

  if (error) return <p className="form-error">Couldn't load decks: {error}</p>
  if (!decks) return <p className="muted">Loading…</p>

  return (
    <div>
      <div className="page-head">
        <h1>Decks</h1>
        <button className="primary" onClick={() => setCreating(true)}>
          New deck
        </button>
      </div>

      {creating && (
        <div className="card-surface" style={{ marginBottom: 'var(--sp-5)' }}>
          <label className="field">
            <span>Name *</span>
            <input value={name} autoFocus onChange={(e) => setName(e.target.value)} />
          </label>
          <label className="field">
            <span>Topic</span>
            <input
              value={topic}
              placeholder="general"
              onChange={(e) => setTopic(e.target.value)}
            />
          </label>
          <div className="actions">
            <button onClick={() => setCreating(false)}>Cancel</button>
            <button className="primary" onClick={create} disabled={!name.trim()}>
              Create
            </button>
          </div>
        </div>
      )}

      {decks.length === 0 && !creating ? (
        <p className="muted">No decks yet — make your first one.</p>
      ) : (
        <div className="deck-grid">
          {decks.map((d) => (
            <button key={d.id} className="deck-tile" onClick={() => navigate(`/deck/${d.id}`)}>
              <span className="deck-tile-name">{d.name}</span>
              <span className="tag">{d.topic}</span>
              <span className="muted">
                {d.card_count} card{d.card_count === 1 ? '' : 's'}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
