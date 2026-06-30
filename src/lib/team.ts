// Team configuration — edit this file to update players and roles

export type PlayerRole = "captain" | "vice-captain" | "player";

export type TeamPlayer = {
  name: string;
  role: PlayerRole;
};

// Players listed in display order: captain first, vice-captain second, then alphabetical
export const TEAM_PLAYERS: TeamPlayer[] = [
  { name: "Jason Tame", role: "captain" },
  { name: "Mark Kingswell", role: "vice-captain" },
  { name: "Adam Gillen", role: "player" },
  { name: "Charlie Cripps", role: "player" },
  { name: "Justin Andrews", role: "player" },
  { name: "Lee Paice", role: "player" },
  { name: "Lewis Johnson", role: "player" },
  { name: "Matt James", role: "player" },
  { name: "Xander Bloomer", role: "player" },
];

export const TEAM_NAME = "Porchester X";

export function getRoleBadge(role: PlayerRole): string | null {
  switch (role) {
    case "captain":
      return "C";
    case "vice-captain":
      return "VC";
    default:
      return null;
  }
}
