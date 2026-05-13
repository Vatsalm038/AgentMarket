import { useState } from 'react'
import { Button } from '@/components/ui/button'

// Static copy-paste guide — no data fetching needed
const CLAUDE_CONFIG = `{
  "mcpServers": {
    "agentmarket": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://YOUR-MCP-HOST/mcp"]
    }
  }
}`

const CLAUDE_CODE_CMD = `claude mcp add agentmarket --transport sse https://YOUR-MCP-HOST/sse`

const MCP_TOOLS = [
  { name: 'ping',                   description: 'Check backend health' },
  { name: 'search_local_merchants', description: 'Find merchants near a location' },
  { name: 'negotiate',              description: 'Run a full buyer-merchant auction' },
  { name: 'verify_receipt',         description: 'Verify an Ed25519 signed receipt' },
  { name: 'get_audit_trail',        description: 'Get full audit log for a session' },
  { name: 'replay_negotiation',     description: 'Re-run a session to verify AI decisions' },
]

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)

  function handleCopy() {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }).catch(() => {
      // Clipboard permission denied — silently ignore, user can copy manually
    })
  }

  return (
    <Button variant="secondary" size="sm" onClick={handleCopy}>
      {copied ? 'Copied!' : 'Copy'}
    </Button>
  )
}

export function InstallMcpPage() {
  return (
    <div className="min-h-screen bg-zinc-50">
      <div className="max-w-3xl mx-auto px-6 py-12 space-y-10">

        {/* Page header */}
        <div>
          <h1 className="text-xl font-medium text-zinc-900">Install MCP</h1>
          <p className="mt-1 text-sm text-zinc-600">
            Connect AgentMarket to Claude or ChatGPT in under a minute.
          </p>
        </div>

        {/* Section 1 — Claude Desktop */}
        <div className="bg-white border border-zinc-200 rounded-md">
          <div className="px-6 py-4 border-b border-zinc-200">
            <h2 className="text-lg font-medium text-zinc-900">Claude Desktop</h2>
          </div>
          <div className="px-6 py-5 space-y-4">
            <ol className="space-y-5 text-sm text-zinc-700 list-decimal list-inside">
              <li>
                Open Claude &rarr; Settings &rarr; Developer &rarr; Edit Config
              </li>
              <li>
                <span>Add to <code className="font-mono text-xs bg-zinc-100 px-1 py-0.5 rounded">claude_desktop_config.json</code>:</span>
                <div className="mt-3 relative">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-zinc-400 font-mono">claude_desktop_config.json</span>
                    <CopyButton text={CLAUDE_CONFIG} />
                  </div>
                  <pre className="bg-zinc-50 border border-zinc-200 text-zinc-700 text-xs font-mono rounded-md p-4 overflow-x-auto">
                    <code>{CLAUDE_CONFIG}</code>
                  </pre>
                </div>
              </li>
              <li>Restart Claude Desktop</li>
            </ol>
          </div>
        </div>

        {/* Section 2 — Claude Code */}
        <div className="bg-white border border-zinc-200 rounded-md">
          <div className="px-6 py-4 border-b border-zinc-200">
            <h2 className="text-lg font-medium text-zinc-900">Claude Code</h2>
          </div>
          <div className="px-6 py-5 space-y-3">
            <p className="text-sm text-zinc-700">Run this command in your terminal:</p>
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-zinc-400 font-mono">terminal</span>
                <CopyButton text={CLAUDE_CODE_CMD} />
              </div>
              <pre className="bg-zinc-50 border border-zinc-200 text-zinc-700 text-xs font-mono rounded-md p-4 overflow-x-auto">
                <code>{CLAUDE_CODE_CMD}</code>
              </pre>
            </div>
          </div>
        </div>

        {/* Section 3 — Available tools */}
        <div className="bg-white border border-zinc-200 rounded-md">
          <div className="px-6 py-4 border-b border-zinc-200">
            <h2 className="text-lg font-medium text-zinc-900">Available Tools</h2>
          </div>
          <div className="overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-zinc-50 border-b border-zinc-200">
                  <th className="px-4 py-2 text-left text-xs uppercase tracking-wide text-zinc-500 font-medium">
                    Tool
                  </th>
                  <th className="px-4 py-2 text-left text-xs uppercase tracking-wide text-zinc-500 font-medium">
                    Description
                  </th>
                </tr>
              </thead>
              <tbody>
                {MCP_TOOLS.map((tool) => (
                  <tr key={tool.name} className="border-b border-zinc-100 last:border-0">
                    <td className="px-4 py-2 font-mono text-xs text-zinc-700">{tool.name}</td>
                    <td className="px-4 py-2 text-zinc-600">{tool.description}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

      </div>
    </div>
  )
}
