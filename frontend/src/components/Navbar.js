"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

/**
 * Navbar — Top navigation bar with brand logo and status indicator.
 */
export default function Navbar() {
  const pathname = usePathname();

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 glass-card !rounded-none border-t-0 border-l-0 border-r-0">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-3 group">
            <div className="relative">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-400 to-brand-600 flex items-center justify-center shadow-lg shadow-brand-500/25 group-hover:shadow-brand-400/40 transition-all duration-300">
                <svg
                  className="w-5 h-5 text-white"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z"
                  />
                </svg>
              </div>
              {/* Pulse dot */}
              <span className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 bg-emerald-400 rounded-full animate-pulse-subtle" />
            </div>
            <span className="text-xl font-bold tracking-tight">
              <span className="gradient-text">CAD</span>
              <span className="text-slate-100">guard</span>
            </span>
          </Link>

          {/* Navigation Links */}
          <div className="flex items-center gap-6">
            <Link
              href="/"
              className={`text-sm font-medium transition-colors duration-200 ${
                pathname === "/"
                  ? "text-brand-400"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Dashboard
            </Link>
            <Link
              href="/login"
              className={`text-sm font-medium transition-colors duration-200 ${
                pathname === "/login"
                  ? "text-brand-400"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Login
            </Link>
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse-subtle" />
              <span className="text-xs font-medium text-emerald-400">
                AI Engine Active
              </span>
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
}
