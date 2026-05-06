---
name: frontend-component-writer
description: Use when creating new React components. Enforces design system rules, TanStack Query for server state, accessibility, and the bank/Anthropic aesthetic.
---

# Writing React Components for AgentMarket

## Aesthetic rules (NON-NEGOTIABLE — see docs/design-system.md)
- Theme: shadcn zinc, NEAR-grayscale only
- Background: white (#fff) or off-white (#fafaf9)
- Typography: Inter body, JetBrains Mono for IDs/code
- Single accent: zinc-900 (near-black) for primary
- Success: green-600 for verified ✓ ONLY
- Error: red-600 for invalid ✗ ONLY
- NO blue, purple, gradients, neon
- rounded-md (NOT rounded-2xl)
- shadow-sm or none (NOT shadow-lg)

## Component structure
```tsx
// src/components/<feature>/<ComponentName>.tsx
import { useQuery } from '@tanstack/react-query'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { fetchSomething } from '@/lib/api'
import { type Something } from '@/types'

interface Props {
  id: string
}

export function ComponentName({ id }: Props) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['something', id],
    queryFn: () => fetchSomething(id),
  })

  if (isLoading) return <ComponentSkeleton />
  if (isError) return <ComponentError />
  if (!data) return <ComponentEmpty />

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-medium">Title</CardTitle>
      </CardHeader>
      <CardContent>
        {/* content */}
      </CardContent>
    </Card>
  )
}

function ComponentSkeleton() {
  return <Skeleton className="h-32 w-full" />
}

function ComponentEmpty() {
  return (
    <div className="text-center py-12 text-zinc-600">
      <p className="text-sm">No data yet.</p>
    </div>
  )
}

function ComponentError() {
  return (
    <div className="text-center py-12 text-red-600">
      <p className="text-sm">Failed to load.</p>
    </div>
  )
}
```

## Required for every data component
- ✅ Loading state (Skeleton)
- ✅ Empty state (helpful guidance, not just "no data")
- ✅ Error state (clear, recoverable)
- ✅ TypeScript strict types from `@/types`

## Required for tables (the heart of this design)
```tsx
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow
} from '@/components/ui/table'

<Table>
  <TableHeader>
    <TableRow>
      <TableHead className="text-xs uppercase tracking-wide">ID</TableHead>
      <TableHead className="text-xs uppercase tracking-wide">Status</TableHead>
    </TableRow>
  </TableHeader>
  <TableBody>
    {items.map((item) => (
      <TableRow key={item.id} className="hover:bg-zinc-50">
        <TableCell className="font-mono text-xs">
          {item.id.slice(0, 12)}...
        </TableCell>
        <TableCell>
          <Badge variant="outline">{item.status}</Badge>
        </TableCell>
      </TableRow>
    ))}
  </TableBody>
</Table>
```

## Mono ID display pattern
```tsx
<span className="font-mono text-xs text-zinc-600">
  {id.slice(0, 12)}...{id.slice(-6)}
</span>
```

## Verify badge pattern
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

## Page layout pattern
```tsx
<div className="min-h-screen bg-zinc-50">
  <header className="border-b border-zinc-200 bg-white">
    <div className="max-w-6xl mx-auto px-6 py-4">
      <h1 className="text-xl font-medium text-zinc-900">Page Title</h1>
    </div>
  </header>
  <main className="max-w-6xl mx-auto px-6 py-8 space-y-8">
    {/* sections */}
  </main>
</div>
```

## Forbidden patterns
- ❌ `useState` for data that comes from the server (use TanStack Query)
- ❌ Inline styles (`style={{...}}`)
- ❌ Custom CSS files (use Tailwind)
- ❌ Custom rolled-your-own dropdown / modal / toast (use shadcn)
- ❌ Color outside the approved palette
- ❌ Emojis as decoration (functional only — ✓ ✗ for verify)
- ❌ Stock photos / hero images
- ❌ `any` type — fix types properly
- ❌ Missing loading/empty/error states

## File placement
- Reusable UI: `src/components/ui/` (shadcn lives here, don't pollute)
- Feature components: `src/components/<feature>/`
- Pages (route components): `src/routes/`
- API client: `src/lib/api.ts`
- Types: `src/types/index.ts`
- Hooks: `src/hooks/`

## Accessibility requirements
- All interactive elements have visible focus rings (shadcn handles by default)
- Tables have proper `<th>` semantics
- Buttons say what they do, not "click here"
- Status colors are accompanied by text or icon (not color-only)
- Form inputs have labels (use shadcn Label)
