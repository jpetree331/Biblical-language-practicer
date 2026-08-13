import { useCallback, useEffect, useState } from 'react'
import { api } from '../api'
import type { Card, Deck } from '../api'
import { CardEditor } from '../components/CardEditor'
import { cardType } from '../config/cardTypes'
import { navigate } from '../hooks/useHashRoute'

type Stats = { due: number; new: number; retention: number | null }

export function DeckPage({ deckId }: { deckId: string }) {
  const [deck, setDeck] = useState<Deck | null>(null)
  const [cards, setCards] = useState<Card[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [editing, setEditing] = useState<Card | null>(null)
  const [adding, setAdding] = useState(false)
  const [renaming, setRenaming] = useState(false)
  const [newName, setNewName] = useState('')

  const load = useCallback(() => {
    api.get<Deck>(`/api/decks/${deckId}`).then(setDeck).catch((e) => setError(String(e)))
    api.get<Card[]>(`/api/decks/${deckId}/cards`).then(setCards).catch((e) => setError(String(e)))
    api.get<Stats>(`/api/review/stats?deck_id=${deckId}`).then(setStats).catch(() => setStats(null))
  }, [deckId])
  useEffect(load, [load])

  const setNewPerDay = async (value: number) => {
    if (!deck) return
    await api.patch(`/api/decks/${deckId}`, { config: { ...deck.config, newPerDay: value } })
    load()
  }

  const saveCard = async (typeKey: string, payload: Record<string, unknown>) => {
    if (editing) {
      await api.patch(`/api/cards/${editing.id}`, { payload })
    } else {
      await api.post('/api/cards', { deck_id: deckId, card_type: typeKey, payload })
    }
    load()
  }

  const deleteCard = async (card: Card) => {
    if (!confirm('Delete this card?')) return
    await api.delete(`/api/cards/${card.id}`)
    load()
  }

  const rename = async () => {
    if (!newName.trim()) return
    await api.patch(`/api/decks/${deckId}`, { name: newName.trim() })
    setRenaming(false)
    load()
  }

  const deleteDeck = async () => {
    if (!confirm(`Delete deck "${deck?.name}" and stop reviewing its cards?`)) return
    await api.delete(`/api/decks/${deckId}`)
    navigate('/decks')
  }

  if (error) return <p className="form-error">{error}</p>
  if (!deck) return <p className="muted">Loading…</p>

  return (
    <div>
      <p>
        <a href="#/decks">← All decks</a>
      </p>
      <div className="page-head">
        {renaming ? (
          <span className="rename-row">
            <input value={newName} autoFocus onChange={(e) => setNewName(e.target.value)} />
            <button className="primary" onClick={rename}>
              Save
            </button>
            <button onClick={() => setRenaming(false)}>Cancel</button>
          </span>
        ) : (
          <h1>
            {deck.name} <span className="tag">{deck.topic}</span>
          </h1>
        )}
        <span className="head-actions">
          <button
            onClick={() => {
              setNewName(deck.name)
              setRenaming(true)
            }}
          >
            Rename
          </button>
          <button onClick={deleteDeck}>Delete deck</button>
          <button onClick={() => setAdding(true)}>Add card</button>
          <button className="primary" onClick={() => navigate(`/review/${deckId}`)}>
            Review
          </button>
        </span>
      </div>

      {stats && (
        <div className="stat-row">
          <span className="stat">
            <strong className={stats.due > 0 ? 'stat-due' : ''}>{stats.due}</strong> due
          </span>
          <span className="stat">
            <strong>{stats.new}</strong> new
          </span>
          <span className="stat">
            retention{' '}
            <strong>{stats.retention === null ? '—' : `${Math.round(stats.retention * 100)}%`}</strong>
          </span>
          <span className="stat muted">
            new/day{' '}
            <input
              className="newperday"
              type="number"
              min={0}
              max={100}
              defaultValue={Number(deck.config.newPerDay ?? 10)}
              onBlur={(e) => {
                const v = Math.max(0, Math.min(100, Number(e.target.value) || 0))
                if (v !== Number(deck.config.newPerDay ?? 10)) void setNewPerDay(v)
              }}
            />
          </span>
        </div>
      )}

      {cards.length === 0 ? (
        <p className="muted">No cards yet.</p>
      ) : (
        <ul className="row-list">
          {cards.map((c) => {
            const spec = cardType(c.card_type)
            return (
              <li key={c.id} className="row">
                <button className="row-main" onClick={() => setEditing(c)}>
                  <span className="tag tag-quiet">{spec.label}</span>
                  <span className="row-summary">{spec.summarize(c.payload)}</span>
                </button>
                <button onClick={() => deleteCard(c)} aria-label="Delete card">
                  ✕
                </button>
              </li>
            )
          })}
        </ul>
      )}

      {(adding || editing) && (
        <CardEditor
          card={editing}
          onSave={saveCard}
          onClose={() => {
            setAdding(false)
            setEditing(null)
          }}
        />
      )}
    </div>
  )
}
