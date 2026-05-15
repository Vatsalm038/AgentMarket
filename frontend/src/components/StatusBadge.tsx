import { Badge } from "@/components/ui/badge"

const config: Record<string, { label: string; className: string }> = {
  negotiating:      { label: "Negotiating",      className: "border-amber-400 text-amber-600" },
  pending_approval: { label: "Pending Approval", className: "border-amber-400 text-amber-600" },
  won:              { label: "Won",              className: "border-[#237B4B] text-[#237B4B]" },
  settled:          { label: "Settled",          className: "border-[#237B4B] text-[#237B4B]" },
  delivered:        { label: "Delivered",        className: "border-[#237B4B] text-[#237B4B]" },
  disputed:         { label: "Disputed",         className: "border-red-400 text-red-600" },
  failed:           { label: "Failed",           className: "border-red-400 text-red-600" },
  pay_later:        { label: "Pay Later",        className: "border-amber-400 text-amber-600" },
  dispatched:       { label: "Dispatched",       className: "border-sky-400 text-sky-600" },
  pending:          { label: "Pending",          className: "border-[#D8E1EA] text-[#6C7F9A]" },
  revoked:          { label: "Revoked",          className: "border-red-400 text-red-600" },
  paid:             { label: "Paid",             className: "border-[#237B4B] text-[#237B4B]" },
}

export function StatusBadge({ status }: { status: string }) {
  const c = config[status] ?? { label: status, className: "border-[#D8E1EA] text-[#6C7F9A]" }
  return (
    <Badge variant="outline" className={`text-xs ${c.className}`}>
      {c.label}
    </Badge>
  )
}
