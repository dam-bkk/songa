import { NextResponse } from "next/server";

export async function GET() {
  const cvApiUrl = (
    process.env.CV_API_URL ?? "http://localhost:8000"
  ).replace(/\/$/, "");

  let cvStatus: "ok" | "offline" = "offline";

  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 3000);

    const res = await fetch(`${cvApiUrl}/health`, {
      signal: controller.signal,
      cache: "no-store",
    });

    clearTimeout(timer);
    if (res.ok) cvStatus = "ok";
  } catch {
    // timeout or network error — stays "offline"
  }

  return NextResponse.json(
    { web: "ok", cv_api: cvStatus },
    {
      status: 200,
      headers: { "Cache-Control": "no-store" },
    },
  );
}
