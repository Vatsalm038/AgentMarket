import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useAuth } from "@/contexts/AuthContext"
import { api } from "@/lib/api"
import { Skill } from "@/types"
import { Button } from "@/components/ui/button"

interface AgentItem {
  agent_id: string
  name: string
  skill_id: string | null
  created_at: string
}

export function BuyerAgentsPage() {
  const { user } = useAuth()
  const qc = useQueryClient()
  const [showDialog, setShowDialog] = useState(false)
  const [nickname, setNickname] = useState("")
  const [selectedSkillId, setSelectedSkillId] = useState("")
  const [createError, setCreateError] = useState<string | null>(null)

  const agentsQuery = useQuery<AgentItem[]>({
    queryKey: ["agents", user?.id],
    queryFn: async () => {
      const res = await api.get<AgentItem[]>("/agents")
      return res.data
    },
  })

  const skillsQuery = useQuery<Skill[]>({
    queryKey: ["skills"],
    queryFn: async () => {
      const res = await api.get<Skill[]>("/skills")
      return res.data
    },
    enabled: showDialog,
  })

  const createAgent = useMutation({
    mutationFn: async () => {
      if (!selectedSkillId) throw new Error("Select a skill.")
      const res = await api.post<AgentItem>("/agents/register", {
        name: nickname || undefined,
        skill_id: selectedSkillId,
      })
      return res.data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["agents"] })
      setShowDialog(false)
      setNickname("")
      setSelectedSkillId("")
      setCreateError(null)
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        (err instanceof Error ? err.message : "Failed to create agent.")
      setCreateError(msg)
    },
  })

  const agents = agentsQuery.data ?? []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-zinc-100">My Agents</h1>
        <Button
          onClick={() => setShowDialog(true)}
          className="bg-zinc-100 text-zinc-900 hover:bg-zinc-200 font-medium text-sm"
        >
          Create Agent
        </Button>
      </div>

      {agentsQuery.isLoading ? (
        <div className="space-y-2 animate-pulse">
          {[1, 2].map((i) => <div key={i} className="h-12 bg-zinc-800 rounded-md" />)}
        </div>
      ) : agentsQuery.isError ? (
        <p className="text-sm text-red-400">Failed to load agents.</p>
      ) : agents.length === 0 ? (
        <div className="text-center py-16 border border-zinc-800 rounded-md">
          <p className="text-sm text-zinc-500">No agents yet.</p>
          <p className="text-xs text-zinc-600 mt-1">Create one above to start negotiating.</p>
        </div>
      ) : (
        <div className="border border-zinc-700 rounded-md overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-zinc-800 border-b border-zinc-700">
                {["ID", "Name", "Skill", "Created"].map((h) => (
                  <th
                    key={h}
                    className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wide text-zinc-500"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {agents.map((agent) => (
                <tr
                  key={agent.agent_id}
                  className="border-b border-zinc-800 last:border-0 hover:bg-zinc-800 transition-colors"
                >
                  <td className="px-4 py-3 font-mono text-xs text-zinc-500">
                    {agent.agent_id.slice(0, 12)}…
                  </td>
                  <td className="px-4 py-3 text-zinc-300">{agent.name}</td>
                  <td className="px-4 py-3 font-mono text-xs text-zinc-500">
                    {agent.skill_id ? `${agent.skill_id.slice(0, 8)}…` : "—"}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-zinc-600">
                    {new Date(agent.created_at).toLocaleDateString("en-IN")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Modal dialog */}
      {showDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div
            className="absolute inset-0 bg-black/70"
            onClick={() => setShowDialog(false)}
          />
          <div className="relative z-10 bg-zinc-900 border border-zinc-700 rounded-md p-6 w-full max-w-sm space-y-5 shadow-sm">
            <h2 className="text-base font-semibold text-zinc-100">Create Agent</h2>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-zinc-400">Nickname (optional)</label>
              <input
                type="text"
                value={nickname}
                onChange={(e) => setNickname(e.target.value)}
                className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-zinc-500"
                placeholder="My Buyer Agent"
              />
            </div>

            <div className="space-y-2">
              <p className="text-xs font-medium text-zinc-400">Skill</p>
              {skillsQuery.isLoading ? (
                <p className="text-sm text-zinc-600">Loading skills…</p>
              ) : skillsQuery.isError ? (
                <p className="text-sm text-red-400">Failed to load skills.</p>
              ) : (skillsQuery.data ?? []).length === 0 ? (
                <p className="text-sm text-zinc-500">No skills available.</p>
              ) : (
                <div className="space-y-2">
                  {(skillsQuery.data ?? []).map((skill) => (
                    <label
                      key={skill.id}
                      className={`flex items-start gap-3 border rounded-md px-3 py-2.5 cursor-pointer transition-colors ${
                        selectedSkillId === skill.id
                          ? "border-emerald-500 bg-emerald-500/5"
                          : "border-zinc-700 hover:border-zinc-600"
                      }`}
                    >
                      <input
                        type="radio"
                        name="skill"
                        value={skill.id}
                        checked={selectedSkillId === skill.id}
                        onChange={() => setSelectedSkillId(skill.id)}
                        className="mt-0.5 accent-emerald-500"
                      />
                      <div>
                        <p className="text-sm text-zinc-200">{skill.name}</p>
                        <p className="text-xs text-zinc-500">{skill.description}</p>
                      </div>
                    </label>
                  ))}
                </div>
              )}
            </div>

            {createError && <p className="text-sm text-red-400">{createError}</p>}

            <div className="flex justify-end gap-3">
              <Button
                variant="ghost"
                onClick={() => setShowDialog(false)}
                className="text-zinc-400 hover:text-zinc-100"
              >
                Cancel
              </Button>
              <Button
                onClick={() => createAgent.mutate()}
                disabled={createAgent.isPending || !selectedSkillId}
                className="bg-zinc-100 text-zinc-900 hover:bg-zinc-200 font-medium"
              >
                {createAgent.isPending ? "Creating…" : "Create"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
