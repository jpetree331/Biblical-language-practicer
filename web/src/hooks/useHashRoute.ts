import { useEffect, useState } from 'react'

/* Hand-rolled hash routing — deliberately no router dependency.
   Routes: #/decks · #/deck/<id> · #/about (default: decks). */

export type Route =
  | { page: 'decks' }
  | { page: 'deck'; id: string }
  | { page: 'review'; id: string }
  | { page: 'about' }

export function parseHash(hash: string): Route {
  const parts = hash.replace(/^#\/?/, '').split('/').filter(Boolean)
  if (parts[0] === 'deck' && parts[1]) return { page: 'deck', id: parts[1] }
  if (parts[0] === 'review' && parts[1]) return { page: 'review', id: parts[1] }
  if (parts[0] === 'about') return { page: 'about' }
  return { page: 'decks' }
}

export function navigate(to: string): void {
  window.location.hash = to
}

export function useHashRoute(): Route {
  const [route, setRoute] = useState<Route>(() => parseHash(window.location.hash))
  useEffect(() => {
    const onChange = () => setRoute(parseHash(window.location.hash))
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])
  return route
}
