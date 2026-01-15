"use client"

import { Stethoscope, Pill, Activity, FileText, HeartPulse } from "lucide-react"
import { cn } from "@/lib/utils"
import { useAuth } from "@/lib/auth-context"

interface WelcomeScreenProps {
  onSuggestionClick: (suggestion: string) => void
  theme?: "light" | "dark"
}

const suggestions = [
  { icon: Stethoscope, label: "Check symptoms", query: "I have a headache and sore throat. What could this be?" },
  { icon: Pill, label: "Medication info", query: "What are the common side effects of ibuprofen?" },
  { icon: Activity, label: "Health tips", query: "How can I improve my sleep quality?" },
  { icon: FileText, label: "Explain results", query: "What does elevated blood pressure mean?" },
  { icon: HeartPulse, label: "Preventive care", query: "What health screenings should I get annually?" },
]

export function WelcomeScreen({ onSuggestionClick, theme = "dark" }: WelcomeScreenProps) {
  const { patientProfile } = useAuth()
  
  // Get first name from full name (e.g., "Lim Zhe Yu" -> "Lim")
  const firstName = patientProfile?.full_name?.split(' ')[0] || 'there'

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
      {/* Greeting */}
      <div className="mb-8">
        <div className="flex items-center justify-center gap-2 mb-4">
          <GeminiStar />
          <span className={cn("text-lg", theme === "dark" ? "text-[#9aa0a6]" : "text-gray-500")}>Hi {firstName}</span>
        </div>
        <h1
          className={cn(
            "text-4xl sm:text-5xl font-medium text-balance",
            theme === "dark" ? "text-[#e3e3e3]" : "text-gray-900",
          )}
        >
          How can I help with your health today?
        </h1>
      </div>

      {/* Disclaimer */}
      <p className={cn("text-sm max-w-md mb-8", theme === "dark" ? "text-[#9aa0a6]" : "text-gray-600")}>
        I can provide general health information, but please consult a healthcare professional for medical advice.
      </p>

      <div className="flex flex-wrap justify-center gap-2 max-w-2xl">
        {suggestions.map((suggestion, index) => (
          <button
            key={index}
            onClick={() => onSuggestionClick(suggestion.query)}
            className={cn(
              "flex items-center gap-2 px-4 py-2.5 rounded-full text-sm border transition-colors",
              theme === "dark"
                ? "bg-[#1e1f20] hover:bg-[#3c4043] border-[#3c4043] text-[#e3e3e3]"
                : "bg-gray-100 hover:bg-gray-200 border-gray-300 text-gray-700",
            )}
          >
            <suggestion.icon className={cn("h-4 w-4", theme === "dark" ? "text-[#9aa0a6]" : "text-gray-500")} />
            <span>{suggestion.label}</span>
          </button>
        ))}
      </div>
    </div>
  )
}

function GeminiStar() {
  return (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z"
        fill="url(#star-gradient)"
      />
      <defs>
        <linearGradient id="star-gradient" x1="2" y1="2" x2="22" y2="22" gradientUnits="userSpaceOnUse">
          <stop stopColor="#4285F4" />
          <stop offset="0.33" stopColor="#EA4335" />
          <stop offset="0.66" stopColor="#FBBC05" />
          <stop offset="1" stopColor="#34A853" />
        </linearGradient>
      </defs>
    </svg>
  )
}
