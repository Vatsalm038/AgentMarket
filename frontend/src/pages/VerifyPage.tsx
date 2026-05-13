import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

// Receipt fields we know how to display from the signed payload
interface ParsedReceipt {
  receipt_id?: string
  policy_id?: string
  amount?: string | number
  buyer_agent?: string
  merchant_agent?: string
  signature_b64?: string
  signed_payload_b64?: string
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
                // secondary variant gives bg-zinc-100; override text color to zinc-600 per spec
                <Badge variant="secondary" className="text-zinc-600">
                  Signature present
                </Badge>
              ) : (
                <Badge variant="outline" className="text-zinc-400">
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
              {receipt.amount !== undefined && (
                <>
                  <dt className="text-zinc-500 font-medium whitespace-nowrap">Amount</dt>
                  <dd className="font-mono text-xs text-zinc-700">{String(receipt.amount)}</dd>
                </>
              )}
              {receipt.buyer_agent && (
                <>
                  <dt className="text-zinc-500 font-medium whitespace-nowrap">Buyer Agent</dt>
                  <dd className="font-mono text-xs text-zinc-700 break-all">{receipt.buyer_agent}</dd>
                </>
              )}
              {receipt.merchant_agent && (
                <>
                  <dt className="text-zinc-500 font-medium whitespace-nowrap">Merchant Agent</dt>
                  <dd className="font-mono text-xs text-zinc-700 break-all">{receipt.merchant_agent}</dd>
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

            <p className="text-xs text-zinc-500 mt-4">
              To cryptographically verify: run{' '}
              <code className="font-mono bg-zinc-100 px-1 py-0.5 rounded">
                verify_receipt(&quot;receipt_id&quot;)
              </code>{' '}
              via the AgentMarket MCP tool.
            </p>
          </div>
        )}

      </div>
    </div>
  )
}
