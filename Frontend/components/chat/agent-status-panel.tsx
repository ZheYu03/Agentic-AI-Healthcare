"use client"

import { Check, Loader2, ArrowRight, Sparkles } from "lucide-react"
import { cn } from "@/lib/utils"

interface AgentStatus {
    agent: string
    status: 'pending' | 'running' | 'complete'
    message?: string
    summary?: string
    keyFindings?: Record<string, any>
}

interface AgentStatusPanelProps {
    statuses: AgentStatus[]
}

const AGENT_CONFIG: Record<string, { icon: string; label: string; color: string }> = {
    'PlannerAgent': {
        icon: '📋',
        label: 'Planning',
        color: 'text-blue-600 dark:text-blue-400'
    },
    'SymptomTriageAgent': {
        icon: '🩺',
        label: 'Symptom Analysis',
        color: 'text-red-600 dark:text-red-400'
    },
    'MedicalQnAAgent': {
        icon: '📚',
        label: 'Medical Research',
        color: 'text-purple-600 dark:text-purple-400'
    },
    'ClinicRecommendationAgent': {
        icon: '🏥',
        label: 'Finding Clinics',
        color: 'text-green-600 dark:text-green-400'
    },
    'InsuranceAdvisorAgent': {
        icon: '💼',
        label: 'Insurance Check',
        color: 'text-yellow-600 dark:text-yellow-400'
    }
}

function getAgentConfig(agentName: string) {
    return AGENT_CONFIG[agentName] || {
        icon: '⚙️',
        label: agentName,
        color: 'text-gray-600 dark:text-gray-400'
    }
}

export function AgentStatusPanel({ statuses }: AgentStatusPanelProps) {
    if (statuses.length === 0) {
        return null
    }

    return (
        <div className="border rounded-2xl p-4 space-y-3 bg-white/50 dark:bg-gray-800/50 backdrop-blur-sm">
            <div className="flex items-center gap-2 font-semibold text-sm">
                <Sparkles className="h-4 w-4 text-blue-500" />
                <span>AI Healthcare Agent</span>
            </div>

            <div className="space-y-2">
                {statuses.map((status, idx) => (
                    <AgentStatusItem key={idx} status={status} />
                ))}
            </div>
        </div>
    )
}

function AgentStatusItem({ status }: { status: AgentStatus }) {
    const config = getAgentConfig(status.agent)

    return (
        <div className="space-y-1 animate-in fade-in slide-in-from-left-2 duration-300">
            <div className="flex items-center gap-2">
                {status.status === 'complete' && (
                    <Check className="h-4 w-4 text-green-500 flex-shrink-0" />
                )}
                {status.status === 'running' && (
                    <Loader2 className="h-4 w-4 animate-spin text-blue-500 flex-shrink-0" />
                )}
                {status.status === 'pending' && (
                    <ArrowRight className="h-4 w-4 text-gray-400 flex-shrink-0" />
                )}

                <span className={cn("text-sm font-medium", config.color)}>
                    {config.icon} {config.label}
                </span>

                {status.status === 'pending' && (
                    <span className="text-xs text-gray-500">(Next)</span>
                )}
            </div>

            {/* Show message for running */}
            {status.status === 'running' && status.message && (
                <div className="ml-6 text-sm text-gray-600 dark:text-gray-400 animate-in fade-in duration-200">
                    → {status.message}
                </div>
            )}

            {/* Show summary for completed */}
            {status.status === 'complete' && status.summary && (
                <div className="ml-6 text-sm text-gray-600 dark:text-gray-400">
                    → {status.summary}
                </div>
            )}

            {/* Show key findings */}
            {status.keyFindings && Object.keys(status.keyFindings).length > 0 && (
                <div className="ml-6 text-xs space-y-0.5">
                    {Object.entries(status.keyFindings).map(([key, value]) => (
                        <div key={key} className="text-gray-500 dark:text-gray-500">
                            • {key}: <span className="font-medium">{String(value)}</span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}
