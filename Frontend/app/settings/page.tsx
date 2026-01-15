"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/lib/auth-context"
import { ProfileForm } from "@/components/settings/profile-form"
import { PreferencesForm } from "@/components/settings/preferences-form"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ArrowLeft, User, Settings, Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"

export default function SettingsPage() {
  const router = useRouter()
  const { user, isLoading } = useAuth()
  const [theme, setTheme] = useState<"light" | "dark">("light")

  // Redirect to home if not authenticated
  useEffect(() => {
    if (!isLoading && !user) {
      router.push("/")
    }
  }, [user, isLoading, router])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-teal-500" />
      </div>
    )
  }

  if (!user) {
    return null
  }

  return (
    <div className={cn(
      "min-h-screen",
      theme === "dark" ? "bg-[#131314] text-white" : "bg-gray-50 text-gray-900"
    )}>
      {/* Header */}
      <header className={cn(
        "sticky top-0 z-10 border-b",
        theme === "dark" ? "bg-[#1a1a1a] border-[#3c4043]" : "bg-white border-gray-200"
      )}>
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center gap-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => router.push("/")}
            className={theme === "dark" ? "hover:bg-[#3c4043]" : ""}
          >
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <h1 className="text-xl font-semibold">Settings</h1>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-4xl mx-auto px-4 py-8">
        <Tabs defaultValue="profile" className="space-y-6">
          <TabsList className={cn(
            "grid w-full max-w-md grid-cols-2",
            theme === "dark" ? "bg-[#1e1f20]" : ""
          )}>
            <TabsTrigger value="profile" className="flex items-center gap-2">
              <User className="h-4 w-4" />
              Profile
            </TabsTrigger>
            <TabsTrigger value="preferences" className="flex items-center gap-2">
              <Settings className="h-4 w-4" />
              Preferences
            </TabsTrigger>
          </TabsList>

          <TabsContent value="profile">
            <ProfileForm theme={theme} />
          </TabsContent>

          <TabsContent value="preferences">
            <PreferencesForm theme={theme} onThemeChange={setTheme} />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  )
}

