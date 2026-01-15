const DEFAULT_BACKEND_URL = "http://127.0.0.1:8000"

function getBackendBaseUrl() {
    const url =
        process.env.BACKEND_URL ||
        process.env.NEXT_PUBLIC_BACKEND_URL ||
        process.env.NEXT_PUBLIC_API_URL ||
        DEFAULT_BACKEND_URL
    return url.replace(/\/+$/, "")
}

export async function POST(req: Request) {
    let body: unknown
    try {
        body = await req.json()
    } catch {
        return new Response(JSON.stringify({ error: "Invalid JSON body" }), { status: 400 })
    }

    const message = typeof (body as any)?.message === "string" ? (body as any).message : ""
    const sessionId =
        typeof (body as any)?.sessionId === "string"
            ? (body as any).sessionId
            : typeof (body as any)?.session_id === "string"
                ? (body as any).session_id
                : ""
    const encounterId =
        typeof (body as any)?.encounterId === "string"
            ? (body as any).encounterId
            : typeof (body as any)?.encounter_id === "string"
                ? (body as any).encounter_id
                : undefined

    const patientId =
        typeof (body as any)?.patientId === "string"
            ? (body as any).patientId
            : typeof (body as any)?.patient_id === "string"
                ? (body as any).patient_id
                : undefined

    const userCoordinates = (body as any)?.userCoordinates
    const validCoordinates =
        userCoordinates &&
            typeof userCoordinates.lat === "number" &&
            typeof userCoordinates.lng === "number"
            ? [userCoordinates.lat, userCoordinates.lng] as [number, number]
            : undefined

    if (!message.trim()) {
        return new Response(JSON.stringify({ error: "Missing 'message' in request body" }), { status: 400 })
    }
    if (!sessionId.trim()) {
        return new Response(JSON.stringify({ error: "Missing 'sessionId' in request body" }), { status: 400 })
    }

    const backendBaseUrl = getBackendBaseUrl()

    try {
        const upstream = await fetch(`${backendBaseUrl}/chat/stream`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                input: message,
                session_id: sessionId,
                encounter_id: encounterId || undefined,
                patient_id: patientId || undefined,
                user_coordinates: validCoordinates,
            }),
            signal: req.signal,
        })

        if (!upstream.ok) {
            const data = await upstream.json().catch(() => ({}))
            return new Response(
                JSON.stringify({ error: (data as any)?.detail || (data as any)?.error || "Backend request failed" }),
                { status: upstream.status }
            )
        }

        // Stream the SSE response from backend to frontend
        return new Response(upstream.body, {
            headers: {
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
            },
        })
    } catch (err: any) {
        return new Response(
            JSON.stringify({
                error:
                    err?.name === "AbortError"
                        ? "Request aborted"
                        : `Failed to reach backend at ${backendBaseUrl} (is it running on port 8000?)`,
            }),
            { status: 502 }
        )
    }
}
