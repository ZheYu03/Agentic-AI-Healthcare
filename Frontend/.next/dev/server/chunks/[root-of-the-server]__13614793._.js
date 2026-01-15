module.exports = [
"[externals]/next/dist/compiled/next-server/app-route-turbo.runtime.dev.js [external] (next/dist/compiled/next-server/app-route-turbo.runtime.dev.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/compiled/next-server/app-route-turbo.runtime.dev.js", () => require("next/dist/compiled/next-server/app-route-turbo.runtime.dev.js"));

module.exports = mod;
}),
"[externals]/next/dist/compiled/next-server/app-page-turbo.runtime.dev.js [external] (next/dist/compiled/next-server/app-page-turbo.runtime.dev.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/compiled/next-server/app-page-turbo.runtime.dev.js", () => require("next/dist/compiled/next-server/app-page-turbo.runtime.dev.js"));

module.exports = mod;
}),
"[externals]/next/dist/server/app-render/work-unit-async-storage.external.js [external] (next/dist/server/app-render/work-unit-async-storage.external.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/server/app-render/work-unit-async-storage.external.js", () => require("next/dist/server/app-render/work-unit-async-storage.external.js"));

module.exports = mod;
}),
"[externals]/next/dist/server/app-render/work-async-storage.external.js [external] (next/dist/server/app-render/work-async-storage.external.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/server/app-render/work-async-storage.external.js", () => require("next/dist/server/app-render/work-async-storage.external.js"));

module.exports = mod;
}),
"[externals]/next/dist/shared/lib/no-fallback-error.external.js [external] (next/dist/shared/lib/no-fallback-error.external.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/shared/lib/no-fallback-error.external.js", () => require("next/dist/shared/lib/no-fallback-error.external.js"));

module.exports = mod;
}),
"[project]/Langgraph/Frontend/app/api/chat/stream/route.ts [app-route] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "POST",
    ()=>POST
]);
const DEFAULT_BACKEND_URL = "http://127.0.0.1:8000";
function getBackendBaseUrl() {
    const url = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || DEFAULT_BACKEND_URL;
    return url.replace(/\/+$/, "");
}
async function POST(req) {
    let body;
    try {
        body = await req.json();
    } catch  {
        return new Response(JSON.stringify({
            error: "Invalid JSON body"
        }), {
            status: 400
        });
    }
    const message = typeof body?.message === "string" ? body.message : "";
    const sessionId = typeof body?.sessionId === "string" ? body.sessionId : typeof body?.session_id === "string" ? body.session_id : "";
    const encounterId = typeof body?.encounterId === "string" ? body.encounterId : typeof body?.encounter_id === "string" ? body.encounter_id : undefined;
    const patientId = typeof body?.patientId === "string" ? body.patientId : typeof body?.patient_id === "string" ? body.patient_id : undefined;
    const userCoordinates = body?.userCoordinates;
    const validCoordinates = userCoordinates && typeof userCoordinates.lat === "number" && typeof userCoordinates.lng === "number" ? [
        userCoordinates.lat,
        userCoordinates.lng
    ] : undefined;
    if (!message.trim()) {
        return new Response(JSON.stringify({
            error: "Missing 'message' in request body"
        }), {
            status: 400
        });
    }
    if (!sessionId.trim()) {
        return new Response(JSON.stringify({
            error: "Missing 'sessionId' in request body"
        }), {
            status: 400
        });
    }
    const backendBaseUrl = getBackendBaseUrl();
    try {
        const upstream = await fetch(`${backendBaseUrl}/chat/stream`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                input: message,
                session_id: sessionId,
                encounter_id: encounterId || undefined,
                patient_id: patientId || undefined,
                user_coordinates: validCoordinates
            }),
            signal: req.signal
        });
        if (!upstream.ok) {
            const data = await upstream.json().catch(()=>({}));
            return new Response(JSON.stringify({
                error: data?.detail || data?.error || "Backend request failed"
            }), {
                status: upstream.status
            });
        }
        // Stream the SSE response from backend to frontend
        return new Response(upstream.body, {
            headers: {
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive'
            }
        });
    } catch (err) {
        return new Response(JSON.stringify({
            error: err?.name === "AbortError" ? "Request aborted" : `Failed to reach backend at ${backendBaseUrl} (is it running on port 8000?)`
        }), {
            status: 502
        });
    }
}
}),
];

//# sourceMappingURL=%5Broot-of-the-server%5D__13614793._.js.map