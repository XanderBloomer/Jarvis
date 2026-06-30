import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Porchester X",
  description: "Porchester X Snooker & Billiards Team",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-gray-950 text-gray-100 min-h-screen antialiased">
        <nav className="bg-gray-900 border-b border-gray-800">
          <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
            <a href="/" className="text-xl font-bold text-emerald-400 tracking-tight">
              Porchester X
            </a>
            <div className="flex gap-6 text-sm">
              <a href="/" className="text-gray-300 hover:text-white transition">
                Home
              </a>
              <a
                href="/billiards-league-2026"
                className="text-gray-300 hover:text-white transition"
              >
                Billiards 2026
              </a>
            </div>
          </div>
        </nav>
        <main>{children}</main>
      </body>
    </html>
  );
}
