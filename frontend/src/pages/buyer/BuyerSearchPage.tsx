import { useState, FormEvent } from "react"
import { Link } from "react-router-dom"
import { useQuery, useMutation } from "@tanstack/react-query"
import { useAuth } from "@/contexts/AuthContext"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { PriceDisplay } from "@/components/PriceDisplay"
import { SavingsBadge } from "@/components/SavingsBadge"

interface AgentItem {
  agent_id: string
  name: string
  skill_id: string | null
}

interface NegotiateResult {
  session_id: string
  status: string
  final_price: number | null
  merchant_name: string | null
  product_title: string | null
  max_price_inr: number | null
  winner_merchant_agent_id?: string | null
  anchor_product_id?: string | null
}

interface PaymentOrderResult {
  order_id: string
  amount_paise: number
  key_id: string
  test_mode?: boolean
}

interface ProductSearchResult {
  id: string
  title: string
  listed_price: number
}

type PaymentState = "idle" | "confirming" | "processing" | "success" | "failed"

function PaymentDialog({
  finalPrice,
  state,
  orderId,
  errorMsg,
  onConfirm,
  onClose,
}: {
  finalPrice: number
  state: PaymentState
  orderId?: string
  errorMsg?: string
  onConfirm: () => void
  onClose: () => void
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="bg-white border border-[#D8E1EA] rounded-lg shadow-xl w-full max-w-sm mx-4 p-6 space-y-5">
        {state === "confirming" && (
          <>
            <div className="space-y-1">
              <h2 className="text-base font-semibold text-[#131212]">Confirm Payment</h2>
              <p className="text-sm text-[#6C7F9A]">
                Authorize a test payment of{" "}
                <span className="font-semibold text-[#131212]">
                  ₹{Number(finalPrice).toLocaleString("en-IN")}
                </span>
                . No real money will be charged (sandbox mode).
              </p>
            </div>
            <div className="flex gap-3 justify-end">
              <Button
                variant="ghost"
                onClick={onClose}
                className="border border-[#D8E1EA] text-[#6C7F9A] hover:bg-[#F5F8FA]"
              >
                Cancel
              </Button>
              <Button
                onClick={onConfirm}
                className="bg-[#237B4B] text-white hover:bg-[#1A5F3D] font-medium"
              >
                Pay ₹{Number(finalPrice).toLocaleString("en-IN")}
              </Button>
            </div>
          </>
        )}

        {state === "processing" && (
          <div className="flex flex-col items-center gap-4 py-4">
            <div className="w-8 h-8 border-3 border-[#D8E1EA] border-t-[#237B4B] rounded-full animate-spin" />
            <p className="text-sm text-[#6C7F9A]">Processing payment…</p>
          </div>
        )}

        {state === "success" && (
          <>
            <div className="flex flex-col items-center gap-3 py-2">
              <div className="w-12 h-12 rounded-full bg-[#E6F4EA] flex items-center justify-center text-2xl">
                ✓
              </div>
              <h2 className="text-base font-semibold text-[#131212]">Payment Authorized</h2>
              <p className="text-sm text-[#6C7F9A] text-center">
                ₹{Number(finalPrice).toLocaleString("en-IN")} authorized (sandbox — no real money charged).
              </p>
              {orderId && (
                <p className="font-mono text-xs text-[#9DACBE]">Order: {orderId}</p>
              )}
            </div>
            <Button
              onClick={onClose}
              className="w-full bg-[#237B4B] text-white hover:bg-[#1A5F3D] font-medium"
            >
              Done
            </Button>
          </>
        )}

        {state === "failed" && (
          <>
            <div className="flex flex-col items-center gap-3 py-2">
              <div className="w-12 h-12 rounded-full bg-red-50 flex items-center justify-center text-2xl text-red-500">
                ✕
              </div>
              <h2 className="text-base font-semibold text-[#131212]">Payment Failed</h2>
              <p className="text-sm text-[#AA2C2C] text-center">{errorMsg ?? "Something went wrong."}</p>
            </div>
            <div className="flex gap-3 justify-end">
              <Button
                variant="ghost"
                onClick={onClose}
                className="border border-[#D8E1EA] text-[#6C7F9A] hover:bg-[#F5F8FA]"
              >
                Close
              </Button>
              <Button
                onClick={onConfirm}
                className="bg-[#237B4B] text-white hover:bg-[#1A5F3D] font-medium"
              >
                Retry
              </Button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export function BuyerSearchPage() {
  const { user } = useAuth()
  const [query, setQuery] = useState("")
  const [city, setCity] = useState("")
  const [maxPrice, setMaxPrice] = useState<string>("")
  const [deliveryDays, setDeliveryDays] = useState<string>("15")
  const [selectedAgentId, setSelectedAgentId] = useState<string>("")
  const [result, setResult] = useState<NegotiateResult | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)

  const [dialogOpen, setDialogOpen] = useState(false)
  const [paymentState, setPaymentState] = useState<PaymentState>("idle")
  const [paymentOrderId, setPaymentOrderId] = useState<string | undefined>()
  const [paymentErrorMsg, setPaymentErrorMsg] = useState<string | undefined>()

  const agentsQuery = useQuery<AgentItem[]>({
    queryKey: ["buyer-agents", user?.id],
    queryFn: async () => {
      try {
        const res = await api.get<AgentItem[]>("/buyer/agents")
        return res.data
      } catch {
        return []
      }
    },
  })

  const agents = agentsQuery.data ?? []

  const negotiate = useMutation({
    mutationFn: async () => {
      const agent = agents.find((a) => a.agent_id === selectedAgentId)
      if (!agent) throw new Error("Select an agent first.")
      const privateKey = localStorage.getItem(`sd_agent_pk_${selectedAgentId}`)
      if (!privateKey) throw new Error("Agent key not found. Please create a new agent.")
      const idempotencyKey = `neg-${selectedAgentId}-${Date.now()}`

      let anchorProductId: string | null = null
      try {
        const searchRes = await api.get<ProductSearchResult[]>(`/products/search?q=${encodeURIComponent(query)}`)
        if (searchRes.data && searchRes.data.length > 0) {
          anchorProductId = searchRes.data[0].id
        }
      } catch {
        // non-fatal
      }

      if (anchorProductId) {
        const res = await api.post<NegotiateResult>(
          "/commerce/auction",
          {
            buyer_agent_id: selectedAgentId,
            agent_private_key: privateKey,
            anchor_product_id: anchorProductId,
            num_merchants: 3,
            use_razorpay: false,
            max_budget_inr: maxPrice ? Number(maxPrice) : undefined,
            buyer_priorities: `lowest price, deliver within ${deliveryDays} days${city ? `, location: ${city}` : ""}`,
          },
          { headers: { "Idempotency-Key": idempotencyKey } },
        )
        return { ...res.data, anchor_product_id: anchorProductId }
      } else {
        const listedPrice = maxPrice ? Number(maxPrice) : 1000
        const initialOffer = Math.round(listedPrice * 0.8)
        const res = await api.post<NegotiateResult>(
          "/commerce/negotiate",
          {
            buyer_agent_id: selectedAgentId,
            agent_private_key: privateKey,
            item: query,
            listed_price: listedPrice,
            initial_offer: initialOffer,
            use_razorpay: false,
          },
          { headers: { "Idempotency-Key": idempotencyKey } },
        )
        return res.data
      }
    },
    onSuccess: (data) => {
      setResult(data)
      setSubmitError(null)
      setPaymentState("idle")
      setPaymentOrderId(undefined)
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        (err instanceof Error ? err.message : "Negotiation failed.")
      setSubmitError(msg)
    },
  })

  const authorizePayment = useMutation({
    mutationFn: async () => {
      if (!result?.session_id || result.final_price == null) {
        throw new Error("No settled deal to authorize.")
      }
      const res = await api.post<PaymentOrderResult>("/commerce/create-razorpay-order", {
        session_id: result.session_id,
        amount_inr: result.final_price,
      })
      return res.data
    },
    onSuccess: (data) => {
      setPaymentState("success")
      setPaymentOrderId(data.order_id)
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        (err instanceof Error ? err.message : "Payment authorization failed.")
      setPaymentState("failed")
      setPaymentErrorMsg(msg)
    },
  })

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setResult(null)
    setSubmitError(null)
    setPaymentState("idle")
    setPaymentOrderId(undefined)
    setDialogOpen(false)
    negotiate.mutate()
  }

  function openPaymentDialog() {
    setPaymentState("confirming")
    setPaymentErrorMsg(undefined)
    setDialogOpen(true)
  }

  function handlePaymentConfirm() {
    setPaymentState("processing")
    authorizePayment.mutate()
  }

  function handleDialogClose() {
    if (paymentState === "processing") return // don't close during processing
    setDialogOpen(false)
  }

  const savedAmount =
    result?.final_price != null && result?.max_price_inr != null
      ? result.max_price_inr - result.final_price
      : null
  const savedPct =
    savedAmount != null && result?.max_price_inr
      ? (savedAmount / result.max_price_inr) * 100
      : null

  const inputClass =
    "w-full bg-white border border-[#D8E1EA] rounded-md px-3 py-2 text-sm text-[#131212] placeholder:text-[#9DACBE] focus:outline-none focus:ring-1 focus:ring-[#4F87C8]"

  return (
    <div className="space-y-8 max-w-xl">
      {dialogOpen && result?.final_price != null && (
        <PaymentDialog
          finalPrice={result.final_price}
          state={paymentState}
          orderId={paymentOrderId}
          errorMsg={paymentErrorMsg}
          onConfirm={handlePaymentConfirm}
          onClose={handleDialogClose}
        />
      )}

      <h1 className="text-xl font-semibold text-[#131212]">Search Products</h1>

      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-[#6C7F9A]">What are you looking for?</label>
          <textarea
            required
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            rows={3}
            className={`${inputClass} resize-none`}
            placeholder="Basmati rice 5kg, organic preferred"
          />
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-medium text-[#6C7F9A]">City / Area</label>
          <input
            type="text"
            value={city}
            onChange={(e) => setCity(e.target.value)}
            className={inputClass}
            placeholder="Mumbai, Andheri, Pune…"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-[#6C7F9A]">Max price (₹)</label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-[#6C7F9A]">₹</span>
              <input
                type="number"
                value={maxPrice}
                onChange={(e) => setMaxPrice(e.target.value)}
                className={`${inputClass} pl-6`}
                placeholder="500"
                min={0}
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-medium text-[#6C7F9A]">Delivery by (days)</label>
            <select
              value={deliveryDays}
              onChange={(e) => setDeliveryDays(e.target.value)}
              className={inputClass}
            >
              <option value="10">10 days</option>
              <option value="15">15 days</option>
              <option value="20">20 days</option>
              <option value="30">30 days</option>
            </select>
          </div>
        </div>

        <div className="space-y-2">
          <p className="text-xs font-medium text-[#6C7F9A]">Agent</p>
          {agentsQuery.isLoading ? (
            <p className="text-sm text-[#9DACBE]">Loading agents…</p>
          ) : agents.length === 0 ? (
            <p className="text-sm text-[#6C7F9A]">
              No agents yet.{" "}
              <Link to="/buyer/agents" className="text-[#131212] underline underline-offset-2">
                Create an agent first
              </Link>
            </p>
          ) : (
            <div className="space-y-2">
              {agents.map((agent) => (
                <label
                  key={agent.agent_id}
                  className={`flex items-center gap-3 border rounded-md px-3 py-2.5 cursor-pointer transition-colors ${
                    selectedAgentId === agent.agent_id
                      ? "border-[#237B4B] bg-[#E6F4EA]"
                      : "border-[#D8E1EA] hover:bg-[#F5F8FA]"
                  }`}
                >
                  <input
                    type="radio"
                    name="agent"
                    value={agent.agent_id}
                    checked={selectedAgentId === agent.agent_id}
                    onChange={() => setSelectedAgentId(agent.agent_id)}
                    className="accent-[#237B4B]"
                  />
                  <span className="text-sm text-[#131212]">{agent.name}</span>
                  {agent.skill_id && (
                    <span className="font-mono text-xs text-[#9DACBE]">{agent.skill_id.replace("skill_", "").replace(/_/g, " ")}</span>
                  )}
                </label>
              ))}
            </div>
          )}
        </div>

        {submitError && <p className="text-sm text-[#AA2C2C]">{submitError}</p>}

        <Button
          type="submit"
          disabled={negotiate.isPending || agents.length === 0}
          className="w-full bg-[#237B4B] text-white hover:bg-[#1A5F3D] font-medium"
        >
          {negotiate.isPending ? "Your agent is negotiating…" : "Find & Negotiate"}
        </Button>
      </form>

      {negotiate.isPending && (
        <div className="border border-[#D8E1EA] rounded-md p-6 text-center space-y-2">
          <div className="inline-block w-5 h-5 border-2 border-[#D8E1EA] border-t-[#237B4B] rounded-full animate-spin" />
          <p className="text-sm text-[#6C7F9A]">Your agent is negotiating with merchants…</p>
        </div>
      )}

      {result && (
        <div className="border border-[#D8E1EA] rounded-md overflow-hidden">
          {/* Winner header */}
          <div className="px-6 py-4 space-y-3">
            <div className="flex items-start justify-between gap-4">
              <div className="space-y-0.5">
                <p className="text-xs text-[#9DACBE] uppercase tracking-wider">Winner</p>
                <p className="text-base font-medium text-[#131212]">
                  {result.product_title ?? "Product"}
                </p>
                {result.merchant_name && (
                  <p className="text-sm text-[#6C7F9A]">from {result.merchant_name}</p>
                )}
                {result.anchor_product_id && (
                  <p className="text-xs text-[#9DACBE]">via auction</p>
                )}
              </div>
              {result.final_price != null && (
                <div className="text-right shrink-0">
                  <PriceDisplay amount={result.final_price} className="text-xl text-[#237B4B]" />
                </div>
              )}
            </div>

            {savedAmount != null && savedPct != null && savedAmount > 0 && (
              <SavingsBadge savedAmount={savedAmount} savedPct={savedPct} />
            )}
          </div>

          {/* Payment CTA */}
          {result.status === "settled" && result.final_price != null && (
            <div className="px-6 py-4 border-t border-[#E4EAF1] bg-[#F5F8FA]">
              {paymentState === "success" ? (
                <div className="flex items-center gap-3">
                  <span className="text-[#237B4B] text-lg font-bold">✓</span>
                  <div>
                    <p className="text-sm font-medium text-[#131212]">Payment authorized</p>
                    <p className="text-xs text-[#9DACBE]">Sandbox — no real money charged. Order: {paymentOrderId}</p>
                  </div>
                </div>
              ) : (
                <Button
                  type="button"
                  onClick={openPaymentDialog}
                  className="w-full bg-[#237B4B] text-white hover:bg-[#1A5F3D] font-medium"
                >
                  Authorize Payment · ₹{Number(result.final_price).toLocaleString("en-IN")}
                </Button>
              )}
            </div>
          )}

          {/* View full deal link */}
          <div className="px-6 py-3 border-t border-[#E4EAF1]">
            <Link
              to={`/buyer/deal/${result.session_id}`}
              className="text-sm text-[#237B4B] hover:text-[#1A5F3D] underline underline-offset-2"
            >
              View full deal →
            </Link>
          </div>
        </div>
      )}
    </div>
  )
}
