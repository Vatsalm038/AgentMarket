import { useState } from "react"
import { NegotiationRound, AuditLogEntry } from "@/types"

function formatTs(iso: string): string {
  return new Date(iso).toLocaleString("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  })
}

function inr(amount: number): string {
  return `₹${amount.toLocaleString("en-IN")}`
}

function NegotiationTable({ rounds }: { rounds: NegotiationRound[] }) {
  if (!rounds || rounds.length === 0) {
    return <p className="text-sm text-zinc-500 py-4">No negotiation rounds recorded.</p>
  }

  return (
    <div className="border border-zinc-700 rounded-md overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-zinc-800 border-b border-zinc-700">
            {["Round", "Type", "Winner", "Time"].map((h) => (
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
            const winnerName = r.winner
              ? String(r.winner.merchant_name ?? r.winner.merchant_id ?? "—")
              : "—"
            const winnerPrice = r.winner
              ? (r.winner.final_price ?? r.winner.floor_price)
              : null
            return (
              <tr
                key={r.round}
                className="border-b border-zinc-800 last:border-0 hover:bg-zinc-800 transition-colors"
              >
                <td className="px-4 py-3 font-mono text-xs text-zinc-500">{r.round}</td>
                <td className="px-4 py-3 text-zinc-400">{r.type}</td>
                <td className="px-4 py-3">
                  {r.winner ? (
                    <span>
                      <span className="text-zinc-200">{winnerName}</span>
                      {winnerPrice != null && (
                        <span className="text-zinc-500 ml-2 tabular-nums">
                          {inr(Number(winnerPrice))}
                        </span>
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

function AuditTimeline({
  entries,
  liveEventCount,
}: {
  entries: AuditLogEntry[]
  liveEventCount: number
}) {
  const [showAll, setShowAll] = useState(false)

  if (entries.length === 0) {
    return <p className="text-sm text-zinc-500 py-4">No audit events.</p>
  }

  const reversed = [...entries].reverse()
  const visible = showAll ? reversed : reversed.slice(0, 5)

  return (
    <>
      <ol className="space-y-1">
        {visible.map((entry, i) => {
          const isLive = i < liveEventCount
          return (
            <li
              key={`${entry.timestamp}|${entry.event}`}
              className="border-l-2 border-zinc-700 pl-4 py-2 ml-2"
            >
              <div className="flex items-center gap-3">
                {isLive && (
                  <span className="text-emerald-500 text-xs select-none">●</span>
                )}
                <span className="text-sm font-mono font-medium text-zinc-200">{entry.event}</span>
                <span className="font-mono text-xs text-zinc-600">{formatTs(entry.timestamp)}</span>
              </div>
              {entry.payload && (
                <details className="mt-1">
                  <summary className="text-xs text-zinc-600 cursor-pointer select-none">
                    payload
                  </summary>
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
          onClick={() => setShowAll((v) => !v)}
          className="mt-3 text-xs text-zinc-500 hover:text-zinc-200 underline underline-offset-2 transition-colors"
        >
          {showAll ? "Show fewer" : `Show all ${entries.length} events`}
        </button>
      )}
    </>
  )
}

interface NegotiationTrailProps {
  rounds: NegotiationRound[]
  auditLog: AuditLogEntry[]
  liveEventCount?: number
}

export function NegotiationTrail({
  rounds,
  auditLog,
  liveEventCount = 0,
}: NegotiationTrailProps) {
  return (
    <div className="space-y-6">
      <section>
        <h2 className="text-sm font-medium text-zinc-500 mb-3">Negotiation Trail</h2>
        <NegotiationTable rounds={rounds} />
      </section>

      <section>
        <h2 className="text-sm font-medium text-zinc-500 mb-3">
          Audit Log ({auditLog.length})
        </h2>
        <AuditTimeline entries={auditLog} liveEventCount={liveEventCount} />
      </section>
    </div>
  )
}
