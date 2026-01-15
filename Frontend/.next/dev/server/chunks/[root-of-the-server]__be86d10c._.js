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
"[externals]/next/dist/server/app-render/after-task-async-storage.external.js [external] (next/dist/server/app-render/after-task-async-storage.external.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/server/app-render/after-task-async-storage.external.js", () => require("next/dist/server/app-render/after-task-async-storage.external.js"));

module.exports = mod;
}),
"[project]/Agentic-AI-Healthcare/Frontend/app/api/chat/route.ts [app-route] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "POST",
    ()=>POST
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$Agentic$2d$AI$2d$Healthcare$2f$Frontend$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$0$2e$7_$40$opentelemetry$2b$api$40$1$2e$9$2e$0_react$2d$dom$40$19$2e$2$2e$0_react$40$19$2e$2$2e$0_$5f$react$40$19$2e$2$2e$0$2f$node_modules$2f$next$2f$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/Agentic-AI-Healthcare/Frontend/node_modules/.pnpm/next@16.0.7_@opentelemetry+api@1.9.0_react-dom@19.2.0_react@19.2.0__react@19.2.0/node_modules/next/server.js [app-route] (ecmascript)");
;
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
        return __TURBOPACK__imported__module__$5b$project$5d2f$Agentic$2d$AI$2d$Healthcare$2f$Frontend$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$0$2e$7_$40$opentelemetry$2b$api$40$1$2e$9$2e$0_react$2d$dom$40$19$2e$2$2e$0_react$40$19$2e$2$2e$0_$5f$react$40$19$2e$2$2e$0$2f$node_modules$2f$next$2f$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["NextResponse"].json({
            error: "Invalid JSON body"
        }, {
            status: 400
        });
    }
    const message = typeof body?.message === "string" ? body.message : "";
    const sessionId = typeof body?.sessionId === "string" ? body.sessionId : typeof body?.session_id === "string" ? body.session_id : "";
    const encounterId = typeof body?.encounterId === "string" ? body.encounterId : typeof body?.encounter_id === "string" ? body.encounter_id : undefined;
    // Extract user coordinates for location-based features (clinic recommendations)
    const userCoordinates = body?.userCoordinates;
    const validCoordinates = userCoordinates && typeof userCoordinates.lat === "number" && typeof userCoordinates.lng === "number" ? [
        userCoordinates.lat,
        userCoordinates.lng
    ] : undefined;
    if (!message.trim()) {
        return __TURBOPACK__imported__module__$5b$project$5d2f$Agentic$2d$AI$2d$Healthcare$2f$Frontend$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$0$2e$7_$40$opentelemetry$2b$api$40$1$2e$9$2e$0_react$2d$dom$40$19$2e$2$2e$0_react$40$19$2e$2$2e$0_$5f$react$40$19$2e$2$2e$0$2f$node_modules$2f$next$2f$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["NextResponse"].json({
            error: "Missing 'message' in request body"
        }, {
            status: 400
        });
    }
    if (!sessionId.trim()) {
        return __TURBOPACK__imported__module__$5b$project$5d2f$Agentic$2d$AI$2d$Healthcare$2f$Frontend$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$0$2e$7_$40$opentelemetry$2b$api$40$1$2e$9$2e$0_react$2d$dom$40$19$2e$2$2e$0_react$40$19$2e$2$2e$0_$5f$react$40$19$2e$2$2e$0$2f$node_modules$2f$next$2f$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["NextResponse"].json({
            error: "Missing 'sessionId' in request body"
        }, {
            status: 400
        });
    }
    const backendBaseUrl = getBackendBaseUrl();
    try {
        const upstream = await fetch(`${backendBaseUrl}/chat`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                input: message,
                session_id: sessionId,
                encounter_id: encounterId || undefined,
                user_coordinates: validCoordinates
            }),
            signal: req.signal
        });
        const data = await upstream.json().catch(()=>({}));
        if (!upstream.ok) {
            return __TURBOPACK__imported__module__$5b$project$5d2f$Agentic$2d$AI$2d$Healthcare$2f$Frontend$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$0$2e$7_$40$opentelemetry$2b$api$40$1$2e$9$2e$0_react$2d$dom$40$19$2e$2$2e$0_react$40$19$2e$2$2e$0_$5f$react$40$19$2e$2$2e$0$2f$node_modules$2f$next$2f$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["NextResponse"].json({
                error: data?.detail || data?.error || "Backend request failed"
            }, {
                status: upstream.status
            });
        }
        const replies = Array.isArray(data?.messages) ? data.messages.map(String) : [];
        // Keep the shape the UI expects: { messages: string[] }
        return __TURBOPACK__imported__module__$5b$project$5d2f$Agentic$2d$AI$2d$Healthcare$2f$Frontend$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$0$2e$7_$40$opentelemetry$2b$api$40$1$2e$9$2e$0_react$2d$dom$40$19$2e$2$2e$0_react$40$19$2e$2$2e$0_$5f$react$40$19$2e$2$2e$0$2f$node_modules$2f$next$2f$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["NextResponse"].json({
            messages: replies,
            // Pass through extra context for future UI improvements (safe if unused)
            route: data?.route,
            execution_plan: data?.execution_plan,
            executed_agents: data?.executed_agents,
            patient_context: data?.patient_context
        }, {
            status: 200
        });
    } catch (err) {
        return __TURBOPACK__imported__module__$5b$project$5d2f$Agentic$2d$AI$2d$Healthcare$2f$Frontend$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$0$2e$7_$40$opentelemetry$2b$api$40$1$2e$9$2e$0_react$2d$dom$40$19$2e$2$2e$0_react$40$19$2e$2$2e$0_$5f$react$40$19$2e$2$2e$0$2f$node_modules$2f$next$2f$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["NextResponse"].json({
            error: err?.name === "AbortError" ? "Request aborted" : `Failed to reach backend at ${backendBaseUrl} (is it running on port 8000?)`
        }, {
            status: 502
        });
    }
}
}),
];

//# sourceMappingURL=%5Broot-of-the-server%5D__be86d10c._.js.map