import { useState } from "react"
import { useParams } from "react-router-dom"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useAuth } from "@/contexts/AuthContext"
import { api } from "@/lib/api"
import { Deal, SignedReceipt, SessionDetailResponse } from "@/types"
import { StatusBadge } from "@/components/StatusBadge"
import { PriceDisplay } from "@/components/PriceDisplay"
import { SavingsBadge } from "@/components/SavingsBadge"
import { DeliveryTimeline } from "@/components/DeliveryTimeline"
import { NegotiationTrail } from "@/components/NegotiationTrail"
import { Button } from "@/components/ui/button"

const ROADMAP = [
  { label: "Negotiated", statuses: ["settled", "paid", "delivered"] },
  { label: "Paid", statuses: ["paid", "delivered"] },
  { label: "Delivered", statuses: ["delivered"] },
]

function DealProgressBar({ status, hasPaid }: { status: string; hasPaid: boolean }) {
  const effectiveStatus = hasPaid && status === "settled" ? "paid" : status
  return (
    <div className="bg-white border border-[#D8E1EA] rounded-md px-6 py-4">
      <div className="flex items-start">
        {ROADMAP.map((step, i) => {
          const done = step.statuses.includes(effectiveStatus)
          const isLast = i === ROADMAP.length - 1
          return (
            <div key={step.label} className="flex items-start flex-1">
              <div className="flex flex-col items-center gap-1.5 min-w-0">
                <div
                  className={`w-7 h-7 rounded-full border-2 flex items-center justify-center text-xs font-bold transition-colors ${
                    done
                      ? "border-[#237B4B] bg-[#237B4B] text-white"
                      : "border-[#D8E1EA] bg-white text-[#9DACBE]"
                  }`}
                >
                  {done ? "✓" : i + 1}
                </div>
                <span
                  className={`text-xs font-medium text-center ${
                    done ? "text-[#237B4B]" : "text-[#9DACBE]"
                  }`}
                >
                  {step.label}
                </span>
              </div>
              {!isLast && (
                <div
                  className={`flex-1 h-0.5 mt-3.5 mx-2 ${
                    ROADMAP[i + 1].statuses.includes(effectiveStatus)
                      ? "bg-[#237B4B]"
                      : "bg-[#D8E1EA]"
                  }`}
                />
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

interface BuyerDealDetail extends Deal {
  session_id?: string
  max_price_inr?: number | null
}

interface PaymentOrder {
  order_id: string
  amount_paise: number
  key_id: string
  test_mode?: boolean
}

function downloadReceipt(receipt: SignedReceipt, sessionId: string) {
  const blob = new Blob([JSON.stringify(receipt, null, 2)], { type: "application/json" })
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = `receipt_${sessionId}.json`
  a.click()
  URL.revokeObjectURL(url)
}

export function BuyerDealDetailPage() {
  const { id = "" } = useParams<{ id: string }>()
  const { user } = useAuth()
  const qc = useQueryClient()
  const [paymentDone, setPaymentDone] = useState<RazorpayOrder | null>(null)
  const [paymentError, setPaymentError] = useState<string | null>(null)

  const dealQuery = useQuery<BuyerDealDetail>({
    queryKey: ["buyer-deal", id, user?.id],
    queryFn: async () => {
      const res = await api.get<BuyerDealDetail>(`/buyer/deal/${id}`)
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

  const authorizePayment = useMutation({
    mutationFn: async () => {
      const finalPrice = sessionQuery.data?.session?.final_price
      if (!finalPrice) throw new Error("No final price on this deal.")
      const res = await api.post<RazorpayOrder>("/commerce/create-razorpay-order", {
        session_id: sessionId,
        amount_inr: finalPrice,
      })
      return res.data
    },
    onSuccess: (data) => {
      setPaymentDone(data)
      setPaymentError(null)
      qc.invalidateQueries({ queryKey: ["buyer-deal", id] })
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        (err instanceof Error ? err.message : "Payment failed.")
      setPaymentError(msg)
    },
  })

  const raiseDispute = useMutation({
    mutationFn: async () => { await api.post(`/buyer/dispute/${id}`) },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["buyer-deal", id] }),
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

  const savedAmount =
    deal.final_price != null && deal.max_price_inr != null
      ? deal.max_price_inr - deal.final_price
      : null
  const savedPct =
    savedAmount != null && deal.max_price_inr
      ? (savedAmount / deal.max_price_inr) * 100
      : null

  const isSettled = deal.status === "settled"
  const finalPrice = session?.final_price ?? deal.final_price
  const needsPayment = isSettled && !paymentDone

  return (
    <div className="space-y-8 max-w-2xl">

      {/* Unpaid top banner */}
      {needsPayment && (
        <div className="bg-[#E6F4EA] border border-[#237B4B]/30 rounded-md px-5 py-4 flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-semibold text-[#131212]">Payment pending</p>
            <p className="text-xs text-[#6C7F9A]">
              Your agent secured a deal at ₹{Number(finalPrice ?? 0).toLocaleString("en-IN")}. Authorize to confirm.
            </p>
          </div>
          {paymentError && <p className="text-xs text-[#AA2C2C]">{paymentError}</p>}
          <Button
            onClick={() => authorizePayment.mutate()}
            disabled={authorizePayment.isPending}
            className="shrink-0 bg-[#237B4B] text-white hover:bg-[#1A5F3D] font-medium text-sm"
          >
            {authorizePayment.isPending ? "Processing…" : `Pay ₹${Number(finalPrice ?? 0).toLocaleString("en-IN")}`}
          </Button>
        </div>
      )}
      {paymentDone && (
        <div className="bg-[#E6F4EA] border border-[#237B4B]/30 rounded-md px-5 py-3 flex items-center gap-3">
          <span className="text-[#237B4B] text-lg font-bold">✓</span>
          <p className="text-sm text-[#131212] font-medium">
            Payment of ₹{Number(finalPrice ?? 0).toLocaleString("en-IN")} authorized
            {paymentDone.test_mode ? " (sandbox — no real money charged)" : ""}
          </p>
        </div>
      )}

      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1">
          <p className="font-mono text-xs text-[#9DACBE]">{id.slice(0, 16)}…</p>
          <h1 className="text-xl font-semibold text-[#131212]">Deal Detail</h1>
          <StatusBadge status={deal.status} />
        </div>
        {finalPrice != null && (
          <PriceDisplay amount={finalPrice} className="text-2xl text-[#237B4B]" />
        )}
      </div>

      {savedAmount != null && savedPct != null && savedAmount > 0 && (
        <SavingsBadge savedAmount={savedAmount} savedPct={savedPct} />
      )}

      {/* Progress roadmap */}
      <DealProgressBar status={deal.status} hasPaid={!!paymentDone} />

      {/* ── Step 1: Payment ───────────────────────────────────────────────── */}
      {isSettled && (
        <section className="border border-[#D8E1EA] rounded-md divide-y divide-[#E4EAF1]">
          <div className="px-5 py-4">
            <p className="text-xs font-medium text-[#9DACBE] uppercase tracking-wider mb-1">Step 1 — Payment</p>
            {!paymentDone ? (
              <div className="space-y-3">
                <p className="text-sm text-[#131212]">
                  Your agent found a deal at{" "}
                  <span className="text-[#237B4B] font-semibold">
                    ₹{Number(finalPrice ?? 0).toLocaleString("en-IN")}
                  </span>
                  . Authorize payment to confirm.
                </p>
                {paymentError && <p className="text-sm text-[#AA2C2C]">{paymentError}</p>}
                <Button
                  onClick={() => authorizePayment.mutate()}
                  disabled={authorizePayment.isPending}
                  className="bg-[#237B4B] hover:bg-[#1A5F3D] text-white font-semibold"
                >
                  {authorizePayment.isPending
                    ? "Processing…"
                    : `Authorize & Pay ₹${Number(finalPrice ?? 0).toLocaleString("en-IN")}`}
                </Button>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <span className="text-[#237B4B] text-lg">✓</span>
                  <p className="text-sm text-[#131212] font-medium">
                    Payment of ₹{Number(finalPrice ?? 0).toLocaleString("en-IN")} authorized
                    {paymentDone.test_mode ? " (sandbox — no real money charged)" : ""}
                  </p>
                </div>
                {paymentDone.order_id && (
                  <p className="font-mono text-xs text-[#9DACBE]">Order: {paymentDone.order_id}</p>
                )}
                {receipt && (
                  <Button
                    variant="ghost"
                    onClick={() => downloadReceipt(receipt, sessionId)}
                    className="border border-[#D8E1EA] text-[#6C7F9A] hover:bg-[#F5F8FA] text-sm"
                  >
                    Download Signed Receipt
                  </Button>
                )}
              </div>
            )}
          </div>
        </section>
      )}

      {/* ── Step 2: Delivery ─────────────────────────────────────────────── */}
      {isSettled && (
        <section className="border border-[#D8E1EA] rounded-md px-5 py-4 space-y-3">
          <p className="text-xs font-medium text-[#9DACBE] uppercase tracking-wider">Step 2 — Delivery</p>
          <DeliveryTimeline deal={deal} />
          <div className="flex gap-3 flex-wrap pt-1">
            {deal.status === "settled" && (
              <Button
                variant="ghost"
                className="border border-red-300 text-red-600 hover:bg-red-50 text-sm"
                onClick={() => raiseDispute.mutate()}
                disabled={raiseDispute.isPending}
              >
                {raiseDispute.isPending ? "Raising…" : "Raise a Dispute"}
              </Button>
            )}
          </div>
        </section>
      )}

      {/* ── Negotiation trail ────────────────────────────────────────────── */}
      <section>
        <h2 className="text-sm font-medium text-[#6C7F9A] mb-3">How the deal was made</h2>
        {sessionQuery.isLoading ? (
          <div className="h-32 bg-[#E4EAF1] rounded-md animate-pulse" />
        ) : session ? (
          <NegotiationTrail rounds={session.rounds} auditLog={auditLog} />
        ) : null}
      </section>

    </div>
  )
}
