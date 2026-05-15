import { BrowserRouter, Routes, Route } from "react-router-dom"
import { AuthProvider } from "@/contexts/AuthContext"
import { RequireAuth } from "@/components/RequireAuth"
import { AppLayout } from "@/layouts/AppLayout"
import { FullscreenLayout } from "@/layouts/FullscreenLayout"
import { Layout } from "@/components/Layout"

// Existing pages
import { LandingPage } from "@/pages/LandingPage"
import { SessionsPage } from "@/pages/SessionsPage"
import { SessionDetailPage } from "@/pages/SessionDetailPage"
import { VerifyPage } from "@/pages/VerifyPage"

// Auth pages
import { LoginPage } from "@/pages/auth/LoginPage"
import { RegisterPage } from "@/pages/auth/RegisterPage"

// Buyer pages
import { BuyerDashboardPage } from "@/pages/buyer/BuyerDashboardPage"
import { BuyerSearchPage } from "@/pages/buyer/BuyerSearchPage"
import { BuyerDealsPage } from "@/pages/buyer/BuyerDealsPage"
import { BuyerDealDetailPage } from "@/pages/buyer/BuyerDealDetailPage"
import { BuyerAgentsPage } from "@/pages/buyer/BuyerAgentsPage"

// Merchant pages
import { MerchantDashboardPage } from "@/pages/merchant/MerchantDashboardPage"
import { MerchantProductsPage } from "@/pages/merchant/MerchantProductsPage"
import { MerchantProductNewPage } from "@/pages/merchant/MerchantProductNewPage"
import { MerchantDealsPage } from "@/pages/merchant/MerchantDealsPage"
import { MerchantDealDetailPage } from "@/pages/merchant/MerchantDealDetailPage"

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public marketing — uses existing Layout */}
          <Route path="/" element={<Layout><LandingPage /></Layout>} />

          {/* Auth — fullscreen, no sidebar */}
          <Route element={<FullscreenLayout />}>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
          </Route>

          {/* Verify is public — fullscreen layout */}
          <Route element={<FullscreenLayout />}>
            <Route path="/verify" element={<VerifyPage />} />
          </Route>

          {/* App — requires auth, uses AppLayout with sidebar */}
          <Route
            element={
              <RequireAuth>
                <AppLayout />
              </RequireAuth>
            }
          >
            <Route path="/buyer/dashboard" element={<BuyerDashboardPage />} />
            <Route path="/buyer/search" element={<BuyerSearchPage />} />
            <Route path="/buyer/deals" element={<BuyerDealsPage />} />
            <Route path="/buyer/deal/:id" element={<BuyerDealDetailPage />} />
            <Route path="/buyer/agents" element={<BuyerAgentsPage />} />
            <Route path="/merchant/dashboard" element={<MerchantDashboardPage />} />
            <Route path="/merchant/products" element={<MerchantProductsPage />} />
            <Route path="/merchant/products/new" element={<MerchantProductNewPage />} />
            <Route path="/merchant/deals" element={<MerchantDealsPage />} />
            <Route path="/merchant/deal/:id" element={<MerchantDealDetailPage />} />
            <Route path="/sessions" element={<SessionsPage />} />
            <Route path="/session/:id" element={<SessionDetailPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
