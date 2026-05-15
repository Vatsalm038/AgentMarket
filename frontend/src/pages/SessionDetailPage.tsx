import React, { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useSession, useSessionWs, mergeAuditLog } from '@/hooks/useApi'
import type { WsStatus } from '@/hooks/useApi'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import type { NegotiationRound, AuditLogEntry, SignedReceipt } from '@/types'

// ─── helpers ─────────────────────────────────────────────────────────────────

function truncateId(id: string): string {
  if (id.length <= 18) return id
  return `${id.slice(0, 12)}...${id.slice(-6)}`
}

function inr(amount: number): string {
  return `₹${amount.toLocaleString('en-IN')}`
}

function statusClass(status: string): string {
  switch (status) {
    case 'settled':  return 'border-green-600 text-green-500'
    case 'pending':  return 'border-zinc-500 text-zinc-400'
    case 'revoked':
    case 'failed':   return 'border-red-600 text-red-500'
    default:         return 'border-zinc-500 text-zinc-400'
  }
}

function formatTs(iso: string): string {
  return new Date(iso).toLocaleString('en-IN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

// ─── sub-components ──────────────────────────────────────────────────────────

function LoadingSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="h-8 bg-zinc-800 rounded-md w-1/3" />
      <div className="h-48 bg-zinc-800 rounded-md" />
      <div className="h-32 bg-zinc-800 rounded-md" />
    </div>
  )
}

function NegotiationTable({ rounds }: { rounds: NegotiationRound[] }) {
  if (!rounds || rounds.length === 0) {
    return (
      <p className="text-sm text-zinc-500 py-4">No negotiation rounds recorded.</p>
    )
  }

  return (
    <div className="border border-zinc-700 rounded-md overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-zinc-800 border-b border-zinc-700">
            {['Round', 'Type', 'Winner', 'Time'].map(h => (
              <th
                key={h}
                className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wide text-zinc-500"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rounds.map((r) => {
            const winnerName = r.winner ? String(r.winner.merchant_name ?? r.winner.merchant_id ?? '—') : '—'
            const winnerPrice = r.winner ? (r.winner.final_price ?? r.winner.floor_price) : null
            return (
              <tr key={r.round} className="border-b border-zinc-800 last:border-0 hover:bg-zinc-800 transition-colors">
                <td className="px-4 py-3 font-mono text-xs text-zinc-500">{r.round}</td>
                <td className="px-4 py-3 text-zinc-400">{r.type}</td>
                <td className="px-4 py-3">
                  {r.winner ? (
                    <span>
                      <span className="text-zinc-200">{winnerName}</span>
                      {winnerPrice != null && (
                        <span className="text-zinc-500 ml-2 tabular-nums">{inr(Number(winnerPrice))}</span>
                      )}
                    </span>
                  ) : (
                    <span className="text-zinc-600">—</span>
                  )}
                </td>
                <td className="px-4 py-3 font-mono text-xs text-zinc-600 whitespace-nowrap">
                  {formatTs(r.timestamp)}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function AuditTimeline({ entries, liveEventCount }: { entries: AuditLogEntry[], liveEventCount: number }) {
  const [showAll, setShowAll] = useState(false)

  if (entries.length === 0) {
    return <p className="text-sm text-zinc-500 py-4">No audit events.</p>
  }

  // Reverse so most-recent event is first; live events land at the top of the reversed slice.
  const reversed = [...entries].reverse()
  const visible = showAll ? reversed : reversed.slice(0, 5)

  return (
    <>
      <ol className="space-y-1">
        {visible.map((entry, i) => {
          // The first liveEventCount entries in the reversed array are the freshly arrived WS events.
          const isLive = i < liveEventCount
          return (
            <li key={`${entry.timestamp}|${entry.event}`} className="border-l-2 border-zinc-700 pl-4 py-2 ml-2">
              <div className="flex items-center gap-3">
                {isLive && (
                  // dot marks events that arrived live over WS and are not yet flushed to REST
                  <span className="text-green-500 text-xs select-none">●</span>
                )}
                <span className="text-sm font-mono font-medium text-zinc-200">{entry.event}</span>
                <span className="font-mono text-xs text-zinc-600">{formatTs(entry.timestamp)}</span>
              </div>
              {entry.payload && (
                // collapsible raw payload — useful for debugging without cluttering the audit trail
                <details className="mt-1">
                  <summary className="text-xs text-zinc-600 cursor-pointer select-none">payload</summary>
                  <pre className="mt-2 font-mono text-xs text-zinc-400 bg-zinc-950 border border-zinc-700 rounded-md p-3 whitespace-pre-wrap break-all">
                    {JSON.stringify(entry.payload, null, 2)}
                  </pre>
                </details>
              )}
            </li>
          )
        })}
      </ol>
      {entries.length > 5 && (
        <button
          onClick={() => setShowAll(v => !v)}
          className="mt-3 text-xs text-zinc-500 hover:text-zinc-200 underline underline-offset-2 transition-colors"
        >
          {showAll ? 'Show fewer' : `Show all ${entries.length} events`}
        </button>
      )}
    </>
  )
}

function downloadReceipt(receipt: SignedReceipt) {
  const blob = new Blob([JSON.stringify(receipt, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `receipt-${receipt.receipt_id.slice(0, 12)}.json`
  a.click()
  URL.revokeObjectURL(url)
}

function ReceiptCard({ receipt }: { receipt: SignedReceipt }) {
  const rows: [string, React.ReactNode][] = [
    ['Receipt ID',     <span className="font-mono text-xs text-zinc-400">{truncateId(receipt.receipt_id)}</span>],
    ['Policy ID',      <span className="font-mono text-xs text-zinc-400">{truncateId(receipt.policy_id)}</span>],
    ['Amount',         <span className="tabular-nums text-zinc-200">{inr(receipt.amount_inr)}</span>],
    ['Buyer agent',    <span className="font-mono text-xs text-zinc-400">{truncateId(receipt.buyer_agent_id)}</span>],
    ['Merchant agent', <span className="font-mono text-xs text-zinc-400">{truncateId(receipt.merchant_agent_id)}</span>],
    ['Settled at',     <span className="text-zinc-300">{formatTs(receipt.created_at)}</span>],
    ...(receipt.razorpay_order_id ? [['Razorpay order', <span className="font-mono text-xs text-zinc-400">{receipt.razorpay_order_id}</span>] as [string, React.ReactNode]] : []),
    ...(receipt.razorpay_payment_id ? [['Razorpay payment', <span className="font-mono text-xs text-zinc-400">{receipt.razorpay_payment_id}</span>] as [string, React.ReactNode]] : []),
  ]

  return (
    <div className="bg-zinc-800 border border-zinc-700 rounded-md p-6 space-y-4">
      <dl className="grid grid-cols-[auto_1fr] gap-x-8 gap-y-2 text-sm">
        {rows.map(([label, value]) => (
          <React.Fragment key={String(label)}>
            <dt className="text-zinc-500 font-medium whitespace-nowrap">{label}</dt>
            <dd className="text-zinc-200">{value}</dd>
          </React.Fragment>
        ))}
      </dl>

      {/* Ed25519 signature — full hex so an auditor can independently verify */}
      <div className="border-t border-zinc-700 pt-4 space-y-1">
        <p className="text-xs text-zinc-500 uppercase tracking-wide font-medium">Ed25519 Signature</p>
        <p className="font-mono text-xs text-zinc-500 break-all">{receipt.signature_b64}</p>
      </div>

      {/* Download the full signed receipt as JSON for offline / auditor verification */}
      <div className="border-t border-zinc-700 pt-4 flex justify-end">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => downloadReceipt(receipt)}
          className="border border-zinc-700 text-zinc-300 hover:bg-zinc-700 hover:text-zinc-100"
        >
          Download receipt (.json)
        </Button>
      </div>
    </div>
  )
}

// ─── WS status badge ──────────────────────────────────────────────────────────

// Maps WebSocket connection state to a small visual indicator.
// "open" is deliberately understated — it's the happy path.
function WsStatusBadge({ status }: { status: WsStatus }) {
  const label: Record<WsStatus, string> = {
    connecting: 'connecting…',
    open:       'live',
    closed:     'disconnected',
    error:      'ws error',
  }
  const cls: Record<WsStatus, string> = {
    connecting: 'border-zinc-600 text-zinc-500',
    open:       'border-zinc-600 text-zinc-400',
    closed:     'border-zinc-700 text-zinc-600',
    error:      'border-red-600 text-red-500',
  }

  return (
    <Badge variant="outline" className={`text-[10px] px-1.5 py-0 ${cls[status]}`}>
      {/* dot indicator */}
      <span
        className={`inline-block w-1.5 h-1.5 rounded-full mr-1.5 ${
          status === 'open' ? 'bg-green-500' :
          status === 'error' ? 'bg-red-500' :
          'bg-zinc-600'
        }`}
      />
      {label[status]}
    </Badge>
  )
}

// ─── page ─────────────────────────────────────────────────────────────────────

export function SessionDetailPage() {
  const { id = '' } = useParams<{ id: string }>()
  const { data, isLoading, isError } = useSession(id)
  const { liveEvents, wsStatus } = useSessionWs(id)

  if (isLoading) return (
    <div className="p-8 max-w-4xl mx-auto">
      <LoadingSkeleton />
    </div>
  )

  if (isError || !data) return (
    <div className="p-8 max-w-4xl mx-auto">
      <p className="text-sm text-zinc-500">Session not found.</p>
    </div>
  )

  const { session, audit_log, signed_receipt, replay_data } = data
  // Merge REST audit_log with any live WS events that haven't been persisted yet.
  // This keeps the timeline complete even before the next REST refetch fires.
  const mergedAuditLog = mergeAuditLog(audit_log, liveEvents)
  // liveAuditCount = how many entries in mergedAuditLog came from WS (not yet in the REST snapshot)
  const liveAuditCount = mergedAuditLog.length - audit_log.length

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-8">

      {/* ── session header ─────────────────────────────────────────────────── */}
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1">
          <p className="font-mono text-xs text-zinc-600">{truncateId(session.id)}</p>
          <h1 className="text-xl font-medium text-zinc-100">{session.item}</h1>
          <div className="flex items-center gap-3 text-sm text-zinc-500">
            <span>Listed {inr(session.listed_price)}</span>
            {session.final_price !== null && (
              <>
                <span className="text-zinc-700">→</span>
                <span className="text-green-500">Settled {inr(session.final_price)}</span>
              </>
            )}
          </div>
          <div className="flex items-center gap-2 pt-1 text-xs text-zinc-600">
            <span>Buyer: <span className="font-mono">{truncateId(session.buyer_agent_id)}</span></span>
            {session.merchant_agent_id && (
              <>
                <span>·</span>
                <span>Merchant: <span className="font-mono">{truncateId(session.merchant_agent_id)}</span></span>
              </>
            )}
          </div>
        </div>

        <div className="flex flex-col items-end gap-2 shrink-0">
          <div className="flex items-center gap-2">
            <Badge variant="outline" className={statusClass(session.status)}>{session.status}</Badge>
            {/* Only show WS badge while the session is pending — once settled the socket closes */}
            {session.status === 'pending' && <WsStatusBadge status={wsStatus} />}
          </div>
          <p className="text-xs text-zinc-600">{formatTs(session.created_at)}</p>
          {replay_data != null && (
            // replay_data presence means the full turn-by-turn log was captured (ADR-007)
            <Button
              variant="ghost"
              size="sm"
              asChild
              className="border border-zinc-700 text-zinc-300 hover:bg-zinc-800 hover:text-zinc-100"
            >
              <Link to={`/replay/${id}`}>View Replay →</Link>
            </Button>
          )}
        </div>
      </div>

      {/* ── negotiation trail ──────────────────────────────────────────────── */}
      <section>
        <h2 className="text-sm font-medium text-zinc-500 mb-3">
          Negotiation Trail
        </h2>
        <NegotiationTable rounds={session.rounds} />
      </section>

      {/* ── audit log ─────────────────────────────────────────────────────── */}
      <section>
        <div className="flex items-center gap-3 mb-3">
          <h2 className="text-sm font-medium text-zinc-500">
            Audit Log ({mergedAuditLog.length})
          </h2>
          {session.status === 'pending' && <WsStatusBadge status={wsStatus} />}
        </div>
        <AuditTimeline entries={mergedAuditLog} liveEventCount={liveAuditCount} />
      </section>

      {/* ── signed receipt ─────────────────────────────────────────────────── */}
      {signed_receipt && (
        <section>
          <h2 className="text-sm font-medium text-zinc-500 mb-3">
            Signed Receipt
          </h2>
          <ReceiptCard receipt={signed_receipt} />
        </section>
      )}

    </div>
  )
}
