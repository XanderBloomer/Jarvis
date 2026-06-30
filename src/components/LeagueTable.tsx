import { PlayerStats } from "@/lib/rankings";

export function LeagueTable({ stats }: { stats: PlayerStats[] }) {
  if (stats.length === 0) {
    return (
      <div className="bg-gray-900 border border-gray-800 rounded-lg p-6 text-center text-gray-500">
        No player data yet.
      </div>
    );
  }

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800 text-gray-400 text-xs uppercase tracking-wider">
              <th className="px-4 py-3 text-left">#</th>
              <th className="px-4 py-3 text-left">Player</th>
              <th className="px-4 py-3 text-center">P</th>
              <th className="px-4 py-3 text-center">W</th>
              <th className="px-4 py-3 text-center">L</th>
              <th className="px-4 py-3 text-center">Win %</th>
              <th className="px-4 py-3 text-center">PF</th>
              <th className="px-4 py-3 text-center">PA</th>
              <th className="px-4 py-3 text-center">+/-</th>
              <th className="px-4 py-3 text-center">Avg</th>
              <th className="px-4 py-3 text-center">High Break</th>
            </tr>
          </thead>
          <tbody>
            {stats.map((player) => (
              <tr
                key={player.id}
                className="border-b border-gray-800/50 hover:bg-gray-800/30 transition"
              >
                <td className="px-4 py-3">
                  <RankBadge rank={player.rank} />
                </td>
                <td className="px-4 py-3 font-medium text-white">
                  {player.name}
                </td>
                <td className="px-4 py-3 text-center text-gray-300">
                  {player.played}
                </td>
                <td className="px-4 py-3 text-center text-emerald-400">
                  {player.wins}
                </td>
                <td className="px-4 py-3 text-center text-red-400">
                  {player.losses}
                </td>
                <td className="px-4 py-3 text-center">
                  <WinPercentage value={player.winPercentage} />
                </td>
                <td className="px-4 py-3 text-center text-gray-300">
                  {player.pointsFor}
                </td>
                <td className="px-4 py-3 text-center text-gray-300">
                  {player.pointsAgainst}
                </td>
                <td className="px-4 py-3 text-center">
                  <span
                    className={
                      player.pointsDiff > 0
                        ? "text-emerald-400"
                        : player.pointsDiff < 0
                          ? "text-red-400"
                          : "text-gray-400"
                    }
                  >
                    {player.pointsDiff > 0 ? "+" : ""}
                    {player.pointsDiff}
                  </span>
                </td>
                <td className="px-4 py-3 text-center text-gray-300">
                  {player.avgScore}
                </td>
                <td className="px-4 py-3 text-center">
                  {player.highBreak !== null ? (
                    <span className="text-amber-400 font-semibold">{player.highBreak}</span>
                  ) : (
                    <span className="text-gray-600">N/A</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="px-4 py-2 border-t border-gray-800 text-xs text-gray-500">
        P = Played, W = Wins, L = Losses, PF = Points For, PA = Points Against,
        +/- = Point Differential, Avg = Average Score, High Break = Best break (25+)
      </div>
    </div>
  );
}

function RankBadge({ rank }: { rank: number }) {
  const colors: Record<number, string> = {
    1: "bg-amber-500/20 text-amber-400 border-amber-500/30",
    2: "bg-gray-400/20 text-gray-300 border-gray-400/30",
    3: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  };

  const colorClass = colors[rank] || "bg-gray-800 text-gray-400 border-gray-700";

  return (
    <span
      className={`inline-flex items-center justify-center w-7 h-7 rounded-full text-xs font-bold border ${colorClass}`}
    >
      {rank}
    </span>
  );
}

function WinPercentage({ value }: { value: number }) {
  let color = "text-gray-400";
  if (value >= 70) color = "text-emerald-400";
  else if (value >= 50) color = "text-blue-400";
  else if (value > 0) color = "text-orange-400";

  return <span className={`font-semibold ${color}`}>{value.toFixed(0)}%</span>;
}
