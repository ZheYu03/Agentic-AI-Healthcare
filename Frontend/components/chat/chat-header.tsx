"use client"

import { cn } from "@/lib/utils"
import { UserMenu } from "@/components/auth/user-menu"

interface ChatHeaderProps {
  onMenuClick: () => void
  onNewChat: () => void
  sidebarOpen: boolean
  theme: "light" | "dark"
  onSettingsClick?: () => void
  onHelpClick?: () => void
}

export function ChatHeader({ sidebarOpen, theme, onSettingsClick, onHelpClick }: ChatHeaderProps) {
  return (
    <header
      className={cn(
        "flex items-center justify-between px-4 py-3 border-b",
        theme === "dark" ? "bg-[#1a1a1a] border-[#3c4043]" : "bg-white border-gray-200",
      )}
    >
      <div className="flex items-center gap-2">
        <MedicalLogo />
        <span className="text-lg font-medium">{sidebarOpen ? "MedAssist" : "MedAssist"}</span>
      </div>
      <UserMenu 
        theme={theme} 
        onSettingsClick={onSettingsClick}
        onHelpClick={onHelpClick}
      />
    </header>
  )
}

function MedicalLogo() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z"
        fill="url(#medical-gradient)"
      />
      <defs>
        <linearGradient id="medical-gradient" x1="2" y1="2" x2="22" y2="22" gradientUnits="userSpaceOnUse">
          <stop stopColor="#4285F4" />
          <stop offset="0.33" stopColor="#EA4335" />
          <stop offset="0.66" stopColor="#FBBC05" />
          <stop offset="1" stopColor="#34A853" />
        </linearGradient>
      </defs>
    </svg>
  )
}
