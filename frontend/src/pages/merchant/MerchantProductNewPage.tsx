import { useState, FormEvent } from "react"
import { useNavigate } from "react-router-dom"
import { useMutation } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"

const CATEGORIES = ["groceries", "electronics", "clothing", "home", "food", "other"] as const

export function MerchantProductNewPage() {
  const navigate = useNavigate()

  const [title, setTitle] = useState("")
  const [description, setDescription] = useState("")
  const [category, setCategory] = useState<string>("groceries")
  const [floorPrice, setFloorPrice] = useState("")
  const [listedPrice, setListedPrice] = useState("")
  const [deliveryRadius, setDeliveryRadius] = useState("")
  const [deliveryMin, setDeliveryMin] = useState("")
  const [deliveryMax, setDeliveryMax] = useState("")
  const [imageUrl, setImageUrl] = useState("")
  const [formError, setFormError] = useState<string | null>(null)

  const create = useMutation({
    mutationFn: async () => {
      await api.post("/merchant/products", {
        title,
        description,
        category,
        floor_price_inr: Number(floorPrice),
        listed_price_inr: Number(listedPrice),
        delivery_radius_km: deliveryRadius ? Number(deliveryRadius) : null,
        delivery_days_min: deliveryMin ? Number(deliveryMin) : null,
        delivery_days_max: deliveryMax ? Number(deliveryMax) : null,
        image_url: imageUrl || null,
      })
    },
    onSuccess: () => {
      navigate("/merchant/products", { replace: true })
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Failed to create product."
      setFormError(msg)
    },
  })

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setFormError(null)
    if (Number(floorPrice) > Number(listedPrice)) {
      setFormError("Floor price cannot exceed listed price.")
      return
    }
    create.mutate()
  }

  const inputClass =
    "w-full bg-zinc-800 border border-zinc-700 rounded-md px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-zinc-500"

  return (
    <div className="space-y-6 max-w-xl">
      <h1 className="text-xl font-semibold text-zinc-100">New Product</h1>

      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-zinc-400">Title</label>
          <input
            required
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className={inputClass}
            placeholder="Basmati Rice 5kg"
          />
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-medium text-zinc-400">Description</label>
          <textarea
            required
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className={`${inputClass} resize-none`}
            placeholder="Premium aged basmati rice, sourced from Punjab…"
          />
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-medium text-zinc-400">Category</label>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className={inputClass}
          >
            {CATEGORIES.map((c) => (
              <option key={c} value={c} className="capitalize">
                {c.charAt(0).toUpperCase() + c.slice(1)}
              </option>
            ))}
          </select>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-zinc-400">Floor Price (₹)</label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-zinc-500">₹</span>
              <input
                required
                type="number"
                min={0}
                value={floorPrice}
                onChange={(e) => setFloorPrice(e.target.value)}
                className={`${inputClass} pl-6`}
                placeholder="350"
              />
            </div>
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-zinc-400">Listed Price (₹)</label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-zinc-500">₹</span>
              <input
                required
                type="number"
                min={0}
                value={listedPrice}
                onChange={(e) => setListedPrice(e.target.value)}
                className={`${inputClass} pl-6`}
                placeholder="500"
              />
            </div>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4">
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-zinc-400">Delivery radius (km)</label>
            <input
              type="number"
              min={0}
              value={deliveryRadius}
              onChange={(e) => setDeliveryRadius(e.target.value)}
              className={inputClass}
              placeholder="25"
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-zinc-400">Min days</label>
            <input
              type="number"
              min={0}
              value={deliveryMin}
              onChange={(e) => setDeliveryMin(e.target.value)}
              className={inputClass}
              placeholder="2"
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-zinc-400">Max days</label>
            <input
              type="number"
              min={0}
              value={deliveryMax}
              onChange={(e) => setDeliveryMax(e.target.value)}
              className={inputClass}
              placeholder="7"
            />
          </div>
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-medium text-zinc-400">
            Image URL (optional, upload coming soon)
          </label>
          <input
            type="url"
            value={imageUrl}
            onChange={(e) => setImageUrl(e.target.value)}
            className={inputClass}
            placeholder="https://example.com/image.jpg"
          />
        </div>

        {formError && <p className="text-sm text-red-400">{formError}</p>}

        <Button
          type="submit"
          disabled={create.isPending}
          className="w-full bg-zinc-100 text-zinc-900 hover:bg-zinc-200 font-medium"
        >
          {create.isPending ? "Creating…" : "Create Product"}
        </Button>
      </form>
    </div>
  )
}
