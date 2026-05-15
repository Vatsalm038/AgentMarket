import { Link } from "react-router-dom"
import { Button } from "@/components/ui/button"

const STEPS = [
  {
    n: "01",
    title: "Describe what you need",
    body: "Type what you want, your max budget, and your city. Your AI agent takes it from there — no forms, no calls, no back-and-forth.",
  },
  {
    n: "02",
    title: "Agents negotiate in real time",
    body: "Multiple merchant agents compete and counter-offer simultaneously. Your agent benchmarks every quote against your priorities and pushes for the best outcome.",
  },
  {
    n: "03",
    title: "You approve. It is sealed forever.",
    body: "One click to confirm. Every deal is cryptographically signed with Ed25519 — tamper-proof, verifiable, and yours forever.",
  },
]

const QUOTES = [
  { merchant: "Raj Electronics",  price: "₹1,840", days: "3 days",  winner: true  },
  { merchant: "Mumbai Gadgets",   price: "₹1,960", days: "5 days",  winner: false },
  { merchant: "Andheri Stores",   price: "₹2,100", days: "7 days",  winner: false },
  { merchant: "Dadar Tech Hub",   price: "₹2,200", days: "10 days", winner: false },
]

const TRUST = [
  {
    tag: "01",
    title: "Cryptographic receipts",
    body: "Every settled deal is signed with Ed25519. Your receipt cannot be altered after the fact — paste it into our Verify tool anytime to confirm authenticity.",
  },
  {
    tag: "02",
    title: "Agent-to-agent negotiation",
    body: "Your buyer agent and the merchant agent exchange structured offers using the same negotiation logic used in enterprise procurement tools.",
  },
  {
    tag: "03",
    title: "Hard spending limits",
    body: "Your agent cannot spend a single rupee beyond the limit you set. The cap is enforced cryptographically — not by a promise.",
  },
  {
    tag: "04",
    title: "Secure payments",
    body: "Money flows through a trusted payment gateway. We never hold your funds — payment is only triggered after you approve the deal.",
  },
  {
    tag: "05",
    title: "Works inside Claude & ChatGPT",
    body: "Connect the SignedDeals MCP server to your Claude or ChatGPT agent and negotiate deals without opening a browser.",
  },
  {
    tag: "06",
    title: "Full audit trail",
    body: "Every round of negotiation is logged in plain English. You can read exactly how your agent argued for a better price.",
  },
]

const FOR_BUYERS = [
  "Tell the agent what you need and your max price",
  "It finds matching merchants automatically",
  "Agents negotiate — you watch or walk away",
  "Pay only when you approve the final price",
]

const FOR_MERCHANTS = [
  "List products once — agents handle incoming negotiations 24/7",
  "Choose your negotiation style: aggressive, data-driven, polite, and more",
  "Never miss a deal while you are away",
  "Get cryptographic proof of every settled transaction",
]

const TIERS = [
  {
    name: "Free",
    price: "₹0",
    period: "/month",
    features: ["5 deals / month", "6 preset negotiation skills", "Signed receipts", "Audit trail"],
    highlight: false,
    cta: "Get started free",
  },
  {
    name: "Pro",
    price: "₹499",
    period: "/month",
    features: ["50 deals / month", "Custom negotiation skills", "Priority merchant matching", "CSV export"],
    highlight: true,
    cta: "Start Pro",
  },
  {
    name: "Business",
    price: "₹1,999",
    period: "/month",
    features: ["Unlimited deals", "MCP / API access", "Bulk product upload", "Dedicated support"],
    highlight: false,
    cta: "Contact us",
  },
]

export function LandingPage() {
  return (
    <div className="min-h-screen bg-white font-sans">

      {/* ── Topnav ── */}
      <header className="border-b border-[#D8E1EA] bg-white sticky top-0 z-30">
        <div className="max-w-5xl mx-auto px-6 h-14 flex items-center justify-between">
          <span className="text-sm font-semibold text-[#131212] tracking-tight">SignedDeals</span>
          <nav className="flex items-center gap-2">
            <Link to="/login" className="text-sm text-[#6C7F9A] hover:text-[#131212] transition-colors px-3 py-1.5">
              Sign in
            </Link>
            <Button asChild size="sm" className="bg-[#237B4B] hover:bg-[#1A5F3D] text-white rounded-md text-sm font-medium">
              <Link to="/register">Get started free</Link>
            </Button>
          </nav>
        </div>
      </header>

      {/* ── 1. Hero ── */}
      <section className="bg-white px-6 py-24 border-b border-[#D8E1EA]">
        <div className="max-w-5xl mx-auto flex flex-col gap-8">
          <span className="inline-flex w-fit items-center border border-[#D8E1EA] rounded-full px-3 py-1 text-xs text-[#6C7F9A] font-medium">
            Beta · India · Test mode
          </span>
          <div className="flex flex-col gap-5 max-w-2xl">
            <h1 className="text-4xl md:text-6xl font-bold text-[#131212] leading-tight tracking-tight">
              Fair deals,<br />signed and sealed.
            </h1>
            <p className="text-base md:text-lg text-[#6C7F9A] leading-relaxed max-w-xl">
              Describe what you want. Your AI agent negotiates with merchants, benchmarks every quote against your budget, and hands you the best price — sealed with a cryptographic signature you can verify forever.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button asChild className="bg-[#237B4B] hover:bg-[#1A5F3D] text-white rounded-md font-semibold px-6">
              <Link to="/register">Start as Buyer — free</Link>
            </Button>
            <Button asChild variant="outline" className="rounded-md border-[#D8E1EA] text-[#131212] hover:bg-[#F5F8FA]">
              <Link to="/register">List as Merchant</Link>
            </Button>
          </div>

          {/* Metric row */}
          <div className="flex flex-wrap gap-8 pt-4 border-t border-[#E4EAF1]">
            {[
              { stat: "Up to 4",    label: "merchants compete per deal" },
              { stat: "Ed25519",    label: "cryptographic receipts"      },
              { stat: "₹0 upfront", label: "free during beta"            },
            ].map(({ stat, label }) => (
              <div key={stat}>
                <p className="text-xl font-bold text-[#131212] font-mono">{stat}</p>
                <p className="text-xs text-[#6C7F9A]">{label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── 2. How it works ── */}
      <section className="bg-[#F5F8FA] px-6 py-20 border-b border-[#D8E1EA]">
        <div className="max-w-5xl mx-auto flex flex-col gap-12">
          <div>
            <p className="text-xs font-mono text-[#9DACBE] uppercase tracking-widest mb-1">How it works</p>
            <h2 className="text-2xl md:text-3xl font-bold text-[#131212]">From request to signed deal in minutes</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-10">
            {STEPS.map((step) => (
              <div key={step.n} className="flex flex-col gap-3">
                <span className="text-5xl font-bold text-[#E4EAF1] font-mono leading-none">{step.n}</span>
                <span className="text-sm font-semibold text-[#131212]">{step.title}</span>
                <p className="text-sm text-[#6C7F9A] leading-relaxed">{step.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── 3. Auction demo ── */}
      <section className="bg-white px-6 py-20 border-b border-[#D8E1EA]">
        <div className="max-w-5xl mx-auto flex flex-col gap-10">
          <div>
            <p className="text-xs font-mono text-[#9DACBE] uppercase tracking-widest mb-1">Live auction</p>
            <h2 className="text-2xl md:text-3xl font-bold text-[#131212]">Real competition, not a fixed price</h2>
            <p className="text-sm text-[#6C7F9A] max-w-xl mt-2">
              Multiple merchant agents bid simultaneously. Your agent picks the best offer against price, delivery, and your stated priorities.
            </p>
          </div>

          <div className="max-w-lg border border-[#D8E1EA] rounded-md overflow-hidden">
            <div className="grid grid-cols-3 bg-[#F5F8FA] border-b border-[#D8E1EA] px-4 py-2.5 text-xs font-mono text-[#9DACBE] uppercase tracking-widest">
              <span>Merchant</span>
              <span className="text-right">Price</span>
              <span className="text-right">Delivery</span>
            </div>
            {QUOTES.map((q, i) => (
              <div
                key={q.merchant}
                className={`grid grid-cols-3 px-4 py-3 text-sm items-center ${
                  i < QUOTES.length - 1 ? "border-b border-[#E4EAF1]" : ""
                } ${q.winner ? "bg-[#F0FBF4]" : "bg-white"}`}
              >
                <span className={`font-medium text-sm ${q.winner ? "text-[#131212]" : "text-[#6C7F9A]"}`}>
                  {q.merchant}
                </span>
                <span className={`text-right font-mono text-xs ${q.winner ? "text-[#237B4B] font-bold" : "text-[#9DACBE]"}`}>
                  {q.price}
                  {q.winner && (
                    <span className="ml-2 text-[9px] border border-[#237B4B] text-[#237B4B] rounded px-1 py-px">
                      BEST
                    </span>
                  )}
                </span>
                <span className={`text-right font-mono text-xs ${q.winner ? "text-[#131212]" : "text-[#9DACBE]"}`}>
                  {q.days}
                </span>
              </div>
            ))}
          </div>

          <p className="text-sm text-[#237B4B] font-semibold font-mono">
            ✓ Agent saved ₹360 — 16% below your max budget
          </p>
        </div>
      </section>

      {/* ── 4. Buyer vs Merchant split ── */}
      <section className="bg-[#F5F8FA] px-6 py-20 border-b border-[#D8E1EA]">
        <div className="max-w-5xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-8">
          <div className="bg-white border border-[#D8E1EA] rounded-md p-8 flex flex-col gap-5">
            <div>
              <p className="text-xs font-mono text-[#9DACBE] uppercase tracking-widest mb-1">For Buyers</p>
              <h3 className="text-xl font-bold text-[#131212]">Stop overpaying. Let your agent haggle.</h3>
            </div>
            <ul className="flex flex-col gap-3">
              {FOR_BUYERS.map((item) => (
                <li key={item} className="flex items-start gap-3 text-sm text-[#6C7F9A]">
                  <span className="text-[#237B4B] font-bold mt-0.5">✓</span>
                  {item}
                </li>
              ))}
            </ul>
            <Button asChild className="w-fit bg-[#237B4B] hover:bg-[#1A5F3D] text-white font-medium">
              <Link to="/register">Sign up as Buyer</Link>
            </Button>
          </div>

          <div className="bg-white border border-[#D8E1EA] rounded-md p-8 flex flex-col gap-5">
            <div>
              <p className="text-xs font-mono text-[#9DACBE] uppercase tracking-widest mb-1">For Merchants</p>
              <h3 className="text-xl font-bold text-[#131212]">Your AI sales agent, always on.</h3>
            </div>
            <ul className="flex flex-col gap-3">
              {FOR_MERCHANTS.map((item) => (
                <li key={item} className="flex items-start gap-3 text-sm text-[#6C7F9A]">
                  <span className="text-[#4F87C8] font-bold mt-0.5">✓</span>
                  {item}
                </li>
              ))}
            </ul>
            <Button asChild variant="outline" className="w-fit border-[#D8E1EA] text-[#131212] hover:bg-[#F5F8FA]">
              <Link to="/register">Sign up as Merchant</Link>
            </Button>
          </div>
        </div>
      </section>

      {/* ── 5. Trust / Features grid ── */}
      <section className="bg-white px-6 py-20 border-b border-[#D8E1EA]">
        <div className="max-w-5xl mx-auto flex flex-col gap-10">
          <div>
            <p className="text-xs font-mono text-[#9DACBE] uppercase tracking-widest mb-1">Built different</p>
            <h2 className="text-2xl md:text-3xl font-bold text-[#131212]">
              Everything we built, and why it matters
            </h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {TRUST.map((card) => (
              <div key={card.title} className="border border-[#D8E1EA] rounded-md p-5 flex flex-col gap-3 hover:bg-[#F5F8FA] transition-colors">
                <span className="font-mono text-xs text-[#9DACBE] tracking-widest">{card.tag}</span>
                <span className="text-sm font-semibold text-[#131212]">{card.title}</span>
                <p className="text-sm text-[#6C7F9A] leading-relaxed">{card.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── 6. Pricing ── */}
      <section className="bg-[#F5F8FA] px-6 py-20 border-b border-[#D8E1EA]">
        <div className="max-w-5xl mx-auto flex flex-col gap-10">
          <div>
            <p className="text-xs font-mono text-[#9DACBE] uppercase tracking-widest mb-1">Pricing</p>
            <h2 className="text-2xl md:text-3xl font-bold text-[#131212]">Simple, transparent pricing</h2>
            <p className="text-sm text-[#6C7F9A] mt-1">All features free during beta. No credit card required.</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {TIERS.map((tier) => (
              <div
                key={tier.name}
                className={`bg-white rounded-md p-6 flex flex-col gap-5 ${
                  tier.highlight
                    ? "border-2 border-[#237B4B] shadow-sm"
                    : "border border-[#D8E1EA]"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-[#131212]">{tier.name}</span>
                  {tier.highlight && (
                    <span className="text-[9px] font-mono bg-[#E6F4EA] text-[#237B4B] rounded-full px-2 py-0.5">
                      MOST POPULAR
                    </span>
                  )}
                </div>
                <div className="flex items-baseline gap-1">
                  <span className="text-3xl font-bold text-[#131212] font-mono">{tier.price}</span>
                  <span className="text-xs text-[#9DACBE]">{tier.period}</span>
                </div>
                <ul className="flex flex-col gap-2 border-t border-[#E4EAF1] pt-4">
                  {tier.features.map((f) => (
                    <li key={f} className="text-xs text-[#6C7F9A] flex gap-2 items-start">
                      <span className="text-[#237B4B] font-bold mt-0.5">✓</span>
                      {f}
                    </li>
                  ))}
                </ul>
                <Button
                  asChild
                  className={tier.highlight
                    ? "bg-[#237B4B] hover:bg-[#1A5F3D] text-white font-medium"
                    : "bg-white border border-[#D8E1EA] text-[#131212] hover:bg-[#F5F8FA]"
                  }
                >
                  <Link to="/register">{tier.cta}</Link>
                </Button>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── 7. MCP / Developer callout ── */}
      <section className="bg-white px-6 py-20 border-b border-[#D8E1EA]">
        <div className="max-w-5xl mx-auto flex flex-col md:flex-row items-start gap-12">
          <div className="flex-1 flex flex-col gap-4">
            <p className="text-xs font-mono text-[#9DACBE] uppercase tracking-widest">For developers</p>
            <h2 className="text-2xl md:text-3xl font-bold text-[#131212]">
              Negotiate from inside Claude or ChatGPT
            </h2>
            <p className="text-sm text-[#6C7F9A] leading-relaxed max-w-md">
              SignedDeals ships an MCP server. Connect it to your AI assistant and
              trigger negotiations, check deal status, and download signed receipts —
              all without opening a browser.
            </p>
            <Button asChild variant="outline" className="w-fit border-[#D8E1EA] text-[#131212] hover:bg-[#F5F8FA]">
              <Link to="/register">Get API access</Link>
            </Button>
          </div>
          <div className="flex-1 bg-[#131212] rounded-md p-5 font-mono text-xs leading-relaxed">
            <p className="text-[#9DACBE] mb-3"># claude_desktop_config.json</p>
            <p><span className="text-[#4F87C8]">"signeddeals"</span><span className="text-white">: {"{"}</span></p>
            <p className="pl-4"><span className="text-[#4F87C8]">"command"</span><span className="text-white">: </span><span className="text-[#237B4B]">"uvx"</span><span className="text-white">,</span></p>
            <p className="pl-4"><span className="text-[#4F87C8]">"args"</span><span className="text-white">: [</span><span className="text-[#237B4B]">"signeddeals-mcp"</span><span className="text-white">],</span></p>
            <p className="pl-4"><span className="text-[#4F87C8]">"env"</span><span className="text-white">: {"{"}</span></p>
            <p className="pl-8"><span className="text-[#4F87C8]">"SD_API_KEY"</span><span className="text-white">: </span><span className="text-[#237B4B]">"&lt;your-key&gt;"</span></p>
            <p className="pl-4"><span className="text-white">{"}"}</span></p>
            <p><span className="text-white">{"}"}</span></p>
          </div>
        </div>
      </section>

      {/* ── 8. Final CTA ── */}
      <section className="bg-[#237B4B] px-6 py-20">
        <div className="max-w-5xl mx-auto flex flex-col items-center gap-6 text-center">
          <h2 className="text-2xl md:text-4xl font-bold text-white leading-tight">
            Stop accepting the first price.<br />Let your agent fight for better.
          </h2>
          <p className="text-sm text-[#A8D5B8] max-w-sm">
            Free during beta. No credit card. Takes 60 seconds to get started.
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            <Button asChild className="bg-white text-[#237B4B] hover:bg-[#F0FBF4] font-semibold px-6">
              <Link to="/register">Get started free</Link>
            </Button>
            <Button asChild variant="outline" className="border-white/40 text-white hover:bg-white/10">
              <Link to="/login">Sign in</Link>
            </Button>
          </div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="bg-[#F5F8FA] border-t border-[#D8E1EA] px-6 py-6">
        <div className="max-w-5xl mx-auto flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div>
            <span className="text-sm font-semibold text-[#131212]">SignedDeals</span>
            <p className="text-xs text-[#9DACBE] mt-0.5">Fair deals, signed and sealed. Made in India.</p>
          </div>
          <nav className="flex flex-wrap gap-6">
            {[
              { label: "Verify receipt", href: "/verify"   },
              { label: "Sign in",        href: "/login"    },
              { label: "Register",       href: "/register" },
            ].map(({ label, href }) => (
              <Link key={label} to={href} className="text-xs text-[#9DACBE] hover:text-[#131212] transition-colors">
                {label}
              </Link>
            ))}
          </nav>
        </div>
      </footer>

    </div>
  )
}
