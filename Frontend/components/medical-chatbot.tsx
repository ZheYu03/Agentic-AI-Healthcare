"use client"

import type { UIMessage } from "ai"
import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { Menu, PenSquare, Search, Settings } from "lucide-react"
import { ChatHeader } from "./chat/chat-header"
import { ChatSidebar } from "./chat/chat-sidebar"
import { ChatMessages } from "./chat/chat-messages"
import { ChatInput } from "./chat/chat-input"
import { WelcomeScreen } from "./chat/welcome-screen"
import { LoginModal } from "./auth/login-modal"
import { PatientOnboardingForm } from "./onboarding/patient-form"
import { useAuth } from "@/lib/auth-context"
import { cn } from "@/lib/utils"
import type { PatientEncounter, EncounterMessage } from "@/lib/supabase"

// Chat session type for local state management
interface ChatSession {
  id: string
  title: string
  messages: UIMessage[]
  createdAt: number
  isFromDatabase?: boolean // Track if session was loaded from database
}

function createMessage(role: UIMessage["role"], text: string): UIMessage {
  const id =
    typeof crypto !== "undefined" && crypto.randomUUID
      ? crypto.randomUUID()
      : Math.random().toString(36).slice(2)

  return {
    id: `${role}-${id}`,
    role,
    parts: [{ type: "text", text }],
  }
}

// Helper to generate a unique ID
function generateId(): string {
  return typeof crypto !== "undefined" && crypto.randomUUID
    ? crypto.randomUUID()
    : Math.random().toString(36).slice(2)
}

// Create a new empty chat session (local only, for UI)
function createSession(id?: string): ChatSession {
  return {
    id: id || generateId(),
    title: "New Chat",
    messages: [],
    createdAt: Date.now(),
  }
}

export function MedicalChatbot() {
  // Sidebar is always open by default
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [inputValue, setInputValue] = useState("")
  const [theme, setTheme] = useState<"light" | "dark">("light")
  const [isLoading, setIsLoading] = useState(false)
  const abortRef = useRef<AbortController | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Auth state
  const { user, isLoading: authLoading, hasCompletedOnboarding, patientProfile, fetchUserEncounters, fetchEncounterMessages, createEncounter, userLocation, requestUserLocation } = useAuth()
  const [showLoginModal, setShowLoginModal] = useState(false)
  const [showOnboarding, setShowOnboarding] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [showHelp, setShowHelp] = useState(false)

  // Chat sessions state (local storage)
  const [sessions, setSessions] = useState<ChatSession[]>(() => [createSession()])
  const [currentSessionId, setCurrentSessionId] = useState<string>(() => sessions[0]?.id || generateId())
  const [isLoadingHistory, setIsLoadingHistory] = useState(false)
  const hasLoadedHistoryRef = useRef(false)

  // Agent status for SSE streaming
  interface AgentStatus {
    agent: string
    status: 'pending' | 'running' | 'complete'
    message?: string
    summary?: string
    keyFindings?: Record<string, any>
  }
  const [agentStatuses, setAgentStatuses] = useState<AgentStatus[]>([])

  // Get current session
  const currentSession = useMemo(
    () => sessions.find((s) => s.id === currentSessionId) || sessions[0],
    [sessions, currentSessionId]
  )
  const messages = currentSession?.messages || []

  // Sessions to show in sidebar - only those with messages
  const sidebarSessions = useMemo(
    () => sessions.filter((s) => s.messages.length > 0),
    [sessions]
  )

  // Session ID for LangSmith tracing (stable per session)
  const sessionId = useMemo(() => `session-${currentSessionId}`, [currentSessionId])

  // Check if user needs onboarding after login
  useEffect(() => {
    if (user && !authLoading && !hasCompletedOnboarding) {
      setShowOnboarding(true)
    }
  }, [user, authLoading, hasCompletedOnboarding])

  // Reset history loaded flag when user changes (logout/login)
  useEffect(() => {
    if (!user || !patientProfile) {
      hasLoadedHistoryRef.current = false
    }
  }, [user, patientProfile])

  // Convert database messages to UIMessage format
  const convertDbMessagesToUIMessages = useCallback((dbMessages: EncounterMessage[]): UIMessage[] => {
    return dbMessages.map((msg) => {
      // Try to parse content as JSON (in case it's stored as stringified parts array)
      let text = msg.content
      try {
        const parsed = JSON.parse(msg.content)
        // If it's an array of parts like [{"type": "text", "text": "..."}], extract the text
        if (Array.isArray(parsed) && parsed.length > 0 && parsed[0].type === 'text') {
          text = parsed[0].text
        }
      } catch {
        // If parsing fails, use content as-is (it's already plain text)
        text = msg.content
      }

      return {
        id: msg.id,
        role: msg.role === 'user' ? 'user' as const : 'assistant' as const,
        parts: [{ type: 'text' as const, text }],
      }
    })
  }, [])

  // Load chat history from database on mount
  useEffect(() => {
    const loadChatHistory = async () => {
      // Only load once when patient profile is available
      if (!patientProfile || hasLoadedHistoryRef.current || isLoadingHistory) {
        return
      }

      hasLoadedHistoryRef.current = true
      setIsLoadingHistory(true)

      try {
        // Fetch all encounters for this patient
        const encounters = await fetchUserEncounters()

        if (encounters.length === 0) {
          // No existing encounters, keep the default new session
          setIsLoadingHistory(false)
          return
        }

        // Fetch messages for each encounter and create sessions
        const sessionsWithMessages: ChatSession[] = await Promise.all(
          encounters.map(async (encounter: PatientEncounter) => {
            const messages = await fetchEncounterMessages(encounter.id)
            const uiMessages = convertDbMessagesToUIMessages(messages)

            // Generate title: prefer first user message, then chief_complaint, then date
            let title = 'Chat Session'
            const firstUserMsg = uiMessages.find((m) => m.role === 'user')
            if (firstUserMsg) {
              const textPart = firstUserMsg.parts.find((p) => p.type === 'text') as { text: string } | undefined
              title = textPart?.text.slice(0, 30) || title
            } else if (encounter.chief_complaint) {
              title = encounter.chief_complaint.slice(0, 30)
            } else {
              // Use encounter date as fallback title
              title = new Date(encounter.created_at).toLocaleDateString()
            }

            return {
              id: encounter.id,
              title,
              messages: uiMessages,
              createdAt: new Date(encounter.created_at).getTime(),
              isFromDatabase: true,
            }
          })
        )

        // Only show sessions that have messages in the sidebar
        const sessionsWithActualMessages = sessionsWithMessages.filter((s) => s.messages.length > 0)

        if (sessionsWithActualMessages.length > 0) {
          // Create a working session for new chats (won't show in sidebar until has messages)
          const workingSession = createSession()
          // Replace all sessions - working session first, then history
          setSessions([workingSession, ...sessionsWithActualMessages])
          setCurrentSessionId(workingSession.id)
        }
      } catch (error) {
        console.error('Error loading chat history:', error)
      } finally {
        setIsLoadingHistory(false)
      }
    }

    loadChatHistory()
  }, [patientProfile, fetchUserEncounters, fetchEncounterMessages, convertDbMessagesToUIMessages, isLoadingHistory])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Helper to update messages in current session
  const updateCurrentSessionMessages = useCallback(
    (updater: (prev: UIMessage[]) => UIMessage[]) => {
      setSessions((prevSessions) =>
        prevSessions.map((session) => {
          if (session.id !== currentSessionId) return session
          const newMessages = updater(session.messages)
          // Update title from first user message if still "New Chat"
          const firstUserMsg = newMessages.find((m) => m.role === "user")
          const newTitle =
            session.title === "New Chat" && firstUserMsg
              ? (firstUserMsg.parts.find((p) => p.type === "text") as { text: string } | undefined)?.text.slice(0, 30) ||
              "New Chat"
              : session.title
          return { ...session, messages: newMessages, title: newTitle }
        })
      )
    },
    [currentSessionId]
  )

  const handleSendMessage = async (text: string) => {
    const trimmed = text.trim()
    if (!trimmed || isLoading) return

    // Check if user is authenticated
    if (!user) {
      setShowLoginModal(true)
      return
    }

    // Check if user has completed onboarding
    if (!hasCompletedOnboarding) {
      setShowOnboarding(true)
      return
    }

    let activeSessionId = currentSessionId
    let activeSession = sessions.find((s) => s.id === currentSessionId)
    let oldSessionId = currentSessionId // Track old ID for session update

    // If current session is not from database and user has patient profile,
    // create an encounter for this session
    if (patientProfile && activeSession && !activeSession.isFromDatabase) {
      const encounter = await createEncounter(trimmed.slice(0, 100))
      if (encounter) {
        // Update the session with the database encounter ID
        setSessions((prev) =>
          prev.map((s) =>
            s.id === oldSessionId
              ? { ...s, id: encounter.id, isFromDatabase: true }
              : s
          )
        )
        activeSessionId = encounter.id
        setCurrentSessionId(encounter.id)
      }
    }

    const userMessage = createMessage("user", trimmed)

    // Use functional update with activeSessionId to handle the ID change
    setSessions((prevSessions) =>
      prevSessions.map((session) => {
        // Match either the old session ID or the new encounter ID
        if (session.id !== activeSessionId && session.id !== oldSessionId) return session
        const newMessages = [...session.messages, userMessage]
        const firstUserMsg = newMessages.find((m) => m.role === "user")
        const newTitle =
          session.title === "New Chat" && firstUserMsg
            ? (firstUserMsg.parts.find((p) => p.type === "text") as { text: string } | undefined)?.text.slice(0, 30) ||
            "New Chat"
            : session.title
        return { ...session, messages: newMessages, title: newTitle }
      })
    )
    setInputValue("")
    setIsLoading(true)

    const controller = new AbortController()
    abortRef.current = controller

    // Note: History handling is now done by LangGraph SQLite checkpointer on backend
    // We only need to send the new message and encounter_id (used as thread_id)

    try {
      // Request location if not already available (for clinic recommendations)
      const location = userLocation || await requestUserLocation()

      // Use SSE streaming endpoint for real-time agent status updates
      const response = await fetch("/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: trimmed,
          sessionId: `session-${activeSessionId}`,
          encounterId: activeSessionId,
          patientId: patientProfile?.id || null,
          userCoordinates: location ? { lat: location.lat, lng: location.lng } : null,
        }),
        signal: controller.signal,
      })

      if (!response.ok) {
        const errorBody = await response.json().catch(() => ({}))
        throw new Error(errorBody.error || errorBody.detail || "Request failed")
      }

      // Consume SSE stream
      const reader = response.body?.getReader()
      const decoder = new TextDecoder()

      if (!reader) {
        throw new Error("No response body reader")
      }

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value)
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const event = JSON.parse(line.slice(6))
              handleSSEEvent(event, activeSessionId)
            } catch (e) {
              console.error('Failed to parse SSE event:', e)
            }
          }
        }
      }
    } catch (error) {
      if (controller.signal.aborted) return
      console.error("[Chat] Failed to reach backend", error)
      // Add error message to session
      setSessions((prevSessions) =>
        prevSessions.map((session) => {
          if (session.id !== activeSessionId) return session
          return {
            ...session,
            messages: [...session.messages, createMessage(
              "assistant",
              "Sorry, I couldn't reach the medical assistant right now. Please try again in a moment.",
            )]
          }
        })
      )
    } finally {
      setIsLoading(false)
      setAgentStatuses([])  // Clear agent statuses when done
      abortRef.current = null
    }
  }

  // Handle SSE events
  const handleSSEEvent = (event: any, sessionId: string) => {
    switch (event.type) {
      case 'execution_plan':
        // Initialize agent statuses
        setAgentStatuses(
          event.agents.map((agent: string) => ({
            agent,
            status: 'pending' as const,
            message: '',
            summary: ''
          }))
        )
        break

      case 'status':
        // General status message (can be displayed if needed)
        console.log('[SSE Status]', event.message)
        break

      case 'agent_start':
        // Mark agent as running
        setAgentStatuses(prev =>
          prev.map(s =>
            s.agent === event.agent
              ? { ...s, status: 'running' as const, message: event.message }
              : s
          )
        )
        break

      case 'agent_complete':
        // Mark agent as complete and move next to running
        setAgentStatuses(prev =>
          prev.map((s, idx) => {
            if (s.agent === event.agent) {
              return {
                ...s,
                status: 'complete' as const,
                summary: event.summary,
                keyFindings: event.key_findings
              }
            }
            // Move next pending agent to running
            if (prev[idx - 1]?.agent === event.agent && s.status === 'pending') {
              return { ...s, status: 'running' as const }
            }
            return s
          })
        )
        break

      case 'response_ready':
        // Add final messages to chat
        const replies = event.messages || []
        setSessions(prevSessions =>
          prevSessions.map(session => {
            if (session.id !== sessionId) return session
            const newMessages = replies.map((msg: string) => createMessage('assistant', String(msg)))
            return { ...session, messages: [...session.messages, ...newMessages] }
          })
        )
        break

      case 'done':
        // Stream complete
        setIsLoading(false)
        break

      case 'error':
        console.error('[SSE Error]', event.message)
        setSessions(prevSessions =>
          prevSessions.map(session => {
            if (session.id !== sessionId) return session
            return {
              ...session,
              messages: [
                ...session.messages,
                createMessage('assistant', `Error: ${event.message}`)
              ]
            }
          })
        )
        setIsLoading(false)
        break
    }
  }

  const handleStop = () => {
    if (abortRef.current) {
      abortRef.current.abort()
      abortRef.current = null
    }
    setIsLoading(false)
  }

  const handleSuggestionClick = (suggestion: string) => {
    // Check auth before sending
    if (!user) {
      setShowLoginModal(true)
      return
    }
    if (!hasCompletedOnboarding) {
      setShowOnboarding(true)
      return
    }
    handleSendMessage(suggestion)
  }

  // Start a new chat session
  const handleNewChat = useCallback(() => {
    // Check if user is authenticated
    if (!user) {
      setShowLoginModal(true)
      return
    }

    // Check if user has completed onboarding
    if (!hasCompletedOnboarding) {
      setShowOnboarding(true)
      return
    }

    // Create a local session - encounter will be created in database
    // when user sends their first message (in handleSendMessage)
    const newSession = createSession()
    setSessions((prev) => [newSession, ...prev])
    setCurrentSessionId(newSession.id)
  }, [user, hasCompletedOnboarding])

  // Select an existing session
  const handleSelectSession = useCallback((sessionId: string) => {
    setCurrentSessionId(sessionId)
  }, [])

  // Handle settings click
  const handleSettingsClick = useCallback(() => {
    setShowSettings(true)
    // Navigate to settings page
    window.location.href = "/settings"
  }, [])

  // Handle help click
  const handleHelpClick = useCallback(() => {
    setShowHelp(true)
    // Navigate to help page
    window.location.href = "/help"
  }, [])

  return (
    <div
      className={cn(
        "flex h-screen overflow-hidden",
        theme === "dark" ? "dark bg-[#131314] text-white" : "bg-white text-gray-900",
      )}
    >
      {/* Sidebar - always visible on desktop */}
      <ChatSidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        theme={theme}
        onThemeChange={setTheme}
        sessions={sidebarSessions}
        currentSessionId={currentSessionId}
        onSelectSession={handleSelectSession}
        onNewChat={handleNewChat}
      />

      {/* Compact vertical rail (only on mobile when sidebar is closed) */}
      {!sidebarOpen && (
        <CompactRail
          theme={theme}
          onMenuClick={() => setSidebarOpen(true)}
          onNewChat={handleNewChat}
          onSettingsClick={handleSettingsClick}
        />
      )}

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <ChatHeader
          onMenuClick={() => setSidebarOpen(!sidebarOpen)}
          onNewChat={handleNewChat}
          sidebarOpen={sidebarOpen}
          theme={theme}
          onSettingsClick={handleSettingsClick}
          onHelpClick={handleHelpClick}
        />

        {/* Chat Area */}
        <main className="flex-1 overflow-hidden flex flex-col">
          <div className="flex-1 overflow-y-auto">
            <div className="max-w-3xl mx-auto px-4 py-6">
              {messages.length === 0 ? (
                <WelcomeScreen onSuggestionClick={handleSuggestionClick} theme={theme} />
              ) : (
                <ChatMessages
                  messages={messages}
                  isLoading={isLoading}
                  theme={theme}
                  agentStatuses={agentStatuses}
                />
              )}
              <div ref={messagesEndRef} />
            </div>
          </div>

          {/* Input Area */}
          <div className={cn(theme === "dark" ? "bg-[#131314]" : "bg-white")}>
            <div className="max-w-3xl mx-auto px-4 py-4">
              <ChatInput
                value={inputValue}
                onChange={setInputValue}
                onSend={handleSendMessage}
                onStop={handleStop}
                isLoading={isLoading}
                theme={theme}
                disabled={!user}
                placeholder={!user ? "Sign in to start chatting..." : "Ask about your health..."}
              />
              {!user && (
                <p className="text-center text-sm text-gray-500 mt-2">
                  <button
                    onClick={() => setShowLoginModal(true)}
                    className="text-teal-500 hover:text-teal-600 font-medium"
                  >
                    Sign in
                  </button>
                  {" "}to start a conversation with MedAssist
                </p>
              )}
            </div>
          </div>
        </main>
      </div>

      {/* Login Modal */}
      <LoginModal
        isOpen={showLoginModal}
        onClose={() => setShowLoginModal(false)}
        theme={theme}
      />

      {/* Onboarding Modal */}
      <PatientOnboardingForm
        isOpen={showOnboarding && !!user && !hasCompletedOnboarding}
        onClose={() => setShowOnboarding(false)}
        theme={theme}
      />
    </div>
  )
}

function CompactRail({
  theme,
  onMenuClick,
  onNewChat,
  onSettingsClick,
}: {
  theme: "light" | "dark"
  onMenuClick: () => void
  onNewChat: () => void
  onSettingsClick: () => void
}) {
  return (
    <div
      className={cn(
        "hidden sm:flex flex-col items-center justify-between py-6 px-3 border-r",
        theme === "dark" ? "bg-[#1e1f20] border-[#3c4043]" : "bg-[#eef2f7] border-gray-200",
      )}
      style={{ width: 72 }}
    >
      <div className="flex flex-col items-center gap-6">
        <button
          type="button"
          onClick={onMenuClick}
          className={cn(
            "rounded-lg p-2 transition-colors",
            theme === "dark" ? "text-[#e3e3e3] hover:bg-[#3c4043]" : "text-gray-700 hover:bg-gray-200",
          )}
          aria-label="Open menu"
        >
          <Menu className="h-5 w-5" />
        </button>
        <button
          type="button"
          onClick={onNewChat}
          className={cn(
            "rounded-lg p-2 transition-colors",
            theme === "dark" ? "text-[#e3e3e3] hover:bg-[#3c4043]" : "text-gray-700 hover:bg-gray-200",
          )}
          aria-label="New chat"
        >
          <PenSquare className="h-5 w-5" />
        </button>
        <button
          type="button"
          className={cn(
            "rounded-lg p-2 transition-colors",
            theme === "dark" ? "text-[#e3e3e3] hover:bg-[#3c4043]" : "text-gray-700 hover:bg-gray-200",
          )}
          aria-label="Search"
        >
          <Search className="h-5 w-5" />
        </button>
      </div>

      <button
        type="button"
        onClick={onSettingsClick}
        className={cn(
          "rounded-lg p-2 transition-colors",
          theme === "dark" ? "text-[#e3e3e3] hover:bg-[#3c4043]" : "text-gray-700 hover:bg-gray-200",
        )}
        aria-label="Settings"
      >
        <Settings className="h-5 w-5" />
      </button>
    </div>
  )
}
