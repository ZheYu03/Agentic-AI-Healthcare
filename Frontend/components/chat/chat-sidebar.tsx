"use client"

import { Menu, PenSquare, Clock, MessageSquare, Search } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { useState, useMemo } from "react"
import type { UIMessage } from "ai"

// Chat session type (must match medical-chatbot.tsx)
interface ChatSession {
  id: string
  title: string
  messages: UIMessage[]
  createdAt: number
}

interface ChatSidebarProps {
  isOpen: boolean
  onClose: () => void
  theme: "light" | "dark"
  onThemeChange: (theme: "light" | "dark") => void
  sessions: ChatSession[]
  currentSessionId: string
  onSelectSession: (sessionId: string) => void
  onNewChat: () => void
}

// Helper to group sessions by time
function groupSessionsByTime(sessions: ChatSession[]) {
  const now = Date.now()
  const oneDayMs = 24 * 60 * 60 * 1000
  const oneWeekMs = 7 * oneDayMs

  const today: ChatSession[] = []
  const yesterday: ChatSession[] = []
  const thisWeek: ChatSession[] = []
  const older: ChatSession[] = []

  for (const session of sessions) {
    const age = now - session.createdAt
    if (age < oneDayMs) {
      today.push(session)
    } else if (age < 2 * oneDayMs) {
      yesterday.push(session)
    } else if (age < oneWeekMs) {
      thisWeek.push(session)
    } else {
      older.push(session)
    }
  }

  return { today, yesterday, thisWeek, older }
}

export function ChatSidebar({
  isOpen,
  onClose,
  theme,
  onThemeChange,
  sessions,
  currentSessionId,
  onSelectSession,
  onNewChat,
}: ChatSidebarProps) {
  const [searchQuery, setSearchQuery] = useState("")

  // Filter sessions by search query
  const filteredSessions = useMemo(() => {
    if (!searchQuery.trim()) return sessions
    const query = searchQuery.toLowerCase()
    return sessions.filter((s) => s.title.toLowerCase().includes(query))
  }, [sessions, searchQuery])

  // Group filtered sessions by time
  const grouped = useMemo(() => groupSessionsByTime(filteredSessions), [filteredSessions])

  const renderSessionList = (sessionList: ChatSession[], label: string) => {
    if (sessionList.length === 0) return null
    return (
      <div className="mb-4">
        <h3
          className={cn(
            "px-1 py-2 text-xs font-medium uppercase tracking-wider flex items-center gap-2",
            theme === "dark" ? "text-[#9aa0a6]" : "text-gray-500"
          )}
        >
          <Clock className="h-3 w-3" />
          {label}
        </h3>
        <nav className="space-y-1">
          {sessionList.map((session) => (
            <button
              key={session.id}
              onClick={() => onSelectSession(session.id)}
              className={cn(
                "w-full flex items-center gap-3 px-3 py-2 text-sm rounded-lg transition-colors text-left",
                session.id === currentSessionId
                  ? theme === "dark"
                    ? "bg-[#3c4043] text-white"
                    : "bg-gray-200 text-gray-900"
                  : theme === "dark"
                    ? "text-[#e3e3e3] hover:bg-[#3c4043]"
                    : "text-gray-800 hover:bg-gray-100"
              )}
            >
              <MessageSquare
                className={cn("h-4 w-4 flex-shrink-0", theme === "dark" ? "text-[#9aa0a6]" : "text-gray-400")}
              />
              <span className="truncate">{session.title}</span>
            </button>
          ))}
        </nav>
      </div>
    )
  }

  return (
    <>
      {/* Backdrop */}
      {isOpen && <div className="fixed inset-0 bg-black/50 z-40 lg:hidden" onClick={onClose} />}

      {/* Sidebar */}
      <aside
        className={cn(
          "relative z-50 h-full border-r overflow-hidden fixed inset-y-0",
          "transition-all duration-300 ease-[cubic-bezier(0.4,0,0.2,1)]",
          isOpen ? "w-80 opacity-100" : "w-0 opacity-0",
          // Desktop inline collapse/expand
          "lg:static lg:flex-shrink-0",
          theme === "dark" ? "bg-[#1e1f20] border-[#3c4043]" : "bg-gray-50 border-gray-200"
        )}
      >
        <div
          className={cn(
            "h-full flex flex-col min-w-[20rem] w-80",
            "transition-opacity duration-300 ease-[cubic-bezier(0.4,0,0.2,1)]",
            isOpen ? "opacity-100" : "opacity-0"
          )}
        >
          {/* Sidebar Header (stable width, no shrink) */}
          <div className="flex-shrink-0 w-full min-w-[20rem] px-4 pt-4 pb-2">
            <div className="flex items-center justify-between">
              <Button
                variant="ghost"
                size="icon"
                onClick={onClose}
                className={cn(
                  "rounded-lg",
                  theme === "dark" ? "text-[#e3e3e3] hover:bg-[#3c4043]" : "text-gray-800 hover:bg-gray-200"
                )}
                aria-label="Collapse sidebar"
              >
                <Menu className="h-5 w-5" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className={cn(
                  "rounded-lg",
                  theme === "dark" ? "text-[#e3e3e3] hover:bg-[#3c4043]" : "text-gray-800 hover:bg-gray-200"
                )}
                aria-label="Search"
              >
                <Search className="h-5 w-5" />
              </Button>
            </div>
          </div>

          {/* New chat (stable width container) */}
          <div className="flex-shrink-0 w-full min-w-[20rem] px-4 pb-4">
            <Button
              variant="ghost"
              onClick={onNewChat}
              className={cn(
                "flex items-center gap-2 rounded-lg px-3 py-2 w-fit whitespace-nowrap",
                theme === "dark" ? "text-[#e3e3e3] hover:bg-[#3c4043]" : "text-gray-800 hover:bg-gray-200"
              )}
            >
              <PenSquare className="h-4 w-4" />
              <span className="font-medium whitespace-nowrap">New chat</span>
            </Button>
          </div>

          {/* Search Bar */}
          <div className="px-4 mb-4">
            <div
              className={cn(
                "flex items-center gap-2 px-3 py-2 rounded-lg border shadow-sm",
                theme === "dark" ? "bg-[#262727] border-[#3c4043]" : "bg-white border-gray-200"
              )}
            >
              <Search className={cn("h-4 w-4", theme === "dark" ? "text-[#9aa0a6]" : "text-gray-400")} />
              <input
                type="text"
                placeholder="Search chats..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className={cn(
                  "w-full bg-transparent border-0 outline-none text-sm placeholder:text-gray-400",
                  theme === "dark" ? "text-[#e3e3e3]" : "text-gray-700"
                )}
              />
            </div>
          </div>

          {/* Chat Sessions List */}
          <div className="flex-1 overflow-y-auto px-4">
            {sessions.length === 0 ? (
              <p className={cn("text-sm px-3 py-4", theme === "dark" ? "text-[#9aa0a6]" : "text-gray-500")}>
                No chats yet. Start a new conversation!
              </p>
            ) : filteredSessions.length === 0 ? (
              <p className={cn("text-sm px-3 py-4", theme === "dark" ? "text-[#9aa0a6]" : "text-gray-500")}>
                No chats match your search.
              </p>
            ) : (
              // Show all chats under "Your Chats" - sorted by most recent first
              renderSessionList(
                [...filteredSessions].sort((a, b) => b.createdAt - a.createdAt),
                "Your Chats"
              )
            )}
          </div>

        </div>
      </aside>
    </>
  )
}
