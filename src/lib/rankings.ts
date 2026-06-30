// Ranking calculation for the league table

export type PlayerStats = {
  id: string;
  name: string;
  played: number;
  wins: number;
  losses: number;
  pointsFor: number;
  pointsAgainst: number;
  pointsDiff: number;
  winPercentage: number;
  avgScore: number;
  highBreak: number | null; // null = no high break recorded
  rank: number;
};

export type MatchResult = {
  opponent: string;
  date: string;
  individualFramesWon: number;
  individualFramesLost: number;
  aggregateResult: "win" | "loss" | "draw";
  totalFramesWon: number; // individual + aggregate (out of 6)
  totalFramesLost: number;
  pointsFor: number;
  pointsAgainst: number;
};

export type TeamRecord = {
  matchesPlayed: number;
  totalFramesWon: number; // includes aggregate frame
  totalFramesLost: number;
  totalFramesDrawn: number;
  matchWins: number;
  matchLosses: number;
  matchDraws: number;
  totalPointsFor: number;
  totalPointsAgainst: number;
};

type FrameData = {
  player: { id: string; name: string };
  playerScore: number;
  opponentScore: number;
  highBreak: number | null;
};

type MatchData = {
  frames: FrameData[];
};

export function calculatePlayerStats(matches: MatchData[]): PlayerStats[] {
  const statsMap = new Map<
    string,
    {
      id: string;
      name: string;
      played: number;
      wins: number;
      losses: number;
      pointsFor: number;
      pointsAgainst: number;
      highBreak: number | null;
    }
  >();

  for (const match of matches) {
    for (const frame of match.frames) {
      const pid = frame.player.id;
      const existing = statsMap.get(pid) || {
        id: pid,
        name: frame.player.name,
        played: 0,
        wins: 0,
        losses: 0,
        pointsFor: 0,
        pointsAgainst: 0,
        highBreak: null,
      };

      existing.played += 1;
      existing.pointsFor += frame.playerScore;
      existing.pointsAgainst += frame.opponentScore;

      if (frame.playerScore > frame.opponentScore) {
        existing.wins += 1;
      } else {
        existing.losses += 1;
      }

      // Track highest break (only from explicitly recorded high breaks)
      if (frame.highBreak !== null && frame.highBreak !== undefined) {
        if (existing.highBreak === null || frame.highBreak > existing.highBreak) {
          existing.highBreak = frame.highBreak;
        }
      }

      statsMap.set(pid, existing);
    }
  }

  const stats: PlayerStats[] = Array.from(statsMap.values()).map((s) => ({
    ...s,
    pointsDiff: s.pointsFor - s.pointsAgainst,
    winPercentage: s.played > 0 ? (s.wins / s.played) * 100 : 0,
    avgScore: s.played > 0 ? Math.round(s.pointsFor / s.played) : 0,
    rank: 0,
  }));

  // Sort: win % desc, then points diff desc, then points for desc
  stats.sort((a, b) => {
    if (b.winPercentage !== a.winPercentage) return b.winPercentage - a.winPercentage;
    if (b.pointsDiff !== a.pointsDiff) return b.pointsDiff - a.pointsDiff;
    return b.pointsFor - a.pointsFor;
  });

  // Assign ranks
  stats.forEach((s, i) => {
    s.rank = i + 1;
  });

  return stats;
}

export function calculateMatchResult(frames: FrameData[]): {
  individualWon: number;
  individualLost: number;
  aggregateResult: "win" | "loss" | "draw";
  totalWon: number;
  totalLost: number;
  totalDrawn: number;
  pointsFor: number;
  pointsAgainst: number;
} {
  let individualWon = 0;
  let individualLost = 0;
  let pointsFor = 0;
  let pointsAgainst = 0;

  for (const frame of frames) {
    pointsFor += frame.playerScore;
    pointsAgainst += frame.opponentScore;
    if (frame.playerScore > frame.opponentScore) {
      individualWon += 1;
    } else {
      individualLost += 1;
    }
  }

  // Aggregate (total points) counts as a 6th frame
  const aggregateResult: "win" | "loss" | "draw" =
    pointsFor > pointsAgainst ? "win" : pointsFor < pointsAgainst ? "loss" : "draw";

  let totalWon = individualWon;
  let totalLost = individualLost;
  let totalDrawn = 0;

  if (aggregateResult === "win") {
    totalWon += 1;
  } else if (aggregateResult === "loss") {
    totalLost += 1;
  } else {
    totalDrawn = 1;
  }

  return {
    individualWon,
    individualLost,
    aggregateResult,
    totalWon,
    totalLost,
    totalDrawn,
    pointsFor,
    pointsAgainst,
  };
}

export function calculateTeamRecord(matches: MatchData[]): TeamRecord {
  const record: TeamRecord = {
    matchesPlayed: matches.length,
    totalFramesWon: 0,
    totalFramesLost: 0,
    totalFramesDrawn: 0,
    matchWins: 0,
    matchLosses: 0,
    matchDraws: 0,
    totalPointsFor: 0,
    totalPointsAgainst: 0,
  };

  for (const match of matches) {
    const result = calculateMatchResult(match.frames);

    record.totalFramesWon += result.totalWon;
    record.totalFramesLost += result.totalLost;
    record.totalFramesDrawn += result.totalDrawn;
    record.totalPointsFor += result.pointsFor;
    record.totalPointsAgainst += result.pointsAgainst;

    // Match result = who won more of the 6 frames
    if (result.totalWon > result.totalLost) {
      record.matchWins += 1;
    } else if (result.totalLost > result.totalWon) {
      record.matchLosses += 1;
    } else {
      record.matchDraws += 1;
    }
  }

  return record;
}
