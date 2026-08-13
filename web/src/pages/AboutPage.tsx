import { useEffect, useState } from 'react'

type Health = { ok: boolean; db: string; version: string }

/** Status + the permanent polytonic render proof (Sprint 0 canary). */
export function AboutPage() {
  const [health, setHealth] = useState<Health | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/health')
      .then((r) => r.json())
      .then(setHealth)
      .catch((e) => setError(String(e)))
  }, [])

  return (
    <div>
      <h1>About</h1>
      <section className="card-surface" style={{ marginBottom: 'var(--sp-5)' }}>
        <h2>Service</h2>
        {health ? (
          <p>
            {health.ok ? 'Healthy' : 'Database problem'} — v{health.version}
            <br />
            <span className="muted">{health.db}</span>
          </p>
        ) : error ? (
          <p className="form-error">Service unreachable: {error}</p>
        ) : (
          <p className="muted">Checking…</p>
        )}
      </section>
      <section className="card-surface">
        <h2>Polytonic proof</h2>
        <p className="greek">ἐν ἀρχῇ ἦν ὁ λόγος, ᾧ ῥῆμα</p>
        <p className="muted">
          If the breathings, iota subscript, and circumflexes render cleanly, the Greek font
          stack is sound.
        </p>
      </section>
    </div>
  )
}
