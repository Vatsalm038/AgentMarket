import { useParams } from "react-router-dom"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useAuth } from "@/contexts/AuthContext"
import { api } from "@/lib/api"
import { Deal } from "@/types"
import { SessionDetailResponse } from "@/types"
import { StatusBadge } from "@/components/StatusBadge"
import { PriceDisplay } from "@/components/PriceDisplay"
import { SavingsBadge } from "@/components/SavingsBadge"
import { DeliveryTimeline } from "@/components/DeliveryTimeline"
import { NegotiationTrail } from "@/components/NegotiationTrail"
import { ReceiptBlock } from "@/components/ReceiptBlock"
import { Button } from "@/components/ui/button"

interface BuyerDealDetail extends Deal {
  session_id?: string
  max_price_inr?: number | null
}

export function BuyerDealDetailPage() {
  const { id = "" } = useParams<{ id: string }>()
  const { user } = useAuth()
  const qc = useQueryClient()

  // Try /buyer/deal/:id first; if not available fall back to session endpoint
  const dealQuery = useQuery<BuyerDealDetail>({
    queryKey: ["buyer-deal", id, user?.id],
    queryFn: async () => {
      const res = await api.get<BuyerDealDetail>(`/buyer/deal/${id}`)
      return res.data
    },
  })

  // Load the session detail (negotiation trail + receipt)
  const sessionId = dealQuery.data?.session_id ?? id
  const sessionQuery = useQuery<SessionDetailResponse>({
    queryKey: ["session", sessionId],
    queryFn: async () => {
      const res = await api.get<SessionDetailResponse>(`/commerce/session/${sessionId}`)
      return res.data
    },
    enabled: !!sessionId,
  })

  const markDelivered = useMutation({
    mutationFn: async () => {
      await api.post(`/buyer/deal/${id}/delivered`)
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["buyer-deal", id] }),
  })

  const raiseDispute = useMutation({
    mutationFn: async () => {
      await api.post(`/buyer/dispute/${id}`)
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["buyer-deal", id] }),
  })

  if (dealQuery.isLoading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-8 bg-zinc-800 rounded-md w-1/3" />
        <div className="h-20 bg-zinc-800 rounded-md" />
        <div className="h-48 bg-zinc-800 rounded-md" />
      </div>
    )
  }

  if (dealQuery.isError) {
    return <p className="text-sm text-red-400">Deal not found.</p>
  }

  const deal = dealQuery.data!
  const session = sessionQuery.data?.session
  const auditLog = sessionQuery.data?.audit_log ?? []
  const receipt = sessionQuery.data?.signed_receipt

  const savedAmount =
    deal.final_price != null && deal.max_price_inr != null
      ? deal.max_price_inr - deal.final_price
      : null
  const savedPct =
    savedAmount != null && deal.max_price_inr
      ? (savedAmount / deal.max_price_inr) * 100
      : null

  return (
    <div className="space-y-8">
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1">
          <p className="font-mono text-xs text-zinc-600">{id.slice(0, 16)}…</p>
          <h1 className="text-xl font-semibold text-zinc-100">Deal Detail</h1>
          <StatusBadge status={deal.status} />
        </div>
        {deal.final_price != null && (
          <PriceDisplay amount={deal.final_price} className="text-2xl text-emerald-400" />
        )}
      </div>

      {/* Savings badge */}
      {savedAmount != null && savedPct != null && savedAmount > 0 && (
        <SavingsBadge savedAmount={savedAmount} savedPct={savedPct} />
      )}

      {/* Delivery timeline */}
      <section>
        <h2 className="text-sm font-medium text-zinc-500 mb-4">Delivery Status</h2>
        <DeliveryTimeline deal={deal} />
      </section>

      {/* Actions */}
      <div className="flex flex-wrap gap-3">
        {deal.payment_status === "pay_later" && (
          <Button
            className="bg-amber-500 text-black hover:bg-amber-400 font-medium"
            onClick={() => {
              // TODO: wire POST /payments/sessions/:id/pay-now
              alert("Pay Now — endpoint not yet wired.")
            }}
          >
            Pay Now
          </Button>
        )}
        {deal.delivery_status === "dispatched" && (
          <Button
            variant="ghost"
            className="border border-zinc-700 text-zinc-300 hover:bg-zinc-800"
            onClick={() => markDelivered.mutate()}
            disabled={markDelivered.isPending}
          >
            {markDelivered.isPending ? "Marking…" : "Mark Delivered"}
          </Button>
        )}
        {deal.status === "settled" && (
          <Button
            variant="ghost"
            className="border border-red-800 text-red-400 hover:bg-red-900/20"
            onClick={() => raiseDispute.mutate()}
            disabled={raiseDispute.isPending}
          >
            {raiseDispute.isPending ? "Raising…" : "Raise Dispute"}
          </Button>
        )}
      </div>

      {/* Negotiation trail */}
      {sessionQuery.isLoading ? (
        <div className="h-32 bg-zinc-800 rounded-md animate-pulse" />
      ) : session ? (
        <NegotiationTrail rounds={session.rounds} auditLog={auditLog} />
      ) : null}

      {/* Receipt */}
      {receipt && (
        <section>
          <h2 className="text-sm font-medium text-zinc-500 mb-3">Signed Receipt</h2>
          <ReceiptBlock receipt={receipt} />
        </section>
      )}
    </div>
  )
}
