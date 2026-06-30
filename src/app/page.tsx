import { TEAM_PLAYERS, getRoleBadge } from "@/lib/team";

export default function Home() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-16">
      {/* Hero */}
      <div className="text-center mb-16">
        <h1 className="text-5xl font-bold mb-4">
          <span className="text-emerald-400">Porchester</span>{" "}
          <span className="text-white">X</span>
        </h1>
        <p className="text-gray-400 text-lg">
          Snooker in the winter. Billiards in the summer.
        </p>
      </div>

      {/* Seasons */}
      <div className="grid gap-6 md:grid-cols-2">
        <a
          href="/billiards-league-2026"
          className="group block bg-gray-900 border border-gray-800 rounded-lg p-6 hover:border-emerald-500/50 transition-all"
        >
          <div className="flex items-center gap-3 mb-3">
            <div className="w-3 h-3 bg-emerald-400 rounded-full animate-pulse" />
            <span className="text-xs text-emerald-400 font-medium uppercase tracking-wider">
              Current Season
            </span>
          </div>
          <h2 className="text-xl font-semibold text-white group-hover:text-emerald-400 transition">
            Billiards League 2026
          </h2>
          <p className="text-gray-400 text-sm mt-2">
            Summer billiards season. First to 200. 5 frames per match.
          </p>
        </a>

        <div className="block bg-gray-900/50 border border-gray-800/50 rounded-lg p-6 opacity-50">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-3 h-3 bg-gray-600 rounded-full" />
            <span className="text-xs text-gray-500 font-medium uppercase tracking-wider">
              Coming Soon
            </span>
          </div>
          <h2 className="text-xl font-semibold text-gray-500">
            Snooker League 2026/27
          </h2>
          <p className="text-gray-600 text-sm mt-2">
            Winter snooker season starts later this year.
          </p>
        </div>
      </div>

      {/* Team */}
      <div className="mt-16">
        <h2 className="text-lg font-semibold text-gray-300 mb-6 text-center">
          The Squad
        </h2>
        <div className="flex flex-wrap justify-center gap-3">
          {TEAM_PLAYERS.map((player) => {
            const badge = getRoleBadge(player.role);
            const isLeadership = player.role !== "player";
            return (
              <span
                key={player.name}
                className={`rounded-full px-4 py-2 text-sm flex items-center gap-2 ${
                  isLeadership
                    ? "bg-emerald-900/30 border border-emerald-700/50 text-emerald-300"
                    : "bg-gray-900 border border-gray-800 text-gray-300"
                }`}
              >
                {player.name}
                {badge && (
                  <span className="bg-emerald-600/30 text-emerald-400 text-xs font-bold px-1.5 py-0.5 rounded">
                    {badge}
                  </span>
                )}
              </span>
            );
          })}
        </div>
      </div>
    </div>
  );
}
