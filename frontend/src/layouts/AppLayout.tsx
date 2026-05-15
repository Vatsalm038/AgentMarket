import { Outlet, NavLink, useNavigate } from "react-router-dom"
import { useAuth } from "@/contexts/AuthContext"

// NavItem active: green tint; inactive: secondary text with light hover
function NavItem({ to, label }: { to: string; label: string }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `block px-3 py-2 rounded-md text-sm font-medium transition-colors ${
          isActive
            ? "bg-[#E6F4EA] text-[#237B4B] font-medium"
            : "text-[#6C7F9A] hover:bg-[#F5F8FA] hover:text-[#131212]"
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
    <div className="min-h-screen bg-[#F5F8FA] flex">
      {/* Sidebar */}
      <aside className="w-56 bg-white border-r border-[#D8E1EA] flex flex-col shrink-0">
        <div className="p-4 border-b border-[#D8E1EA]">
          <span className="text-[#131212] font-semibold tracking-tight">SignedDeals</span>
        </div>
        <nav className="flex-1 p-3 space-y-1">
          {user?.is_buyer && (
            <>
              <p className="text-[10px] text-[#9DACBE] uppercase tracking-wider px-3 pt-3 pb-1">
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
              <p className="text-[10px] text-[#9DACBE] uppercase tracking-wider px-3 pt-3 pb-1">
                Merchant
              </p>
              <NavItem to="/merchant/dashboard" label="Dashboard" />
              <NavItem to="/merchant/products" label="Products" />
              <NavItem to="/merchant/deals" label="Deals" />
              <NavItem to="/merchant/agent" label="My Agent" />
            </>
          )}
          <p className="text-[10px] text-[#9DACBE] uppercase tracking-wider px-3 pt-3 pb-1">
            Platform
          </p>
          <NavItem to="/sessions" label="Audit Log" />
          <NavItem to="/verify" label="Verify Receipt" />
        </nav>
        <div className="p-3 border-t border-[#D8E1EA]">
          <p className="text-xs text-[#9DACBE] px-3 truncate mb-1">{user?.email}</p>
          <button
            onClick={handleLogout}
            className="w-full text-left px-3 py-2 text-sm text-[#6C7F9A] hover:text-[#131212] hover:bg-[#F5F8FA] rounded-md transition-colors"
          >
            Sign out
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-auto bg-[#F5F8FA]">
        <div className="max-w-5xl mx-auto px-6 py-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
