import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useAuth } from "@/contexts/AuthContext"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"

interface MerchantAgentInfo {
  agent_id: string
  skill_id: string | null
  skill_name?: string
  merchant_id: string
  created_at: string
}

interface Skill {
  id: string
  name: string
  description: string
}

const SKILL_LABELS: Record<string, string> = {
  aggressive_haggler: "Aggressive Haggler",
  bulk_or_loyalty: "Bulk / Loyalty",
  data_driven: "Data Driven",
  polite_diplomat: "Polite Diplomat",
  urgent: "Urgent Closer",
  walk_away: "Walk Away",
}

export function MerchantAgentPage() {
  const { user } = useAuth()
  const qc = useQueryClient()
  const [selectedSkill, setSelectedSkill] = useState<string>("")
  const [showSkillPicker, setShowSkillPicker] = useState(false)

  const agentQuery = useQuery<{ agent: MerchantAgentInfo | null; message?: string }>({
    queryKey: ["merchant-agent", user?.id],
    queryFn: async () => {
      try {
        const res = await api.get<{ agent: MerchantAgentInfo | null; message?: string }>("/merchant/agent")
        return res.data
      } catch (err: unknown) {
        const status = (err as { response?: { status?: number } })?.response?.status
        if (status === 404 || status === 403) return { agent: null }
        throw err
      }
    },
  })

  const skillsQuery = useQuery<Skill[]>({
    queryKey: ["skills"],
    queryFn: async () => {
      const res = await api.get<Skill[]>("/skills")
      return res.data
    },
    enabled: showSkillPicker,
  })

  const createAgent = useMutation({
    mutationFn: async () => {
      if (!selectedSkill) throw new Error("Select a skill.")
      const res = await api.post<MerchantAgentInfo>("/merchant/agent/create", { skill_id: selectedSkill })
      return res.data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["merchant-agent"] })
      setShowSkillPicker(false)
      setSelectedSkill("")
    },
  })

  const updateSkill = useMutation({
    mutationFn: async () => {
      if (!selectedSkill) throw new Error("Select a skill.")
      const res = await api.patch<MerchantAgentInfo>("/merchant/agent", { skill_id: selectedSkill })
      return res.data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["merchant-agent"] })
      setShowSkillPicker(false)
      setSelectedSkill("")
    },
  })

  const agent = agentQuery.data?.agent
  const skills = skillsQuery.data ?? []
  const isPending = createAgent.isPending || updateSkill.isPending
  const mutationError = createAgent.error || updateSkill.error

  function handleSave() {
    if (agent) updateSkill.mutate()
    else createAgent.mutate()
  }

  return (
    <div className="space-y-8 max-w-xl">
      <div>
        <h1 className="text-xl font-semibold text-[#131212]">My Agent</h1>
        <p className="text-sm text-[#6C7F9A] mt-1">
          Your agent negotiates on your behalf when buyers search for your products. Pick a skill that matches your sales style.
        </p>
      </div>

      {agentQuery.isLoading && (
        <div className="border border-[#D8E1EA] rounded-md p-6 space-y-3 animate-pulse">
          <div className="h-3 w-1/3 bg-[#E4EAF1] rounded" />
          <div className="h-3 w-2/3 bg-[#E4EAF1] rounded" />
          <div className="h-3 w-1/2 bg-[#E4EAF1] rounded" />
        </div>
      )}

      {!agentQuery.isLoading && !agent && (
        <div className="border border-[#D8E1EA] rounded-md p-6 space-y-4">
          <p className="text-sm text-[#6C7F9A]">No agent yet. Create one to start receiving buyer negotiations.</p>
          {!showSkillPicker ? (
            <Button
              onClick={() => { setShowSkillPicker(true); }}
              className="bg-[#237B4B] text-white hover:bg-[#1A5F3D] font-medium text-sm"
            >
              Create Agent
            </Button>
          ) : null}
        </div>
      )}

      {agent && !showSkillPicker && (
        <div className="border border-[#D8E1EA] rounded-md divide-y divide-[#E4EAF1]">
          <div className="px-5 py-4">
            <p className="text-[10px] text-[#9DACBE] uppercase tracking-wider mb-3">Agent Info</p>
            <dl className="space-y-3">
              <div className="flex justify-between items-baseline gap-4">
                <dt className="text-xs text-[#6C7F9A]">Agent ID</dt>
                <dd className="font-mono text-xs text-[#131212] break-all text-right">{agent.agent_id}</dd>
              </div>
              <div className="flex justify-between items-baseline gap-4">
                <dt className="text-xs text-[#6C7F9A]">Current skill</dt>
                <dd className="text-xs text-[#131212] font-medium">
                  {agent.skill_id ? (SKILL_LABELS[agent.skill_id.replace("skill_", "")] ?? agent.skill_id) : "—"}
                </dd>
              </div>
              <div className="flex justify-between items-baseline gap-4">
                <dt className="text-xs text-[#6C7F9A]">Created</dt>
                <dd className="text-xs text-[#131212]">
                  {new Date(agent.created_at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })}
                </dd>
              </div>
            </dl>
          </div>
          <div className="px-5 py-4 flex items-center justify-between">
            <p className="text-xs text-[#6C7F9A] max-w-xs">
              Your agent competes against other merchants automatically. Change skill to adjust negotiation style.
            </p>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => { setShowSkillPicker(true); setSelectedSkill(agent.skill_id ?? "") }}
              className="border border-[#D8E1EA] text-[#6C7F9A] hover:bg-[#F5F8FA] text-xs shrink-0"
            >
              Change skill
            </Button>
          </div>
        </div>
      )}

      {/* Skill picker — shown for both create and update */}
      {showSkillPicker && (
        <div className="border border-[#D8E1EA] rounded-md p-5 space-y-4">
          <p className="text-sm font-medium text-[#131212]">{agent ? "Change negotiation skill" : "Choose a negotiation skill"}</p>

          {skillsQuery.isLoading ? (
            <div className="space-y-2 animate-pulse">
              {[1,2,3].map(i => <div key={i} className="h-14 bg-[#E4EAF1] rounded-md" />)}
            </div>
          ) : (
            <div className="space-y-2">
              {skills.map((skill) => (
                <label
                  key={skill.id}
                  className={`flex items-start gap-3 border rounded-md px-3 py-2.5 cursor-pointer transition-colors ${
                    selectedSkill === skill.id
                      ? "border-[#237B4B] bg-[#E6F4EA]"
                      : "border-[#D8E1EA] hover:bg-[#F5F8FA]"
                  }`}
                >
                  <input
                    type="radio"
                    name="merchant_skill"
                    value={skill.id}
                    checked={selectedSkill === skill.id}
                    onChange={() => setSelectedSkill(skill.id)}
                    className="mt-0.5 accent-[#237B4B]"
                  />
                  <div>
                    <p className="text-sm text-[#131212]">{SKILL_LABELS[skill.name] ?? skill.name}</p>
                    <p className="text-xs text-[#6C7F9A]">{skill.description}</p>
                  </div>
                </label>
              ))}
            </div>
          )}

          {mutationError && (
            <p className="text-sm text-[#AA2C2C]">
              {(mutationError as { message?: string })?.message ?? "Failed. Try again."}
            </p>
          )}

          <div className="flex gap-3 justify-end">
            <Button
              variant="ghost"
              onClick={() => { setShowSkillPicker(false); setSelectedSkill("") }}
              className="border border-[#D8E1EA] text-[#6C7F9A] hover:bg-[#F5F8FA]"
            >
              Cancel
            </Button>
            <Button
              disabled={!selectedSkill || isPending}
              onClick={handleSave}
              className="bg-[#237B4B] text-white hover:bg-[#1A5F3D] font-medium"
            >
              {isPending ? "Saving…" : agent ? "Save" : "Create Agent"}
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
