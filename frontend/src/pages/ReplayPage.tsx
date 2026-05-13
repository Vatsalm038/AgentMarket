import { Link, useParams } from 'react-router-dom'
import { useSession } from '@/hooks/useApi'
import { Badge } from '@/components/ui/badge'

// ─── Replay data type ─────────────────────────────────────────────────────────

interface MerchantQuote {
  merchant_id: string
  merchant_name: string
  prompt: string
  response: string
  floor_price: number
  final_price: number
}

interface BuyerEvaluation {
  prompt: string
  response: string
  winner_id: string
  winner_price: number
}

interface ReplayData {
  merchant_quotes?: MerchantQuote[]
  buyer_evaluation?: BuyerEvaluation
  model?: string
  seed?: number
  temperature?: number
}

// Type guard — replay_data is `unknown` from the API, cast carefully
function isReplayData(v: unknown): v is ReplayData {
  return typeof v === 'object' && v !== null
}

// ─── Collapsible prompt / response pair ──────────────────────────────────────

function CollapsibleBlock({ label, text }: { label: string; text: string }) {
  return (
    <details className="mt-2">
      <summary className="cursor-pointer text-xs text-zinc-500 select-none">
        {label}
      </summary>
      <pre className="mt-2 font-mono text-xs bg-zinc-50 border border-zinc-100 rounded-md p-3 whitespace-pre-wrap break-all text-zinc-600 overflow-auto max-h-48">
        {text}
      </pre>
    </details>
  )
}

// ─── Merchant quote card ──────────────────────────────────────────────────────

function MerchantQuoteCard({ quote }: { quote: MerchantQuote }) {
  return (
    <div className="bg-white border border-zinc-200 rounded-md p-4 mb-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-zinc-900">
          {quote.merchant_name}
        </span>
        <span className="font-mono text-xs text-zinc-500">
          floor ₹{quote.floor_price} · final ₹{quote.final_price}
        </span>
      </div>
      <CollapsibleBlock label="prompt" text={quote.prompt} />
      <CollapsibleBlock label="response" text={quote.response} />
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export function ReplayPage() {
  const { id = '' } = useParams<{ id: string }>()
  const { data, isLoading, isError } = useSession(id)

  // Truncate session id for the back-link label (first 8 chars)
  const truncatedId = id.slice(0, 8)

  // ── Loading ──
  if (isLoading) {
    return (
      <div className="min-h-screen bg-zinc-50 p-8">
        <div className="max-w-5xl mx-auto">
          <div className="h-6 w-40 bg-zinc-100 rounded-md animate-pulse mb-8" />
          <div className="grid grid-cols-2 gap-6">
            <div className="h-64 bg-zinc-100 rounded-md animate-pulse" />
            <div className="h-64 bg-zinc-100 rounded-md animate-pulse" />
          </div>
        </div>
      </div>
    )
  }

  // ── Error / missing ──
  if (isError || !data) {
    return (
      <div className="min-h-screen bg-zinc-50 p-8">
        <div className="max-w-5xl mx-auto">
          <p className="text-sm text-zinc-500">Session not found.</p>
        </div>
      </div>
    )
  }

  const { winner_skill_id, llm_seed, replay_data } = data
  const rd: ReplayData | null = isReplayData(replay_data) ? replay_data : null

  return (
    <div className="min-h-screen bg-zinc-50">
      {/* ── Top bar ── */}
      <div className="bg-white border-b border-zinc-200 px-8 py-4">
        <div className="max-w-5xl mx-auto">
          {/* Back link */}
          <Link
            to={`/session/${id}`}
            className="text-sm text-zinc-500 hover:text-zinc-900 transition-colors"
          >
            &larr; Session {truncatedId}
          </Link>

          {/* Title row */}
          <div className="mt-3 flex items-start justify-between gap-4">
            <div>
              <h1 className="text-xl font-medium text-zinc-900">
                Verifiable Replay
              </h1>
              <p className="mt-1 text-sm text-zinc-600">
                Original run vs. deterministic replay. Same seed, same
                temperature, same prompts.
              </p>
            </div>

            {/* Right-side metadata */}
            <div className="flex flex-col items-end gap-2 shrink-0">
              {winner_skill_id && (
                <Badge className="bg-zinc-100 text-zinc-700 hover:bg-zinc-100 border-0">
                  Skill: {winner_skill_id}
                </Badge>
              )}
              {llm_seed !== null && llm_seed !== undefined && (
                <span className="font-mono text-xs text-zinc-500">
                  seed: {llm_seed}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ── Body ── */}
      <div className="max-w-5xl mx-auto px-8 py-8">

        {/* Two-column layout */}
        <div className="grid grid-cols-2 gap-6">

          {/* Left — Original run */}
          <div>
            <p className="text-sm font-medium uppercase tracking-wide text-zinc-500 mb-3">
              Original
            </p>

            {rd === null ? (
              <p className="text-sm text-zinc-500">
                Replay data not captured for this session.
              </p>
            ) : (
              <>
                {rd.merchant_quotes && rd.merchant_quotes.length > 0 ? (
                  rd.merchant_quotes.map((q) => (
                    <MerchantQuoteCard key={q.merchant_id} quote={q} />
                  ))
                ) : (
                  <p className="text-sm text-zinc-500">
                    No merchant quotes recorded.
                  </p>
                )}

                {/* Model / temperature metadata */}
                {(rd.model || rd.temperature !== undefined) && (
                  <div className="mt-2 font-mono text-xs text-zinc-400 space-x-3">
                    {rd.model && <span>model: {rd.model}</span>}
                    {rd.temperature !== undefined && (
                      <span>temp: {rd.temperature}</span>
                    )}
                  </div>
                )}
              </>
            )}
          </div>

          {/* Right — Replay (simulated) */}
          <div>
            <p className="text-sm font-medium uppercase tracking-wide text-zinc-500 mb-3">
              Replay
            </p>

            <div className="bg-zinc-50 border border-zinc-200 rounded-md p-6 text-center">
              <p className="text-sm font-medium text-zinc-900">
                Replay execution happens via MCP
              </p>
              <p className="text-sm text-zinc-500 mt-1">
                Run{' '}
                <code className="font-mono text-xs">
                  replay_negotiation(&quot;{id}&quot;)
                </code>{' '}
                in Claude or ChatGPT to execute a live replay and compare
                outcomes.
              </p>
              <pre className="mt-4 font-mono text-xs bg-white border border-zinc-100 rounded-md p-3 text-left text-zinc-600">
                {`replay_negotiation("${id}")`}
              </pre>
            </div>
          </div>
        </div>

        {/* ── Buyer evaluation (full width) ── */}
        {rd?.buyer_evaluation && (
          <div className="mt-10">
            <p className="text-sm font-medium uppercase tracking-wide text-zinc-500 mb-3">
              Buyer Evaluation
            </p>

            <div className="bg-white border border-zinc-200 rounded-md p-4">
              <div className="flex items-center gap-4 text-xs font-mono text-zinc-500">
                <span>winner: {rd.buyer_evaluation.winner_id}</span>
                <span>price: ₹{rd.buyer_evaluation.winner_price}</span>
              </div>
              <CollapsibleBlock
                label="prompt"
                text={rd.buyer_evaluation.prompt}
              />
              <CollapsibleBlock
                label="response"
                text={rd.buyer_evaluation.response}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
