import { calculateMatchResult } from "@/lib/rankings";

type FrameData = {
  frameNumber: number;
  player: { id: string; name: string };
  playerScore: number;
  opponentScore: number;
  highBreak: number | null;
};

type MatchData = {
  id: string;
  date: string | Date;
  opponent: string;
  frames: FrameData[];
};

export function RecentMatches({ matches }: { matches: MatchData[] }) {
  if (matches.length === 0) {
    return (
      <div className="bg-gray-900 border border-gray-800 rounded-lg p-6 text-center text-gray-500">
        No matches recorded yet.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {matches.map((match) => {
        const result = calculateMatchResult(match.frames);

        const matchOutcome =
          result.totalWon > result.totalLost
            ? "WIN"
            : result.totalLost > result.totalWon
              ? "LOSS"
              : "DRAW";

        const outcomeColor =
          matchOutcome === "WIN"
            ? "text-emerald-400"
            : matchOutcome === "LOSS"
              ? "text-red-400"
              : "text-amber-400";

        const aggColor =
          result.aggregateResult === "win"
            ? "text-emerald-400"
            : result.aggregateResult === "loss"
              ? "text-red-400"
              : "text-amber-400";

        return (
          <div
            key={match.id}
            className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden"
          >
            {/* Match header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
              <div>
                <span className="font-medium text-white">Porchester X</span>
                <span className="text-gray-500 mx-2">vs</span>
                <span className="text-gray-300">{match.opponent}</span>
              </div>
              <div className="flex items-center gap-4">
                <span className={`text-sm font-bold ${outcomeColor}`}>
                  {result.totalWon}-{result.totalLost}
                  {result.totalDrawn > 0 ? ` (${result.totalDrawn}D)` : ""}{" "}
                  {matchOutcome}
                </span>
                <span className="text-xs text-gray-500">
                  {new Date(match.date).toLocaleDateString("en-GB", {
                    day: "numeric",
                    month: "short",
                    year: "numeric",
                  })}
                </span>
              </div>
            </div>

            {/* Individual frames */}
            <div className="divide-y divide-gray-800/50">
              {match.frames.map((frame) => {
                const won = frame.playerScore > frame.opponentScore;
                return (
                  <div
                    key={frame.frameNumber}
                    className="flex items-center justify-between px-4 py-2 text-sm"
                  >
                    <span className="text-xs text-gray-600 w-6">
                      {frame.frameNumber}.
                    </span>
                    <span
                      className={`flex-1 ${won ? "text-emerald-400" : "text-gray-400"}`}
                    >
                      {frame.player.name}
                    </span>
                    <span className="flex items-center justify-center px-4">
                      <span
                        className={`font-mono font-bold w-8 text-right ${won ? "text-white" : "text-gray-500"}`}
                      >
                        {frame.playerScore}
                      </span>
                      <span className="text-gray-600 mx-1">-</span>
                      <span
                        className={`font-mono font-bold w-8 text-left ${!won ? "text-white" : "text-gray-500"}`}
                      >
                        {frame.opponentScore}
                      </span>
                    </span>
                    <span className="w-16 text-right">
                      {won ? (
                        <span className="text-xs text-emerald-400 font-medium">
                          WIN
                        </span>
                      ) : (
                        <span className="text-xs text-red-400 font-medium">
                          LOSS
                        </span>
                      )}
                    </span>
                  </div>
                );
              })}

              {/* Aggregate frame */}
              <div className="flex items-center justify-between px-4 py-2 text-sm bg-gray-800/30 border-t border-gray-700">
                <span className="text-xs text-gray-600 w-6">6.</span>
                <span className={`flex-1 font-medium ${aggColor}`}>
                  Aggregate
                </span>
                <span className="flex items-center justify-center px-4">
                  <span
                    className={`font-mono font-bold w-10 text-right ${result.aggregateResult === "win" ? "text-white" : "text-gray-500"}`}
                  >
                    {result.pointsFor}
                  </span>
                  <span className="text-gray-600 mx-1">-</span>
                  <span
                    className={`font-mono font-bold w-10 text-left ${result.aggregateResult === "loss" ? "text-white" : "text-gray-500"}`}
                  >
                    {result.pointsAgainst}
                  </span>
                </span>
                <span className="w-16 text-right">
                  <span className={`text-xs font-medium ${aggColor}`}>
                    {result.aggregateResult === "win"
                      ? "WIN"
                      : result.aggregateResult === "loss"
                        ? "LOSS"
                        : "DRAW"}
                  </span>
                </span>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
