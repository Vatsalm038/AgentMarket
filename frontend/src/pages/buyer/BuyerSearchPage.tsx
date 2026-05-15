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

  const agentsQuery = useQuery<AgentItem[]>({
    queryKey: ["agents", user?.id],
    queryFn: async () => {
      const res = await api.get<AgentItem[]>("/agents")
      return res.data
    },
  })

  const agents = agentsQuery.data ?? []

  const negotiate = useMutation({
    mutationFn: async () => {
      const agent = agents.find((a) => a.agent_id === selectedAgentId)
      if (!agent) throw new Error("Select an agent first.")
      const res = await api.post<NegotiateResult>("/commerce/negotiate", {
        buyer_agent_id: selectedAgentId,
        product_description: query,
        location: city,
        max_price_inr: maxPrice ? Number(maxPrice) : undefined,
        skill_id: agent.skill_id,
        delivery_days: Number(deliveryDays),
      })
      return res.data
    },
    onSuccess: (data) => {
      setResult(data)
      setSubmitError(null)
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        (err instanceof Error ? err.message : "Negotiation failed.")
      setSubmitError(msg)
    },
  })

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setResult(null)
    setSubmitError(null)
    negotiate.mutate()
  }

  const savedAmount =
    result?.final_price != null && result?.max_price_inr != null
      ? result.max_price_inr - result.final_price
      : null
  const savedPct =
    savedAmount != null && result?.max_price_inr
      ? (savedAmount / result.max_price_inr) * 100
      : null

  return (
    <div className="space-y-8 max-w-xl">
      <h1 className="text-xl font-semibold text-zinc-100">Search Products</h1>

      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-zinc-400">What are you looking for?</label>
          <textarea
            required
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            rows={3}
            className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-zinc-500 resize-none"
            placeholder="Basmati rice 5kg, organic preferred"
          />
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-medium text-zinc-400">City / Area</label>
          <input
            type="text"
            value={city}
            onChange={(e) => setCity(e.target.value)}
            className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-zinc-500"
            placeholder="Mumbai, Andheri, Pune…"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-zinc-400">Max price (₹)</label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-zinc-500">₹</span>
              <input
                type="number"
                value={maxPrice}
                onChange={(e) => setMaxPrice(e.target.value)}
                className="w-full bg-zinc-800 border border-zinc-700 rounded-md pl-6 pr-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-zinc-500"
                placeholder="500"
                min={0}
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-medium text-zinc-400">Delivery by (days)</label>
            <select
              value={deliveryDays}
              onChange={(e) => setDeliveryDays(e.target.value)}
              className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:ring-1 focus:ring-zinc-500"
            >
              <option value="10">10 days</option>
              <option value="15">15 days</option>
              <option value="20">20 days</option>
              <option value="30">30 days</option>
            </select>
          </div>
        </div>

        <div className="space-y-2">
          <p className="text-xs font-medium text-zinc-400">Agent</p>
          {agentsQuery.isLoading ? (
            <p className="text-sm text-zinc-600">Loading agents…</p>
          ) : agents.length === 0 ? (
            <p className="text-sm text-zinc-500">
              No agents yet.{" "}
              <Link to="/buyer/agents" className="text-zinc-300 underline underline-offset-2">
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
                      ? "border-emerald-500 bg-emerald-500/5"
                      : "border-zinc-700 hover:border-zinc-600"
                  }`}
                >
                  <input
                    type="radio"
                    name="agent"
                    value={agent.agent_id}
                    checked={selectedAgentId === agent.agent_id}
                    onChange={() => setSelectedAgentId(agent.agent_id)}
                    className="accent-emerald-500"
                  />
                  <span className="text-sm text-zinc-200">{agent.name}</span>
                  {agent.skill_id && (
                    <span className="font-mono text-xs text-zinc-600">{agent.skill_id.slice(0, 8)}…</span>
                  )}
                </label>
              ))}
            </div>
          )}
        </div>

        {submitError && <p className="text-sm text-red-400">{submitError}</p>}

        <Button
          type="submit"
          disabled={negotiate.isPending || agents.length === 0}
          className="w-full bg-zinc-100 text-zinc-900 hover:bg-zinc-200 font-medium"
        >
          {negotiate.isPending ? "Your agent is negotiating…" : "Find & Negotiate"}
        </Button>
      </form>

      {/* Loading state */}
      {negotiate.isPending && (
        <div className="border border-zinc-700 rounded-md p-6 text-center space-y-2">
          <div className="inline-block w-5 h-5 border-2 border-zinc-600 border-t-emerald-500 rounded-full animate-spin" />
          <p className="text-sm text-zinc-400">Your agent is negotiating with merchants…</p>
        </div>
      )}

      {/* Result */}
      {result && (
        <div className="border border-zinc-700 rounded-md p-6 space-y-3">
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-0.5">
              <p className="text-xs text-zinc-500 uppercase tracking-wider">Result</p>
              <p className="text-base font-medium text-zinc-100">
                {result.product_title ?? "Product"}
              </p>
              {result.merchant_name && (
                <p className="text-sm text-zinc-500">from {result.merchant_name}</p>
              )}
            </div>
            {result.final_price != null && (
              <div className="text-right shrink-0">
                <PriceDisplay amount={result.final_price} className="text-xl text-emerald-400" />
              </div>
            )}
          </div>

          {savedAmount != null && savedPct != null && savedAmount > 0 && (
            <SavingsBadge savedAmount={savedAmount} savedPct={savedPct} />
          )}

          <Link
            to={`/session/${result.session_id}`}
            className="inline-block mt-2 text-sm text-zinc-300 underline underline-offset-2 hover:text-zinc-100"
          >
            View Full Deal →
          </Link>
        </div>
      )}
    </div>
  )
}
