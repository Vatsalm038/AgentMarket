import { Outlet, NavLink, useNavigate } from "react-router-dom"
import { useAuth } from "@/contexts/AuthContext"

// NavLink helper — active = zinc-100, inactive = zinc-400
function NavItem({ to, label }: { to: string; label: string }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `block px-3 py-2 rounded-md text-sm font-medium transition-colors ${
          isActive
            ? "bg-zinc-800 text-zinc-100"
            : "text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800"
        }`
      }
    >
      {label}
    </NavLink>
  )
}

export function AppLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate("/login")
  }

  return (
    <div className="min-h-screen bg-zinc-900 flex">
      {/* Sidebar */}
      <aside className="w-56 bg-zinc-950 border-r border-zinc-800 flex flex-col shrink-0">
        <div className="p-4 border-b border-zinc-800">
          <span className="text-zinc-100 font-semibold tracking-tight">SignedDeals</span>
        </div>
        <nav className="flex-1 p-3 space-y-1">
          {user?.is_buyer && (
            <>
              <p className="text-[10px] text-zinc-600 uppercase tracking-wider px-3 pt-2 pb-1">
                Buyer
              </p>
              <NavItem to="/buyer/dashboard" label="Dashboard" />
              <NavItem to="/buyer/search" label="Search" />
              <NavItem to="/buyer/deals" label="My Deals" />
              <NavItem to="/buyer/agents" label="Agents" />
            </>
          )}
          {user?.is_merchant && (
            <>
              <p className="text-[10px] text-zinc-600 uppercase tracking-wider px-3 pt-2 pb-1">
                Merchant
              </p>
              <NavItem to="/merchant/dashboard" label="Dashboard" />
              <NavItem to="/merchant/products" label="Products" />
              <NavItem to="/merchant/deals" label="Deals" />
            </>
          )}
          <p className="text-[10px] text-zinc-600 uppercase tracking-wider px-3 pt-4 pb-1">
            Platform
          </p>
          <NavItem to="/sessions" label="Audit Log" />
          <NavItem to="/verify" label="Verify Receipt" />
        </nav>
        <div className="p-3 border-t border-zinc-800">
          <p className="text-xs text-zinc-500 px-3 truncate mb-1">{user?.email}</p>
          <button
            onClick={handleLogout}
            className="w-full text-left px-3 py-2 text-sm text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 rounded-md transition-colors"
          >
            Sign out
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-auto">
        <div className="max-w-5xl mx-auto px-6 py-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
