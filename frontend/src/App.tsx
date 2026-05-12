import { BrowserRouter, Routes, Route } from "react-router-dom"
import { Layout } from "@/components/Layout"
import { LandingPage } from "@/pages/LandingPage"
import { SessionsPage } from "@/pages/SessionsPage"
import { SessionDetailPage } from "@/pages/SessionDetailPage"
import { ReplayPage } from "@/pages/ReplayPage"
import { VerifyPage } from "@/pages/VerifyPage"
import { InstallMcpPage } from "@/pages/InstallMcpPage"

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/"            element={<Layout><LandingPage /></Layout>} />
        <Route path="/sessions"    element={<Layout><SessionsPage /></Layout>} />
        <Route path="/session/:id" element={<Layout><SessionDetailPage /></Layout>} />
        <Route path="/replay/:id"  element={<Layout><ReplayPage /></Layout>} />
        <Route path="/verify"      element={<Layout><VerifyPage /></Layout>} />
        <Route path="/install-mcp" element={<Layout><InstallMcpPage /></Layout>} />
      </Routes>
    </BrowserRouter>
  )
}
