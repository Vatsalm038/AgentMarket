import { useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

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
  const fileInputRef = useRef<HTMLInputElement>(null)

  function handleVerify() {
    setReceipt(null)
    setParseError(null)
    try {
      const parsed = JSON.parse(input) as ParsedReceipt
      setReceipt(parsed)
    } catch {
      setParseError('Could not read the receipt — make sure you pasted or uploaded the correct file.')
    }
  }

  function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (evt) => {
      setInput((evt.target?.result as string) ?? '')
      setReceipt(null)
      setParseError(null)
    }
    reader.readAsText(file)
  }

  const hasSignature = Boolean(receipt?.signature_b64)

  return (
    <div className="max-w-2xl space-y-8">
      <div>
        <h1 className="text-xl font-medium text-[#131212]">Verify Receipt</h1>
        <p className="mt-1 text-sm text-[#6C7F9A]">
          Paste or upload your receipt JSON file to inspect a signed deal receipt.
        </p>
      </div>

      <div className="bg-white border border-[#D8E1EA] rounded-md px-6 py-5 space-y-4">
        <div>
          <label htmlFor="receipt-input" className="block text-sm font-medium text-[#131212] mb-2">
            Receipt JSON
          </label>
          <textarea
            id="receipt-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Paste receipt JSON here, or use the upload button below…"
            className="w-full h-48 font-mono text-xs border border-[#D8E1EA] rounded-md p-3 bg-[#F5F8FA] focus:outline-none focus:ring-1 focus:ring-[#4F87C8] resize-y text-[#131212] placeholder:text-[#9DACBE]"
          />
        </div>

        <div className="flex items-center gap-3">
          <Button
            onClick={handleVerify}
            disabled={!input.trim()}
            className="bg-[#237B4B] hover:bg-[#1A5F3D] text-white disabled:opacity-40"
          >
            Verify
          </Button>
          <Button
            variant="ghost"
            onClick={() => fileInputRef.current?.click()}
            className="border border-[#D8E1EA] text-[#6C7F9A] hover:bg-[#F5F8FA] hover:text-[#131212]"
          >
            Upload JSON file
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".json,application/json"
            className="hidden"
            onChange={handleFile}
          />
        </div>
      </div>

      {parseError && (
        <p className="text-sm text-[#AA2C2C]">{parseError}</p>
      )}

      {receipt && (
        <div className="bg-white border border-[#D8E1EA] rounded-md px-6 py-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-medium text-[#131212]">Receipt Details</h2>
            {hasSignature ? (
              <Badge variant="outline" className="border-[#237B4B] text-[#237B4B]">Signed ✓</Badge>
            ) : (
              <Badge variant="outline" className="border-red-400 text-red-600">No signature</Badge>
            )}
          </div>

          <dl className="grid grid-cols-[auto_1fr] gap-x-8 gap-y-3 text-sm">
            {receipt.receipt_id && (
              <>
                <dt className="text-[#6C7F9A] font-medium whitespace-nowrap">Receipt ID</dt>
                <dd className="font-mono text-xs text-[#131212] break-all">{receipt.receipt_id}</dd>
              </>
            )}
            {receipt.amount_inr !== undefined && (
              <>
                <dt className="text-[#6C7F9A] font-medium whitespace-nowrap">Amount paid</dt>
                <dd className="text-[#237B4B] font-semibold">₹{Number(receipt.amount_inr).toLocaleString('en-IN')}</dd>
              </>
            )}
            {receipt.buyer_agent_id && (
              <>
                <dt className="text-[#6C7F9A] font-medium whitespace-nowrap">Buyer Agent</dt>
                <dd className="font-mono text-xs text-[#131212] break-all">{receipt.buyer_agent_id}</dd>
              </>
            )}
            {receipt.merchant_agent_id && (
              <>
                <dt className="text-[#6C7F9A] font-medium whitespace-nowrap">Merchant Agent</dt>
                <dd className="font-mono text-xs text-[#131212] break-all">{receipt.merchant_agent_id}</dd>
              </>
            )}
            {receipt.razorpay_order_id && (
              <>
                <dt className="text-[#6C7F9A] font-medium whitespace-nowrap">Payment Order</dt>
                <dd className="font-mono text-xs text-[#131212] break-all">{receipt.razorpay_order_id}</dd>
              </>
            )}
            {receipt.razorpay_payment_id && (
              <>
                <dt className="text-[#6C7F9A] font-medium whitespace-nowrap">Payment ID</dt>
                <dd className="font-mono text-xs text-[#131212] break-all">{receipt.razorpay_payment_id}</dd>
              </>
            )}
            {receipt.signature_b64 && (
              <>
                <dt className="text-[#6C7F9A] font-medium whitespace-nowrap">Signature</dt>
                <dd className="font-mono text-xs text-[#6C7F9A] break-all" title={receipt.signature_b64}>
                  {truncate(receipt.signature_b64)}
                </dd>
              </>
            )}
            {receipt.created_at && (
              <>
                <dt className="text-[#6C7F9A] font-medium whitespace-nowrap">Signed at</dt>
                <dd className="text-xs text-[#131212]">
                  {new Date(receipt.created_at).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })}
                </dd>
              </>
            )}
          </dl>

          {hasSignature && (
            <div className="rounded-md bg-[#E6F4EA] border border-[#237B4B]/30 px-4 py-3">
              <p className="text-sm text-[#237B4B]">
                This receipt has a cryptographic signature. It was signed by your buyer agent and cannot be tampered with.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
