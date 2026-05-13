import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useHealth } from '@/hooks/useApi'

// Feature strip data — kept here so the grid is data-driven, not repeated JSX
const FEATURES = [
  {
    title: 'Policy-Bounded Spending',
    description:
      'Every buyer agent operates within a cryptographically signed spending policy. No transaction can exceed the declared limit — enforced at the protocol layer, not the UI.',
  },
  {
    title: 'AI Negotiation',
    description:
      'Buyer and merchant agents negotiate price autonomously using GPT-4o-mini. Rounds are capped, math is computed server-side, and the LLM never touches money arithmetic.',
  },
  {
    title: 'Verifiable Receipts',
    description:
      'Settled transactions produce an Ed25519-signed receipt referencing the policy ID. Any party can verify the signature against the published platform public key.',
  },
]

export function LandingPage() {
  const health = useHealth()

  const isUp = health.data?.status === 'ok'
  const badgeLabel = health.isLoading ? 'Checking...' : isUp ? 'API online' : 'API offline'
  const badgeClass = health.isLoading
    ? 'border-zinc-300 text-zinc-500'
    : isUp
    ? 'border-green-600 text-green-700'
    : 'border-red-600 text-red-700'

  return (
    <div className="flex flex-col gap-0">
      {/* ── Hero ────────────────────────────────────────────────────────────── */}
      <section className="bg-white border-b border-zinc-200 -mx-6 -mt-8 px-6 py-16">
        <div className="max-w-5xl mx-auto flex flex-col gap-6">
          <div className="flex items-start justify-between">
            <h1 className="text-xl font-medium text-zinc-900 max-w-xl leading-snug">
              Agentic commerce for Indian hyperlocal markets
            </h1>
            {/* Health badge — shows API reachability */}
            <Badge variant="outline" className={`mt-1 ${badgeClass}`}>
              {badgeLabel}
            </Badge>
          </div>
          <p className="text-sm text-zinc-600 max-w-lg leading-relaxed">
            Buyers describe what they want. Merchants list what they have. AI agents negotiate
            on both sides — every spending decision cryptographically bounded by a signed
            policy with verifiable receipts.
          </p>
          <div className="flex gap-3 pt-2">
            <Button asChild className="bg-zinc-900 hover:bg-zinc-700 text-white rounded-md">
              <Link to="/sessions">View Sessions</Link>
            </Button>
            <Button asChild variant="outline" className="rounded-md border-zinc-200 text-zinc-700">
              <Link to="/install-mcp">Install MCP</Link>
            </Button>
          </div>
        </div>
      </section>

      {/* ── Feature strip ───────────────────────────────────────────────── */}
      <section className="py-14">
        <h2 className="text-lg font-medium text-zinc-900 mb-8">How it works</h2>
        <div className="grid grid-cols-3 gap-4">
          {FEATURES.map((f) => (
            <div
              key={f.title}
              className="bg-white border border-zinc-200 rounded-md p-5 flex flex-col gap-2"
            >
              <span className="text-sm font-medium text-zinc-900">{f.title}</span>
              <p className="text-sm text-zinc-600 leading-relaxed">{f.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Audit strip ─────────────────────────────────────────────────── */}
      <section className="bg-white border border-zinc-200 rounded-md px-6 py-8 flex items-center justify-between">
        <p className="text-sm text-zinc-500">
          Every state change is written to an immutable audit log. No silent mutations.
        </p>
        <Button asChild variant="outline" className="rounded-md border-zinc-200 text-zinc-700 text-sm">
          <Link to="/sessions">Audit sessions</Link>
        </Button>
      </section>
    </div>
  )
}
