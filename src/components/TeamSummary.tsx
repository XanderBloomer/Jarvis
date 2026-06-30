import { TeamRecord } from "@/lib/rankings";

export function TeamSummary({ record }: { record: TeamRecord }) {
  if (record.matchesPlayed === 0) {
    return (
      <div className="bg-gray-900 border border-gray-800 rounded-lg p-6 text-center text-gray-500">
        No matches played yet. Add your first result to get started.
      </div>
    );
  }

  const totalFrames = record.totalFramesWon + record.totalFramesLost + record.totalFramesDrawn;
  const frameWinRate = totalFrames > 0
    ? ((record.totalFramesWon / totalFrames) * 100).toFixed(0)
    : "0";

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <StatCard
        label="Matches"
        value={record.matchesPlayed.toString()}
        sub={`${record.matchWins}W ${record.matchDraws}D ${record.matchLosses}L`}
      />
      <StatCard
        label="Frames (inc. aggregate)"
        value={`${record.totalFramesWon}-${record.totalFramesLost}${record.totalFramesDrawn > 0 ? `-${record.totalFramesDrawn}D` : ""}`}
        sub={`${frameWinRate}% win rate`}
      />
      <StatCard
        label="Points For"
        value={record.totalPointsFor.toLocaleString()}
        sub={`avg ${Math.round(record.totalPointsFor / (record.matchesPlayed * 5))} per frame`}
      />
      <StatCard
        label="Points Against"
        value={record.totalPointsAgainst.toLocaleString()}
        sub={`diff: ${record.totalPointsFor - record.totalPointsAgainst > 0 ? "+" : ""}${record.totalPointsFor - record.totalPointsAgainst}`}
      />
    </div>
  );
}

function StatCard({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub: string;
}) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
      <p className="text-xs text-gray-500 uppercase tracking-wider">{label}</p>
      <p className="text-2xl font-bold text-white mt-1">{value}</p>
      <p className="text-xs text-gray-400 mt-1">{sub}</p>
    </div>
  );
}
