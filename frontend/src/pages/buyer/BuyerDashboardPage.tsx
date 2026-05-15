import { Link } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { useAuth } from "@/contexts/AuthContext"
import { api } from "@/lib/api"
import { Deal } from "@/types"
import { StatusBadge } from "@/components/StatusBadge"
import { PriceDisplay } from "@/components/PriceDisplay"

interface BuyerStats {
  total_deals: number
  total_saved_inr: number
  active_agents: number
}

function StatCard({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="bg-zinc-800 border border-zinc-700 rounded-md p-5">
      <p className="text-xs text-zinc-500 uppercase tracking-wider mb-1">{label}</p>
      <div className="text-2xl font-semibold text-zinc-100">{value}</div>
    </div>
  )
}

function SkeletonCard() {
  return <div className="h-24 bg-zinc-800 border border-zinc-700 rounded-md animate-pulse" />
}

export function BuyerDashboardPage() {
  const { user } = useAuth()

  const statsQuery = useQuery<BuyerStats>({
    queryKey: ["buyer-stats", user?.id],
    queryFn: async () => {
      const res = await api.get<BuyerStats>("/buyer/stats")
      return res.data
    },
  })

  const dealsQuery = useQuery<Deal[]>({
    queryKey: ["buyer-deals", user?.id],
    queryFn: async () => {
      const res = await api.get<Deal[]>("/buyer/deals")
      return res.data
    },
  })

  const recentDeals = dealsQuery.data?.slice(0, 5) ?? []

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-zinc-100">Buyer Dashboard</h1>
        <Link
          to="/buyer/search"
          className="text-sm text-zinc-400 hover:text-zinc-100 border border-zinc-700 px-3 py-1.5 rounded-md transition-colors"
        >
          Start searching →
        </Link>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        {statsQuery.isLoading ? (
          <>
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </>
        ) : statsQuery.isError ? (
          <p className="col-span-3 text-sm text-red-400">Failed to load stats.</p>
        ) : (
          <>
            <StatCard label="Total Deals" value={statsQuery.data?.total_deals ?? 0} />
            <StatCard
              label="Money Saved"
              value={
                <PriceDisplay
                  amount={statsQuery.data?.total_saved_inr ?? 0}
                  className="text-emerald-400"
                />
              }
            />
            <StatCard label="Active Agents" value={statsQuery.data?.active_agents ?? 0} />
          </>
        )}
      </div>

      {/* Recent deals */}
      <div>
        <h2 className="text-sm font-medium text-zinc-500 mb-3">Recent Deals</h2>
        {dealsQuery.isLoading ? (
          <div className="space-y-2 animate-pulse">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-12 bg-zinc-800 rounded-md" />
            ))}
          </div>
        ) : dealsQuery.isError ? (
          <p className="text-sm text-red-400">Failed to load deals.</p>
        ) : recentDeals.length === 0 ? (
          <div className="text-center py-12 border border-zinc-800 rounded-md">
            <p className="text-sm text-zinc-500">No deals yet.</p>
            <Link to="/buyer/search" className="mt-2 inline-block text-sm text-zinc-300 underline underline-offset-2">
              Start a search
            </Link>
          </div>
        ) : (
          <div className="border border-zinc-700 rounded-md overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-zinc-800 border-b border-zinc-700">
                  {["Status", "Final Price", "Date"].map((h) => (
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
                {recentDeals.map((deal) => (
                  <tr
                    key={deal.id}
                    className="border-b border-zinc-800 last:border-0 hover:bg-zinc-800 transition-colors"
                  >
                    <td className="px-4 py-3">
                      <Link to={`/buyer/deal/${deal.id}`}>
                        <StatusBadge status={deal.status} />
                      </Link>
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
    </div>
  )
}
