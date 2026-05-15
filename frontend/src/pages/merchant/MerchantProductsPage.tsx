import { Link } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { useAuth } from "@/contexts/AuthContext"
import { api } from "@/lib/api"
import { Product } from "@/types"
import { PriceDisplay } from "@/components/PriceDisplay"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"

export function MerchantProductsPage() {
  const { user } = useAuth()

  const { data, isLoading, isError } = useQuery<Product[]>({
    queryKey: ["merchant-products", user?.id],
    queryFn: async () => {
      const res = await api.get<Product[]>("/merchant/products")
      return res.data
    },
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-[#131212]">Products</h1>
        <Link to="/merchant/products/new">
          <Button className="bg-[#237B4B] text-white hover:bg-[#1A5F3D] font-medium text-sm">
            New Product
          </Button>
        </Link>
      </div>

      {isLoading ? (
        <div className="space-y-2 animate-pulse">
          {[1, 2, 3].map((i) => <div key={i} className="h-12 bg-[#E4EAF1] rounded-md" />)}
        </div>
      ) : isError ? (
        <p className="text-sm text-[#AA2C2C]">Failed to load products.</p>
      ) : !data || data.length === 0 ? (
        <div className="text-center py-16 border border-[#D8E1EA] rounded-md">
          <p className="text-sm text-[#6C7F9A]">No products listed yet.</p>
          <Link
            to="/merchant/products/new"
            className="mt-2 inline-block text-sm text-[#131212] underline underline-offset-2"
          >
            Add your first product
          </Link>
        </div>
      ) : (
        <div className="border border-[#D8E1EA] rounded-md overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-[#F5F8FA] border-b border-[#D8E1EA]">
                {["Title", "Category", "Floor Price", "Listed Price", "Status"].map((h) => (
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
              {data.map((product) => (
                <tr
                  key={product.id}
                  className="border-b border-[#E4EAF1] last:border-0 hover:bg-[#F5F8FA] transition-colors"
                >
                  <td className="px-4 py-3 text-[#131212]">{product.title}</td>
                  <td className="px-4 py-3 text-[#6C7F9A] capitalize">{product.category}</td>
                  <td className="px-4 py-3">
                    <PriceDisplay amount={product.floor_price_inr} />
                  </td>
                  <td className="px-4 py-3">
                    <PriceDisplay amount={product.listed_price_inr} />
                  </td>
                  <td className="px-4 py-3">
                    <Badge
                      variant="outline"
                      className={
                        product.is_active
                          ? "border-[#237B4B] text-[#237B4B] text-xs"
                          : "border-[#D8E1EA] text-[#9DACBE] text-xs"
                      }
                    >
                      {product.is_active ? "Active" : "Paused"}
                    </Badge>
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
