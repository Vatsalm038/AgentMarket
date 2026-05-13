import React from 'react'
import { useParams, Link } from 'react-router-dom'
import { useSession } from '@/hooks/useApi'
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
    case 'settled':  return 'border-green-600 text-green-700'
    case 'pending':  return 'border-zinc-400 text-zinc-600'
    case 'revoked':
    case 'failed':   return 'border-red-600 text-red-700'
    default:         return 'border-zinc-400 text-zinc-600'
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
      <div className="h-8 bg-zinc-100 rounded-md w-1/3" />
      <div className="h-48 bg-zinc-100 rounded-md" />
      <div className="h-32 bg-zinc-100 rounded-md" />
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
    <div className="border border-zinc-200 rounded-md overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-zinc-50 border-b border-zinc-200">
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
              <tr key={r.round} className="border-b border-zinc-100 last:border-0 hover:bg-zinc-50">
                <td className="px-4 py-3 font-mono text-xs text-zinc-500">{r.round}</td>
                <td className="px-4 py-3 text-zinc-600">{r.type}</td>
                <td className="px-4 py-3">
                  {r.winner ? (
                    <span>
                      <span className="text-zinc-900">{winnerName}</span>
                      {winnerPrice != null && (
                        <span className="text-zinc-500 ml-2 tabular-nums">{inr(Number(winnerPrice))}</span>
                      )}
                    </span>
                  ) : (
                    <span className="text-zinc-400">—</span>
                  )}
                </td>
                <td className="px-4 py-3 font-mono text-xs text-zinc-400 whitespace-nowrap">
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

function AuditTimeline({ entries }: { entries: AuditLogEntry[] }) {
  if (entries.length === 0) {
    return <p className="text-sm text-zinc-500 py-4">No audit events.</p>
  }

  return (
    <ol className="space-y-3">
      {entries.map((entry, i) => (
        <li key={i} className="border-l-2 border-zinc-200 pl-4 py-1 ml-2">
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium text-zinc-800">{entry.event}</span>
            <span className="font-mono text-xs text-zinc-400">{formatTs(entry.timestamp)}</span>
          </div>
          {entry.payload && (
            // collapsible raw payload — useful for debugging without cluttering the audit trail
            <details className="mt-1">
              <summary className="text-xs text-zinc-400 cursor-pointer select-none">payload</summary>
              <pre className="mt-1 font-mono text-xs text-zinc-500 whitespace-pre-wrap break-all">
                {JSON.stringify(entry.payload, null, 2)}
              </pre>
            </details>
          )}
        </li>
      ))}
    </ol>
  )
}

function ReceiptCard({ receipt }: { receipt: SignedReceipt }) {
  const rows: [string, React.ReactNode][] = [
    ['Receipt ID',     <span className="font-mono text-xs text-zinc-500">{truncateId(receipt.receipt_id)}</span>],
    ['Policy ID',      <span className="font-mono text-xs text-zinc-500">{truncateId(receipt.policy_id)}</span>],
    ['Amount',         <span className="tabular-nums">{inr(receipt.amount_inr)}</span>],
    ['Buyer agent',    <span className="font-mono text-xs text-zinc-500">{truncateId(receipt.buyer_agent_id)}</span>],
    ['Merchant agent', <span className="font-mono text-xs text-zinc-500">{truncateId(receipt.merchant_agent_id)}</span>],
    ['Settled at',     <span>{formatTs(receipt.created_at)}</span>],
    ...(receipt.razorpay_order_id ? [['Razorpay order', <span className="font-mono text-xs text-zinc-500">{receipt.razorpay_order_id}</span>] as [string, React.ReactNode]] : []),
    ...(receipt.razorpay_payment_id ? [['Razorpay payment', <span className="font-mono text-xs text-zinc-500">{receipt.razorpay_payment_id}</span>] as [string, React.ReactNode]] : []),
  ]

  return (
    <div className="bg-white border border-zinc-200 rounded-md p-6 space-y-4">
      <dl className="grid grid-cols-[auto_1fr] gap-x-8 gap-y-2 text-sm">
        {rows.map(([label, value]) => (
          <React.Fragment key={String(label)}>
            <dt className="text-zinc-500 font-medium whitespace-nowrap">{label}</dt>
            <dd className="text-zinc-900">{value}</dd>
          </React.Fragment>
        ))}
      </dl>

      {/* Ed25519 signature — full hex so an auditor can independently verify */}
      <div className="border-t border-zinc-100 pt-4 space-y-1">
        <p className="text-xs text-zinc-500 uppercase tracking-wide font-medium">Ed25519 Signature</p>
        <p className="font-mono text-xs text-zinc-400 break-all">{receipt.signature_b64}</p>
      </div>
    </div>
  )
}

// ─── page ─────────────────────────────────────────────────────────────────────

export function SessionDetailPage() {
  const { id = '' } = useParams<{ id: string }>()
  const { data, isLoading, isError } = useSession(id)

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

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-8">

      {/* ── session header ─────────────────────────────────────────────────── */}
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1">
          <p className="font-mono text-xs text-zinc-400">{truncateId(session.id)}</p>
          <h1 className="text-xl font-medium text-zinc-900">{session.item}</h1>
          <div className="flex items-center gap-3 text-sm text-zinc-500">
            <span>Listed {inr(session.listed_price)}</span>
            {session.final_price !== null && (
              <>
                <span className="text-zinc-300">→</span>
                <span className="text-green-700">Settled {inr(session.final_price)}</span>
              </>
            )}
          </div>
          <div className="flex items-center gap-2 pt-1 text-xs text-zinc-400">
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
          <Badge variant="outline" className={statusClass(session.status)}>{session.status}</Badge>
          <p className="text-xs text-zinc-400">{formatTs(session.created_at)}</p>
          {replay_data != null && (
            // replay_data presence means the full turn-by-turn log was captured (ADR-007)
            <Button variant="outline" size="sm" asChild>
              <Link to={`/replay/${id}`}>View Replay →</Link>
            </Button>
          )}
        </div>
      </div>

      {/* ── negotiation trail ──────────────────────────────────────────────── */}
      <section>
        <h2 className="text-sm font-medium uppercase tracking-wide text-zinc-500 mb-3">
          Negotiation Trail
        </h2>
        <NegotiationTable rounds={session.rounds} />
      </section>

      {/* ── audit log ─────────────────────────────────────────────────────── */}
      <section>
        <h2 className="text-sm font-medium uppercase tracking-wide text-zinc-500 mb-3">
          Audit Log
        </h2>
        <AuditTimeline entries={audit_log} />
      </section>

      {/* ── signed receipt ─────────────────────────────────────────────────── */}
      {signed_receipt && (
        <section>
          <h2 className="text-sm font-medium uppercase tracking-wide text-zinc-500 mb-3">
            Signed Receipt
          </h2>
          <ReceiptCard receipt={signed_receipt} />
        </section>
      )}

    </div>
  )
}
