import { Deal } from "@/types"

const STEPS = [
  { key: "negotiating", label: "Negotiating" },
  { key: "won",         label: "Deal Won" },
  { key: "paid",        label: "Payment" },
  { key: "dispatched",  label: "Dispatched" },
  { key: "delivered",   label: "Delivered" },
]

function resolveStepIndex(deal: Pick<Deal, "status" | "payment_status" | "delivery_status">): number {
  if (deal.delivery_status === "delivered") return 4
  if (deal.delivery_status === "dispatched") return 3
  if (deal.payment_status === "paid") return 2
  if (deal.status === "won" || deal.status === "settled") return 1
  return 0
}

interface DeliveryTimelineProps {
  deal: Pick<Deal, "status" | "payment_status" | "delivery_status">
}

export function DeliveryTimeline({ deal }: DeliveryTimelineProps) {
  const currentStep = resolveStepIndex(deal)

  return (
    <div className="flex items-start gap-0">
      {STEPS.map((step, i) => {
        const isPast    = i < currentStep
        const isCurrent = i === currentStep

        return (
          <div key={step.key} className="flex items-center flex-1 last:flex-none">
            <div className="flex flex-col items-center">
              {/* Circle */}
              <div
                className={`w-7 h-7 rounded-full border-2 flex items-center justify-center text-xs font-mono
                  ${isCurrent ? "border-emerald-500 bg-emerald-500 text-white" :
                    isPast    ? "border-zinc-600 bg-zinc-600 text-zinc-300" :
                               "border-zinc-700 bg-zinc-800 text-zinc-600"}
                `}
              >
                {isPast ? "✓" : i + 1}
              </div>
              {/* Label */}
              <span
                className={`mt-1.5 text-[10px] text-center whitespace-nowrap
                  ${isCurrent ? "text-emerald-400 font-medium" :
                    isPast    ? "text-zinc-500" :
                               "text-zinc-700"}
                `}
              >
                {step.label}
              </span>
            </div>

            {/* Connector line — not after last step */}
            {i < STEPS.length - 1 && (
              <div
                className={`flex-1 h-0.5 mt-[-14px] mx-1
                  ${i < currentStep ? "bg-zinc-600" : "bg-zinc-800"}
                `}
              />
            )}
          </div>
        )
      })}
    </div>
  )
}
