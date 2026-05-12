import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { SessionSummary, SessionDetailResponse } from '@/types'

// Sessions list — stale time inherited from QueryClient default (30s)
export function useSessions() {
  return useQuery<SessionSummary[]>({
    queryKey: ['sessions'],
    queryFn: () => api.get('/commerce/sessions').then(r => r.data),
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
