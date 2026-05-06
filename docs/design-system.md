# Design System — AgentMarket

Aesthetic: Anthropic console + Stripe dashboard + Linear + RBI/SEBI website.
Bank-grade trust through restraint.

## Reference URLs (look at these before designing)
- console.anthropic.com
- dashboard.stripe.com
- linear.app
- rbi.org.in (yes, really — for the audit table aesthetic)

## Hard rules

### Color
- Background: white (#ffffff) or off-white (#fafaf9)
- Text: zinc-900 (#18181b) for body, zinc-600 (#52525b) for secondary
- Borders: zinc-200 (#e4e4e7), 1px solid
- Primary action: zinc-900 background, white text
- Success only: green-600 (#16a34a) — for verified ✓ states only
- Error only: red-600 (#dc2626) — for invalid ✗ states only
- NO blue, purple, orange, pink, gradients

### Typography
- Body: Inter, font-sans
- Codes/IDs/signatures/JSON: JetBrains Mono, font-mono
- Headings: Inter, font-medium (not bold)
- Sizes: text-sm default, text-base for body, text-lg for h2, text-xl for h1
- No uppercase except very small labels (text-xs uppercase tracking-wide)

### Spacing
- Tailwind default scale: 2, 4, 6, 8, 12, 16
- Generous whitespace, especially around tables
- p-6 inside cards, p-8 around page sections

### Components
- shadcn/ui only. Don't write custom components unless shadcn doesn't have it.
- rounded-md (NOT rounded-2xl)
- shadow-sm or none (NOT shadow-lg)
- Buttons: zinc-900 primary, zinc-200 secondary, ghost for tertiary
- Tables: shadcn Table — primary data viz pattern
- Badges: shadcn Badge with variant outline for status

### Tables (the heart of this design)
- Use for: sessions list, negotiation rounds, audit log, merchants list
- Compact rows, mono font for IDs
- Sortable headers (use shadcn data-table or simple sort)
- Hover state: bg-zinc-50
- Selected row: bg-zinc-100

### What NOT to do
- ❌ Gradient backgrounds
- ❌ Blue primary buttons
- ❌ Card-heavy dashboards (use tables)
- ❌ rounded-2xl or rounded-3xl
- ❌ shadow-lg or shadow-xl
- ❌ Animated icons or marquees
- ❌ Hero images or stock photos
- ❌ Emojis as decoration (functional only — ✓ for verified)
- ❌ Inline styles
- ❌ "AI startup" purple/cyan/neon

### What TO do
- ✅ Tables with mono IDs
- ✅ Single near-black accent
- ✅ Whitespace
- ✅ Loading skeletons (shadcn Skeleton)
- ✅ Empty states with helpful guidance
- ✅ Badge for status (outline variant)
- ✅ Code blocks (mono, light gray bg) for JSON receipts
- ✅ Subtle focus rings

## Component patterns

### Page layout
```tsx
<div className="min-h-screen bg-zinc-50">
  <header className="border-b border-zinc-200 bg-white">
    <div className="max-w-6xl mx-auto px-6 py-4">...</div>
  </header>
  <main className="max-w-6xl mx-auto px-6 py-8">...</main>
</div>
```

### Section header
```tsx
<div className="border-b border-zinc-200 pb-3 mb-6">
  <h2 className="text-lg font-medium text-zinc-900">Negotiation Trail</h2>
  <p className="text-sm text-zinc-600 mt-1">All rounds and decisions, signed and timestamped</p>
</div>
```

### Mono ID display
```tsx
<span className="font-mono text-xs text-zinc-600">
  {id.slice(0, 12)}...{id.slice(-6)}
</span>
```

### Verify badge
```tsx
{valid ? (
  <Badge variant="outline" className="border-green-600 text-green-700">
    ✓ Verified
  </Badge>
) : (
  <Badge variant="outline" className="border-red-600 text-red-700">
    ✗ Invalid
  </Badge>
)}
```

## Pages (6 total)

1. `/` — landing, 4 sentences, 2 CTA buttons
2. `/sessions` — table of all sessions
3. `/session/:id` — auth + trail + receipt stacked
4. `/replay/:id` — side-by-side original vs replay
5. `/verify` — paste receipt JSON, verify it
6. `/install-mcp` — copy-paste MCP install instructions

That's it. No more pages. If you want to add one, push it to backlog.md.
