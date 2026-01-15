(globalThis.TURBOPACK || (globalThis.TURBOPACK = [])).push([typeof document === "object" ? document.currentScript : undefined,
"[project]/lib/supabase.ts [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "BLOOD_TYPES",
    ()=>BLOOD_TYPES,
    "GENDERS",
    ()=>GENDERS,
    "MALAYSIAN_STATES",
    ()=>MALAYSIAN_STATES,
    "createClient",
    ()=>createClient,
    "getSupabaseClient",
    ()=>getSupabaseClient,
    "isSupabaseConfigured",
    ()=>isSupabaseConfigured
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$0$2e$7_$40$opentelemetry$2b$api$40$1$2e$9$2e$0_react$2d$dom$40$19$2e$2$2e$0_react$40$19$2e$2$2e$0_$5f$react$40$19$2e$2$2e$0$2f$node_modules$2f$next$2f$dist$2f$build$2f$polyfills$2f$process$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = /*#__PURE__*/ __turbopack_context__.i("[project]/node_modules/.pnpm/next@16.0.7_@opentelemetry+api@1.9.0_react-dom@19.2.0_react@19.2.0__react@19.2.0/node_modules/next/dist/build/polyfills/process.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f2e$pnpm$2f40$supabase$2b$ssr$40$0$2e$8$2e$0_$40$supabase$2b$supabase$2d$js$40$2$2e$87$2e$3$2f$node_modules$2f40$supabase$2f$ssr$2f$dist$2f$module$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$locals$3e$__ = __turbopack_context__.i("[project]/node_modules/.pnpm/@supabase+ssr@0.8.0_@supabase+supabase-js@2.87.3/node_modules/@supabase/ssr/dist/module/index.js [app-client] (ecmascript) <locals>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f2e$pnpm$2f40$supabase$2b$ssr$40$0$2e$8$2e$0_$40$supabase$2b$supabase$2d$js$40$2$2e$87$2e$3$2f$node_modules$2f40$supabase$2f$ssr$2f$dist$2f$module$2f$createBrowserClient$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/.pnpm/@supabase+ssr@0.8.0_@supabase+supabase-js@2.87.3/node_modules/@supabase/ssr/dist/module/createBrowserClient.js [app-client] (ecmascript)");
;
// Check if Supabase is configured
const supabaseUrl = ("TURBOPACK compile-time value", "https://avwwjppetdhzjccdydfr.supabase.co");
const supabaseAnonKey = ("TURBOPACK compile-time value", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImF2d3dqcHBldGRoempjY2R5ZGZyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjU4ODk0MzgsImV4cCI6MjA4MTQ2NTQzOH0.wueW3n6mykDQbWWEIdUGuvZ3kyd6ur-ThHKO-QHyJrA");
const isSupabaseConfigured = !!(supabaseUrl && supabaseAnonKey);
function createClient() {
    if ("TURBOPACK compile-time falsy", 0) //TURBOPACK unreachable
    ;
    return (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f2e$pnpm$2f40$supabase$2b$ssr$40$0$2e$8$2e$0_$40$supabase$2b$supabase$2d$js$40$2$2e$87$2e$3$2f$node_modules$2f40$supabase$2f$ssr$2f$dist$2f$module$2f$createBrowserClient$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["createBrowserClient"])(supabaseUrl, supabaseAnonKey);
}
// Singleton instance for client-side
let browserClient = null;
function getSupabaseClient() {
    if ("TURBOPACK compile-time falsy", 0) //TURBOPACK unreachable
    ;
    if ("TURBOPACK compile-time falsy", 0) //TURBOPACK unreachable
    ;
    // Client-side: reuse existing client
    if (!browserClient) {
        browserClient = createClient();
    }
    return browserClient;
}
const MALAYSIAN_STATES = [
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
    'Terengganu'
];
const BLOOD_TYPES = [
    'A+',
    'A-',
    'B+',
    'B-',
    'AB+',
    'AB-',
    'O+',
    'O-',
    'Unknown'
];
const GENDERS = [
    'Male',
    'Female',
    'Other'
];
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/lib/auth-context.tsx [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "AuthProvider",
    ()=>AuthProvider,
    "useAuth",
    ()=>useAuth
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$0$2e$7_$40$opentelemetry$2b$api$40$1$2e$9$2e$0_react$2d$dom$40$19$2e$2$2e$0_react$40$19$2e$2$2e$0_$5f$react$40$19$2e$2$2e$0$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/.pnpm/next@16.0.7_@opentelemetry+api@1.9.0_react-dom@19.2.0_react@19.2.0__react@19.2.0/node_modules/next/dist/compiled/react/jsx-dev-runtime.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$0$2e$7_$40$opentelemetry$2b$api$40$1$2e$9$2e$0_react$2d$dom$40$19$2e$2$2e$0_react$40$19$2e$2$2e$0_$5f$react$40$19$2e$2$2e$0$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/.pnpm/next@16.0.7_@opentelemetry+api@1.9.0_react-dom@19.2.0_react@19.2.0__react@19.2.0/node_modules/next/dist/compiled/react/index.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$supabase$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/lib/supabase.ts [app-client] (ecmascript)");
;
var _s = __turbopack_context__.k.signature(), _s1 = __turbopack_context__.k.signature();
"use client";
;
;
const AuthContext = /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$0$2e$7_$40$opentelemetry$2b$api$40$1$2e$9$2e$0_react$2d$dom$40$19$2e$2$2e$0_react$40$19$2e$2$2e$0_$5f$react$40$19$2e$2$2e$0$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["createContext"])(null);
function AuthProvider({ children }) {
    _s();
    const [user, setUser] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$0$2e$7_$40$opentelemetry$2b$api$40$1$2e$9$2e$0_react$2d$dom$40$19$2e$2$2e$0_react$40$19$2e$2$2e$0_$5f$react$40$19$2e$2$2e$0$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    const [session, setSession] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$0$2e$7_$40$opentelemetry$2b$api$40$1$2e$9$2e$0_react$2d$dom$40$19$2e$2$2e$0_react$40$19$2e$2$2e$0_$5f$react$40$19$2e$2$2e$0$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    const [isLoading, setIsLoading] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$0$2e$7_$40$opentelemetry$2b$api$40$1$2e$9$2e$0_react$2d$dom$40$19$2e$2$2e$0_react$40$19$2e$2$2e$0_$5f$react$40$19$2e$2$2e$0$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(true);
    const [patientProfile, setPatientProfile] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$0$2e$7_$40$opentelemetry$2b$api$40$1$2e$9$2e$0_react$2d$dom$40$19$2e$2$2e$0_react$40$19$2e$2$2e$0_$5f$react$40$19$2e$2$2e$0$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    const [userPreferences, setUserPreferences] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$0$2e$7_$40$opentelemetry$2b$api$40$1$2e$9$2e$0_react$2d$dom$40$19$2e$2$2e$0_react$40$19$2e$2$2e$0_$5f$react$40$19$2e$2$2e$0$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    // Geolocation state
    const [userLocation, setUserLocation] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$0$2e$7_$40$opentelemetry$2b$api$40$1$2e$9$2e$0_react$2d$dom$40$19$2e$2$2e$0_react$40$19$2e$2$2e$0_$5f$react$40$19$2e$2$2e$0$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    const [isLocationLoading, setIsLocationLoading] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$0$2e$7_$40$opentelemetry$2b$api$40$1$2e$9$2e$0_react$2d$dom$40$19$2e$2$2e$0_react$40$19$2e$2$2e$0_$5f$react$40$19$2e$2$2e$0$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(false);
    const [locationError, setLocationError] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$0$2e$7_$40$opentelemetry$2b$api$40$1$2e$9$2e$0_react$2d$dom$40$19$2e$2$2e$0_react$40$19$2e$2$2e$0_$5f$react$40$19$2e$2$2e$0$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    // Handle case when Supabase is not configured
    const supabase = __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$supabase$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["isSupabaseConfigured"] ? (0, __TURBOPACK__imported__module__$5b$project$5d2f$lib$2f$supabase$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["getSupabaseClient"])() : null;
    // Check if user has completed onboarding (has patient profile)
    const hasCompletedOnboarding = !!patientProfile;
    // Fetch patient profile
    const refreshPatientProfile = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$0$2e$7_$40$opentelemetry$2b$api$40$1$2e$9$2e$0_react$2d$dom$40$19$2e$2$2e$0_react$40$19$2e$2$2e$0_$5f$react$40$19$2e$2$2e$0$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useCallback"])({
        "AuthProvider.useCallback[refreshPatientProfile]": async ()=>{
            if (!user || !supabase) {
                setPatientProfile(null);
                return;
            }
            try {
                const { data, error } = await supabase.from('Patient Data').select('*').eq('user_id', user.id).single();
                if (error && error.code !== 'PGRST116') {
                    console.error('Error fetching patient profile:', error);
                }
                setPatientProfile(data || null);
            } catch (err) {
                console.error('Error fetching patient profile:', err);
                setPatientProfile(null);
            }
        }
    }["AuthProvider.useCallback[refreshPatientProfile]"], [
        user,
        supabase
    ]);
    // Default preferences for new users
    const defaultPreferences = {
        theme: 'system',
        language: 'en',
        notifications_enabled: true,
        email_notifications: true,
        sms_notifications: false,
        timezone: 'Asia/Kuala_Lumpur'
    };
    // Fetch user preferences (creates defaults if not exists)
    const refreshUserPreferences = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$0$2e$7_$40$opentelemetry$2b$api$40$1$2e$9$2e$0_react$2d$dom$40$19$2e$2$2e$0_react$40$19$2e$2$2e$0_$5f$react$40$19$2e$2$2e$0$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useCallback"])({
        "AuthProvider.useCallback[refreshUserPreferences]": async ()=>{
            if (!user || !supabase) {
                setUserPreferences(null);
                return;
            }
            try {
                // Try to fetch existing preferences
                const { data, error } = await supabase.from('User Preferences').select('*').eq('user_id', user.id).single();
                if (error && error.code === 'PGRST116') {
                    // No preferences found - create default preferences for new user
                    console.log('Creating default preferences for new user');
                    const { data: newData, error: insertError } = await supabase.from('User Preferences').insert({
                        user_id: user.id,
                        ...defaultPreferences
                    }).select().single();
                    if (insertError) {
                        console.error('Error creating default preferences:', insertError);
                        setUserPreferences(null);
                    } else {
                        setUserPreferences(newData);
                    }
                } else if (error) {
                    console.error('Error fetching user preferences:', error);
                    setUserPreferences(null);
                } else {
                    setUserPreferences(data);
                }
            } catch (err) {
                console.error('Error fetching user preferences:', err);
                setUserPreferences(null);
            }
        }
    }["AuthProvider.useCallback[refreshUserPreferences]"], [
        user,
        supabase
    ]);
    // Initialize auth state
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$0$2e$7_$40$opentelemetry$2b$api$40$1$2e$9$2e$0_react$2d$dom$40$19$2e$2$2e$0_react$40$19$2e$2$2e$0_$5f$react$40$19$2e$2$2e$0$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useEffect"])({
        "AuthProvider.useEffect": ()=>{
            if (!supabase) {
                // Supabase not configured - skip auth initialization
                setIsLoading(false);
                return;
            }
            // Use getSession() which reads from cookies (fast, local) instead of getUser() which makes network request
            const initAuth = {
                "AuthProvider.useEffect.initAuth": async ()=>{
                    try {
                        // Use getSession() which is fast (reads from cookies/localStorage)
                        // The onAuthStateChange listener will handle updates
                        const { data: { session }, error } = await supabase.auth.getSession();
                        if (error) {
                            console.log('No active session:', error.message);
                            setUser(null);
                            setSession(null);
                        } else {
                            setSession(session);
                            setUser(session?.user ?? null);
                        }
                    } catch (err) {
                        console.error('Error initializing auth:', err);
                        setUser(null);
                        setSession(null);
                    } finally{
                        setIsLoading(false);
                    }
                }
            }["AuthProvider.useEffect.initAuth"];
            initAuth();
            // Listen for auth changes
            const { data: { subscription } } = supabase.auth.onAuthStateChange({
                "AuthProvider.useEffect": async (event, session)=>{
                    console.log('Auth state changed:', event, session?.user?.email);
                    setSession(session);
                    setUser(session?.user ?? null);
                }
            }["AuthProvider.useEffect"]);
            return ({
                "AuthProvider.useEffect": ()=>subscription.unsubscribe()
            })["AuthProvider.useEffect"];
        }
    }["AuthProvider.useEffect"], [
        supabase
    ]);
    // Fetch profile data when user changes
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$0$2e$7_$40$opentelemetry$2b$api$40$1$2e$9$2e$0_react$2d$dom$40$19$2e$2$2e$0_react$40$19$2e$2$2e$0_$5f$react$40$19$2e$2$2e$0$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useEffect"])({
        "AuthProvider.useEffect": ()=>{
            if (user) {
                refreshPatientProfile();
                refreshUserPreferences();
            } else {
                setPatientProfile(null);
                setUserPreferences(null);
            }
        }
    }["AuthProvider.useEffect"], [
        user,
        refreshPatientProfile,
        refreshUserPreferences
    ]);
    // Auth methods
    const signInWithEmail = async (email, password)=>{
        if (!supabase) {
            return {
                error: {
                    message: 'Supabase not configured'
                }
            };
        }
        const { error } = await supabase.auth.signInWithPassword({
            email,
            password
        });
        return {
            error
        };
    };
    const signUpWithEmail = async (email, password)=>{
        if (!supabase) {
            return {
                error: {
                    message: 'Supabase not configured'
                }
            };
        }
        const { error } = await supabase.auth.signUp({
            email,
            password
        });
        return {
            error
        };
    };
    const signInWithGoogle = async ()=>{
        if (!supabase) {
            return {
                error: {
                    message: 'Supabase not configured'
                }
            };
        }
        const { error } = await supabase.auth.signInWithOAuth({
            provider: 'google',
            options: {
                redirectTo: `${window.location.origin}/auth/callback`
            }
        });
        return {
            error
        };
    };
    const signOut = async ()=>{
        if (supabase) {
            await supabase.auth.signOut();
        }
        setPatientProfile(null);
        setUserPreferences(null);
    };
    // Profile methods
    const createPatientProfile = async (data)=>{
        if (!user) return {
            error: new Error('Not authenticated')
        };
        if (!supabase) return {
            error: new Error('Supabase not configured')
        };
        try {
            const { error } = await supabase.from('Patient Data').insert({
                ...data,
                user_id: user.id
            });
            if (error) throw error;
            await refreshPatientProfile();
            return {
                error: null
            };
        } catch (err) {
            return {
                error: err
            };
        }
    };
    const updatePatientProfile = async (data)=>{
        if (!user || !patientProfile) return {
            error: new Error('Not authenticated or no profile')
        };
        if (!supabase) return {
            error: new Error('Supabase not configured')
        };
        try {
            const { error } = await supabase.from('Patient Data').update(data).eq('id', patientProfile.id);
            if (error) throw error;
            await refreshPatientProfile();
            return {
                error: null
            };
        } catch (err) {
            return {
                error: err
            };
        }
    };
    // Preferences methods - only updates when user explicitly changes settings
    const updateUserPreferences = async (data)=>{
        if (!user) return {
            error: new Error('Not authenticated')
        };
        if (!supabase) return {
            error: new Error('Supabase not configured')
        };
        try {
            // Preferences are auto-created on login, so we always update
            const { error } = await supabase.from('User Preferences').update(data).eq('user_id', user.id);
            if (error) throw error;
            await refreshUserPreferences();
            return {
                error: null
            };
        } catch (err) {
            return {
                error: err
            };
        }
    };
    // Chat history methods
    const fetchUserEncounters = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$0$2e$7_$40$opentelemetry$2b$api$40$1$2e$9$2e$0_react$2d$dom$40$19$2e$2$2e$0_react$40$19$2e$2$2e$0_$5f$react$40$19$2e$2$2e$0$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useCallback"])({
        "AuthProvider.useCallback[fetchUserEncounters]": async ()=>{
            if (!patientProfile || !supabase) {
                return [];
            }
            try {
                // Fetch encounters that belong to this patient OR have NULL patient_id (legacy encounters)
                // First, get encounters with matching patient_id
                const { data: ownedEncounters, error: ownedError } = await supabase.from('Patient Encounters').select('*').eq('patient_id', patientProfile.id).order('created_at', {
                    ascending: false
                });
                // Also get encounters with NULL patient_id (created before patient linking was implemented)
                const { data: orphanEncounters, error: orphanError } = await supabase.from('Patient Encounters').select('*').is('patient_id', null).order('created_at', {
                    ascending: false
                });
                if (ownedError) {
                    console.error('Error fetching owned encounters:', ownedError);
                }
                if (orphanError) {
                    console.error('Error fetching orphan encounters:', orphanError);
                }
                // Migrate orphan encounters to this patient (one-time fix)
                if (orphanEncounters && orphanEncounters.length > 0) {
                    // Update orphan encounters to belong to this patient
                    for (const encounter of orphanEncounters){
                        await supabase.from('Patient Encounters').update({
                            patient_id: patientProfile.id
                        }).eq('id', encounter.id);
                    }
                }
                // Combine both sets, removing duplicates
                const allEncounters = [
                    ...ownedEncounters || [],
                    ...orphanEncounters || []
                ];
                const uniqueEncounters = allEncounters.filter({
                    "AuthProvider.useCallback[fetchUserEncounters].uniqueEncounters": (encounter, index, self)=>index === self.findIndex({
                            "AuthProvider.useCallback[fetchUserEncounters].uniqueEncounters": (e)=>e.id === encounter.id
                        }["AuthProvider.useCallback[fetchUserEncounters].uniqueEncounters"])
                }["AuthProvider.useCallback[fetchUserEncounters].uniqueEncounters"]);
                // Sort by created_at descending
                uniqueEncounters.sort({
                    "AuthProvider.useCallback[fetchUserEncounters]": (a, b)=>new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
                }["AuthProvider.useCallback[fetchUserEncounters]"]);
                return uniqueEncounters;
            } catch (err) {
                console.error('Error fetching encounters:', err);
                return [];
            }
        }
    }["AuthProvider.useCallback[fetchUserEncounters]"], [
        patientProfile,
        supabase
    ]);
    const fetchEncounterMessages = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$0$2e$7_$40$opentelemetry$2b$api$40$1$2e$9$2e$0_react$2d$dom$40$19$2e$2$2e$0_react$40$19$2e$2$2e$0_$5f$react$40$19$2e$2$2e$0$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useCallback"])({
        "AuthProvider.useCallback[fetchEncounterMessages]": async (encounterId)=>{
            if (!supabase) {
                return [];
            }
            try {
                const { data, error } = await supabase.from('Encounter Messages').select('*').eq('encounter_id', encounterId).order('created_at', {
                    ascending: true
                });
                if (error) {
                    console.error('Error fetching messages:', error);
                    return [];
                }
                return data || [];
            } catch (err) {
                console.error('Error fetching messages:', err);
                return [];
            }
        }
    }["AuthProvider.useCallback[fetchEncounterMessages]"], [
        supabase
    ]);
    const createEncounter = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$0$2e$7_$40$opentelemetry$2b$api$40$1$2e$9$2e$0_react$2d$dom$40$19$2e$2$2e$0_react$40$19$2e$2$2e$0_$5f$react$40$19$2e$2$2e$0$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useCallback"])({
        "AuthProvider.useCallback[createEncounter]": async (chiefComplaint)=>{
            if (!patientProfile || !supabase) {
                return null;
            }
            try {
                const { data, error } = await supabase.from('Patient Encounters').insert({
                    patient_id: patientProfile.id,
                    encounter_type: 'chat',
                    chief_complaint: chiefComplaint || 'Chat session',
                    status: 'active'
                }).select().single();
                if (error) {
                    console.error('Error creating encounter:', error);
                    return null;
                }
                return data;
            } catch (err) {
                console.error('Error creating encounter:', err);
                return null;
            }
        }
    }["AuthProvider.useCallback[createEncounter]"], [
        patientProfile,
        supabase
    ]);
    // Request user's geolocation using browser API
    const requestUserLocation = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$0$2e$7_$40$opentelemetry$2b$api$40$1$2e$9$2e$0_react$2d$dom$40$19$2e$2$2e$0_react$40$19$2e$2$2e$0_$5f$react$40$19$2e$2$2e$0$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useCallback"])({
        "AuthProvider.useCallback[requestUserLocation]": async ()=>{
            // Return cached location if available
            if (userLocation) {
                return userLocation;
            }
            // Check if geolocation is supported
            if (!navigator.geolocation) {
                setLocationError('Geolocation is not supported by your browser');
                return null;
            }
            setIsLocationLoading(true);
            setLocationError(null);
            return new Promise({
                "AuthProvider.useCallback[requestUserLocation]": (resolve)=>{
                    navigator.geolocation.getCurrentPosition({
                        "AuthProvider.useCallback[requestUserLocation]": (position)=>{
                            const location = {
                                lat: position.coords.latitude,
                                lng: position.coords.longitude
                            };
                            setUserLocation(location);
                            setIsLocationLoading(false);
                            console.log('[Geolocation] User location obtained:', location);
                            resolve(location);
                        }
                    }["AuthProvider.useCallback[requestUserLocation]"], {
                        "AuthProvider.useCallback[requestUserLocation]": (error)=>{
                            let errorMessage = 'Failed to get location';
                            switch(error.code){
                                case error.PERMISSION_DENIED:
                                    errorMessage = 'Location permission denied. Please enable location access in your browser settings.';
                                    break;
                                case error.POSITION_UNAVAILABLE:
                                    errorMessage = 'Location information is unavailable.';
                                    break;
                                case error.TIMEOUT:
                                    errorMessage = 'Location request timed out.';
                                    break;
                            }
                            setLocationError(errorMessage);
                            setIsLocationLoading(false);
                            console.warn('[Geolocation] Error:', errorMessage);
                            resolve(null);
                        }
                    }["AuthProvider.useCallback[requestUserLocation]"], {
                        enableHighAccuracy: true,
                        timeout: 10000,
                        maximumAge: 300000
                    });
                }
            }["AuthProvider.useCallback[requestUserLocation]"]);
        }
    }["AuthProvider.useCallback[requestUserLocation]"], [
        userLocation
    ]);
    // Auto-request location when user logs in and completes onboarding
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$0$2e$7_$40$opentelemetry$2b$api$40$1$2e$9$2e$0_react$2d$dom$40$19$2e$2$2e$0_react$40$19$2e$2$2e$0_$5f$react$40$19$2e$2$2e$0$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useEffect"])({
        "AuthProvider.useEffect": ()=>{
            if (user && hasCompletedOnboarding && !userLocation && !isLocationLoading) {
                // Request location after a short delay to not block the UI
                const timer = setTimeout({
                    "AuthProvider.useEffect.timer": ()=>{
                        requestUserLocation();
                    }
                }["AuthProvider.useEffect.timer"], 1000);
                return ({
                    "AuthProvider.useEffect": ()=>clearTimeout(timer)
                })["AuthProvider.useEffect"];
            }
        }
    }["AuthProvider.useEffect"], [
        user,
        hasCompletedOnboarding,
        userLocation,
        isLocationLoading,
        requestUserLocation
    ]);
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$0$2e$7_$40$opentelemetry$2b$api$40$1$2e$9$2e$0_react$2d$dom$40$19$2e$2$2e$0_react$40$19$2e$2$2e$0_$5f$react$40$19$2e$2$2e$0$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(AuthContext.Provider, {
        value: {
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
            createEncounter
        },
        children: children
    }, void 0, false, {
        fileName: "[project]/lib/auth-context.tsx",
        lineNumber: 474,
        columnNumber: 5
    }, this);
}
_s(AuthProvider, "UxkUvnW9NZPUgULL8tXiNg3JLYU=");
_c = AuthProvider;
function useAuth() {
    _s1();
    const context = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$0$2e$7_$40$opentelemetry$2b$api$40$1$2e$9$2e$0_react$2d$dom$40$19$2e$2$2e$0_react$40$19$2e$2$2e$0_$5f$react$40$19$2e$2$2e$0$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useContext"])(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}
_s1(useAuth, "b9L3QQ+jgeyIrH0NfHrJ8nn7VMU=");
var _c;
__turbopack_context__.k.register(_c, "AuthProvider");
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
]);

//# sourceMappingURL=lib_5f47735c._.js.map