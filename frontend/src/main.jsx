import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './styles/index.css'
import App from './App.jsx'
import { assertEnv } from './config/env'

// Surface missing required config the moment the app boots, rather than
// letting it fail confusingly deep inside a Supabase call or a Career AI
// network request later.
assertEnv()

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
