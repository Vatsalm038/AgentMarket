import React from "react"
import { Button } from "@/components/ui/button"
import { SignedReceipt } from "@/types"

function truncateId(id: string): string {
  if (id.length <= 18) return id
  return `${id.slice(0, 12)}...${id.slice(-6)}`
}

function inr(amount: number): string {
  return `₹${amount.toLocaleString("en-IN")}`
}

function formatTs(iso: string): string {
  return new Date(iso).toLocaleString("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  })
}

function downloadReceipt(receipt: SignedReceipt) {
  const blob = new Blob([JSON.stringify(receipt, null, 2)], { type: "application/json" })
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = `receipt-${receipt.receipt_id.slice(0, 12)}.json`
  a.click()
  URL.revokeObjectURL(url)
}

export function ReceiptBlock({ receipt }: { receipt: SignedReceipt }) {
  const rows: [string, React.ReactNode][] = [
    ["Receipt ID",     <span className="font-mono text-xs text-zinc-400">{truncateId(receipt.receipt_id)}</span>],
    ["Policy ID",      <span className="font-mono text-xs text-zinc-400">{truncateId(receipt.policy_id)}</span>],
    ["Amount",         <span className="tabular-nums text-zinc-200">{inr(receipt.amount_inr)}</span>],
    ["Buyer agent",    <span className="font-mono text-xs text-zinc-400">{truncateId(receipt.buyer_agent_id)}</span>],
    ["Merchant agent", <span className="font-mono text-xs text-zinc-400">{truncateId(receipt.merchant_agent_id)}</span>],
    ["Settled at",     <span className="text-zinc-300">{formatTs(receipt.created_at)}</span>],
    ...(receipt.razorpay_order_id
      ? [["Payment order", <span className="font-mono text-xs text-zinc-400">{receipt.razorpay_order_id}</span>] as [string, React.ReactNode]]
      : []),
    ...(receipt.razorpay_payment_id
      ? [["Payment ID", <span className="font-mono text-xs text-zinc-400">{receipt.razorpay_payment_id}</span>] as [string, React.ReactNode]]
      : []),
  ]

  return (
    <div className="bg-zinc-800 border border-zinc-700 rounded-md p-6 space-y-4">
      <dl className="grid grid-cols-[auto_1fr] gap-x-8 gap-y-2 text-sm">
        {rows.map(([label, value]) => (
          <React.Fragment key={String(label)}>
            <dt className="text-zinc-500 font-medium whitespace-nowrap">{label}</dt>
            <dd className="text-zinc-200">{value}</dd>
          </React.Fragment>
        ))}
      </dl>

      <div className="border-t border-zinc-700 pt-4 space-y-1">
        <p className="text-xs text-zinc-500 uppercase tracking-wide font-medium">Ed25519 Signature</p>
        <p className="font-mono text-xs text-zinc-500 break-all">{receipt.signature_b64}</p>
      </div>

      <div className="border-t border-zinc-700 pt-4 flex justify-end">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => downloadReceipt(receipt)}
          className="border border-zinc-700 text-zinc-300 hover:bg-zinc-700 hover:text-zinc-100"
        >
          Download receipt (.json)
        </Button>
      </div>
    </div>
  )
}
