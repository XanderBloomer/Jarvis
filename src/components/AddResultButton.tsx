"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

type Player = { id: string; name: string };

type FrameEntry = {
  playerId: string;
  playerScore: string;
  opponentScore: string;
  highBreak: string;
};

const emptyFrame = (): FrameEntry => ({
  playerId: "",
  playerScore: "",
  opponentScore: "",
  highBreak: "",
});

export function AddResultButton({ players }: { players: Player[] }) {
  const [authenticated, setAuthenticated] = useState(false);
  const [showPasswordPrompt, setShowPasswordPrompt] = useState(false);
  const [password, setPassword] = useState("");
  const [authError, setAuthError] = useState("");
  const [authLoading, setAuthLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [date, setDate] = useState(new Date().toISOString().split("T")[0]);
  const [opponent, setOpponent] = useState("");
  const [frames, setFrames] = useState<FrameEntry[]>(
    Array.from({ length: 5 }, emptyFrame)
  );
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const router = useRouter();

  const handleAuth = async () => {
    setAuthLoading(true);
    setAuthError("");
    try {
      const res = await fetch("/api/auth", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });
      if (res.ok) {
        setAuthenticated(true);
        setShowPasswordPrompt(false);
        setOpen(true);
        setPassword("");
      } else {
        setAuthError("Incorrect password");
      }
    } catch {
      setAuthError("Network error");
    } finally {
      setAuthLoading(false);
    }
  };

  const updateFrame = (index: number, field: keyof FrameEntry, value: string) => {
    setFrames((prev) => {
      const updated = [...prev];
      updated[index] = { ...updated[index], [field]: value };
      return updated;
    });
  };

  const getUsedPlayerIds = (excludeIndex: number) => {
    return frames
      .filter((_, i) => i !== excludeIndex)
      .map((f) => f.playerId)
      .filter(Boolean);
  };

  const validate = (): string | null => {
    if (!date) return "Date is required";
    if (!opponent.trim()) return "Opponent team name is required";

    for (let i = 0; i < 5; i++) {
      const f = frames[i];
      if (!f.playerId) return `Frame ${i + 1}: Select a player`;

      const ps = parseInt(f.playerScore);
      const os = parseInt(f.opponentScore);

      if (isNaN(ps) || ps < 0 || ps > 200)
        return `Frame ${i + 1}: Player score must be 0-200`;
      if (isNaN(os) || os < 0 || os > 200)
        return `Frame ${i + 1}: Opponent score must be 0-200`;

      const hbStr = (f.highBreak || "").trim();
      if (hbStr !== "") {
        const hb = parseInt(hbStr);
        if (isNaN(hb) || hb < 25 || hb > 200)
          return `Frame ${i + 1}: High break must be between 25 and 200`;
      }
    }

    const playerIds = frames.map((f) => f.playerId);
    if (new Set(playerIds).size !== 5)
      return "Each player can only play one frame per match";

    return null;
  };

  const handleSubmit = async () => {
    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }

    setSaving(true);
    setError("");

    try {
      const res = await fetch("/api/matches", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          date,
          opponent: opponent.trim(),
          season: "billiards-2026",
          frames: frames.map((f, i) => ({
            playerId: f.playerId,
            playerScore: parseInt(f.playerScore),
            opponentScore: parseInt(f.opponentScore),
            highBreak: (f.highBreak || "").trim() !== "" ? parseInt(f.highBreak) : null,
            frameNumber: i + 1,
          })),
        }),
      });

      if (!res.ok) {
        const data = await res.json();
        setError(data.error || "Failed to save result");
        return;
      }

      // Success — close modal and refresh
      setOpen(false);
      setOpponent("");
      setFrames(Array.from({ length: 5 }, emptyFrame));
      router.refresh();
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  if (!open) {
    // Show password prompt
    if (showPasswordPrompt) {
      return (
        <>
          <div
            className="fixed inset-0 bg-black/60 z-40"
            onClick={() => {
              setShowPasswordPrompt(false);
              setPassword("");
              setAuthError("");
            }}
          />
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div className="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-sm shadow-2xl">
              <div className="px-6 py-4 border-b border-gray-800">
                <h2 className="text-lg font-semibold text-white">
                  Enter Password
                </h2>
              </div>
              <div className="px-6 py-4 space-y-3">
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleAuth()}
                  placeholder="Password"
                  autoFocus
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-emerald-500"
                />
                {authError && (
                  <p className="text-red-400 text-sm">{authError}</p>
                )}
              </div>
              <div className="flex justify-end gap-3 px-6 py-4 border-t border-gray-800">
                <button
                  onClick={() => {
                    setShowPasswordPrompt(false);
                    setPassword("");
                    setAuthError("");
                  }}
                  className="px-4 py-2 text-sm text-gray-400 hover:text-white transition"
                >
                  Cancel
                </button>
                <button
                  onClick={handleAuth}
                  disabled={authLoading || !password}
                  className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white px-6 py-2 rounded-lg text-sm font-medium transition"
                >
                  {authLoading ? "Checking..." : "Submit"}
                </button>
              </div>
            </div>
          </div>
        </>
      );
    }

    return (
      <button
        onClick={() => {
          if (authenticated) {
            setOpen(true);
          } else {
            setShowPasswordPrompt(true);
          }
        }}
        className="bg-emerald-600 hover:bg-emerald-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition"
      >
        + Add Result
      </button>
    );
  }

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 z-40"
        onClick={() => setOpen(false)}
      />

      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-xl max-h-[90vh] overflow-y-auto shadow-2xl">
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
            <h2 className="text-lg font-semibold text-white">
              Add Match Result
            </h2>
            <button
              onClick={() => setOpen(false)}
              className="text-gray-400 hover:text-white text-xl"
            >
              &times;
            </button>
          </div>

          <div className="px-6 py-4 space-y-4">
            {/* Match info */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-gray-400 mb-1">
                  Date
                </label>
                <input
                  type="date"
                  value={date}
                  onChange={(e) => setDate(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-emerald-500"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">
                  Opponent Team
                </label>
                <input
                  type="text"
                  value={opponent}
                  onChange={(e) => setOpponent(e.target.value)}
                  placeholder="e.g. Railway Club"
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-emerald-500"
                />
              </div>
            </div>

            {/* Frames */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <p className="text-xs text-gray-400 uppercase tracking-wider">
                  Frames (5)
                </p>
                <div className="grid grid-cols-4 gap-2 text-xs text-gray-500 w-[70%]">
                  <span>Player</span>
                  <span className="text-center">Our Score</span>
                  <span className="text-center">Their Score</span>
                  <span className="text-center">High Break</span>
                </div>
              </div>
              {frames.map((frame, i) => {
                const usedIds = getUsedPlayerIds(i);
                return (
                  <div
                    key={i}
                    className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-3"
                  >
                    <p className="text-xs text-gray-500 mb-2">
                      Frame {i + 1}
                    </p>
                    <div className="grid grid-cols-4 gap-2">
                      <select
                        value={frame.playerId}
                        onChange={(e) =>
                          updateFrame(i, "playerId", e.target.value)
                        }
                        className="bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-white text-sm focus:outline-none focus:border-emerald-500"
                      >
                        <option value="">Select player</option>
                        {players.map((p) => (
                          <option
                            key={p.id}
                            value={p.id}
                            disabled={usedIds.includes(p.id)}
                          >
                            {p.name}
                          </option>
                        ))}
                      </select>
                      <input
                        type="number"
                        min="0"
                        max="200"
                        value={frame.playerScore}
                        onChange={(e) =>
                          updateFrame(i, "playerScore", e.target.value)
                        }
                        placeholder="0-200"
                        className="bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-white text-sm text-center placeholder-gray-500 focus:outline-none focus:border-emerald-500"
                      />
                      <input
                        type="number"
                        min="0"
                        max="200"
                        value={frame.opponentScore}
                        onChange={(e) =>
                          updateFrame(i, "opponentScore", e.target.value)
                        }
                        placeholder="0-200"
                        className="bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-white text-sm text-center placeholder-gray-500 focus:outline-none focus:border-emerald-500"
                      />
                      <input
                        type="number"
                        min="25"
                        max="200"
                        value={frame.highBreak || ""}
                        onChange={(e) =>
                          updateFrame(i, "highBreak", e.target.value)
                        }
                        placeholder="25+"
                        className="bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-white text-sm text-center placeholder-gray-500 focus:outline-none focus:border-emerald-500"
                      />
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Error */}
            {error && (
              <div className="bg-red-500/10 border border-red-500/30 text-red-400 rounded-lg px-4 py-2 text-sm">
                {error}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="flex justify-end gap-3 px-6 py-4 border-t border-gray-800">
            <button
              onClick={() => setOpen(false)}
              className="px-4 py-2 text-sm text-gray-400 hover:text-white transition"
            >
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              disabled={saving}
              className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed text-white px-6 py-2 rounded-lg text-sm font-medium transition"
            >
              {saving ? "Saving..." : "Save Result"}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
