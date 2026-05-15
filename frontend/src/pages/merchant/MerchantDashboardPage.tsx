import { Link } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { useAuth } from "@/contexts/AuthContext"
import { api } from "@/lib/api"
import { Deal } from "@/types"
import { StatusBadge } from "@/components/StatusBadge"
import { PriceDisplay } from "@/components/PriceDisplay"

interface MerchantStats {
  active_listings: number
  pending_deliveries: number
  total_deals: number
  total_revenue_inr: number
}

function StatCard({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="bg-white border border-[#D8E1EA] rounded-md p-5">
      <p className="text-xs text-[#9DACBE] uppercase tracking-wider mb-1">{label}</p>
      <div className="text-2xl font-semibold text-[#131212]">{value}</div>
    </div>
  )
}

export function MerchantDashboardPage() {
  const { user } = useAuth()

  const statsQuery = useQuery<MerchantStats>({
    queryKey: ["merchant-stats", user?.id],
    queryFn: async () => {
      const res = await api.get<MerchantStats>("/merchant/stats")
      return res.data
    },
  })

  const dealsQuery = useQuery<Deal[]>({
    queryKey: ["merchant-deals", user?.id],
    queryFn: async () => {
      const res = await api.get<Deal[]>("/merchant/deals")
      return res.data
    },
  })

  const recentDeals = dealsQuery.data?.slice(0, 5) ?? []

  return (
    <div className="space-y-8">
      <h1 className="text-xl font-semibold text-[#131212]">Merchant Dashboard</h1>

      <div className="grid grid-cols-4 gap-4">
        {statsQuery.isLoading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-24 bg-white border border-[#D8E1EA] rounded-md animate-pulse" />
          ))
        ) : statsQuery.isError ? (
          <p className="col-span-4 text-sm text-[#AA2C2C]">Failed to load stats.</p>
        ) : (
          <>
            <StatCard label="Active Listings" value={statsQuery.data?.active_listings ?? 0} />
            <StatCard label="Pending Deliveries" value={statsQuery.data?.pending_deliveries ?? 0} />
            <StatCard label="Total Deals" value={statsQuery.data?.total_deals ?? 0} />
            <StatCard
              label="Revenue"
              value={
                <PriceDisplay
                  amount={statsQuery.data?.total_revenue_inr ?? 0}
                  className="text-sky-600"
                />
              }
            />
          </>
        )}
      </div>

      <div>
        <h2 className="text-sm font-medium text-[#6C7F9A] mb-3">Recent Deals</h2>
        {dealsQuery.isLoading ? (
          <div className="space-y-2 animate-pulse">
            {[1, 2, 3].map((i) => <div key={i} className="h-12 bg-[#E4EAF1] rounded-md" />)}
          </div>
        ) : dealsQuery.isError ? (
          <p className="text-sm text-[#AA2C2C]">Failed to load deals.</p>
        ) : recentDeals.length === 0 ? (
          <div className="text-center py-12 border border-[#D8E1EA] rounded-md">
            <p className="text-sm text-[#6C7F9A]">No deals yet.</p>
          </div>
        ) : (
          <div className="border border-[#D8E1EA] rounded-md overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-[#F5F8FA] border-b border-[#D8E1EA]">
                  {["Session ID", "Status", "Final Price", "Date"].map((h) => (
                    <th
                      key={h}
                      className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wide text-[#9DACBE]"
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
                    className="border-b border-[#E4EAF1] last:border-0 hover:bg-[#F5F8FA] transition-colors"
                  >
                    <td className="px-4 py-3">
                      <Link
                        to={`/merchant/deal/${deal.id}`}
                        className="font-mono text-xs text-[#6C7F9A] hover:text-[#131212]"
                      >
                        {deal.id.slice(0, 12)}…
                      </Link>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={deal.status} />
                    </td>
                    <td className="px-4 py-3 text-[#131212]">
                      {deal.final_price != null ? (
                        <PriceDisplay amount={deal.final_price} />
                      ) : (
                        <span className="text-[#9DACBE]">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-[#9DACBE]">
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
