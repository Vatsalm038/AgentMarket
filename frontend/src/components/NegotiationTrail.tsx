import { useState } from "react"
import { NegotiationRound, AuditLogEntry } from "@/types"

function formatTs(iso: string): string {
  return new Date(iso).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })
}

function inr(amount: number): string {
  return `₹${Number(amount).toLocaleString("en-IN")}`
}

function roundTypeLabel(type: string): string {
  const map: Record<string, string> = {
    auction_round: "Auction",
    negotiate_round: "Negotiation",
    settle: "Settled",
  }
  return map[type] ?? type.replace(/_/g, " ")
}

function auditEventToEnglish(event: string, payload: Record<string, unknown> | null): string {
  const p = payload ?? {}
  switch (event) {
    case "session_started":
      return `Negotiation started for "${p.item ?? "item"}" — listed at ${inr(Number(p.listed_price ?? 0))}, your opening offer was ${inr(Number(p.initial_offer ?? 0))}.`
    case "auction_quotes_collected": {
      const quotes = (p.quotes as { merchant: string; price: number }[] | undefined) ?? []
      const lines = quotes.map(q => `${q.merchant}: ${inr(Number(q.price))}`).join(", ")
      return `${quotes.length} merchant${quotes.length !== 1 ? "s" : ""} submitted quotes — ${lines}.`
    }
    case "auction_winner_selected":
      return `Winner: ${p.winner ?? "merchant"} at ${inr(Number(p.price ?? 0))}. ${p.reason ?? "Best offer selected."}`
    case "payment_settled":
      return `Payment of ${inr(Number(p.amount ?? 0))} recorded and receipt cryptographically signed.`
    case "policy_check_passed":
      return `Your spending policy approved this transaction.`
    case "policy_check_failed":
      return `Your spending policy blocked this transaction: ${p.reason ?? "limit exceeded"}.`
    case "delivery_update":
      return `Delivery status updated to "${p.status ?? "unknown"}".`
    case "dispute_opened":
      return `A dispute was raised for this order.`
    default:
      return event.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())
  }
}

function NegotiationTable({ rounds }: { rounds: NegotiationRound[] }) {
  if (!rounds || rounds.length === 0) {
    return <p className="text-sm text-[#6C7F9A] py-4">No negotiation rounds recorded.</p>
  }

  return (
    <div className="border border-[#D8E1EA] rounded-md overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-[#F5F8FA] border-b border-[#D8E1EA]">
            {["Round", "Type", "Winner", "Time"].map((h) => (
              <th key={h} className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wide text-[#9DACBE]">
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
            const winnerPrice = r.winner ? (r.winner.final_price ?? r.winner.floor_price) : null
            return (
              <tr key={r.round} className="border-b border-[#E4EAF1] last:border-0 hover:bg-[#F5F8FA] transition-colors">
                <td className="px-4 py-3 font-mono text-xs text-[#6C7F9A]">{r.round}</td>
                <td className="px-4 py-3 text-[#6C7F9A]">{roundTypeLabel(r.type)}</td>
                <td className="px-4 py-3">
                  {r.winner ? (
                    <span>
                      <span className="text-[#131212]">{winnerName}</span>
                      {winnerPrice != null && (
                        <span className="text-[#6C7F9A] ml-2 tabular-nums">{inr(Number(winnerPrice))}</span>
                      )}
                    </span>
                  ) : (
                    <span className="text-[#9DACBE]">—</span>
                  )}
                </td>
                <td className="px-4 py-3 font-mono text-xs text-[#9DACBE] whitespace-nowrap">{formatTs(r.timestamp)}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function AuditTimeline({ entries, liveEventCount }: { entries: AuditLogEntry[]; liveEventCount: number }) {
  const [showAll, setShowAll] = useState(false)

  if (entries.length === 0) {
    return <p className="text-sm text-[#6C7F9A] py-4">No events yet.</p>
  }

  const reversed = [...entries].reverse()
  const visible = showAll ? reversed : reversed.slice(0, 5)

  return (
    <>
      <ol className="space-y-3">
        {visible.map((entry, i) => {
          const isLive = i < liveEventCount
          return (
            <li key={`${entry.timestamp}|${entry.event}`} className="border-l-2 border-[#D8E1EA] pl-4 py-1 ml-2">
              <div className="flex items-start gap-2">
                {isLive && <span className="text-[#237B4B] text-xs mt-0.5 shrink-0">●</span>}
                <div className="space-y-0.5">
                  <p className="text-sm text-[#131212] leading-snug">
                    {auditEventToEnglish(entry.event, entry.payload)}
                  </p>
                  <p className="font-mono text-xs text-[#9DACBE]">{formatTs(entry.timestamp)}</p>
                </div>
              </div>
            </li>
          )
        })}
      </ol>
      {entries.length > 5 && (
        <button
          onClick={() => setShowAll(v => !v)}
          className="mt-3 text-xs text-[#6C7F9A] hover:text-[#131212] underline underline-offset-2 transition-colors"
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

export function NegotiationTrail({ rounds, auditLog, liveEventCount = 0 }: NegotiationTrailProps) {
  return (
    <div className="space-y-6">
      <section>
        <h2 className="text-sm font-medium text-[#6C7F9A] mb-3">Negotiation Trail</h2>
        <NegotiationTable rounds={rounds} />
      </section>
      <section>
        <h2 className="text-sm font-medium text-[#6C7F9A] mb-3">What happened ({auditLog.length} events)</h2>
        <AuditTimeline entries={auditLog} liveEventCount={liveEventCount} />
      </section>
    </div>
  )
}
