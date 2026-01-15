"use client"

import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from 'react'
import { User, Session, AuthError, type AuthChangeEvent } from '@supabase/supabase-js'
import { getSupabaseClient, isSupabaseConfigured, type PatientData, type UserPreferences, type PatientEncounter, type EncounterMessage } from './supabase'

// User location type for geolocation
interface UserLocation {
  lat: number
  lng: number
}

interface AuthContextType {
  user: User | null
  session: Session | null
  isLoading: boolean
  patientProfile: PatientData | null
  userPreferences: UserPreferences | null
  hasCompletedOnboarding: boolean
  // Geolocation
  userLocation: UserLocation | null
  isLocationLoading: boolean
  locationError: string | null
  requestUserLocation: () => Promise<UserLocation | null>
  // Auth methods
  signInWithEmail: (email: string, password: string) => Promise<{ error: AuthError | null }>
  signUpWithEmail: (email: string, password: string) => Promise<{ error: AuthError | null }>
  signInWithGoogle: () => Promise<{ error: AuthError | null }>
  signOut: () => Promise<void>
  // Profile methods
  refreshPatientProfile: () => Promise<void>
  updatePatientProfile: (data: Partial<PatientData>) => Promise<{ error: Error | null }>
  createPatientProfile: (data: Omit<PatientData, 'id' | 'user_id' | 'created_at' | 'updated_at'>) => Promise<{ error: Error | null }>
  // Preferences methods
  refreshUserPreferences: () => Promise<void>
  updateUserPreferences: (data: Partial<UserPreferences>) => Promise<{ error: Error | null }>
  // Chat history methods
  fetchUserEncounters: () => Promise<PatientEncounter[]>
  fetchEncounterMessages: (encounterId: string) => Promise<EncounterMessage[]>
  createEncounter: (chiefComplaint?: string) => Promise<PatientEncounter | null>
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [session, setSession] = useState<Session | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [patientProfile, setPatientProfile] = useState<PatientData | null>(null)
  const [userPreferences, setUserPreferences] = useState<UserPreferences | null>(null)
  
  // Geolocation state
  const [userLocation, setUserLocation] = useState<UserLocation | null>(null)
  const [isLocationLoading, setIsLocationLoading] = useState(false)
  const [locationError, setLocationError] = useState<string | null>(null)

  // Handle case when Supabase is not configured
  const supabase = isSupabaseConfigured ? getSupabaseClient() : null

  // Check if user has completed onboarding (has patient profile)
  const hasCompletedOnboarding = !!patientProfile

  // Fetch patient profile
  const refreshPatientProfile = useCallback(async () => {
    if (!user || !supabase) {
      setPatientProfile(null)
      return
    }

    try {
      const { data, error } = await supabase
        .from('Patient Data')
        .select('*')
        .eq('user_id', user.id)
        .single()

      // Supabase returns error code PGRST116 when no row exists; treat that as "not onboarded".
      if (error) {
        if (error.code && error.code !== 'PGRST116') {
          console.error('Error fetching patient profile:', error)
        }
        if (!error.code) {
          // Unknown error shape; avoid noisy logging but reset profile.
          console.warn('Patient profile fetch returned unexpected error shape; treating as empty.')
        }
      }
      setPatientProfile(data || null)
    } catch (err) {
      console.error('Error fetching patient profile:', err)
      setPatientProfile(null)
    }
  }, [user, supabase])

  // Default preferences for new users
  const defaultPreferences = {
    theme: 'system',
    language: 'en',
    notifications_enabled: true,
    email_notifications: true,
    sms_notifications: false,
    timezone: 'Asia/Kuala_Lumpur',
  }

  // Fetch user preferences (creates defaults if not exists)
  const refreshUserPreferences = useCallback(async () => {
    if (!user || !supabase) {
      setUserPreferences(null)
      return
    }

    try {
      // Try to fetch existing preferences
      const { data, error } = await supabase
        .from('User Preferences')
        .select('*')
        .eq('user_id', user.id)
        .single()

      if (error && error.code === 'PGRST116') {
        // No preferences found - create default preferences for new user
        console.log('Creating default preferences for new user')
        const { data: newData, error: insertError } = await supabase
          .from('User Preferences')
          .insert({
            user_id: user.id,
            ...defaultPreferences,
          })
          .select()
          .single()

        if (insertError) {
          console.error('Error creating default preferences:', insertError)
          setUserPreferences(null)
        } else {
          setUserPreferences(newData)
        }
      } else if (error) {
        if (error.code) {
          console.error('Error fetching user preferences:', error)
        } else {
          console.warn('User preferences fetch returned unexpected error shape; treating as empty.')
        }
        setUserPreferences(null)
      } else {
        setUserPreferences(data)
      }
    } catch (err) {
      console.error('Error fetching user preferences:', err)
      setUserPreferences(null)
    }
  }, [user, supabase])

  // Initialize auth state
  useEffect(() => {
    if (!supabase) {
      // Supabase not configured - skip auth initialization
      setIsLoading(false)
      return
    }

    // Use getSession() which reads from cookies (fast, local) instead of getUser() which makes network request
    const initAuth = async () => {
      try {
        // Use getSession() which is fast (reads from cookies/localStorage)
        // The onAuthStateChange listener will handle updates
        const { data: { session }, error } = await supabase.auth.getSession()

        if (error) {
          console.log('No active session:', error.message)
          setUser(null)
          setSession(null)
        } else {
          setSession(session)
          setUser(session?.user ?? null)
        }
      } catch (err) {
        console.error('Error initializing auth:', err)
        setUser(null)
        setSession(null)
      } finally {
        setIsLoading(false)
      }
    }

    initAuth()

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event: AuthChangeEvent, session: Session | null) => {
        console.log('Auth state changed:', event, session?.user?.email)
        setSession(session)
        setUser(session?.user ?? null)
      }
    )

    return () => subscription.unsubscribe()
  }, [supabase])

  // Fetch profile data when user changes
  useEffect(() => {
    if (user) {
      refreshPatientProfile()
      refreshUserPreferences()
    } else {
      setPatientProfile(null)
      setUserPreferences(null)
    }
  }, [user, refreshPatientProfile, refreshUserPreferences])

  // Auth methods
  const signInWithEmail = async (email: string, password: string) => {
    if (!supabase) {
      return { error: { message: 'Supabase not configured' } as AuthError }
    }
    const { error } = await supabase.auth.signInWithPassword({ email, password })
    return { error }
  }

  const signUpWithEmail = async (email: string, password: string) => {
    if (!supabase) {
      return { error: { message: 'Supabase not configured' } as AuthError }
    }
    const { error } = await supabase.auth.signUp({ email, password })
    return { error }
  }

  const signInWithGoogle = async () => {
    if (!supabase) {
      return { error: { message: 'Supabase not configured' } as AuthError }
    }
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
      },
    })
    return { error }
  }

  const signOut = async () => {
    if (supabase) {
      await supabase.auth.signOut()
    }
    setPatientProfile(null)
    setUserPreferences(null)
  }

  // Profile methods
  const createPatientProfile = async (
    data: Omit<PatientData, 'id' | 'user_id' | 'created_at' | 'updated_at'>
  ) => {
    if (!user) return { error: new Error('Not authenticated') }
    if (!supabase) return { error: new Error('Supabase not configured') }

    try {
      const { error } = await supabase
        .from('Patient Data')
        .insert({
          ...data,
          user_id: user.id,
        })

      if (error) throw error
      await refreshPatientProfile()
      return { error: null }
    } catch (err) {
      return { error: err as Error }
    }
  }

  const updatePatientProfile = async (data: Partial<PatientData>) => {
    if (!user || !patientProfile) return { error: new Error('Not authenticated or no profile') }
    if (!supabase) return { error: new Error('Supabase not configured') }

    try {
      const { error } = await supabase
        .from('Patient Data')
        .update(data)
        .eq('id', patientProfile.id)

      if (error) throw error
      await refreshPatientProfile()
      return { error: null }
    } catch (err) {
      return { error: err as Error }
    }
  }

  // Preferences methods - only updates when user explicitly changes settings
  const updateUserPreferences = async (data: Partial<UserPreferences>) => {
    if (!user) return { error: new Error('Not authenticated') }
    if (!supabase) return { error: new Error('Supabase not configured') }

    try {
      // Preferences are auto-created on login, so we always update
      const { error } = await supabase
        .from('User Preferences')
        .update(data)
        .eq('user_id', user.id)
      
      if (error) throw error
      await refreshUserPreferences()
      return { error: null }
    } catch (err) {
      return { error: err as Error }
    }
  }

  // Chat history methods
  const fetchUserEncounters = useCallback(async (): Promise<PatientEncounter[]> => {
    if (!patientProfile || !supabase) {
      return []
    }

    try {
      // Fetch encounters that belong to this patient OR have NULL patient_id (legacy encounters)
      // First, get encounters with matching patient_id
      const { data: ownedEncounters, error: ownedError } = await supabase
        .from('Patient Encounters')
        .select('*')
        .eq('patient_id', patientProfile.id)
        .order('created_at', { ascending: false })

      // Also get encounters with NULL patient_id (created before patient linking was implemented)
      const { data: orphanEncounters, error: orphanError } = await supabase
        .from('Patient Encounters')
        .select('*')
        .is('patient_id', null)
        .order('created_at', { ascending: false })

      if (ownedError) {
        console.error('Error fetching owned encounters:', ownedError)
      }
      if (orphanError) {
        console.error('Error fetching orphan encounters:', orphanError)
      }

      // Migrate orphan encounters to this patient (one-time fix)
      if (orphanEncounters && orphanEncounters.length > 0) {
        // Update orphan encounters to belong to this patient
        for (const encounter of orphanEncounters) {
          await supabase
            .from('Patient Encounters')
            .update({ patient_id: patientProfile.id })
            .eq('id', encounter.id)
        }
      }

      // Combine both sets, removing duplicates
      const allEncounters = [...(ownedEncounters || []), ...(orphanEncounters || [])]
      const uniqueEncounters = allEncounters.filter((encounter, index, self) =>
        index === self.findIndex((e) => e.id === encounter.id)
      )

      // Sort by created_at descending
      uniqueEncounters.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())

      return uniqueEncounters
    } catch (err) {
      console.error('Error fetching encounters:', err)
      return []
    }
  }, [patientProfile, supabase])

  const fetchEncounterMessages = useCallback(async (encounterId: string): Promise<EncounterMessage[]> => {
    if (!supabase) {
      return []
    }

    try {
      const { data, error } = await supabase
        .from('Encounter Messages')
        .select('*')
        .eq('encounter_id', encounterId)
        .order('created_at', { ascending: true })

      if (error) {
        console.error('Error fetching messages:', error)
        return []
      }

      return data || []
    } catch (err) {
      console.error('Error fetching messages:', err)
      return []
    }
  }, [supabase])

  const createEncounter = useCallback(async (chiefComplaint?: string): Promise<PatientEncounter | null> => {
    if (!patientProfile || !supabase) {
      return null
    }

    try {
      const { data, error } = await supabase
        .from('Patient Encounters')
        .insert({
          patient_id: patientProfile.id,
          encounter_type: 'chat',
          chief_complaint: chiefComplaint || 'Chat session',
          status: 'active',
        })
        .select()
        .single()

      if (error) {
        console.error('Error creating encounter:', error)
        return null
      }

      return data
    } catch (err) {
      console.error('Error creating encounter:', err)
      return null
    }
  }, [patientProfile, supabase])

  // Request user's geolocation using browser API
  const requestUserLocation = useCallback(async (): Promise<UserLocation | null> => {
    // Return cached location if available
    if (userLocation) {
      return userLocation
    }

    // Check if geolocation is supported
    if (!navigator.geolocation) {
      setLocationError('Geolocation is not supported by your browser')
      return null
    }

    setIsLocationLoading(true)
    setLocationError(null)

    return new Promise((resolve) => {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const location: UserLocation = {
            lat: position.coords.latitude,
            lng: position.coords.longitude,
          }
          setUserLocation(location)
          setIsLocationLoading(false)
          console.log('[Geolocation] User location obtained:', location)
          resolve(location)
        },
        (error) => {
          let errorMessage = 'Failed to get location'
          switch (error.code) {
            case error.PERMISSION_DENIED:
              errorMessage = 'Location permission denied. Please enable location access in your browser settings.'
              break
            case error.POSITION_UNAVAILABLE:
              errorMessage = 'Location information is unavailable.'
              break
            case error.TIMEOUT:
              errorMessage = 'Location request timed out.'
              break
          }
          setLocationError(errorMessage)
          setIsLocationLoading(false)
          console.warn('[Geolocation] Error:', errorMessage)
          resolve(null)
        },
        {
          enableHighAccuracy: true,
          timeout: 10000,
          maximumAge: 300000, // Cache for 5 minutes
        }
      )
    })
  }, [userLocation])

  // Auto-request location when user logs in and completes onboarding
  useEffect(() => {
    if (user && hasCompletedOnboarding && !userLocation && !isLocationLoading) {
      // Request location after a short delay to not block the UI
      const timer = setTimeout(() => {
        requestUserLocation()
      }, 1000)
      return () => clearTimeout(timer)
    }
  }, [user, hasCompletedOnboarding, userLocation, isLocationLoading, requestUserLocation])

  return (
    <AuthContext.Provider
      value={{
        user,
        session,
        isLoading,
        patientProfile,
        userPreferences,
        hasCompletedOnboarding,
        // Geolocation
        userLocation,
        isLocationLoading,
        locationError,
        requestUserLocation,
        // Auth methods
        signInWithEmail,
        signUpWithEmail,
        signInWithGoogle,
        signOut,
        refreshPatientProfile,
        updatePatientProfile,
        createPatientProfile,
        refreshUserPreferences,
        updateUserPreferences,
        fetchUserEncounters,
        fetchEncounterMessages,
        createEncounter,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
