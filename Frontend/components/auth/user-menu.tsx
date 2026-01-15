"use client"

import { useState } from "react"
import { useAuth } from "@/lib/auth-context"
import { LoginModal } from "./login-modal"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { User, Settings, HelpCircle, LogOut, Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"

interface UserMenuProps {
  theme?: "light" | "dark"
  onSettingsClick?: () => void
  onHelpClick?: () => void
}

export function UserMenu({ theme = "light", onSettingsClick, onHelpClick }: UserMenuProps) {
  const { user, isLoading, patientProfile, signOut } = useAuth()
  const [showLoginModal, setShowLoginModal] = useState(false)
  const [isSigningOut, setIsSigningOut] = useState(false)

  const handleSignOut = async () => {
    setIsSigningOut(true)
    await signOut()
    setIsSigningOut(false)
  }

  // Get user initials for avatar
  const getInitials = () => {
    if (patientProfile?.full_name) {
      const names = patientProfile.full_name.split(" ")
      return names.map((n) => n[0]).slice(0, 2).join("").toUpperCase()
    }
    if (user?.email) {
      return user.email[0].toUpperCase()
    }
    return "U"
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="h-8 w-8 rounded-full bg-gray-200 animate-pulse flex items-center justify-center">
        <Loader2 className="h-4 w-4 animate-spin text-gray-400" />
      </div>
    )
  }

  // Not logged in - show sign in button
  if (!user) {
    return (
      <>
        <Button
          variant="default"
          size="sm"
          onClick={() => setShowLoginModal(true)}
          className="bg-gradient-to-r from-teal-500 to-blue-600 hover:from-teal-600 hover:to-blue-700 text-white"
        >
          Sign In
        </Button>
        <LoginModal
          isOpen={showLoginModal}
          onClose={() => setShowLoginModal(false)}
          theme={theme}
        />
      </>
    )
  }

  // Logged in - show user menu
  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            className="relative h-9 w-9 rounded-full p-0"
          >
            <Avatar className="h-9 w-9 border-2 border-transparent hover:border-teal-500 transition-colors">
              <AvatarImage
                src={user.user_metadata?.avatar_url}
                alt={patientProfile?.full_name || user.email || "User"}
              />
              <AvatarFallback className="bg-gradient-to-br from-teal-500 to-blue-600 text-white font-medium">
                {getInitials()}
              </AvatarFallback>
            </Avatar>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent
          align="end"
          className={cn(
            "w-56",
            theme === "dark" && "bg-[#1e1f20] border-[#3c4043] text-white"
          )}
        >
          <DropdownMenuLabel className="font-normal">
            <div className="flex flex-col space-y-1">
              <p className="text-sm font-medium leading-none">
                {patientProfile?.full_name || "User"}
              </p>
              <p className={cn(
                "text-xs leading-none",
                theme === "dark" ? "text-gray-400" : "text-gray-500"
              )}>
                {user.email}
              </p>
            </div>
          </DropdownMenuLabel>
          <DropdownMenuSeparator className={theme === "dark" ? "bg-[#3c4043]" : ""} />
          <DropdownMenuItem
            className={cn(
              "cursor-pointer",
              theme === "dark" && "focus:bg-[#3c4043]"
            )}
            onClick={onSettingsClick}
          >
            <User className="mr-2 h-4 w-4" />
            <span>Profile</span>
          </DropdownMenuItem>
          <DropdownMenuItem
            className={cn(
              "cursor-pointer",
              theme === "dark" && "focus:bg-[#3c4043]"
            )}
            onClick={onSettingsClick}
          >
            <Settings className="mr-2 h-4 w-4" />
            <span>Settings</span>
          </DropdownMenuItem>
          <DropdownMenuItem
            className={cn(
              "cursor-pointer",
              theme === "dark" && "focus:bg-[#3c4043]"
            )}
            onClick={onHelpClick}
          >
            <HelpCircle className="mr-2 h-4 w-4" />
            <span>Help</span>
          </DropdownMenuItem>
          <DropdownMenuSeparator className={theme === "dark" ? "bg-[#3c4043]" : ""} />
          <DropdownMenuItem
            className={cn(
              "cursor-pointer text-red-500 focus:text-red-500",
              theme === "dark" && "focus:bg-[#3c4043]"
            )}
            onClick={handleSignOut}
            disabled={isSigningOut}
          >
            {isSigningOut ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <LogOut className="mr-2 h-4 w-4" />
            )}
            <span>Sign out</span>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      <LoginModal
        isOpen={showLoginModal}
        onClose={() => setShowLoginModal(false)}
        theme={theme}
      />
    </>
  )
}

