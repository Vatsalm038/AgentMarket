import axios from 'axios'

// baseURL falls back to /api in production — Vite proxies /api → localhost:8000 in dev
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? '/api',
  headers: { 'Content-Type': 'application/json' },
})

// Attach JWT from localStorage on every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("sd_token")
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// On 401, clear auth and redirect to login
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("sd_token")
      localStorage.removeItem("sd_user")
      window.location.href = "/login"
    }
    return Promise.reject(error)
  }
)
