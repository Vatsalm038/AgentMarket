import { useNavigate, Link } from 'react-router-dom'
import { useSessions } from '@/hooks/useApi'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import type { SessionSummary } from '@/types'

// ─── Reusable skeleton (exported for 3.6/3.7 pages) ──────────────────────────

export function TableSkeleton({ rows = 5, cols = 6 }: { rows?: number; cols?: number }) {
  // Deterministic widths — no Math.random() so SSR/hydration stays stable
  const widths = ['w-16', 'w-24', 'w-32']

  return (
    <div className="border border-[#D8E1EA] rounded-md overflow-hidden">
      <table className="w-full">
        <tbody>
          {Array.from({ length: rows }).map((_, rowIndex) => (
            <tr key={rowIndex} className="border-b border-[#E4EAF1] last:border-0">
              {Array.from({ length: cols }).map((_, colIndex) => {
                const width = widths[(rowIndex * cols + colIndex) % 3]
                return (
                  <td key={colIndex} className="px-4 py-3">
                    <div className={`h-4 bg-[#E4EAF1] rounded animate-pulse ${width}`} />
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ─── Reusable empty state (exported for 3.6/3.7 pages) ───────────────────────

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string
  description: string
  action?: { label: string; href: string }
}) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <p className="text-sm font-medium text-[#131212] mb-1">{title}</p>
      <p className="text-sm text-[#6C7F9A] mb-4">{description}</p>
      {action && (
        <Button
          variant="ghost"
          size="sm"
          asChild
          className="border border-[#D8E1EA] text-[#6C7F9A] hover:bg-[#F5F8FA] hover:text-[#131212]"
        >
          <Link to={action.href}>{action.label}</Link>
        </Button>
      )}
    </div>
  )
}

// ─── Status badge helper ──────────────────────────────────────────────────────

function statusClass(status: SessionSummary['status']): string {
  switch (status) {
    case 'settled': return 'border-green-600 text-green-600'
    case 'pending': return 'border-[#D8E1EA] text-[#6C7F9A]'
    case 'revoked':
    case 'failed':  return 'border-red-400 text-red-600'
  }
}

// ─── Price formatter (INR, tabular nums) ─────────────────────────────────────

function fmtPrice(amount: number): string {
  return '₹' + amount.toLocaleString('en-IN')
}

// ─── Date formatter ───────────────────────────────────────────────────────────

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleString('en-IN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

// ─── Sessions table ───────────────────────────────────────────────────────────

const COLS = ['Session ID', 'Item', 'Status', 'Listed', 'Settled', 'Buyer Agent', 'Created']

function SessionsTable({ sessions }: { sessions: SessionSummary[] }) {
  const navigate = useNavigate()

  return (
    <div className="border border-[#D8E1EA] rounded-md overflow-hidden">
      <table className="w-full">
        <thead>
          <tr className="bg-[#F5F8FA] border-b border-[#D8E1EA]">
            {COLS.map((col) => (
              <th
                key={col}
                className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wide text-[#9DACBE]"
              >
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sessions.map((s) => (
            <tr
              key={s.session_id}
              className="border-b border-[#E4EAF1] last:border-0 hover:bg-[#F5F8FA] cursor-pointer transition-colors"
              onClick={() => navigate(`/session/${s.session_id}`)}
            >
              {/* Session ID — mono, truncated */}
              <td className="px-4 py-3 font-mono text-xs text-[#6C7F9A]">
                {s.session_id.slice(0, 12)}...{s.session_id.slice(-6)}
              </td>

              {/* Item */}
              <td className="px-4 py-3 text-sm text-[#131212]">{s.item}</td>

              {/* Status badge */}
              <td className="px-4 py-3 text-sm">
                <Badge variant="outline" className={statusClass(s.status)}>{s.status}</Badge>
              </td>

              {/* Listed price */}
              <td className="px-4 py-3 text-sm tabular-nums text-[#131212]">
                {fmtPrice(s.listed_price)}
              </td>

              {/* Settled price */}
              <td className="px-4 py-3 text-sm tabular-nums">
                {s.final_price !== null ? (
                  <span className="text-[#237B4B]">{fmtPrice(s.final_price)}</span>
                ) : (
                  <span className="text-[#9DACBE]">—</span>
                )}
              </td>

              {/* Buyer agent — mono, truncated */}
              <td className="px-4 py-3 font-mono text-xs text-[#6C7F9A]">
                {s.buyer_agent_id.slice(0, 12)}...{s.buyer_agent_id.slice(-6)}
              </td>

              {/* Created at */}
              <td className="px-4 py-3 text-sm text-[#6C7F9A]">{fmtDate(s.created_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export function SessionsPage() {
  const { data, isLoading, isError, refetch } = useSessions()

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
          <div>
            <h1 className="text-xl font-medium text-[#131212]">Sessions</h1>
            <p className="text-sm text-[#6C7F9A] mt-1">All negotiation sessions</p>
          </div>
          {/* Refresh button — icon-only, ghost */}
          <button
            onClick={() => refetch()}
            className="p-2 rounded-md text-[#6C7F9A] hover:text-[#131212] hover:bg-[#F5F8FA] transition-colors"
            aria-label="Refresh sessions"
          >
            {/* Inline SVG to avoid any icon library dependency */}
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8" />
              <path d="M21 3v5h-5" />
              <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16" />
              <path d="M3 21v-5h5" />
            </svg>
          </button>
        </div>

        {/* States */}
        {isLoading && <TableSkeleton rows={5} cols={7} />}

        {isError && (
          <p className="text-sm text-[#6C7F9A]">Failed to load sessions.</p>
        )}

        {!isLoading && !isError && data && data.length === 0 && (
          <EmptyState
            title="No sessions yet."
            description="Run the negotiate MCP tool to start your first session."
            action={{ label: 'Install MCP →', href: '/install-mcp' }}
          />
        )}

        {!isLoading && !isError && data && data.length > 0 && (
          <SessionsTable sessions={data} />
        )}
    </div>
  )
}
