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
      const res = await api.post<{ access_token: string; user: AuthUser }>("/auth/login", {
        email,
        password,
      })
      const { access_token, user } = res.data
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
    <div className="w-full max-w-sm bg-zinc-900 border border-zinc-800 rounded-md p-8 space-y-6">
      <div className="space-y-1">
        <h1 className="text-xl font-semibold text-zinc-100">Sign in</h1>
        <p className="text-sm text-zinc-500">Enter your credentials to continue.</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-zinc-400" htmlFor="email">
            Email
          </label>
          <input
            id="email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-zinc-500"
            placeholder="you@example.com"
          />
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-medium text-zinc-400" htmlFor="password">
            Password
          </label>
          <input
            id="password"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-zinc-500"
            placeholder="••••••••"
          />
        </div>

        {error && <p className="text-sm text-red-400">{error}</p>}

        <Button
          type="submit"
          disabled={isPending}
          className="w-full bg-zinc-100 text-zinc-900 hover:bg-zinc-200 font-medium"
        >
          {isPending ? "Signing in…" : "Sign in"}
        </Button>
      </form>

      <p className="text-sm text-zinc-500 text-center">
        Don't have an account?{" "}
        <Link to="/register" className="text-zinc-300 hover:text-zinc-100 underline underline-offset-2">
          Register
        </Link>
      </p>
    </div>
  )
}
