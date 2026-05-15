import { Outlet, Link } from "react-router-dom"

// Centered single-column, no sidebar. Used for login/register/verify.
export function FullscreenLayout() {
  return (
    <div className="min-h-screen bg-[#F5F8FA] flex flex-col">
      <div className="p-6 flex items-center gap-3">
        <Link
          to="/"
          className="text-[#6C7F9A] hover:text-[#131212] transition-colors"
          title="Home"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
            <polyline points="9 22 9 12 15 12 15 22"/>
          </svg>
        </Link>
        <Link to="/" className="text-[#131212] font-semibold tracking-tight text-lg">
          SignedDeals
        </Link>
      </div>
      <div className="flex-1 flex items-center justify-center px-4">
        <Outlet />
      </div>
    </div>
  )
}
