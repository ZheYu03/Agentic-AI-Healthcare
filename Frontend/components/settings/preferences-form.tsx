"use client"

import { useState, useEffect } from "react"
import { useAuth } from "@/lib/auth-context"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Loader2, Save, Settings, Bell, Globe, Palette } from "lucide-react"
import { cn } from "@/lib/utils"

interface PreferencesFormProps {
  theme?: "light" | "dark"
  onThemeChange?: (theme: "light" | "dark") => void
}

const LANGUAGES = [
  { value: "en", label: "English" },
  { value: "ms", label: "Bahasa Malaysia" },
  { value: "zh", label: "中文" },
  { value: "ta", label: "தமிழ்" },
] as const

const TIMEZONES = [
  { value: "Asia/Kuala_Lumpur", label: "Malaysia (GMT+8)" },
  { value: "Asia/Singapore", label: "Singapore (GMT+8)" },
  { value: "Asia/Bangkok", label: "Thailand (GMT+7)" },
  { value: "Asia/Jakarta", label: "Indonesia (GMT+7)" },
] as const

export function PreferencesForm({ theme = "light", onThemeChange }: PreferencesFormProps) {
  const { userPreferences, updateUserPreferences } = useAuth()
  const [isLoading, setIsLoading] = useState(false)
  const [isSaved, setIsSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Form state
  const [formData, setFormData] = useState({
    theme: "system",
    language: "en",
    notifications_enabled: true,
    email_notifications: true,
    sms_notifications: false,
    timezone: "Asia/Kuala_Lumpur",
  })

  // Load preferences into form
  useEffect(() => {
    if (userPreferences) {
      setFormData({
        theme: userPreferences.theme || "system",
        language: userPreferences.language || "en",
        notifications_enabled: userPreferences.notifications_enabled ?? true,
        email_notifications: userPreferences.email_notifications ?? true,
        sms_notifications: userPreferences.sms_notifications ?? false,
        timezone: userPreferences.timezone || "Asia/Kuala_Lumpur",
      })
    }
  }, [userPreferences])

  const updateField = (field: string, value: string | boolean) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
    setIsSaved(false)

    // Apply theme change immediately
    if (field === "theme" && onThemeChange) {
      if (value === "dark") {
        onThemeChange("dark")
      } else if (value === "light") {
        onThemeChange("light")
      }
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setIsLoading(true)

    try {
      const { error } = await updateUserPreferences(formData)

      if (error) {
        setError(error.message)
      } else {
        setIsSaved(true)
        setTimeout(() => setIsSaved(false), 3000)
      }
    } catch (err) {
      setError("An unexpected error occurred")
    } finally {
      setIsLoading(false)
    }
  }

  const selectClass = theme === "dark" ? "bg-[#262727] border-[#3c4043] text-white" : ""
  const labelClass = theme === "dark" ? "text-gray-200" : ""

  return (
    <Card className={theme === "dark" ? "bg-[#1e1f20] border-[#3c4043]" : ""}>
      <CardHeader>
        <CardTitle className={cn("flex items-center gap-2", theme === "dark" ? "text-white" : "")}>
          <Settings className="h-5 w-5" />
          Preferences
        </CardTitle>
        <CardDescription className={theme === "dark" ? "text-gray-400" : ""}>
          Customize your MedAssist experience
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Appearance */}
          <div className="space-y-4">
            <h3 className={cn("font-medium flex items-center gap-2", theme === "dark" ? "text-white" : "")}>
              <Palette className="h-4 w-4" />
              Appearance
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="theme" className={labelClass}>Theme</Label>
                <Select value={formData.theme} onValueChange={(v) => updateField("theme", v)}>
                  <SelectTrigger className={selectClass}>
                    <SelectValue placeholder="Select theme" />
                  </SelectTrigger>
                  <SelectContent className={theme === "dark" ? "bg-[#262727] border-[#3c4043]" : ""}>
                    <SelectItem value="system">System</SelectItem>
                    <SelectItem value="light">Light</SelectItem>
                    <SelectItem value="dark">Dark</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>

          {/* Language & Region */}
          <div className="space-y-4">
            <h3 className={cn("font-medium flex items-center gap-2", theme === "dark" ? "text-white" : "")}>
              <Globe className="h-4 w-4" />
              Language & Region
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="language" className={labelClass}>Language</Label>
                <Select value={formData.language} onValueChange={(v) => updateField("language", v)}>
                  <SelectTrigger className={selectClass}>
                    <SelectValue placeholder="Select language" />
                  </SelectTrigger>
                  <SelectContent className={theme === "dark" ? "bg-[#262727] border-[#3c4043]" : ""}>
                    {LANGUAGES.map((lang) => (
                      <SelectItem key={lang.value} value={lang.value}>
                        {lang.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="timezone" className={labelClass}>Timezone</Label>
                <Select value={formData.timezone} onValueChange={(v) => updateField("timezone", v)}>
                  <SelectTrigger className={selectClass}>
                    <SelectValue placeholder="Select timezone" />
                  </SelectTrigger>
                  <SelectContent className={theme === "dark" ? "bg-[#262727] border-[#3c4043]" : ""}>
                    {TIMEZONES.map((tz) => (
                      <SelectItem key={tz.value} value={tz.value}>
                        {tz.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>

          {/* Notifications */}
          <div className="space-y-4">
            <h3 className={cn("font-medium flex items-center gap-2", theme === "dark" ? "text-white" : "")}>
              <Bell className="h-4 w-4" />
              Notifications
            </h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label className={labelClass}>Enable Notifications</Label>
                  <p className={cn("text-sm", theme === "dark" ? "text-gray-400" : "text-gray-500")}>
                    Receive notifications about your health updates
                  </p>
                </div>
                <Switch
                  checked={formData.notifications_enabled}
                  onCheckedChange={(checked) => updateField("notifications_enabled", checked)}
                />
              </div>
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label className={labelClass}>Email Notifications</Label>
                  <p className={cn("text-sm", theme === "dark" ? "text-gray-400" : "text-gray-500")}>
                    Receive health reminders via email
                  </p>
                </div>
                <Switch
                  checked={formData.email_notifications}
                  onCheckedChange={(checked) => updateField("email_notifications", checked)}
                  disabled={!formData.notifications_enabled}
                />
              </div>
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label className={labelClass}>SMS Notifications</Label>
                  <p className={cn("text-sm", theme === "dark" ? "text-gray-400" : "text-gray-500")}>
                    Receive urgent alerts via SMS
                  </p>
                </div>
                <Switch
                  checked={formData.sms_notifications}
                  onCheckedChange={(checked) => updateField("sms_notifications", checked)}
                  disabled={!formData.notifications_enabled}
                />
              </div>
            </div>
          </div>

          {error && (
            <div className="text-red-500 text-sm">{error}</div>
          )}

          <div className="flex justify-end">
            <Button 
              type="submit" 
              disabled={isLoading}
              className="bg-gray-900 text-white hover:bg-gray-600 disabled:bg-gray-300 disabled:text-gray-500"
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : isSaved ? (
                <>
                  <Save className="mr-2 h-4 w-4" />
                  Saved!
                </>
              ) : (
                <>
                  <Save className="mr-2 h-4 w-4" />
                  Save Preferences
                </>
              )}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}

