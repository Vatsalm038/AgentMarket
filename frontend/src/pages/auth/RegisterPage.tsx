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
  const [isBuyer, setIsBuyer] = useState(false)
  const [isMerchant, setIsMerchant] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isPending, setIsPending] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)

    if (!isBuyer && !isMerchant) {
      setError("Select at least one role.")
      return
    }

    setIsPending(true)
    try {
      const res = await api.post<{ access_token: string; user: AuthUser }>("/auth/register", {
        email,
        password,
        display_name: displayName || null,
        is_buyer: isBuyer,
        is_merchant: isMerchant,
      })
      const { access_token, user } = res.data
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

  const roleCardBase =
    "flex-1 border rounded-md p-4 cursor-pointer transition-colors text-left space-y-1 select-none"
  const roleCardActive = "border-emerald-500 bg-emerald-500/5"
  const roleCardInactive = "border-zinc-700 bg-zinc-800 hover:border-zinc-600"

  return (
    <div className="w-full max-w-sm bg-zinc-900 border border-zinc-800 rounded-md p-8 space-y-6">
      <div className="space-y-1">
        <h1 className="text-xl font-semibold text-zinc-100">Create account</h1>
        <p className="text-sm text-zinc-500">Join SignedDeals today.</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-zinc-400" htmlFor="display_name">
            Display name (optional)
          </label>
          <input
            id="display_name"
            type="text"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-zinc-500"
            placeholder="Ravi Sharma"
          />
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-medium text-zinc-400" htmlFor="reg_email">
            Email
          </label>
          <input
            id="reg_email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-zinc-500"
            placeholder="you@example.com"
          />
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-medium text-zinc-400" htmlFor="reg_password">
            Password
          </label>
          <input
            id="reg_password"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-zinc-500"
            placeholder="••••••••"
          />
        </div>

        <div className="space-y-2">
          <p className="text-xs font-medium text-zinc-400">I want to…</p>
          <div className="flex gap-3">
            <button
              type="button"
              onClick={() => setIsBuyer((v) => !v)}
              className={`${roleCardBase} ${isBuyer ? roleCardActive : roleCardInactive}`}
            >
              <p className={`text-sm font-medium ${isBuyer ? "text-emerald-400" : "text-zinc-200"}`}>
                Buy
              </p>
              <p className="text-xs text-zinc-500">Search products, run agents</p>
            </button>
            <button
              type="button"
              onClick={() => setIsMerchant((v) => !v)}
              className={`${roleCardBase} ${isMerchant ? roleCardActive : roleCardInactive}`}
            >
              <p className={`text-sm font-medium ${isMerchant ? "text-emerald-400" : "text-zinc-200"}`}>
                Sell
              </p>
              <p className="text-xs text-zinc-500">List products, fulfill orders</p>
            </button>
          </div>
        </div>

        {error && <p className="text-sm text-red-400">{error}</p>}

        <Button
          type="submit"
          disabled={isPending}
          className="w-full bg-zinc-100 text-zinc-900 hover:bg-zinc-200 font-medium"
        >
          {isPending ? "Creating account…" : "Create account"}
        </Button>
      </form>

      <p className="text-sm text-zinc-500 text-center">
        Already have an account?{" "}
        <Link to="/login" className="text-zinc-300 hover:text-zinc-100 underline underline-offset-2">
          Sign in
        </Link>
      </p>
    </div>
  )
}
