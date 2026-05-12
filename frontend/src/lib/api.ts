import axios from 'axios'

// baseURL falls back to /api in production — Vite proxies /api → localhost:8000 in dev
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? '/api',
  headers: { 'Content-Type': 'application/json' },
})
