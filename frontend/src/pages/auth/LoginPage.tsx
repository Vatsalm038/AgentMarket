import { useState, FormEvent } from "react"
import { Link, useNavigate, useSearchParams } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { useAuth } from "@/contexts/AuthContext"
import { api } from "@/lib/api"
import { AuthUser } from "@/types"

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()

  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [isPending, setIsPending] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setIsPending(true)
    try {
      const res = await api.post<{
        access_token: string
        user_id: string
        email: string
        is_buyer: boolean
        is_merchant: boolean
      }>("/auth/login", { email, password })
      const { access_token, user_id, email: userEmail, is_buyer, is_merchant } = res.data
      const user: AuthUser = { id: user_id, email: userEmail, display_name: null, is_buyer, is_merchant }
      login(access_token, user)
      const next = params.get("next")
      if (next) {
        navigate(next, { replace: true })
      } else if (user.is_buyer) {
        navigate("/buyer/dashboard", { replace: true })
      } else {
        navigate("/merchant/dashboard", { replace: true })
      }
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Invalid email or password."
      setError(msg)
    } finally {
      setIsPending(false)
    }
  }

  return (
    <div className="w-full max-w-sm bg-white border border-[#D8E1EA] rounded-lg p-8 space-y-6">
      <div className="space-y-1">
        <h1 className="text-xl font-semibold text-[#131212]">Sign in</h1>
        <p className="text-sm text-[#6C7F9A]">Enter your credentials to continue.</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-[#6C7F9A]" htmlFor="email">
            Email
          </label>
          <input
            id="email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full bg-[#F5F8FA] border border-[#D8E1EA] rounded-md px-3 py-2 text-sm text-[#131212] placeholder-[#9DACBE] focus:outline-none focus:ring-1 focus:ring-[#4F87C8] focus:border-[#4F87C8]"
            placeholder="you@example.com"
          />
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-medium text-[#6C7F9A]" htmlFor="password">
            Password
          </label>
          <input
            id="password"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full bg-[#F5F8FA] border border-[#D8E1EA] rounded-md px-3 py-2 text-sm text-[#131212] placeholder-[#9DACBE] focus:outline-none focus:ring-1 focus:ring-[#4F87C8] focus:border-[#4F87C8]"
            placeholder="••••••••"
          />
        </div>

        {error && <p className="text-sm text-[#AA2C2C]">{error}</p>}

        <Button
          type="submit"
          disabled={isPending}
          className="w-full bg-[#237B4B] text-white hover:bg-[#1A5F3D] font-medium rounded-md py-2 text-sm"
        >
          {isPending ? "Signing in…" : "Sign in"}
        </Button>
      </form>

      <p className="text-sm text-[#6C7F9A] text-center">
        Don't have an account?{" "}
        <Link to="/register" className="text-[#237B4B] hover:text-[#1A5F3D] underline underline-offset-2">
          Register
        </Link>
      </p>
    </div>
  )
}
