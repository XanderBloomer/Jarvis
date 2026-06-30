import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  const { password } = (await request.json()) as { password: string };

  const adminPassword = process.env.ADMIN_PASSWORD;

  if (!adminPassword) {
    return NextResponse.json(
      { error: "Server auth not configured" },
      { status: 500 }
    );
  }

  if (password === adminPassword) {
    return NextResponse.json({ authenticated: true });
  }

  return NextResponse.json(
    { error: "Incorrect password" },
    { status: 401 }
  );
}
