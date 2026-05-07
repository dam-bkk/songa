// POST /api/demo
// Receives { name, email, club, role, message }
// Current: log + return { success: true }
// Structure ready for future email integration (Resend, Mailgun, etc.)

export async function POST(req: Request) {
  const body = await req.json() as {
    name?: string;
    email?: string;
    club?: string;
    role?: string;
    message?: string;
  };

  // Basic validation
  if (!body.name || !body.email || !body.club || !body.role) {
    return Response.json({ success: false, error: "Missing required fields" }, { status: 400 });
  }

  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(body.email)) {
    return Response.json({ success: false, error: "Invalid email format" }, { status: 400 });
  }

  // TODO: send email via Resend / Mailgun
  console.log("[/api/demo] New demo request:", {
    name: body.name,
    email: body.email,
    club: body.club,
    role: body.role,
    message: body.message ?? "",
    timestamp: new Date().toISOString(),
  });

  return Response.json({ success: true });
}
