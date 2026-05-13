import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { api } from '@/lib/api'
import type { SessionSummary, SessionDetailResponse, AuditLogEntry } from '@/types'

// Shape returned by GET /health
interface HealthResponse {
  status: string
}

// ─── WebSocket types ──────────────────────────────────────────────────────────

// Every event pushed by the backend over /ws/session/{id}
export interface WsEvent {
  event: string
  payload: Record<string, unknown> | null
  timestamp: string  // ISO 8601
}

// Connection states surfaced to the UI (maps to a status badge)
export type WsStatus = 'connecting' | 'open' | 'closed' | 'error'

// Sessions list — stale time inherited from QueryClient default (30s)
export function useSessions() {
  return useQuery<SessionSummary[]>({
    queryKey: ['sessions'],
    queryFn: () => api.get('/commerce/sessions').then(r => r.data),
  })
}

// Backend health check — refetch every 30 s so the badge stays current
export function useHealth() {
  return useQuery<HealthResponse>({
    queryKey: ['health'],
    queryFn: () => api.get('/health').then(r => r.data),
    refetchInterval: 30_000,
  })
}

// Single session detail — disabled when id is empty (prevents spurious 404s on mount)
export function useSession(id: string) {
  return useQuery<SessionDetailResponse>({
    queryKey: ['session', id],
    queryFn: () => api.get(`/commerce/session/${id}`).then(r => r.data),
    enabled: !!id,
  })
}

// ─── useSessionWs ─────────────────────────────────────────────────────────────
// Opens a WebSocket to /ws/session/{id} and:
//   • appends each inbound WsEvent to `liveEvents`
//   • invalidates ['session', id] on 'session.settled' so the query refetches
//   • cleans up the socket on unmount or id change
//
// Derives the WS base URL from VITE_API_URL by swapping the scheme.
// Falls back to the current page's host if VITE_API_URL is relative (/api).
function wsBaseUrl(): string {
  const apiUrl = import.meta.env.VITE_API_URL as string | undefined
  if (apiUrl && apiUrl.startsWith('http')) {
    // Replace http(s):// with ws(s)://
    return apiUrl.replace(/^http/, 'ws')
  }
  // Relative or absent — use current host with appropriate ws scheme
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
  return `${proto}://${window.location.host}`
}

export function useSessionWs(id: string): {
  liveEvents: WsEvent[]
  wsStatus: WsStatus
} {
  const queryClient = useQueryClient()
  const [liveEvents, setLiveEvents] = useState<WsEvent[]>([])
  const [wsStatus, setWsStatus] = useState<WsStatus>('connecting')
  // Keep a ref so the cleanup closure always sees the latest socket instance
  const socketRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!id) return

    setLiveEvents([])
    setWsStatus('connecting')

    const url = `${wsBaseUrl()}/ws/session/${id}`
    const ws = new WebSocket(url)
    socketRef.current = ws

    ws.onopen = () => setWsStatus('open')

    ws.onmessage = (evt) => {
      let parsed: WsEvent
      try {
        parsed = JSON.parse(evt.data as string) as WsEvent
      } catch {
        return // ignore malformed frames
      }

      // Append new event to the live list (oldest → newest order)
      setLiveEvents(prev => [...prev, parsed])

      // When the session settles, invalidate the TanStack Query cache so the
      // REST detail query refetches and the signed receipt appears immediately.
      if (parsed.event === 'session.settled') {
        void queryClient.invalidateQueries({ queryKey: ['session', id] })
        void queryClient.invalidateQueries({ queryKey: ['sessions'] })
      }
    }

    ws.onerror = () => setWsStatus('error')

    ws.onclose = () => {
      // Only update status if this is still the active socket (not a stale
      // closure from a previous id).
      if (socketRef.current === ws) {
        setWsStatus('closed')
      }
    }

    return () => {
      socketRef.current = null
      ws.close()
    }
  }, [id, queryClient])

  return { liveEvents, wsStatus }
}

// Merge REST audit log with live WS events, deduplicating by timestamp+event.
// Live events are appended after the persisted log so the timeline stays
// chronological even when the socket delivers events that the REST endpoint
// hasn't persisted yet.
export function mergeAuditLog(
  restLog: AuditLogEntry[],
  liveEvents: WsEvent[],
): AuditLogEntry[] {
  const seen = new Set(restLog.map(e => `${e.timestamp}|${e.event}`))
  const fresh: AuditLogEntry[] = liveEvents
    .filter(e => !seen.has(`${e.timestamp}|${e.event}`))
    .map(e => ({ event: e.event, payload: e.payload, timestamp: e.timestamp }))
  return [...restLog, ...fresh]
}
