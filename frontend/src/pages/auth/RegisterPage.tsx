import { useState, FormEvent } from "react"
import { Link, useNavigate } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { useAuth } from "@/contexts/AuthContext"
import { api } from "@/lib/api"
import { AuthUser } from "@/types"

export function RegisterPage() {
  const { login } = useAuth()
  const navigate = useNavigate()

  const [displayName, setDisplayName] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [isPending, setIsPending] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)

    if (!role) {
      setError("Select a role to continue.")
      return
    }

    setIsPending(true)
    try {
      const res = await api.post<{
        access_token: string
        user_id: string
        email: string
        is_buyer: boolean
        is_merchant: boolean
      }>("/auth/register", {
        email,
        password,
        display_name: displayName || null,
        is_buyer: role === "buyer",
        is_merchant: role === "merchant",
      })
      const { access_token, user_id, email: userEmail, is_buyer, is_merchant } = res.data
      const user: AuthUser = { id: user_id, email: userEmail, display_name: displayName || null, is_buyer, is_merchant }
      login(access_token, user)
      navigate(user.is_buyer ? "/buyer/dashboard" : "/merchant/dashboard", { replace: true })
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Registration failed. Try a different email."
      setError(msg)
    } finally {
      setIsPending(false)
    }
  }

  type Role = "buyer" | "merchant" | null
  const [role, setRole] = useState<Role>(null)
  const isBuyerSelected = role === "buyer"
  const isMerchantSelected = role === "merchant"

  const roleCardBase =
    "w-full border rounded-md p-4 cursor-pointer transition-colors text-left space-y-1 select-none"
  const roleCardActive = "border-[#237B4B] bg-[#E6F4EA]"
  const roleCardInactive = "border-[#D8E1EA] bg-[#F5F8FA] hover:border-[#B9C6D8]"

  return (
    <div className="w-full max-w-sm bg-white border border-[#D8E1EA] rounded-lg p-8 space-y-6">
      <div className="space-y-1">
        <h1 className="text-xl font-semibold text-[#131212]">Create account</h1>
        <p className="text-sm text-[#6C7F9A]">Join SignedDeals today.</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-[#6C7F9A]" htmlFor="display_name">
            Display name (optional)
          </label>
          <input
            id="display_name"
            type="text"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            className="w-full bg-[#F5F8FA] border border-[#D8E1EA] rounded-md px-3 py-2 text-sm text-[#131212] placeholder-[#9DACBE] focus:outline-none focus:ring-1 focus:ring-[#4F87C8] focus:border-[#4F87C8]"
            placeholder="Ravi Sharma"
          />
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-medium text-[#6C7F9A]" htmlFor="reg_email">
            Email
          </label>
          <input
            id="reg_email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full bg-[#F5F8FA] border border-[#D8E1EA] rounded-md px-3 py-2 text-sm text-[#131212] placeholder-[#9DACBE] focus:outline-none focus:ring-1 focus:ring-[#4F87C8] focus:border-[#4F87C8]"
            placeholder="you@example.com"
          />
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-medium text-[#6C7F9A]" htmlFor="reg_password">
            Password
          </label>
          <input
            id="reg_password"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full bg-[#F5F8FA] border border-[#D8E1EA] rounded-md px-3 py-2 text-sm text-[#131212] placeholder-[#9DACBE] focus:outline-none focus:ring-1 focus:ring-[#4F87C8] focus:border-[#4F87C8]"
            placeholder="••••••••"
          />
        </div>

        <div className="space-y-2">
          <p className="text-xs font-medium text-[#6C7F9A]">I want to…</p>
          <div className="flex flex-col gap-2">
            <button
              type="button"
              onClick={() => setRole("buyer")}
              className={`${roleCardBase} ${isBuyerSelected ? roleCardActive : roleCardInactive}`}
            >
              <p className={`text-sm font-medium ${isBuyerSelected ? "text-[#237B4B]" : "text-[#131212]"}`}>
                Buy
              </p>
              <p className="text-xs text-[#6C7F9A]">Search products, run agents</p>
            </button>
            <button
              type="button"
              onClick={() => setRole("merchant")}
              className={`${roleCardBase} ${isMerchantSelected ? roleCardActive : roleCardInactive}`}
            >
              <p className={`text-sm font-medium ${isMerchantSelected ? "text-[#237B4B]" : "text-[#131212]"}`}>
                Sell
              </p>
              <p className="text-xs text-[#6C7F9A]">List products, fulfill orders</p>
            </button>
          </div>
        </div>

        {error && <p className="text-sm text-[#AA2C2C]">{error}</p>}

        <Button
          type="submit"
          disabled={isPending}
          className="w-full bg-[#237B4B] text-white hover:bg-[#1A5F3D] font-medium rounded-md py-2 text-sm"
        >
          {isPending ? "Creating account…" : "Create account"}
        </Button>
      </form>

      <p className="text-sm text-[#6C7F9A] text-center">
        Already have an account?{" "}
        <Link to="/login" className="text-[#237B4B] hover:text-[#1A5F3D] underline underline-offset-2">
          Sign in
        </Link>
      </p>
    </div>
  )
}
