export function ProfitBadge({ profitAmount, profitPct }: { profitAmount: number; profitPct: number }) {
  return (
    <span className="text-xs font-medium text-sky-400 bg-sky-400/10 px-2 py-0.5 rounded-full">
      Profit ₹{profitAmount.toLocaleString("en-IN")} ({profitPct.toFixed(1)}% above floor)
    </span>
  )
}
