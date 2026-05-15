import { useState } from "react"
import { useParams } from "react-router-dom"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useAuth } from "@/contexts/AuthContext"
import { api } from "@/lib/api"
import { Deal, SessionDetailResponse } from "@/types"
import { StatusBadge } from "@/components/StatusBadge"
import { PriceDisplay } from "@/components/PriceDisplay"
import { ProfitBadge } from "@/components/ProfitBadge"
import { DeliveryTimeline } from "@/components/DeliveryTimeline"
import { NegotiationTrail } from "@/components/NegotiationTrail"
import { ReceiptBlock } from "@/components/ReceiptBlock"
import { Button } from "@/components/ui/button"

interface MerchantDeal extends Deal {
  session_id?: string
  floor_price_inr?: number | null
}

export function MerchantDealDetailPage() {
  const { id = "" } = useParams<{ id: string }>()
  const { user } = useAuth()
  const qc = useQueryClient()
  const [proofUrl, setProofUrl] = useState("")

  const dealQuery = useQuery<MerchantDeal>({
    queryKey: ["merchant-deal", id, user?.id],
    queryFn: async () => {
      const res = await api.get<MerchantDeal>(`/merchant/deal/${id}`)
      return res.data
    },
  })

  const sessionId = dealQuery.data?.session_id ?? id
  const sessionQuery = useQuery<SessionDetailResponse>({
    queryKey: ["session", sessionId],
    queryFn: async () => {
      const res = await api.get<SessionDetailResponse>(`/commerce/session/${sessionId}`)
      return res.data
    },
    enabled: !!sessionId,
  })

  const updateDelivery = useMutation({
    mutationFn: async (body: Record<string, string>) => {
      await api.put(`/merchant/delivery/${id}`, body)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["merchant-deal", id] })
      qc.invalidateQueries({ queryKey: ["session", sessionId] })
    },
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

  const profitAmount =
    deal.final_price != null && deal.floor_price_inr != null
      ? deal.final_price - deal.floor_price_inr
      : null
  const profitPct =
    profitAmount != null && deal.floor_price_inr
      ? (profitAmount / deal.floor_price_inr) * 100
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
          <PriceDisplay amount={deal.final_price} className="text-2xl text-sky-400" />
        )}
      </div>

      {profitAmount != null && profitPct != null && profitAmount > 0 && (
        <ProfitBadge profitAmount={profitAmount} profitPct={profitPct} />
      )}

      <section>
        <h2 className="text-sm font-medium text-zinc-500 mb-4">Delivery Status</h2>
        <DeliveryTimeline deal={deal} />
      </section>

      {/* Actions */}
      <div className="flex flex-wrap gap-3">
        {(!deal.delivery_status || deal.delivery_status === "pending") && (
          <Button
            variant="ghost"
            className="border border-zinc-700 text-zinc-300 hover:bg-zinc-800"
            onClick={() => updateDelivery.mutate({ delivery_status: "dispatched" })}
            disabled={updateDelivery.isPending}
          >
            Mark Dispatched
          </Button>
        )}
        {deal.delivery_status === "dispatched" && (
          <Button
            variant="ghost"
            className="border border-emerald-700 text-emerald-400 hover:bg-emerald-900/20"
            onClick={() => updateDelivery.mutate({ delivery_status: "delivered" })}
            disabled={updateDelivery.isPending}
          >
            Mark Delivered
          </Button>
        )}
      </div>

      {/* Upload proof URL */}
      <div className="flex gap-3 items-end">
        <div className="flex-1 space-y-1.5">
          <label className="text-xs font-medium text-zinc-400">Proof image URL</label>
          <input
            type="url"
            value={proofUrl}
            onChange={(e) => setProofUrl(e.target.value)}
            className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-zinc-500"
            placeholder="https://example.com/proof.jpg"
          />
        </div>
        <Button
          variant="ghost"
          className="border border-zinc-700 text-zinc-300 hover:bg-zinc-800 shrink-0"
          onClick={() => updateDelivery.mutate({ proof_image_url: proofUrl })}
          disabled={!proofUrl || updateDelivery.isPending}
        >
          Upload
        </Button>
      </div>

      {sessionQuery.isLoading ? (
        <div className="h-32 bg-zinc-800 rounded-md animate-pulse" />
      ) : session ? (
        <NegotiationTrail rounds={session.rounds} auditLog={auditLog} />
      ) : null}

      {receipt && (
        <section>
          <h2 className="text-sm font-medium text-zinc-500 mb-3">Signed Receipt</h2>
          <ReceiptBlock receipt={receipt} />
        </section>
      )}
    </div>
  )
}
