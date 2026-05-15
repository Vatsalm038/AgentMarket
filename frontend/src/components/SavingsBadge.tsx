export function SavingsBadge({ savedAmount, savedPct }: { savedAmount: number; savedPct: number }) {
  return (
    <span className="text-xs font-medium text-[#237B4B] bg-[#E6F4EA] px-2 py-0.5 rounded-full">
      Saved ₹{savedAmount.toLocaleString("en-IN")} ({savedPct.toFixed(1)}% below max)
    </span>
  )
}
