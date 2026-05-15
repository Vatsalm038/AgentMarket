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
        <div className="h-8 bg-[#E4EAF1] rounded-md w-1/3" />
        <div className="h-20 bg-[#E4EAF1] rounded-md" />
        <div className="h-48 bg-[#E4EAF1] rounded-md" />
      </div>
    )
  }

  if (dealQuery.isError) {
    return <p className="text-sm text-[#AA2C2C]">Deal not found.</p>
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
          <p className="font-mono text-xs text-[#9DACBE]">{id.slice(0, 16)}…</p>
          <h1 className="text-xl font-semibold text-[#131212]">Deal Detail</h1>
          <StatusBadge status={deal.status} />
        </div>
        {deal.final_price != null && (
          <PriceDisplay amount={deal.final_price} className="text-2xl text-sky-600" />
        )}
      </div>

      {profitAmount != null && profitPct != null && profitAmount > 0 && (
        <ProfitBadge profitAmount={profitAmount} profitPct={profitPct} />
      )}

      <section>
        <h2 className="text-sm font-medium text-[#6C7F9A] mb-4">Delivery Status</h2>
        <DeliveryTimeline deal={deal} />
      </section>

      {/* Actions */}
      <div className="flex flex-wrap gap-3">
        {(!deal.delivery_status || deal.delivery_status === "pending") && (
          <Button
            variant="ghost"
            className="border border-[#D8E1EA] text-[#6C7F9A] hover:bg-[#F5F8FA]"
            onClick={() => updateDelivery.mutate({ delivery_status: "dispatched" })}
            disabled={updateDelivery.isPending}
          >
            Mark Dispatched
          </Button>
        )}
        {deal.delivery_status === "dispatched" && (
          <Button
            variant="ghost"
            className="border border-[#237B4B] text-[#237B4B] hover:bg-[#E6F4EA]"
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
          <label className="text-xs font-medium text-[#6C7F9A]">Proof image URL</label>
          <input
            type="url"
            value={proofUrl}
            onChange={(e) => setProofUrl(e.target.value)}
            className="w-full bg-white border border-[#D8E1EA] rounded-md px-3 py-2 text-sm text-[#131212] placeholder:text-[#9DACBE] focus:outline-none focus:ring-1 focus:ring-[#4F87C8]"
            placeholder="https://example.com/proof.jpg"
          />
        </div>
        <Button
          variant="ghost"
          className="border border-[#D8E1EA] text-[#6C7F9A] hover:bg-[#F5F8FA] shrink-0"
          onClick={() => updateDelivery.mutate({ proof_image_url: proofUrl })}
          disabled={!proofUrl || updateDelivery.isPending}
        >
          Upload
        </Button>
      </div>

      {sessionQuery.isLoading ? (
        <div className="h-32 bg-[#E4EAF1] rounded-md animate-pulse" />
      ) : session ? (
        <NegotiationTrail rounds={session.rounds} auditLog={auditLog} />
      ) : null}

      {receipt && (
        <section>
          <h2 className="text-sm font-medium text-[#6C7F9A] mb-3">Signed Receipt</h2>
          <ReceiptBlock receipt={receipt} />
        </section>
      )}
    </div>
  )
}
