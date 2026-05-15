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
      <h1 className="text-xl font-semibold text-[#131212]">Deals</h1>

      {isLoading ? (
        <div className="space-y-2 animate-pulse">
          {[1, 2, 3, 4].map((i) => <div key={i} className="h-12 bg-[#E4EAF1] rounded-md" />)}
        </div>
      ) : isError ? (
        <p className="text-sm text-[#AA2C2C]">Failed to load deals.</p>
      ) : !data || data.length === 0 ? (
        <div className="text-center py-16 border border-[#D8E1EA] rounded-md">
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
              {data.map((deal) => (
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
  )
}
