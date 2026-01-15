"use client"

import { useState } from "react"
import { useAuth } from "@/lib/auth-context"
import { MALAYSIAN_STATES, BLOOD_TYPES, GENDERS } from "@/lib/supabase"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Checkbox } from "@/components/ui/checkbox"
import { Textarea } from "@/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Loader2, User, Phone, Mail, MapPin, Heart, AlertTriangle, UserCheck } from "lucide-react"
import { cn } from "@/lib/utils"

interface PatientFormProps {
  isOpen: boolean
  onClose: () => void
  theme?: "light" | "dark"
}

export function PatientOnboardingForm({ isOpen, onClose, theme = "light" }: PatientFormProps) {
  const { user, createPatientProfile } = useAuth()
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [step, setStep] = useState(1)

  // Form state
  const [formData, setFormData] = useState({
    full_name: "",
    ic_number: "",
    date_of_birth: "",
    gender: "",
    phone: user?.phone || "",
    email: user?.email || "",
    address: "",
    state: "",
    postcode: "",
    blood_type: "",
    drug_allergies: "",
    medical_allergies: "",
    food_env_allergies: "",
    nkda: false,
    emergency_contact_name: "",
    emergency_contact_phone: "",
  })

  const updateField = (field: string, value: string | boolean) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
  }

  const handleSubmit = async () => {
    setError(null)
    setIsLoading(true)

    // Validation
    if (!formData.full_name || !formData.ic_number || !formData.date_of_birth || !formData.gender) {
      setError("Please fill in all required fields")
      setIsLoading(false)
      return
    }

    if (!formData.emergency_contact_name || !formData.emergency_contact_phone) {
      setError("Emergency contact information is required")
      setIsLoading(false)
      return
    }

    try {
      const { error } = await createPatientProfile({
        full_name: formData.full_name,
        ic_number: formData.ic_number,
        date_of_birth: formData.date_of_birth,
        gender: formData.gender,
        phone: formData.phone || undefined,
        email: formData.email || undefined,
        address: formData.address || undefined,
        state: formData.state || undefined,
        postcode: formData.postcode || undefined,
        blood_type: formData.blood_type || undefined,
        emergency_contact_name: formData.emergency_contact_name,
        emergency_contact_phone: formData.emergency_contact_phone,
        allergies_reviewed: true,
        nkda: formData.nkda,
        drug_allergies: formData.nkda ? undefined : formData.drug_allergies || undefined,
        medical_allergies: formData.nkda ? undefined : formData.medical_allergies || undefined,
        food_env_allergies: formData.nkda ? undefined : formData.food_env_allergies || undefined,
      })

      if (error) {
        setError(error.message)
      } else {
        onClose()
      }
    } catch (err) {
      setError("An unexpected error occurred")
    } finally {
      setIsLoading(false)
    }
  }

  const renderStep1 = () => (
    <div className="space-y-4">
      <div className="flex items-center gap-2 mb-4">
        <User className="h-5 w-5 text-teal-500" />
        <h3 className={cn("font-medium", theme === "dark" ? "text-white" : "text-gray-900")}>
          Personal Information
        </h3>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="full_name" className={theme === "dark" ? "text-gray-200" : ""}>
            Full Name <span className="text-red-500">*</span>
          </Label>
          <Input
            id="full_name"
            placeholder="Ahmad bin Abdullah"
            value={formData.full_name}
            onChange={(e) => updateField("full_name", e.target.value)}
            className={theme === "dark" ? "bg-[#262727] border-[#3c4043] text-white" : ""}
            required
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="ic_number" className={theme === "dark" ? "text-gray-200" : ""}>
            IC Number <span className="text-red-500">*</span>
          </Label>
          <Input
            id="ic_number"
            placeholder="901231-14-5678"
            value={formData.ic_number}
            onChange={(e) => updateField("ic_number", e.target.value)}
            className={theme === "dark" ? "bg-[#262727] border-[#3c4043] text-white" : ""}
            required
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="date_of_birth" className={theme === "dark" ? "text-gray-200" : ""}>
            Date of Birth <span className="text-red-500">*</span>
          </Label>
          <Input
            id="date_of_birth"
            type="date"
            value={formData.date_of_birth}
            onChange={(e) => updateField("date_of_birth", e.target.value)}
            className={theme === "dark" ? "bg-[#262727] border-[#3c4043] text-white" : ""}
            required
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="gender" className={theme === "dark" ? "text-gray-200" : ""}>
            Gender <span className="text-red-500">*</span>
          </Label>
          <Select value={formData.gender} onValueChange={(v) => updateField("gender", v)}>
            <SelectTrigger className={theme === "dark" ? "bg-[#262727] border-[#3c4043] text-white" : ""}>
              <SelectValue placeholder="Select gender" />
            </SelectTrigger>
            <SelectContent className={theme === "dark" ? "bg-[#262727] border-[#3c4043]" : ""}>
              {GENDERS.map((gender) => (
                <SelectItem key={gender} value={gender.toLowerCase()}>
                  {gender}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="flex justify-end pt-4">
        <Button 
          onClick={() => setStep(2)} 
          disabled={!formData.full_name || !formData.ic_number || !formData.date_of_birth || !formData.gender}
          className="bg-gray-900 hover:bg-gray-600 text-white disabled:bg-gray-300 disabled:text-gray-500"
        >
          Next
        </Button>
      </div>
    </div>
  )

  const renderStep2 = () => (
    <div className="space-y-4">
      <div className="flex items-center gap-2 mb-4">
        <Phone className="h-5 w-5 text-teal-500" />
        <h3 className={cn("font-medium", theme === "dark" ? "text-white" : "text-gray-900")}>
          Contact Information
        </h3>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="phone" className={theme === "dark" ? "text-gray-200" : ""}>
            Phone Number <span className="text-red-500">*</span>
          </Label>
          <Input
            id="phone"
            type="tel"
            placeholder="+60 12-345 6789"
            value={formData.phone}
            onChange={(e) => updateField("phone", e.target.value)}
            className={theme === "dark" ? "bg-[#262727] border-[#3c4043] text-white" : ""}
            required
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="email" className={theme === "dark" ? "text-gray-200" : ""}>
            Email <span className="text-red-500">*</span>
          </Label>
          <Input
            id="email"
            type="email"
            placeholder="you@example.com"
            value={formData.email}
            onChange={(e) => updateField("email", e.target.value)}
            className={theme === "dark" ? "bg-[#262727] border-[#3c4043] text-white" : ""}
            required
          />
        </div>

        <div className="md:col-span-2 space-y-2">
          <Label htmlFor="address" className={theme === "dark" ? "text-gray-200" : ""}>
            Address <span className="text-red-500">*</span>
          </Label>
          <Textarea
            id="address"
            placeholder="No. 123, Jalan ABC, Taman XYZ"
            value={formData.address}
            onChange={(e) => updateField("address", e.target.value)}
            className={cn("min-h-[80px]", theme === "dark" ? "bg-[#262727] border-[#3c4043] text-white" : "")}
            required
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="state" className={theme === "dark" ? "text-gray-200" : ""}>
            State <span className="text-red-500">*</span>
          </Label>
          <Select value={formData.state} onValueChange={(v) => updateField("state", v)}>
            <SelectTrigger className={theme === "dark" ? "bg-[#262727] border-[#3c4043] text-white" : ""}>
              <SelectValue placeholder="Select state" />
            </SelectTrigger>
            <SelectContent className={theme === "dark" ? "bg-[#262727] border-[#3c4043]" : ""}>
              {MALAYSIAN_STATES.map((state) => (
                <SelectItem key={state} value={state}>
                  {state}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label htmlFor="postcode" className={theme === "dark" ? "text-gray-200" : ""}>
            Postcode <span className="text-red-500">*</span>
          </Label>
          <Input
            id="postcode"
            placeholder="50000"
            value={formData.postcode}
            onChange={(e) => updateField("postcode", e.target.value)}
            className={theme === "dark" ? "bg-[#262727] border-[#3c4043] text-white" : ""}
            required
          />
        </div>
      </div>

      <div className="flex justify-between pt-4">
        <Button variant="outline" onClick={() => setStep(1)}>
          Back
        </Button>
        <Button 
          onClick={() => setStep(3)}
          disabled={!formData.phone || !formData.email || !formData.address || !formData.state || !formData.postcode}
          className="bg-gray-900 hover:bg-gray-600 text-white disabled:bg-gray-300 disabled:text-gray-500"
        >
          Next
        </Button>
      </div>
    </div>
  )

  const renderStep3 = () => (
    <div className="space-y-4">
      <div className="flex items-center gap-2 mb-4">
        <Heart className="h-5 w-5 text-teal-500" />
        <h3 className={cn("font-medium", theme === "dark" ? "text-white" : "text-gray-900")}>
          Health Information
        </h3>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="blood_type" className={theme === "dark" ? "text-gray-200" : ""}>
            Blood Type <span className="text-red-500">*</span>
          </Label>
          <Select value={formData.blood_type} onValueChange={(v) => updateField("blood_type", v)}>
            <SelectTrigger className={theme === "dark" ? "bg-[#262727] border-[#3c4043] text-white" : ""}>
              <SelectValue placeholder="Select blood type" />
            </SelectTrigger>
            <SelectContent className={theme === "dark" ? "bg-[#262727] border-[#3c4043]" : ""}>
              {BLOOD_TYPES.map((type) => (
                <SelectItem key={type} value={type}>
                  {type}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="space-y-3">
        <Label className={theme === "dark" ? "text-gray-200" : ""}>
          Known Allergies <span className="text-red-500">*</span>
        </Label>
        
        <div className="flex items-center space-x-2">
          <Checkbox
            id="nkda"
            checked={formData.nkda}
            onCheckedChange={(checked) => {
              updateField("nkda", !!checked)
              // Clear all allergy fields when NKDA is checked
              if (checked) {
                updateField("drug_allergies", "")
                updateField("medical_allergies", "")
                updateField("food_env_allergies", "")
              }
            }}
          />
          <Label
            htmlFor="nkda"
            className={cn("text-sm font-normal cursor-pointer", theme === "dark" ? "text-gray-300" : "")}
          >
            No Known Allergies (NKA)
          </Label>
        </div>

        {!formData.nkda && (
          <div className="space-y-4 pt-2">
            <p className={cn("text-xs", theme === "dark" ? "text-gray-400" : "text-gray-500")}>
              Fill in at least one allergy field below
            </p>
            {/* Drug Allergies - Critical */}
            <div className="space-y-2">
              <Label className={cn("text-sm font-medium flex items-center gap-2", theme === "dark" ? "text-gray-200" : "")}>
                <span className="w-2 h-2 rounded-full bg-red-500"></span>
                Drug Allergies (Critical)
              </Label>
              <Textarea
                placeholder="List drug allergies with reactions (e.g., Penicillin - anaphylaxis, Aspirin - hives)"
                value={formData.drug_allergies}
                onChange={(e) => updateField("drug_allergies", e.target.value)}
                className={cn(
                  "min-h-[70px] border-red-200 focus:border-red-400",
                  theme === "dark" ? "bg-[#262727] border-red-900/50 text-white focus:border-red-700" : ""
                )}
              />
            </div>

            {/* Medical Environment Allergies - High Risk */}
            <div className="space-y-2">
              <Label className={cn("text-sm font-medium flex items-center gap-2", theme === "dark" ? "text-gray-200" : "")}>
                <span className="w-2 h-2 rounded-full bg-orange-500"></span>
                Medical Environment (High Risk)
              </Label>
              <Textarea
                placeholder="List medical allergies (e.g., Latex - skin reaction, Contrast dye - hives, Iodine)"
                value={formData.medical_allergies}
                onChange={(e) => updateField("medical_allergies", e.target.value)}
                className={cn(
                  "min-h-[70px] border-orange-200 focus:border-orange-400",
                  theme === "dark" ? "bg-[#262727] border-orange-900/50 text-white focus:border-orange-700" : ""
                )}
              />
            </div>

            {/* Food & Environmental Allergies - Context */}
            <div className="space-y-2">
              <Label className={cn("text-sm font-medium flex items-center gap-2", theme === "dark" ? "text-gray-200" : "")}>
                <span className="w-2 h-2 rounded-full bg-blue-500"></span>
                Food & Environmental (Context)
              </Label>
              <Textarea
                placeholder="List food/environmental allergies (e.g., Peanuts - swelling, Shellfish, Pollen - seasonal)"
                value={formData.food_env_allergies}
                onChange={(e) => updateField("food_env_allergies", e.target.value)}
                className={cn(
                  "min-h-[70px] border-blue-200 focus:border-blue-400",
                  theme === "dark" ? "bg-[#262727] border-blue-900/50 text-white focus:border-blue-700" : ""
                )}
              />
            </div>
          </div>
        )}
      </div>

      <div className="flex justify-between pt-4">
        <Button variant="outline" onClick={() => setStep(2)}>
          Back
        </Button>
        <Button 
          onClick={() => setStep(4)}
          disabled={
            !formData.blood_type || 
            (!formData.nkda && !formData.drug_allergies && !formData.medical_allergies && !formData.food_env_allergies)
          }
          className="bg-gray-900 hover:bg-gray-600 text-white disabled:bg-gray-300 disabled:text-gray-500"
        >
          Next
        </Button>
      </div>
    </div>
  )

  const renderStep4 = () => (
    <div className="space-y-4">
      <div className="flex items-center gap-2 mb-4">
        <AlertTriangle className="h-5 w-5 text-teal-500" />
        <h3 className={cn("font-medium", theme === "dark" ? "text-white" : "text-gray-900")}>
          Emergency Contact <span className="text-red-500">*</span>
        </h3>
      </div>

      <p className={cn("text-sm mb-4", theme === "dark" ? "text-gray-400" : "text-gray-500")}>
        Please provide emergency contact information. This person will be contacted in case of medical emergencies.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="emergency_contact_name" className={theme === "dark" ? "text-gray-200" : ""}>
            Contact Name <span className="text-red-500">*</span>
          </Label>
          <Input
            id="emergency_contact_name"
            placeholder="Family member or friend"
            value={formData.emergency_contact_name}
            onChange={(e) => updateField("emergency_contact_name", e.target.value)}
            className={theme === "dark" ? "bg-[#262727] border-[#3c4043] text-white" : ""}
            required
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="emergency_contact_phone" className={theme === "dark" ? "text-gray-200" : ""}>
            Contact Phone <span className="text-red-500">*</span>
          </Label>
          <Input
            id="emergency_contact_phone"
            type="tel"
            placeholder="+60 12-345 6789"
            value={formData.emergency_contact_phone}
            onChange={(e) => updateField("emergency_contact_phone", e.target.value)}
            className={theme === "dark" ? "bg-[#262727] border-[#3c4043] text-white" : ""}
            required
          />
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 text-red-500 text-sm p-3 bg-red-50 rounded-lg">
          <AlertTriangle className="h-4 w-4" />
          {error}
        </div>
      )}

      <div className="flex justify-between pt-4">
        <Button variant="outline" onClick={() => setStep(3)}>
          Back
        </Button>
        <Button
          onClick={handleSubmit}
          disabled={isLoading || !formData.emergency_contact_name || !formData.emergency_contact_phone}
          className="bg-gray-900 hover:bg-gray-600 text-white disabled:bg-gray-300 disabled:text-gray-500"
        >
          {isLoading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Saving...
            </>
          ) : (
            <>
              <UserCheck className="mr-2 h-4 w-4" />
              Complete Setup
            </>
          )}
        </Button>
      </div>
    </div>
  )

  // Progress indicator
  const ProgressIndicator = () => (
    <div className="flex items-center justify-center gap-2 mb-6">
      {[1, 2, 3, 4].map((s) => (
        <div
          key={s}
          className={cn(
            "w-2.5 h-2.5 rounded-full transition-colors",
            s === step
              ? "bg-teal-500"
              : s < step
                ? "bg-teal-300"
                : theme === "dark"
                  ? "bg-[#3c4043]"
                  : "bg-gray-200"
          )}
        />
      ))}
    </div>
  )

  return (
    <Dialog open={isOpen} onOpenChange={() => {}}>
      <DialogContent
        className={cn(
          "sm:max-w-lg max-h-[90vh] overflow-y-auto [&>button]:hidden",
          theme === "dark" ? "bg-[#1e1f20] text-white border-[#3c4043]" : "bg-white"
        )}
        onInteractOutside={(e) => e.preventDefault()}
        onEscapeKeyDown={(e) => e.preventDefault()}
      >
        <DialogHeader>
          <DialogTitle className={theme === "dark" ? "text-white" : ""}>
            Welcome to MedAssist! 👋
          </DialogTitle>
          <DialogDescription className={theme === "dark" ? "text-gray-400" : ""}>
            Let&apos;s set up your profile so we can provide personalized health assistance.
          </DialogDescription>
        </DialogHeader>

        <ProgressIndicator />

        {step === 1 && renderStep1()}
        {step === 2 && renderStep2()}
        {step === 3 && renderStep3()}
        {step === 4 && renderStep4()}
      </DialogContent>
    </Dialog>
  )
}

