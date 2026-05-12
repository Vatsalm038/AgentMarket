import { Link, useLocation } from "react-router-dom"
import { cn } from "@/lib/utils"

const navLinks = [
  { to: "/sessions",    label: "Sessions"    },
  { to: "/install-mcp", label: "Install MCP" },
  { to: "/verify",      label: "Verify"      },
]

export function Layout({ children }: { children: React.ReactNode }) {
  const { pathname } = useLocation()

  return (
    <div className="min-h-screen bg-zinc-50">
      <header className="border-b border-zinc-200 bg-white">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          {/* Brand mark — intentionally plain, no logo graphic */}
          <Link to="/" className="text-sm font-medium text-zinc-900 tracking-tight">
            AgentMarket
          </Link>
          <nav className="flex items-center gap-6">
            {navLinks.map(({ to, label }) => (
              <Link
                key={to}
                to={to}
                className={cn(
                  "text-sm transition-colors",
                  // Active state: full zinc-900. Inactive: muted zinc-500 that darkens on hover.
                  pathname.startsWith(to)
                    ? "text-zinc-900 font-medium"
                    : "text-zinc-500 hover:text-zinc-900"
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
