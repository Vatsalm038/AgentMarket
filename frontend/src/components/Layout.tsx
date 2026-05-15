import { Link, useLocation } from "react-router-dom"
import { cn } from "@/lib/utils"

const navLinks = [
  { to: "/sessions", label: "Sessions" },
  { to: "/verify",   label: "Verify"   },
]

export function Layout({ children }: { children: React.ReactNode }) {
  const { pathname } = useLocation()

  return (
    <div className="min-h-screen bg-zinc-900">
      {/* Header — slightly elevated surface against the zinc-900 background */}
      <header className="border-b border-zinc-700 bg-zinc-950">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          {/* Brand mark — intentionally plain, no logo graphic */}
          <Link to="/" className="text-sm font-medium text-zinc-100 tracking-tight">
            AgentMarket
          </Link>
          <nav className="flex items-center gap-6">
            {navLinks.map(({ to, label }) => (
              <Link
                key={to}
                to={to}
                className={cn(
                  "text-sm transition-colors",
                  // Active: zinc-100. Inactive: zinc-500 that lightens on hover.
                  pathname.startsWith(to)
                    ? "text-zinc-100 font-medium"
                    : "text-zinc-500 hover:text-zinc-100"
                )}
              >
                {label}
              </Link>
            ))}
          </nav>
        </div>
      </header>
      <main className="max-w-6xl mx-auto px-6 py-8">{children}</main>
    </div>
  )
}
