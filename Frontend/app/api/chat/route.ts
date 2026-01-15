import { NextResponse } from "next/server"

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
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 })
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

  // Extract patient_id for LTM and data consistency
  const patientId =
    typeof (body as any)?.patientId === "string"
      ? (body as any).patientId
      : typeof (body as any)?.patient_id === "string"
        ? (body as any).patient_id
        : undefined

  // Extract user coordinates for location-based features (clinic recommendations)
  const userCoordinates = (body as any)?.userCoordinates
  const validCoordinates =
    userCoordinates &&
      typeof userCoordinates.lat === "number" &&
      typeof userCoordinates.lng === "number"
      ? [userCoordinates.lat, userCoordinates.lng] as [number, number]
      : undefined

  if (!message.trim()) {
    return NextResponse.json({ error: "Missing 'message' in request body" }, { status: 400 })
  }
  if (!sessionId.trim()) {
    return NextResponse.json({ error: "Missing 'sessionId' in request body" }, { status: 400 })
  }

  const backendBaseUrl = getBackendBaseUrl()

  try {
    const upstream = await fetch(`${backendBaseUrl}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        input: message,
        session_id: sessionId,
        encounter_id: encounterId || undefined,
        patient_id: patientId || undefined, // Forward patient_id for LTM and data consistency
        user_coordinates: validCoordinates,
      }),
      signal: req.signal,
    })

    const data = await upstream.json().catch(() => ({}))

    if (!upstream.ok) {
      return NextResponse.json(
        { error: (data as any)?.detail || (data as any)?.error || "Backend request failed" },
        { status: upstream.status },
      )
    }

    const replies: string[] = Array.isArray((data as any)?.messages) ? (data as any).messages.map(String) : []

    // Keep the shape the UI expects: { messages: string[] }
    return NextResponse.json(
      {
        messages: replies,
        // Pass through extra context for future UI improvements (safe if unused)
        route: (data as any)?.route,
        execution_plan: (data as any)?.execution_plan,
        executed_agents: (data as any)?.executed_agents,
        patient_context: (data as any)?.patient_context,
      },
      { status: 200 },
    )
  } catch (err: any) {
    return NextResponse.json(
      {
        error:
          err?.name === "AbortError"
            ? "Request aborted"
            : `Failed to reach backend at ${backendBaseUrl} (is it running on port 8000?)`,
      },
      { status: 502 },
    )
  }
}
