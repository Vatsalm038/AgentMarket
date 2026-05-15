export function PriceDisplay({ amount, className = "" }: { amount: number; className?: string }) {
  return (
    <span className={`font-mono ${className}`}>
      ₹{amount.toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 2 })}
    </span>
  )
}
