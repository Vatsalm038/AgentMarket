import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

// Receipt fields matching the backend settled_transactions shape
interface ParsedReceipt {
  receipt_id?: string
  policy_id?: string
  amount_inr?: number
  buyer_agent_id?: string
  merchant_agent_id?: string
  signature_b64?: string
  signed_payload_b64?: string
  payload_json?: string
  razorpay_order_id?: string
  razorpay_payment_id?: string
  created_at?: string
  [key: string]: unknown
}

function truncate(value: string, maxLen = 40): string {
  return value.length > maxLen ? value.slice(0, maxLen) + '…' : value
}

export function VerifyPage() {
  const [input, setInput] = useState('')
  const [receipt, setReceipt] = useState<ParsedReceipt | null>(null)
  const [parseError, setParseError] = useState<string | null>(null)

  function handleVerify() {
    // Reset previous state before each attempt
    setReceipt(null)
    setParseError(null)

    try {
      const parsed = JSON.parse(input) as ParsedReceipt
      setReceipt(parsed)
    } catch {
      setParseError('Invalid JSON — could not parse receipt.')
    }
  }

  const hasSignature = Boolean(receipt?.signature_b64)

  return (
    <div className="min-h-screen bg-zinc-50">
      <div className="max-w-2xl mx-auto px-6 py-12 space-y-8">

        {/* Page header */}
        <div>
          <h1 className="text-xl font-medium text-zinc-900">Verify Receipt</h1>
          <p className="mt-1 text-sm text-zinc-600">
            Paste a signed receipt to verify the Ed25519 signature against the platform public key.
          </p>
        </div>

        {/* Input card */}
        <div className="bg-white border border-zinc-200 rounded-md px-6 py-5 space-y-4">
          <div>
            <label htmlFor="receipt-input" className="block text-sm font-medium text-zinc-700 mb-2">
              Receipt JSON
            </label>
            <textarea
              id="receipt-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Paste receipt JSON here..."
              className="w-full h-48 font-mono text-xs border border-zinc-200 rounded-md p-3 bg-white focus:outline-none focus:ring-1 focus:ring-zinc-400 resize-y text-zinc-900 placeholder:text-zinc-400"
            />
          </div>
          <Button onClick={handleVerify} disabled={!input.trim()}>
            Verify
          </Button>
        </div>

        {/* Parse error */}
        {parseError && (
          <p className="text-sm text-red-600">{parseError}</p>
        )}

        {/* Result card */}
        {receipt && (
          <div className="bg-white border border-zinc-200 rounded-md px-6 py-5 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-medium text-zinc-900">Receipt Fields</h2>
              {hasSignature ? (
                <Badge variant="outline" className="border-zinc-300 text-zinc-600">
                  Signature present
                </Badge>
              ) : (
                <Badge variant="outline" className="border-red-300 text-red-600">
                  No signature
                </Badge>
              )}
            </div>

            <dl className="grid grid-cols-[auto_1fr] gap-x-8 gap-y-2 text-sm">
              {receipt.receipt_id && (
                <>
                  <dt className="text-zinc-500 font-medium whitespace-nowrap">Receipt ID</dt>
                  <dd className="font-mono text-xs text-zinc-700 break-all">{receipt.receipt_id}</dd>
                </>
              )}
              {receipt.policy_id && (
                <>
                  <dt className="text-zinc-500 font-medium whitespace-nowrap">Policy ID</dt>
                  <dd className="font-mono text-xs text-zinc-700 break-all">{receipt.policy_id}</dd>
                </>
              )}
              {receipt.amount_inr !== undefined && (
                <>
                  <dt className="text-zinc-500 font-medium whitespace-nowrap">Amount</dt>
                  {/* en-IN locale gives Indian comma grouping: 1,00,000 */}
                  <dd className="font-mono text-xs text-zinc-700">₹{receipt.amount_inr.toLocaleString('en-IN')}</dd>
                </>
              )}
              {receipt.buyer_agent_id && (
                <>
                  <dt className="text-zinc-500 font-medium whitespace-nowrap">Buyer Agent</dt>
                  <dd className="font-mono text-xs text-zinc-700 break-all">{receipt.buyer_agent_id}</dd>
                </>
              )}
              {receipt.merchant_agent_id && (
                <>
                  <dt className="text-zinc-500 font-medium whitespace-nowrap">Merchant Agent</dt>
                  <dd className="font-mono text-xs text-zinc-700 break-all">{receipt.merchant_agent_id}</dd>
                </>
              )}
              {receipt.razorpay_order_id && (
                <>
                  <dt className="text-zinc-500 font-medium whitespace-nowrap">Razorpay Order</dt>
                  <dd className="font-mono text-xs text-zinc-700 break-all">{receipt.razorpay_order_id}</dd>
                </>
              )}
              {receipt.razorpay_payment_id && (
                <>
                  <dt className="text-zinc-500 font-medium whitespace-nowrap">Razorpay Payment</dt>
                  <dd className="font-mono text-xs text-zinc-700 break-all">{receipt.razorpay_payment_id}</dd>
                </>
              )}
              {receipt.signature_b64 && (
                <>
                  <dt className="text-zinc-500 font-medium whitespace-nowrap">Signature</dt>
                  {/* Truncate long base64 signatures for readability */}
                  <dd className="font-mono text-xs text-zinc-700 break-all" title={receipt.signature_b64}>
                    {truncate(receipt.signature_b64)}
                  </dd>
                </>
              )}
              {receipt.created_at && (
                <>
                  <dt className="text-zinc-500 font-medium whitespace-nowrap">Created At</dt>
                  <dd className="font-mono text-xs text-zinc-700">{receipt.created_at}</dd>
                </>
              )}
            </dl>

            {/* Expandable raw payload — useful for debugging / auditing */}
            {receipt.payload_json && (
              <details className="mt-2">
                <summary className="text-xs text-zinc-500 cursor-pointer select-none hover:text-zinc-700">
                  Raw payload_json
                </summary>
                <pre className="mt-2 text-xs font-mono bg-zinc-50 border border-zinc-200 rounded-md p-3 overflow-x-auto text-zinc-700 whitespace-pre-wrap break-all">
                  {(() => {
                    try {
                      return JSON.stringify(JSON.parse(receipt.payload_json!), null, 2)
                    } catch {
                      // Not valid JSON — render as-is
                      return receipt.payload_json
                    }
                  })()}
                </pre>
              </details>
            )}

            <p className="text-xs text-zinc-500 mt-4">
              To cryptographically verify: run{' '}
              <code className="font-mono bg-zinc-100 px-1 py-0.5 rounded">
                verify_receipt(&quot;receipt_id&quot;)
              </code>{' '}
              via the AgentMarket MCP tool.
            </p>

            {/* Footer: deep-link to session + MCP hint, only when receipt_id is known */}
            {receipt.receipt_id && (
              <div className="pt-4 border-t border-zinc-100 flex items-center justify-between">
                <span className="text-xs text-zinc-400">
                  View session or run{' '}
                  <code className="font-mono bg-zinc-100 px-1 py-0.5 rounded text-zinc-600">
                    get_session
                  </code>{' '}
                  MCP tool with this receipt ID.
                </span>
                <a
                  href={`/sessions?receipt=${receipt.receipt_id}`}
                  className="text-xs font-medium text-zinc-700 underline underline-offset-2 hover:text-zinc-900"
                >
                  View session
                </a>
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  )
}
