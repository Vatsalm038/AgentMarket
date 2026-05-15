import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useAuth } from "@/contexts/AuthContext"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"

const BUILTIN_SKILLS = [
  { id: "skill_aggressive_haggler", name: "Aggressive Haggler", description: "Push hard for lowest price, anchor low" },
  { id: "skill_bulk_or_loyalty",    name: "Bulk / Loyalty",     description: "Leverage repeat business for better pricing" },
  { id: "skill_data_driven",        name: "Data Driven",        description: "Justify offers with market data & comparisons" },
  { id: "skill_polite_diplomat",    name: "Polite Diplomat",    description: "Courteous, concedes in small graceful steps" },
  { id: "skill_urgent",             name: "Urgent Closer",      description: "Trade margin for speed; pushes for fast close" },
  { id: "skill_walk_away",          name: "Walk Away",          description: "Credibly threatens to disengage; firm on limits" },
]

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
  const [createdAgentId, setCreatedAgentId] = useState<string | null>(null)

  const agentsQuery = useQuery<AgentItem[]>({
    queryKey: ["agents", user?.id],
    queryFn: async () => {
      try {
        const res = await api.get<AgentItem[]>(`/buyer/agents`)
        return res.data
      } catch {
        return []
      }
    },
  })


  const createAgent = useMutation({
    mutationFn: async () => {
      if (!selectedSkillId) throw new Error("Select a skill.")
      const res = await api.post<{ agent_id: string; public_key: string; private_key: string }>("/agents/register", {
        owner_id: user?.id,
        owner_user_id: user?.id,
        role: "user_agent",
      })
      return res.data
    },
    onSuccess: async (data) => {
      localStorage.setItem(`sd_agent_pk_${data.agent_id}`, data.private_key)
      // Auto-delegate a spending policy so the agent can negotiate immediately
      try {
        await api.post("/agents/delegate", {
          agent_id: data.agent_id,
          owner_private_key: data.private_key,
          owner_public_key: data.public_key,
          max_per_txn: 10000,
          max_per_day: 50000,
          currency: "INR",
        })
      } catch {
        // Non-fatal — user can still see the agent; negotiation will fail until policy exists
      }
      qc.invalidateQueries({ queryKey: ["agents"] })
      setShowDialog(false)
      setNickname("")
      setSelectedSkillId("")
      setCreateError(null)
      setCreatedAgentId(data.agent_id)
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        (err instanceof Error ? err.message : "Failed to create agent.")
      setCreateError(msg)
    },
  })

  const deleteAgent = useMutation({
    mutationFn: async (agentId: string) => {
      await api.delete(`/buyer/agents/${agentId}`)
      localStorage.removeItem(`sd_agent_pk_${agentId}`)
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["agents"] }),
  })

  const agents = agentsQuery.data ?? []

  const inputClass =
    "w-full bg-white border border-[#D8E1EA] rounded-md px-3 py-2 text-sm text-[#131212] placeholder:text-[#9DACBE] focus:outline-none focus:ring-1 focus:ring-[#4F87C8]"

  return (
    <div className="space-y-6">
      {createdAgentId && (
        <div className="border border-[#237B4B]/30 bg-[#E6F4EA] rounded-md px-4 py-3 flex items-start justify-between gap-4">
          <div className="space-y-0.5">
            <p className="text-sm font-medium text-[#237B4B]">Agent created</p>
            <p className="text-xs text-[#6C7F9A]">
              Signing key stored in this browser. If you clear browser data this agent will stop working — create a new one if that happens.
            </p>
            <p className="font-mono text-xs text-[#9DACBE] mt-1">{createdAgentId}</p>
          </div>
          <button onClick={() => setCreatedAgentId(null)} className="text-[#9DACBE] hover:text-[#131212] text-lg leading-none mt-0.5">×</button>
        </div>
      )}

      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-[#131212]">My Agents</h1>
        <Button
          onClick={() => setShowDialog(true)}
          className="bg-[#237B4B] text-white hover:bg-[#1A5F3D] font-medium text-sm"
        >
          Create Agent
        </Button>
      </div>

      {agentsQuery.isLoading ? (
        <div className="space-y-2 animate-pulse">
          {[1, 2].map((i) => <div key={i} className="h-12 bg-[#E4EAF1] rounded-md" />)}
        </div>
      ) : agentsQuery.isError ? (
        <p className="text-sm text-[#AA2C2C]">Failed to load agents.</p>
      ) : agents.length === 0 ? (
        <div className="text-center py-16 border border-[#D8E1EA] rounded-md">
          <p className="text-sm text-[#6C7F9A]">No agents yet.</p>
          <p className="text-xs text-[#9DACBE] mt-1">Create one above to start negotiating.</p>
        </div>
      ) : (
        <div className="border border-[#D8E1EA] rounded-md overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-[#F5F8FA] border-b border-[#D8E1EA]">
                {["ID", "Name", "Skill", "Created", ""].map((h) => (
                  <th
                    key={h}
                    className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wide text-[#9DACBE]"
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
                  className="border-b border-[#E4EAF1] last:border-0 hover:bg-[#F5F8FA] transition-colors"
                >
                  <td className="px-4 py-3 font-mono text-xs text-[#6C7F9A]">
                    {agent.agent_id.slice(0, 12)}…
                  </td>
                  <td className="px-4 py-3 text-[#131212]">{agent.name}</td>
                  <td className="px-4 py-3 font-mono text-xs text-[#6C7F9A]">
                    {agent.skill_id ? `${agent.skill_id.slice(0, 8)}…` : "—"}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-[#9DACBE]">
                    {new Date(agent.created_at).toLocaleDateString("en-IN")}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => {
                        if (confirm("Delete this agent? This cannot be undone.")) {
                          deleteAgent.mutate(agent.agent_id)
                        }
                      }}
                      disabled={deleteAgent.isPending}
                      className="text-xs text-red-600 hover:text-red-400 disabled:opacity-40"
                    >
                      Delete
                    </button>
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
            className="absolute inset-0 bg-black/50"
            onClick={() => setShowDialog(false)}
          />
          <div className="relative z-10 bg-white border border-[#D8E1EA] rounded-md p-6 w-full max-w-sm space-y-5 shadow-sm">
            <h2 className="text-base font-semibold text-[#131212]">Create Agent</h2>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-[#6C7F9A]">Nickname (optional)</label>
              <input
                type="text"
                value={nickname}
                onChange={(e) => setNickname(e.target.value)}
                className={inputClass}
                placeholder="My Buyer Agent"
              />
            </div>

            <div className="space-y-2">
              <p className="text-xs font-medium text-[#6C7F9A]">Skill</p>
              <div className="space-y-2">
                {BUILTIN_SKILLS.map((skill) => (
                  <label
                    key={skill.id}
                    className={`flex items-start gap-3 border rounded-md px-3 py-2.5 cursor-pointer transition-colors ${
                      selectedSkillId === skill.id
                        ? "border-[#237B4B] bg-[#E6F4EA]"
                        : "border-[#D8E1EA] hover:bg-[#F5F8FA]"
                    }`}
                  >
                    <input
                      type="radio"
                      name="skill"
                      value={skill.id}
                      checked={selectedSkillId === skill.id}
                      onChange={() => setSelectedSkillId(skill.id)}
                      className="mt-0.5 accent-[#237B4B]"
                    />
                    <div>
                      <p className="text-sm text-[#131212]">{skill.name}</p>
                      <p className="text-xs text-[#6C7F9A]">{skill.description}</p>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            {createError && <p className="text-sm text-[#AA2C2C]">{createError}</p>}

            <div className="flex justify-end gap-3">
              <Button
                variant="ghost"
                onClick={() => setShowDialog(false)}
                className="border border-[#D8E1EA] text-[#6C7F9A] hover:bg-[#F5F8FA]"
              >
                Cancel
              </Button>
              <Button
                onClick={() => createAgent.mutate()}
                disabled={createAgent.isPending || !selectedSkillId}
                className="bg-[#237B4B] text-white hover:bg-[#1A5F3D] font-medium"
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
