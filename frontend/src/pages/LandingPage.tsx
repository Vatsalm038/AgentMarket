import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'

// Merchant quote cards for the auction section
const QUOTES = [
  { merchant: 'Raj Electronics',  price: '₹1,840', days: '3 days',  winner: true  },
  { merchant: 'Mumbai Gadgets',   price: '₹1,960', days: '5 days',  winner: false },
  { merchant: 'Andheri Stores',   price: '₹2,100', days: '7 days',  winner: false },
  { merchant: 'Dadar Tech Hub',   price: '₹2,200', days: '10 days', winner: false },
]

const TRUST_CARDS = [
  {
    title: 'Tamper-proof receipts',
    body: 'Every settled deal is signed with Ed25519 cryptography. Your receipt is verifiable — forever.',
  },
  {
    title: 'You approve every rupee',
    body: 'Your agent cannot spend beyond your set limit without your explicit approval. Always.',
  },
  {
    title: 'Payment via Razorpay',
    body: "Your money goes directly through Razorpay — India's most trusted payment gateway. We never touch it.",
  },
]

const TIERS = [
  {
    name: 'Free',
    price: '₹0',
    period: '/month',
    features: ['5 deals/month', '6 preset negotiation skills', 'Signed receipts'],
    highlight: false,
  },
  {
    name: 'Pro',
    price: '₹499',
    period: '/month',
    features: ['50 deals/month', 'Custom skills', 'Priority matching'],
    highlight: true,
  },
  {
    name: 'Business',
    price: '₹1,999',
    period: '/month',
    features: ['Unlimited deals', 'API access', 'Bulk listing upload'],
    highlight: false,
  },
]

export function LandingPage() {
  return (
    // -mx-6 -mt-8 undoes the Layout wrapper's padding so sections can go edge-to-edge
    <div className="-mx-6 -mt-8">

      {/* ── 1. Hero ───────────────────────────────────────────────────────────── */}
      <section className="bg-zinc-950 px-6 py-20 md:py-32">
        <div className="max-w-5xl mx-auto flex flex-col gap-8">
          <div className="flex flex-col gap-5">
            <h1 className="text-4xl md:text-6xl font-bold text-zinc-100 leading-tight tracking-tight">
              Fair deals,<br />signed and sealed.
            </h1>
            <p className="text-base md:text-lg text-zinc-400 max-w-xl leading-relaxed">
              AI agents negotiate on your behalf.{' '}
              You approve. Every deal cryptographically signed.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button
              asChild
              className="bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-semibold rounded-md"
            >
              <Link to="/register">Start as Buyer</Link>
            </Button>
            <Button
              asChild
              variant="ghost"
              className="rounded-md border border-zinc-700 text-zinc-300 hover:bg-zinc-800 hover:text-zinc-100"
            >
              <Link to="/register">List as Merchant</Link>
            </Button>
          </div>
        </div>
      </section>

      {/* ── 2. How it works ───────────────────────────────────────────────────── */}
      <section className="bg-zinc-900 px-6 py-20">
        <div className="max-w-5xl mx-auto flex flex-col gap-12">
          <h2 className="text-2xl md:text-3xl font-bold text-zinc-100">
            How SignedDeals works
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-10">
            {[
              {
                n: '01',
                title: 'You describe what you need',
                body: 'Tell us what you want, your budget, and your city. No lengthy forms.',
              },
              {
                n: '02',
                title: 'Agents compete for you',
                body: 'Up to 4 merchants bid. Your AI agent picks the best deal using your chosen negotiation style.',
              },
              {
                n: '03',
                title: 'You approve, it\'s sealed',
                body: 'One tap to confirm. You get a cryptographically signed receipt — tamper-proof and verifiable.',
              },
            ].map((step) => (
              <div key={step.n} className="flex flex-col gap-3">
                {/* Large step number in muted zinc */}
                <span className="text-5xl font-bold text-zinc-700 font-mono leading-none">
                  {step.n}
                </span>
                <span className="text-base font-semibold text-zinc-100">{step.title}</span>
                <p className="text-sm text-zinc-400 leading-relaxed">{step.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── 3. Multi-merchant auction ─────────────────────────────────────────── */}
      <section className="bg-zinc-800 px-6 py-16">
        <div className="max-w-5xl mx-auto flex flex-col gap-10">
          <div className="flex flex-col gap-3">
            <h2 className="text-2xl md:text-3xl font-bold text-zinc-100">
              Real competition, not a fixed price
            </h2>
            <p className="text-sm md:text-base text-zinc-400 max-w-xl">
              Multiple merchants submit quotes. Your agent evaluates every offer against your priorities.
            </p>
          </div>

          {/* Quote cards */}
          <div className="flex flex-col gap-2 max-w-md">
            {QUOTES.map((q) => (
              <div
                key={q.merchant}
                className={`rounded-md px-4 py-3 flex items-center justify-between text-sm ${
                  q.winner
                    ? 'border border-emerald-500 bg-zinc-900 text-zinc-100'
                    : 'border border-zinc-700 bg-zinc-900 text-zinc-400'
                }`}
              >
                <span className="font-medium">{q.merchant}</span>
                <span className="flex gap-4 font-mono text-xs">
                  <span className={q.winner ? 'text-emerald-400' : ''}>{q.price}</span>
                  <span>{q.days}</span>
                  {q.winner && (
                    <span className="text-emerald-500 font-semibold">Winner</span>
                  )}
                </span>
              </div>
            ))}
          </div>

          <p className="text-sm text-emerald-400 font-medium">
            Your agent saved you ₹360 (16% below your max of ₹2,200)
          </p>
        </div>
      </section>

      {/* ── 4. Trust signals ─────────────────────────────────────────────────── */}
      <section className="bg-zinc-900 px-6 py-16">
        <div className="max-w-5xl mx-auto flex flex-col gap-10">
          <h2 className="text-2xl md:text-3xl font-bold text-zinc-100">
            Built for trust
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {TRUST_CARDS.map((card) => (
              <div
                key={card.title}
                className="bg-zinc-800 border border-zinc-700 rounded-md p-5 flex flex-col gap-2"
              >
                <span className="text-sm font-semibold text-zinc-100">{card.title}</span>
                <p className="text-sm text-zinc-400 leading-relaxed">{card.body}</p>
              </div>
            ))}
          </div>
          {/* Beta disclaimer */}
          <p className="text-xs text-amber-400">
            Currently in beta — test mode only, no real money
          </p>
        </div>
      </section>

      {/* ── 5. Pricing ───────────────────────────────────────────────────────── */}
      <section className="bg-zinc-800 px-6 py-16">
        <div className="max-w-5xl mx-auto flex flex-col gap-10">
          <div className="flex flex-col gap-2">
            <h2 className="text-2xl md:text-3xl font-bold text-zinc-100">
              Simple, outcome-based pricing
            </h2>
            <p className="text-sm text-zinc-400">
              Pay for deals closed, not for access. Coming soon — all features free during beta.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {TIERS.map((tier) => (
              <div key={tier.name} className="relative flex flex-col">
                {/* "Beta: all features free" banner only on Pro */}
                {tier.highlight && (
                  <div className="rounded-t-md bg-emerald-500 text-zinc-950 text-xs font-semibold text-center py-1 px-3">
                    Beta: all features free
                  </div>
                )}
                <div
                  className={`bg-zinc-900 border border-zinc-700 p-5 flex flex-col gap-4 flex-1 ${
                    tier.highlight ? 'rounded-b-md border-t-0' : 'rounded-md'
                  }`}
                >
                  <span className="text-sm font-semibold text-zinc-100">{tier.name}</span>
                  {/* Price in JetBrains Mono */}
                  <div className="flex items-baseline gap-1">
                    <span className="text-3xl font-bold text-zinc-100 font-mono">
                      {tier.price}
                    </span>
                    <span className="text-xs text-zinc-500">{tier.period}</span>
                  </div>
                  <ul className="flex flex-col gap-1">
                    {tier.features.map((f) => (
                      <li key={f} className="text-xs text-zinc-400">
                        · {f}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── 6. CTA footer ────────────────────────────────────────────────────── */}
      <section className="bg-zinc-950 px-6 py-16">
        <div className="max-w-5xl mx-auto flex flex-col items-center gap-6 text-center">
          <h2 className="text-2xl md:text-3xl font-bold text-zinc-100">
            Ready to let your agent negotiate?
          </h2>
          <div className="flex flex-wrap justify-center gap-3">
            <Button
              asChild
              className="bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-semibold rounded-md"
            >
              <Link to="/register">Register as Buyer</Link>
            </Button>
            <Button
              asChild
              variant="ghost"
              className="rounded-md border border-zinc-700 text-zinc-300 hover:bg-zinc-800 hover:text-zinc-100"
            >
              <Link to="/register">Register as Merchant</Link>
            </Button>
          </div>
          <p className="text-xs text-zinc-500">No credit card needed. Test mode.</p>
        </div>
      </section>

      {/* ── 7. Site footer ───────────────────────────────────────────────────── */}
      <footer className="bg-zinc-950 border-t border-zinc-800 px-6 py-6">
        <div className="max-w-5xl mx-auto flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <span className="text-xs text-zinc-500">
            SignedDeals · Fair deals, signed and sealed.
          </span>
          <nav className="flex flex-wrap gap-5">
            {[
              { label: 'How it works', href: '#' },
              { label: 'Pricing',      href: '#' },
              { label: 'Verify Receipt', href: '/verify' },
              { label: 'Sign in',      href: '/login' },
            ].map(({ label, href }) => (
              <Link
                key={label}
                to={href}
                className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
              >
                {label}
              </Link>
            ))}
          </nav>
        </div>
      </footer>
    </div>
  )
}
