import { BrowserRouter, Routes, Route } from "react-router-dom"
import { Layout } from "@/components/Layout"
import { LandingPage } from "@/pages/LandingPage"
import { SessionsPage } from "@/pages/SessionsPage"
import { SessionDetailPage } from "@/pages/SessionDetailPage"
import { VerifyPage } from "@/pages/VerifyPage"

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/"            element={<Layout><LandingPage /></Layout>} />
        <Route path="/sessions"    element={<Layout><SessionsPage /></Layout>} />
        <Route path="/session/:id" element={<Layout><SessionDetailPage /></Layout>} />
        <Route path="/verify"      element={<Layout><VerifyPage /></Layout>} />
      </Routes>
    </BrowserRouter>
  )
}
