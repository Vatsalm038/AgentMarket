import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { SessionSummary, SessionDetailResponse } from '@/types'

// Shape returned by GET /health
interface HealthResponse {
  status: string
}

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
