"use client"

import { useRef, useEffect, useState, type KeyboardEvent } from "react"
import { Mic, Send, Square } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

// Extend Window interface for Web Speech API
declare global {
  interface Window {
    SpeechRecognition: any
    webkitSpeechRecognition: any
  }
}

interface ChatInputProps {
  value: string
  onChange: (value: string) => void
  onSend: (message: string) => void
  onStop: () => void
  isLoading: boolean
  theme: "light" | "dark"
  disabled?: boolean
  placeholder?: string
}

export function ChatInput({ value, onChange, onSend, onStop, isLoading, theme, disabled = false, placeholder = "Ask about your health..." }: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const recognitionRef = useRef<any>(null)
  const [isListening, setIsListening] = useState(false)
  const [speechSupported, setSpeechSupported] = useState(false)

  // Initialize Speech Recognition
  useEffect(() => {
    if (typeof window !== 'undefined' && ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window)) {
      setSpeechSupported(true)
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
      recognitionRef.current = new SpeechRecognition()
      recognitionRef.current.continuous = true  // Keep listening until manually stopped
      recognitionRef.current.interimResults = true  // Show results while speaking
      recognitionRef.current.lang = 'en-US'
      recognitionRef.current.maxAlternatives = 1

      recognitionRef.current.onstart = () => {
        setIsListening(true)
      }

      recognitionRef.current.onresult = (event: any) => {
        let finalTranscript = ''
        let interimTranscript = ''

        for (let i = event.resultIndex; i < event.results.length; i++) {
          const transcript = event.results[i][0].transcript
          if (event.results[i].isFinal) {
            finalTranscript += transcript + ' '
          } else {
            interimTranscript += transcript
          }
        }

        // Only update with final results to avoid flickering
        if (finalTranscript) {
          onChange(value + finalTranscript)
        }
      }

      recognitionRef.current.onerror = (event: any) => {
        console.error('Speech recognition error:', event.error)
        if (event.error === 'not-allowed') {
          alert('Microphone access denied. Please enable microphone permissions in your browser settings.')
        }
        setIsListening(false)
      }

      recognitionRef.current.onend = () => {
        setIsListening(false)
      }
    }

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop()
      }
    }
  }, [value, onChange])

  const toggleListening = async () => {
    if (!speechSupported) {
      alert('Speech recognition is not supported in your browser. Please use Chrome, Edge, or Safari.')
      return
    }

    if (isListening) {
      recognitionRef.current?.stop()
    } else {
      try {
        // Request microphone permission explicitly
        await navigator.mediaDevices.getUserMedia({ audio: true })
        recognitionRef.current?.start()
      } catch (error) {
        console.error('Microphone permission error:', error)
        alert('Please allow microphone access to use voice input.')
      }
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      if (value.trim() && !isLoading) {
        onSend(value)
      }
    }
  }

  const handleInput = () => {
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = "auto"
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`
    }
  }

  return (
    <div className="relative">
      <div
        className={cn(
          "rounded-3xl border focus-within:border-opacity-70 transition-colors",
          theme === "dark"
            ? "bg-[#1e1f20] border-[#3c4043] focus-within:border-[#5f6368]"
            : "bg-gray-100 border-gray-300 focus-within:border-gray-400",
        )}
      >
        <div className="px-4 pt-4 pb-2">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => {
              onChange(e.target.value)
              handleInput()
            }}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            className={cn(
              "w-full bg-transparent resize-none outline-none text-base min-h-[24px] max-h-[200px] placeholder-opacity-70",
              theme === "dark" ? "text-[#e3e3e3] placeholder-[#9aa0a6]" : "text-gray-900 placeholder-gray-500",
              disabled && "cursor-not-allowed opacity-60",
            )}
            rows={1}
            disabled={isLoading || disabled}
          />
        </div>

        {/* Bottom Controls */}
        <div className="flex items-center justify-between px-2 pb-2">
          <div className="flex items-center gap-1">
            {/* Removed + and Tools buttons */}
          </div>

          <div className="flex items-center gap-2">
            {isLoading ? (
              <Button
                onClick={onStop}
                variant="ghost"
                size="icon"
                className={cn(
                  "h-9 w-9",
                  theme === "dark" ? "text-[#e3e3e3] hover:bg-[#3c4043]" : "text-gray-700 hover:bg-gray-200",
                )}
              >
                <Square className="h-5 w-5 fill-current" />
              </Button>
            ) : (
              <>
                <Button
                  onClick={toggleListening}
                  variant="ghost"
                  size="icon"
                  className={cn(
                    "h-9 w-9 transition-all",
                    isListening
                      ? "text-red-500 animate-pulse"
                      : theme === "dark"
                        ? "text-[#9aa0a6] hover:text-[#e3e3e3] hover:bg-[#3c4043]"
                        : "text-gray-500 hover:text-gray-700 hover:bg-gray-200",
                  )}
                  title={isListening ? "Stop listening" : "Start voice input"}
                >
                  <Mic className={cn("h-5 w-5", isListening && "fill-current")} />
                </Button>
                <Button
                  onClick={() => value.trim() && onSend(value)}
                  variant="ghost"
                  size="icon"
                  disabled={!value.trim()}
                  className={cn(
                    "h-9 w-9 transition-colors",
                    value.trim()
                      ? theme === "dark"
                        ? "text-[#e3e3e3] hover:bg-[#3c4043]"
                        : "text-gray-700 hover:bg-gray-200"
                      : theme === "dark"
                        ? "text-[#5f6368] cursor-not-allowed"
                        : "text-gray-400 cursor-not-allowed",
                  )}
                >
                  <Send className="h-5 w-5" />
                </Button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
