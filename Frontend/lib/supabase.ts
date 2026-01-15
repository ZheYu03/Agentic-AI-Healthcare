import { createBrowserClient } from '@supabase/ssr'

// Check if Supabase is configured
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

export const isSupabaseConfigured = !!(supabaseUrl && supabaseAnonKey)

// Create a single supabase client for browser-side usage
export function createClient() {
  if (!supabaseUrl || !supabaseAnonKey) {
    console.warn(
      '⚠️ Supabase not configured. Please create Frontend/.env.local with:\n' +
      'NEXT_PUBLIC_SUPABASE_URL=your-supabase-url\n' +
      'NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key'
    )
    // Return a mock client that won't crash the app
    return null as any
  }
  return createBrowserClient(supabaseUrl, supabaseAnonKey)
}

// Singleton instance for client-side
let browserClient: ReturnType<typeof createBrowserClient> | null = null

export function getSupabaseClient() {
  if (!isSupabaseConfigured) {
    return null as any
  }
  
  if (typeof window === 'undefined') {
    // Server-side: always create a new client
    return createClient()
  }
  
  // Client-side: reuse existing client
  if (!browserClient) {
    browserClient = createClient()
  }
  return browserClient
}

// Types for database tables
export interface PatientData {
  id: string
  user_id: string
  full_name: string
  ic_number: string
  date_of_birth: string
  gender: string
  phone?: string
  email?: string
  address?: string
  state?: string
  postcode?: string
  blood_type?: string
  emergency_contact_name: string
  emergency_contact_phone: string
  allergies_reviewed: boolean
  nkda: boolean
  drug_allergies?: string | null
  medical_allergies?: string | null
  food_env_allergies?: string | null
  created_at: string
  updated_at: string
}

export interface UserPreferences {
  id: string
  user_id: string
  theme: string
  language: string
  notifications_enabled: boolean
  email_notifications: boolean
  sms_notifications: boolean
  timezone: string
  created_at: string
  updated_at: string
}

export interface PatientEncounter {
  id: string
  patient_id: string | null
  encounter_type: string
  encounter_date: string
  end_date?: string | null
  chief_complaint?: string | null
  status: string
  urgency_level?: string | null
  facility_id?: string | null
  provider_name?: string | null
  visit_summary?: string | null
  disposition?: string | null
  created_at: string
  updated_at: string
}

export interface EncounterMessage {
  id: string
  encounter_id: string
  role: string
  content: string
  agent_name?: string | null
  metadata?: Record<string, unknown> | null
  created_at: string
}

// Malaysian states for dropdown
export const MALAYSIAN_STATES = [
  'Johor',
  'Kedah',
  'Kelantan',
  'Kuala Lumpur',
  'Labuan',
  'Melaka',
  'Negeri Sembilan',
  'Pahang',
  'Penang',
  'Perak',
  'Perlis',
  'Putrajaya',
  'Sabah',
  'Sarawak',
  'Selangor',
  'Terengganu',
] as const

// Blood types
export const BLOOD_TYPES = [
  'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-', 'Unknown'
] as const

// Gender options
export const GENDERS = ['Male', 'Female', 'Other'] as const

