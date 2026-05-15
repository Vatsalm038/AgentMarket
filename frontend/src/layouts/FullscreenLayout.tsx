import { Outlet, Link } from "react-router-dom"

// Centered single-column, no sidebar. Used for login/register/verify.
export function FullscreenLayout() {
  return (
    <div className="min-h-screen bg-zinc-950 flex flex-col">
      <div className="p-6">
        <Link to="/" className="text-zinc-100 font-semibold tracking-tight text-lg">
          SignedDeals
        </Link>
      </div>
      <div className="flex-1 flex items-center justify-center px-4">
        <Outlet />
      </div>
    </div>
  )
}
