import { Link } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { useAuth } from "@/contexts/AuthContext"
import { api } from "@/lib/api"
import { Deal } from "@/types"
import { PriceDisplay } from "@/components/PriceDisplay"

const STEPS = ["Negotiated", "Paid", "Delivered"] as const

function DealProgress({ status }: { status: string }) {
  const doneIndex =
    status === "delivered" ? 2
    : status === "paid" ? 1
    : status === "settled" ? 0
    : -1

  return (
    <div className="flex items-center gap-1">
      {STEPS.map((step, i) => {
        const done = i <= doneIndex
        const current = i === doneIndex
        return (
          <div key={step} className="flex items-center gap-1">
            <div className="flex flex-col items-center gap-0.5">
              <div
                className={`w-2 h-2 rounded-full ${
                  done ? "bg-[#237B4B]" : "bg-[#D8E1EA]"
                } ${current ? "ring-2 ring-[#237B4B]/30" : ""}`}
              />
              <span
                className={`text-[10px] whitespace-nowrap ${
                  done ? "text-[#237B4B] font-medium" : "text-[#9DACBE]"
                }`}
              >
                {step}
              </span>
            </div>
            {i < STEPS.length - 1 && (
              <div
                className={`w-6 h-px mb-3 ${i < doneIndex ? "bg-[#237B4B]" : "bg-[#D8E1EA]"}`}
              />
            )}
          </div>
        )
      })}
    </div>
  )
}

export function BuyerDealsPage() {
  const { user } = useAuth()

  const { data, isLoading, isError } = useQuery<Deal[]>({
    queryKey: ["buyer-deals", user?.id],
    queryFn: async () => {
      const res = await api.get<Deal[]>("/buyer/deals")
      return res.data
    },
  })

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-[#131212]">My Deals</h1>

      {isLoading ? (
        <div className="space-y-2 animate-pulse">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-16 bg-[#E4EAF1] rounded-md" />
          ))}
        </div>
      ) : isError ? (
        <p className="text-sm text-[#AA2C2C]">Failed to load deals.</p>
      ) : !data || data.length === 0 ? (
        <div className="text-center py-16 border border-[#D8E1EA] rounded-md">
          <p className="text-sm text-[#6C7F9A]">No deals yet.</p>
          <Link
            to="/buyer/search"
            className="mt-2 inline-block text-sm text-[#131212] underline underline-offset-2"
          >
            Start a search
          </Link>
        </div>
      ) : (
        <div className="border border-[#D8E1EA] rounded-md overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-[#F5F8FA] border-b border-[#D8E1EA]">
                {["Deal", "Progress", "Price", "Action"].map((h) => (
                  <th
                    key={h}
                    className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-[#9DACBE]"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.map((deal) => {
                const needsPayment = deal.status === "settled"
                return (
                  <tr
                    key={deal.id}
                    className="border-b border-[#E4EAF1] last:border-0 hover:bg-[#F5F8FA] transition-colors"
                  >
                    <td className="px-4 py-3">
                      <div className="space-y-0.5">
                        <Link
                          to={`/buyer/deal/${deal.id}`}
                          className="font-mono text-xs text-[#6C7F9A] hover:text-[#131212]"
                        >
                          {deal.id.slice(0, 12)}…
                        </Link>
                        <p className="text-xs text-[#9DACBE]">
                          {new Date(deal.created_at).toLocaleDateString("en-IN")}
                        </p>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <DealProgress status={deal.status} />
                    </td>
                    <td className="px-4 py-3 text-[#131212]">
                      {deal.final_price != null ? (
                        <PriceDisplay amount={deal.final_price} />
                      ) : (
                        <span className="text-[#9DACBE]">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {needsPayment ? (
                        <Link
                          to={`/buyer/deal/${deal.id}`}
                          className="inline-flex items-center gap-1 text-xs font-medium text-white bg-[#237B4B] hover:bg-[#1A5F3D] px-3 py-1.5 rounded-md transition-colors"
                        >
                          Pay now
                        </Link>
                      ) : (
                        <Link
                          to={`/buyer/deal/${deal.id}`}
                          className="text-xs text-[#6C7F9A] hover:text-[#131212] underline underline-offset-2"
                        >
                          View
                        </Link>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
