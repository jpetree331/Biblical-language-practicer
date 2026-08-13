import { useHashRoute } from './hooks/useHashRoute'
import { AboutPage } from './pages/AboutPage'
import { DeckPage } from './pages/DeckPage'
import { DecksPage } from './pages/DecksPage'

export default function App() {
  const route = useHashRoute()

  return (
    <>
      <nav className="app-nav">
        <a className="wordmark" href="#/decks">
          Scriptorium
        </a>
        <a href="#/decks">Decks</a>
        <a href="#/about">About</a>
      </nav>
      <main className="app-main">
        {route.page === 'decks' && <DecksPage />}
        {route.page === 'deck' && <DeckPage key={route.id} deckId={route.id} />}
        {route.page === 'about' && <AboutPage />}
      </main>
    </>
  )
}
