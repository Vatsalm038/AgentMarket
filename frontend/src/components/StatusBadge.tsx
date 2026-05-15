import { Badge } from "@/components/ui/badge"

const config: Record<string, { label: string; className: string }> = {
  negotiating:      { label: "Negotiating",      className: "border-amber-400 text-amber-400" },
  pending_approval: { label: "Pending Approval", className: "border-amber-400 text-amber-400" },
  won:              { label: "Won",              className: "border-emerald-500 text-emerald-500" },
  settled:          { label: "Settled",          className: "border-emerald-500 text-emerald-500" },
  delivered:        { label: "Delivered",        className: "border-emerald-500 text-emerald-500" },
  disputed:         { label: "Disputed",         className: "border-red-500 text-red-500" },
  failed:           { label: "Failed",           className: "border-red-500 text-red-500" },
  pay_later:        { label: "Pay Later",        className: "border-amber-400 text-amber-400" },
  dispatched:       { label: "Dispatched",       className: "border-sky-400 text-sky-400" },
  pending:          { label: "Pending",          className: "border-zinc-500 text-zinc-400" },
  revoked:          { label: "Revoked",          className: "border-red-500 text-red-500" },
  paid:             { label: "Paid",             className: "border-emerald-500 text-emerald-500" },
}

export function StatusBadge({ status }: { status: string }) {
  const c = config[status] ?? { label: status, className: "border-zinc-500 text-zinc-400" }
  return (
    <Badge variant="outline" className={`text-xs ${c.className}`}>
      {c.label}
    </Badge>
  )
}
