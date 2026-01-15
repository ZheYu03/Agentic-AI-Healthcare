"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"
import { 
  ArrowLeft, 
  HelpCircle, 
  MessageCircle, 
  Shield, 
  Stethoscope, 
  Clock,
  AlertTriangle,
  Heart,
  Mail
} from "lucide-react"
import { cn } from "@/lib/utils"

const FAQ_ITEMS = [
  {
    question: "What is MedAssist?",
    answer: "MedAssist is an AI-powered health assistant that helps you understand your symptoms, provides general health information, and guides you on when to seek professional medical care. It uses advanced AI technology to provide personalized health insights."
  },
  {
    question: "Is MedAssist a replacement for a doctor?",
    answer: "No, MedAssist is not a replacement for professional medical advice, diagnosis, or treatment. It's designed to help you better understand your health and make informed decisions about when to seek medical care. Always consult with a healthcare professional for medical concerns."
  },
  {
    question: "How does the symptom checker work?",
    answer: "Our symptom checker uses AI to analyze the symptoms you describe and provides possible causes and recommendations. It follows clinical guidelines and medical protocols to give you relevant information and helps determine the urgency of your situation."
  },
  {
    question: "Is my health information secure?",
    answer: "Yes, we take your privacy seriously. All your health data is encrypted and stored securely. We comply with data protection regulations and never share your personal health information with third parties without your explicit consent."
  },
  {
    question: "What should I do in a medical emergency?",
    answer: "In case of a medical emergency, please call 999 (Malaysia) or go to your nearest emergency department immediately. MedAssist is not designed for emergency situations and cannot provide real-time emergency assistance."
  },
  {
    question: "How accurate is the health information provided?",
    answer: "MedAssist uses information from trusted medical sources and clinical guidelines. However, the information provided is for educational purposes only and may not apply to your specific situation. Always verify with a healthcare professional."
  },
  {
    question: "Can I use MedAssist for my family members?",
    answer: "Each user should have their own account as the health information and recommendations are personalized based on individual health profiles. Creating separate accounts ensures accurate and relevant health guidance for each person."
  },
  {
    question: "How do I update my health profile?",
    answer: "You can update your health profile by going to Settings > Profile. Keeping your profile up-to-date helps MedAssist provide more accurate and personalized health information."
  },
]

const FEATURES = [
  {
    icon: Stethoscope,
    title: "Symptom Checker",
    description: "Describe your symptoms and get guidance on possible causes and next steps"
  },
  {
    icon: Heart,
    title: "Health Information",
    description: "Access reliable health information about conditions, medications, and treatments"
  },
  {
    icon: Clock,
    title: "Urgency Assessment",
    description: "Understand the urgency of your symptoms and when to seek care"
  },
  {
    icon: Shield,
    title: "Privacy First",
    description: "Your health data is encrypted and protected at all times"
  },
]

export default function HelpPage() {
  const router = useRouter()
  const [theme] = useState<"light" | "dark">("light")

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
          <h1 className="text-xl font-semibold">Help & Support</h1>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-4xl mx-auto px-4 py-8 space-y-8">
        {/* Emergency Notice */}
        <Card className="border-red-200 bg-red-50">
          <CardContent className="flex items-start gap-4 py-4">
            <AlertTriangle className="h-6 w-6 text-red-500 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-semibold text-red-700">Medical Emergency?</h3>
              <p className="text-sm text-red-600 mt-1">
                If you&apos;re experiencing a medical emergency, call <strong>999</strong> immediately or go to your nearest emergency department. MedAssist is not designed for emergency situations.
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Features */}
        <section>
          <h2 className={cn("text-lg font-semibold mb-4", theme === "dark" ? "text-white" : "")}>
            What MedAssist Can Help With
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {FEATURES.map((feature) => (
              <Card key={feature.title} className={theme === "dark" ? "bg-[#1e1f20] border-[#3c4043]" : ""}>
                <CardContent className="flex items-start gap-4 py-4">
                  <div className="p-2 rounded-lg bg-teal-100">
                    <feature.icon className="h-5 w-5 text-teal-600" />
                  </div>
                  <div>
                    <h3 className={cn("font-medium", theme === "dark" ? "text-white" : "")}>
                      {feature.title}
                    </h3>
                    <p className={cn("text-sm mt-1", theme === "dark" ? "text-gray-400" : "text-gray-500")}>
                      {feature.description}
                    </p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>

        {/* FAQ */}
        <section>
          <Card className={theme === "dark" ? "bg-[#1e1f20] border-[#3c4043]" : ""}>
            <CardHeader>
              <CardTitle className={cn("flex items-center gap-2", theme === "dark" ? "text-white" : "")}>
                <HelpCircle className="h-5 w-5" />
                Frequently Asked Questions
              </CardTitle>
              <CardDescription className={theme === "dark" ? "text-gray-400" : ""}>
                Find answers to common questions about MedAssist
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Accordion type="single" collapsible className="w-full">
                {FAQ_ITEMS.map((item, index) => (
                  <AccordionItem key={index} value={`item-${index}`}>
                    <AccordionTrigger className={cn(
                      "text-left",
                      theme === "dark" ? "text-white hover:text-gray-300" : ""
                    )}>
                      {item.question}
                    </AccordionTrigger>
                    <AccordionContent className={theme === "dark" ? "text-gray-400" : "text-gray-600"}>
                      {item.answer}
                    </AccordionContent>
                  </AccordionItem>
                ))}
              </Accordion>
            </CardContent>
          </Card>
        </section>

        {/* Contact */}
        <section>
          <Card className={theme === "dark" ? "bg-[#1e1f20] border-[#3c4043]" : ""}>
            <CardHeader>
              <CardTitle className={cn("flex items-center gap-2", theme === "dark" ? "text-white" : "")}>
                <MessageCircle className="h-5 w-5" />
                Need More Help?
              </CardTitle>
              <CardDescription className={theme === "dark" ? "text-gray-400" : ""}>
                We&apos;re here to help you
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className={theme === "dark" ? "text-gray-300" : "text-gray-600"}>
                If you couldn&apos;t find the answer you were looking for, feel free to reach out to our support team.
              </p>
              <div className="flex flex-col sm:flex-row gap-4">
                <Button variant="outline" className="flex items-center gap-2">
                  <Mail className="h-4 w-4" />
                  Email Support
                </Button>
                <Button variant="outline" className="flex items-center gap-2">
                  <MessageCircle className="h-4 w-4" />
                  Live Chat
                </Button>
              </div>
            </CardContent>
          </Card>
        </section>

        {/* Disclaimer */}
        <section className={cn(
          "text-center py-8 text-sm",
          theme === "dark" ? "text-gray-500" : "text-gray-400"
        )}>
          <p>
            MedAssist provides general health information for educational purposes only.
            It is not a substitute for professional medical advice, diagnosis, or treatment.
          </p>
          <p className="mt-2">
            © 2024 MedAssist. All rights reserved.
          </p>
        </section>
      </main>
    </div>
  )
}

