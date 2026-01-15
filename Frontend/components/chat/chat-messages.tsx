"use client"

import type { UIMessage } from "ai"
import { cn } from "@/lib/utils"
import { User, Sparkles } from "lucide-react"

interface AgentStatus {
  agent: string
  status: 'pending' | 'running' | 'complete'
  message?: string
  summary?: string
  keyFindings?: Record<string, any>
}

interface ChatMessagesProps {
  messages: UIMessage[]
  isLoading: boolean
  theme?: "light" | "dark"
  agentStatuses?: AgentStatus[]
}

export function ChatMessages({
  messages,
  isLoading,
  theme = "dark",
  agentStatuses = []
}: ChatMessagesProps) {
  return (
    <div className="space-y-6">
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} theme={theme} />
      ))}
      {isLoading && messages[messages.length - 1]?.role === "user" && (
        <div className="flex gap-3">
          <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 via-red-500 to-yellow-500 flex items-center justify-center">
            <Sparkles className="h-4 w-4 text-white" />
          </div>
          <div className="flex-1 max-w-[88%]">
            <div className={cn(
              "rounded-2xl px-3 py-3",
              theme === "dark" ? "bg-[#1e1f20] text-[#e3e3e3]" : "bg-gray-100 text-gray-900"
            )}>
              {agentStatuses.length === 0 ? (
                <div className="flex items-center gap-2">
                  <span className="text-sm">Thinking</span>
                  <div className="flex gap-1">
                    <span className="animate-bounce" style={{ animationDelay: "0ms" }}>.</span>
                    <span className="animate-bounce" style={{ animationDelay: "150ms" }}>.</span>
                    <span className="animate-bounce" style={{ animationDelay: "300ms" }}>.</span>
                  </div>
                </div>
              ) : (
                <ThinkingStatusPanel statuses={agentStatuses} />
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function MessageBubble({ message, theme }: { message: UIMessage; theme: "light" | "dark" }) {
  const isUser = message.role === "user"

  return (
    <div className={cn("flex gap-3", isUser && "flex-row-reverse")}>
      <div
        className={cn(
          "flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center",
          isUser
            ? "bg-gradient-to-br from-teal-500 to-blue-600"
            : "bg-gradient-to-br from-blue-500 via-red-500 to-yellow-500",
        )}
      >
        {isUser ? <User className="h-4 w-4 text-white" /> : <Sparkles className="h-4 w-4 text-white" />}
      </div>
      <div className={cn("flex-1 max-w-[88%]", isUser && "flex justify-end")}>
        <div
          className={cn(
            "rounded-2xl px-4 py-3",
            isUser
              ? theme === "dark"
                ? "bg-[#3c4043] text-[#e3e3e3]"
                : "bg-gray-200 text-gray-900"
              : theme === "dark"
                ? "bg-[#1e1f20] text-[#e3e3e3]"
                : "bg-gray-100 text-gray-900",
          )}
        >
          {message.parts.map((part, index) => {
            if (part.type === "text") {
              return (
                <div key={index} className={cn("prose max-w-none", theme === "dark" ? "prose-invert" : "")}>
                  <FormattedText text={part.text} />
                </div>
              )
            }
            return null
          })}
        </div>
      </div>
    </div>
  )
}

// Helper to detect and linkify URLs in text
function LinkifyText({ text }: { text: string }) {
  const urlRegex = /(https?:\/\/[^\s]+)/g
  const parts = text.split(urlRegex)

  return (
    <>
      {parts.map((part, i) => {
        if (urlRegex.test(part)) {
          // Reset regex lastIndex
          urlRegex.lastIndex = 0
          return (
            <a
              key={i}
              href={part}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:text-blue-800 underline"
            >
              {part}
            </a>
          )
        }
        return <span key={i}>{part}</span>
      })}
    </>
  )
}

function FormattedText({ text }: { text: string }) {
  // Simple markdown-like formatting
  const lines = text.split("\n")

  return (
    <div className="space-y-2">
      {lines.map((line, index) => {
        // Check if line is a section header (ends with colon and is short)
        // Increased limit to 100 to support longer insurance plan names
        if (line.trim().endsWith(':') && line.trim().length < 100 && line.trim().length > 0) {
          return (
            <p key={index} className="font-bold mt-3 mb-1">
              {line}
            </p>
          )
        }
        if (line.startsWith("**") && line.endsWith("**")) {
          return (
            <p key={index} className="font-semibold">
              {line.slice(2, -2)}
            </p>
          )
        }
        if (line.startsWith("- ") || line.startsWith("• ")) {
          return (
            <li key={index} className="ml-4 list-disc">
              <LinkifyText text={line.slice(2)} />
            </li>
          )
        }
        if (line.trim() === "") {
          return <br key={index} />
        }
        // Check if line contains a URL
        if (line.includes("http://") || line.includes("https://")) {
          return <p key={index}><LinkifyText text={line} /></p>
        }
        return <p key={index}>{line}</p>
      })}
    </div>
  )
}

// Thinking Status Panel - shows agent execution progress inside the thinking bubble
function ThinkingStatusPanel({ statuses }: { statuses: AgentStatus[] }) {
  const AGENT_CONFIG: Record<string, { icon: string; label: string; color: string }> = {
    'PlannerAgent': { icon: '📋', label: 'Planning', color: 'text-blue-400' },
    'SymptomTriageAgent': { icon: '🩺', label: 'Symptom Analysis', color: 'text-red-400' },
    'MedicalQnAAgent': { icon: '📚', label: 'Medical Research', color: 'text-purple-400' },
    'ClinicRecommendationAgent': { icon: '🏥', label: 'Finding Clinics', color: 'text-green-400' },
    'InsuranceAdvisorAgent': { icon: '💼', label: 'Insurance Check', color: 'text-yellow-400' }
  }

  const getAgentConfig = (agentName: string) => {
    return AGENT_CONFIG[agentName] || { icon: '⚙️', label: agentName, color: 'text-gray-400' }
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 text-sm mb-3">
        <span>Thinking</span>
        <div className="flex gap-1">
          <span className="animate-bounce" style={{ animationDelay: "0ms" }}>.</span>
          <span className="animate-bounce" style={{ animationDelay: "150ms" }}>.</span>
          <span className="animate-bounce" style={{ animationDelay: "300ms" }}>.</span>
        </div>
      </div>

      {statuses.map((status, idx) => {
        const config = getAgentConfig(status.agent)

        return (
          <div key={idx} className="space-y-1 animate-in fade-in slide-in-from-left-2 duration-300">
            <div className="flex items-center gap-2">
              {status.status === 'complete' && (
                <span className="text-green-400 text-sm">✓</span>
              )}
              {status.status === 'running' && (
                <div className="w-3 h-3 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
              )}
              {status.status === 'pending' && (
                <span className="text-gray-500 text-sm">○</span>
              )}

              <span className={cn("text-xs font-medium", config.color)}>
                {config.icon} {config.label}
              </span>

              {status.status === 'pending' && (
                <span className="text-xs text-gray-600">(Next)</span>
              )}
            </div>

            {/* Show message for running */}
            {status.status === 'running' && status.message && (
              <div className="ml-5 text-xs text-gray-400 animate-in fade-in duration-200">
                → {status.message}
              </div>
            )}

            {/* Show summary for completed */}
            {status.status === 'complete' && status.summary && (
              <div className="ml-5 text-xs text-gray-400">
                → {status.summary}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
