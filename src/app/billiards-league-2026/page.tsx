import { prisma } from "@/lib/prisma";
import { calculatePlayerStats, calculateTeamRecord } from "@/lib/rankings";
import { LeagueTable } from "@/components/LeagueTable";
import { TeamSummary } from "@/components/TeamSummary";
import { AddResultButton } from "@/components/AddResultButton";
import { RecentMatches } from "@/components/RecentMatches";

export const dynamic = "force-dynamic";

export default async function BilliardsLeague2026() {
  const [matches, players] = await Promise.all([
    prisma.match.findMany({
      where: { season: "billiards-2026" },
      include: {
        frames: {
          include: { player: true },
          orderBy: { frameNumber: "asc" },
        },
      },
      orderBy: { date: "desc" },
    }),
    prisma.player.findMany({ orderBy: { name: "asc" } }),
  ]);

  const playerStats = calculatePlayerStats(matches);
  const teamRecord = calculateTeamRecord(matches);

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white">Billiards League 2026</h1>
          <p className="text-gray-400 mt-1">
            Summer season &middot; First to 200 &middot; 5 frames per match
          </p>
        </div>
        <AddResultButton
          players={players.map((p) => ({ id: p.id, name: p.name }))}
        />
      </div>

      {/* Team Summary */}
      <TeamSummary record={teamRecord} />

      {/* Player Rankings Table */}
      <div className="mt-8">
        <h2 className="text-lg font-semibold text-gray-300 mb-4">
          Player Rankings
        </h2>
        <LeagueTable stats={playerStats} />
      </div>

      {/* Recent Matches */}
      <div className="mt-8">
        <h2 className="text-lg font-semibold text-gray-300 mb-4">
          Recent Matches
        </h2>
        <RecentMatches matches={matches.slice(0, 10)} />
      </div>
    </div>
  );
}
