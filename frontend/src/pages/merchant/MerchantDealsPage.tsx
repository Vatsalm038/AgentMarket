import { Link } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { useAuth } from "@/contexts/AuthContext"
import { api } from "@/lib/api"
import { Deal } from "@/types"
import { StatusBadge } from "@/components/StatusBadge"
import { PriceDisplay } from "@/components/PriceDisplay"

export function MerchantDealsPage() {
  const { user } = useAuth()

  const { data, isLoading, isError } = useQuery<Deal[]>({
    queryKey: ["merchant-deals", user?.id],
    queryFn: async () => {
      const res = await api.get<Deal[]>("/merchant/deals")
      return res.data
    },
  })

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-zinc-100">Deals</h1>

      {isLoading ? (
        <div className="space-y-2 animate-pulse">
          {[1, 2, 3, 4].map((i) => <div key={i} className="h-12 bg-zinc-800 rounded-md" />)}
        </div>
      ) : isError ? (
        <p className="text-sm text-red-400">Failed to load deals.</p>
      ) : !data || data.length === 0 ? (
        <div className="text-center py-16 border border-zinc-800 rounded-md">
          <p className="text-sm text-zinc-500">No deals yet.</p>
        </div>
      ) : (
        <div className="border border-zinc-700 rounded-md overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-zinc-800 border-b border-zinc-700">
                {["Session ID", "Status", "Final Price", "Date"].map((h) => (
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
              {data.map((deal) => (
                <tr
                  key={deal.id}
                  className="border-b border-zinc-800 last:border-0 hover:bg-zinc-800 transition-colors"
                >
                  <td className="px-4 py-3">
                    <Link
                      to={`/merchant/deal/${deal.id}`}
                      className="font-mono text-xs text-zinc-400 hover:text-zinc-100"
                    >
                      {deal.id.slice(0, 12)}…
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={deal.status} />
                  </td>
                  <td className="px-4 py-3 text-zinc-300">
                    {deal.final_price != null ? (
                      <PriceDisplay amount={deal.final_price} />
                    ) : (
                      <span className="text-zinc-600">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-zinc-600">
                    {new Date(deal.created_at).toLocaleDateString("en-IN")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
