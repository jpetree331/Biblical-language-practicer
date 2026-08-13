import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@fontsource/playfair-display/700.css'
import '@fontsource/libre-franklin/400.css'
import '@fontsource/libre-franklin/600.css'
import '@fontsource/noto-serif/400.css'
import '@fontsource/noto-serif/700.css'
import './theme.css'
import App from './App'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
