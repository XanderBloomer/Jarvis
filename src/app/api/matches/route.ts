import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

// GET all matches for a season
export async function GET(request: NextRequest) {
  const season = request.nextUrl.searchParams.get("season") || "billiards-2026";

  const matches = await prisma.match.findMany({
    where: { season },
    include: {
      frames: {
        include: { player: true },
        orderBy: { frameNumber: "asc" },
      },
    },
    orderBy: { date: "desc" },
  });

  return NextResponse.json(matches);
}

// POST a new match with 5 frames
export async function POST(request: NextRequest) {
  const body = await request.json();

  const { date, opponent, season, frames } = body as {
    date: string;
    opponent: string;
    season: string;
    frames: {
      playerId: string;
      playerScore: number;
      opponentScore: number;
      highBreak: number | null;
      frameNumber: number;
    }[];
  };

  // Validation
  if (!date || !opponent || !frames || frames.length !== 5) {
    return NextResponse.json(
      { error: "A match requires a date, opponent, and exactly 5 frames" },
      { status: 400 }
    );
  }

  for (const frame of frames) {
    if (
      frame.playerScore < 0 ||
      frame.playerScore > 200 ||
      frame.opponentScore < 0 ||
      frame.opponentScore > 200
    ) {
      return NextResponse.json(
        { error: "Scores must be between 0 and 200" },
        { status: 400 }
      );
    }
    if (!frame.playerId) {
      return NextResponse.json(
        { error: "Each frame requires a player" },
        { status: 400 }
      );
    }
    if (frame.highBreak !== null && frame.highBreak !== undefined) {
      if (frame.highBreak < 25 || frame.highBreak > 200) {
        return NextResponse.json(
          { error: "High break must be between 25 and 200" },
          { status: 400 }
        );
      }
    }
  }

  // Check for duplicate players in the same match
  const playerIds = frames.map((f) => f.playerId);
  if (new Set(playerIds).size !== playerIds.length) {
    return NextResponse.json(
      { error: "Each player can only play one frame per match" },
      { status: 400 }
    );
  }

  const match = await prisma.match.create({
    data: {
      date: new Date(date),
      opponent,
      season: season || "billiards-2026",
      seasonType: "billiards",
      frames: {
        create: frames.map((f) => ({
          playerId: f.playerId,
          playerScore: f.playerScore,
          opponentScore: f.opponentScore,
          highBreak: f.highBreak || null,
          frameNumber: f.frameNumber,
        })),
      },
    },
    include: {
      frames: {
        include: { player: true },
        orderBy: { frameNumber: "asc" },
      },
    },
  });

  return NextResponse.json(match, { status: 201 });
}
