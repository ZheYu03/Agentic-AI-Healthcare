"use client"

import { useState, useEffect } from "react"
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
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Loader2, Save, User } from "lucide-react"
import { cn } from "@/lib/utils"

interface ProfileFormProps {
  theme?: "light" | "dark"
}

export function ProfileForm({ theme = "light" }: ProfileFormProps) {
  const { patientProfile, updatePatientProfile } = useAuth()
  const [isLoading, setIsLoading] = useState(false)
  const [isSaved, setIsSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Form state
  const [formData, setFormData] = useState({
    full_name: "",
    ic_number: "",
    date_of_birth: "",
    gender: "",
    phone: "",
    email: "",
    address: "",
    state: "",
    postcode: "",
    blood_type: "",
    nkda: false,
    drug_allergies: "",
    medical_allergies: "",
    food_env_allergies: "",
    emergency_contact_name: "",
    emergency_contact_phone: "",
  })

  // Load profile data into form
  useEffect(() => {
    if (patientProfile) {
      // Normalize gender to lowercase to match SelectItem values
      const normalizedGender = patientProfile.gender?.toLowerCase() || ""
      
      // Find matching state (case-insensitive)
      const normalizedState = MALAYSIAN_STATES.find(
        s => s.toLowerCase() === patientProfile.state?.toLowerCase()
      ) || patientProfile.state || ""
      
      // Find matching blood type (case-insensitive)
      const normalizedBloodType = BLOOD_TYPES.find(
        b => b.toLowerCase() === patientProfile.blood_type?.toLowerCase()
      ) || patientProfile.blood_type || ""

      setFormData({
        full_name: patientProfile.full_name || "",
        ic_number: patientProfile.ic_number || "",
        date_of_birth: patientProfile.date_of_birth || "",
        gender: normalizedGender,
        phone: patientProfile.phone || "",
        email: patientProfile.email || "",
        address: patientProfile.address || "",
        state: normalizedState,
        postcode: patientProfile.postcode || "",
        blood_type: normalizedBloodType,
        nkda: patientProfile.nkda || false,
        drug_allergies: patientProfile.drug_allergies || "",
        medical_allergies: patientProfile.medical_allergies || "",
        food_env_allergies: patientProfile.food_env_allergies || "",
        emergency_contact_name: patientProfile.emergency_contact_name || "",
        emergency_contact_phone: patientProfile.emergency_contact_phone || "",
      })
    }
  }, [patientProfile])

  const updateField = (field: string, value: string | boolean) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
    setIsSaved(false)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setIsLoading(true)

    try {
      const { error } = await updatePatientProfile({
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
        nkda: formData.nkda,
        // When NKA is checked, explicitly set to null to clear DB fields
        drug_allergies: formData.nkda ? null : (formData.drug_allergies || null),
        medical_allergies: formData.nkda ? null : (formData.medical_allergies || null),
        food_env_allergies: formData.nkda ? null : (formData.food_env_allergies || null),
      })

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

  const inputClass = theme === "dark" ? "bg-[#262727] border-[#3c4043] text-white" : ""
  const labelClass = theme === "dark" ? "text-gray-200" : ""

  return (
    <Card className={theme === "dark" ? "bg-[#1e1f20] border-[#3c4043]" : ""}>
      <CardHeader>
        <CardTitle className={cn("flex items-center gap-2", theme === "dark" ? "text-white" : "")}>
          <User className="h-5 w-5" />
          Profile Information
        </CardTitle>
        <CardDescription className={theme === "dark" ? "text-gray-400" : ""}>
          Update your personal and medical information
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Personal Information */}
          <div className="space-y-4">
            <h3 className={cn("font-medium", theme === "dark" ? "text-white" : "")}>
              Personal Information
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="full_name" className={labelClass}>Full Name</Label>
                <Input
                  id="full_name"
                  value={formData.full_name}
                  onChange={(e) => updateField("full_name", e.target.value)}
                  className={inputClass}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="ic_number" className={labelClass}>IC Number</Label>
                <Input
                  id="ic_number"
                  value={formData.ic_number}
                  onChange={(e) => updateField("ic_number", e.target.value)}
                  className={inputClass}
                  disabled
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="date_of_birth" className={labelClass}>Date of Birth</Label>
                <Input
                  id="date_of_birth"
                  type="date"
                  value={formData.date_of_birth}
                  onChange={(e) => updateField("date_of_birth", e.target.value)}
                  className={inputClass}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="gender" className={labelClass}>Gender</Label>
                <Select value={formData.gender} onValueChange={(v) => updateField("gender", v)}>
                  <SelectTrigger className={inputClass}>
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
          </div>

          {/* Contact Information */}
          <div className="space-y-4">
            <h3 className={cn("font-medium", theme === "dark" ? "text-white" : "")}>
              Contact Information
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="phone" className={labelClass}>Phone</Label>
                <Input
                  id="phone"
                  type="tel"
                  value={formData.phone}
                  onChange={(e) => updateField("phone", e.target.value)}
                  className={inputClass}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="email" className={labelClass}>Email</Label>
                <Input
                  id="email"
                  type="email"
                  value={formData.email}
                  onChange={(e) => updateField("email", e.target.value)}
                  className={inputClass}
                />
              </div>
              <div className="md:col-span-2 space-y-2">
                <Label htmlFor="address" className={labelClass}>Address</Label>
                <Textarea
                  id="address"
                  value={formData.address}
                  onChange={(e) => updateField("address", e.target.value)}
                  className={cn("min-h-[80px]", inputClass)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="state" className={labelClass}>State</Label>
                <Select value={formData.state} onValueChange={(v) => updateField("state", v)}>
                  <SelectTrigger className={inputClass}>
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
                <Label htmlFor="postcode" className={labelClass}>Postcode</Label>
                <Input
                  id="postcode"
                  value={formData.postcode}
                  onChange={(e) => updateField("postcode", e.target.value)}
                  className={inputClass}
                />
              </div>
            </div>
          </div>

          {/* Health Information */}
          <div className="space-y-4">
            <h3 className={cn("font-medium", theme === "dark" ? "text-white" : "")}>
              Health Information
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="blood_type" className={labelClass}>Blood Type</Label>
                <Select value={formData.blood_type} onValueChange={(v) => updateField("blood_type", v)}>
                  <SelectTrigger className={inputClass}>
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
              <div className="space-y-2 pt-8">
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
                  <Label htmlFor="nkda" className={cn("font-normal cursor-pointer", labelClass)}>
                    No Known Allergies (NKA)
                  </Label>
                </div>
              </div>
            </div>
            
            {/* Allergy Fields - shown when NKDA is unchecked */}
            {!formData.nkda && (
              <div className="space-y-4 mt-4">
                {/* Drug Allergies - Critical */}
                <div className="space-y-2">
                  <Label htmlFor="drug_allergies" className={cn("flex items-center gap-2", labelClass)}>
                    <span className="w-2 h-2 rounded-full bg-red-500"></span>
                    Drug Allergies (Critical)
                  </Label>
                  <Textarea
                    id="drug_allergies"
                    placeholder="List drug allergies with reactions (e.g., Penicillin - anaphylaxis, Aspirin - hives)"
                    value={formData.drug_allergies}
                    onChange={(e) => updateField("drug_allergies", e.target.value)}
                    className={cn(
                      "min-h-[70px] border-red-200 focus:border-red-400",
                      theme === "dark" ? "bg-[#262727] border-red-900/50 text-white focus:border-red-700" : ""
                    )}
                  />
                  <p className={cn("text-xs", theme === "dark" ? "text-gray-400" : "text-gray-500")}>
                    Important for medication safety - include reaction type
                  </p>
                </div>

                {/* Medical Environment Allergies - High Risk */}
                <div className="space-y-2">
                  <Label htmlFor="medical_allergies" className={cn("flex items-center gap-2", labelClass)}>
                    <span className="w-2 h-2 rounded-full bg-orange-500"></span>
                    Medical Environment (High Risk)
                  </Label>
                  <Textarea
                    id="medical_allergies"
                    placeholder="List medical allergies (e.g., Latex - skin reaction, Contrast dye - hives, Iodine, Anesthesia)"
                    value={formData.medical_allergies}
                    onChange={(e) => updateField("medical_allergies", e.target.value)}
                    className={cn(
                      "min-h-[70px] border-orange-200 focus:border-orange-400",
                      theme === "dark" ? "bg-[#262727] border-orange-900/50 text-white focus:border-orange-700" : ""
                    )}
                  />
                  <p className={cn("text-xs", theme === "dark" ? "text-gray-400" : "text-gray-500")}>
                    Important for medical procedures and hospital visits
                  </p>
                </div>

                {/* Food & Environmental Allergies - Context */}
                <div className="space-y-2">
                  <Label htmlFor="food_env_allergies" className={cn("flex items-center gap-2", labelClass)}>
                    <span className="w-2 h-2 rounded-full bg-blue-500"></span>
                    Food & Environmental (Context)
                  </Label>
                  <Textarea
                    id="food_env_allergies"
                    placeholder="List food/environmental allergies (e.g., Peanuts - swelling, Shellfish, Pollen - seasonal, Dust)"
                    value={formData.food_env_allergies}
                    onChange={(e) => updateField("food_env_allergies", e.target.value)}
                    className={cn(
                      "min-h-[70px] border-blue-200 focus:border-blue-400",
                      theme === "dark" ? "bg-[#262727] border-blue-900/50 text-white focus:border-blue-700" : ""
                    )}
                  />
                  <p className={cn("text-xs", theme === "dark" ? "text-gray-400" : "text-gray-500")}>
                    Helps identify potential cross-reactivity with medications
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Emergency Contact */}
          <div className="space-y-4">
            <h3 className={cn("font-medium", theme === "dark" ? "text-white" : "")}>
              Emergency Contact
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="emergency_contact_name" className={labelClass}>Contact Name</Label>
                <Input
                  id="emergency_contact_name"
                  value={formData.emergency_contact_name}
                  onChange={(e) => updateField("emergency_contact_name", e.target.value)}
                  className={inputClass}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="emergency_contact_phone" className={labelClass}>Contact Phone</Label>
                <Input
                  id="emergency_contact_phone"
                  type="tel"
                  value={formData.emergency_contact_phone}
                  onChange={(e) => updateField("emergency_contact_phone", e.target.value)}
                  className={inputClass}
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
                  Save Changes
                </>
              )}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}

