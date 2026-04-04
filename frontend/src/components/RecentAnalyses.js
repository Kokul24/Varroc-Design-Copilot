"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { authenticatedFetch, clearAuthSession } from "@/lib/auth";

/**
 * RecentAnalyses — List of recent analysis results on the dashboard.
 */
export default function RecentAnalyses() {
  const router = useRouter();
  const [analyses, setAnalyses] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRecent();
  }, []);

  async function fetchRecent() {
    try {
      const res = await authenticatedFetch(`/api/analyses?limit=8`);
      if (res.status === 401) {
        clearAuthSession();
        router.replace("/login");
        return;
      }
      if (res.ok) {
        const data = await res.json();
        setAnalyses(data.analyses || []);
      }
    } catch {
      /* Silently fail */
    } finally {
      setLoading(false);
    }
  }

  const getRiskColor = (label) => {
    switch (label) {
      case "LOW":
        return "badge-low";
      case "MEDIUM":
        return "badge-medium";
      case "HIGH":
        return "badge-high";
      default:
        return "badge-low";
    }
  };

  const getRiskGlow = (label) => {
    switch (label) {
      case "LOW":
        return "border-emerald-500/10";
      case "MEDIUM":
        return "border-amber-500/10";
      case "HIGH":
        return "border-red-500/10";
      default:
        return "";
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return "Just now";
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now - date;
    const minutes = Math.floor(diff / 60000);
    if (minutes < 1) return "Just now";
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    return date.toLocaleDateString();
  };

  if (loading) {
    return (
      <div className="space-y-3">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="glass-card-light p-4 animate-pulse">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg shimmer" />
              <div className="flex-1 space-y-2">
                <div className="h-4 w-32 rounded shimmer" />
                <div className="h-3 w-20 rounded shimmer" />
              </div>
              <div className="h-6 w-16 rounded-full shimmer" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (analyses.length === 0) {
    return (
      <div className="glass-card-light p-8 text-center">
        <div className="w-12 h-12 mx-auto rounded-xl bg-slate-800 flex items-center justify-center mb-3">
          <svg
            className="w-6 h-6 text-slate-600"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M2.25 13.5h3.86a2.25 2.25 0 012.012 1.244l.256.512a2.25 2.25 0 002.013 1.244h3.218a2.25 2.25 0 002.013-1.244l.256-.512a2.25 2.25 0 012.013-1.244h3.859"
            />
          </svg>
        </div>
        <p className="text-sm text-slate-500">No analyses yet</p>
        <p className="text-xs text-slate-600 mt-1">
          Upload a file to get started
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {analyses.map((analysis, index) => (
        <Link
          key={analysis.id}
          href={`/results/${analysis.id}`}
          className={`block glass-card-light p-4 hover:bg-slate-800/60 transition-all duration-200 group animate-slide-up ${getRiskGlow(analysis.risk_label)}`}
          style={{ animationDelay: `${index * 50}ms` }}
          id={`recent-analysis-${analysis.id}`}
        >
          <div className="flex items-center gap-3">
            {/* Score circle */}
            <div
              className={`w-10 h-10 rounded-lg flex items-center justify-center text-sm font-bold ${
                analysis.risk_label === "LOW"
                  ? "bg-emerald-500/10 text-emerald-400"
                  : analysis.risk_label === "MEDIUM"
                  ? "bg-amber-500/10 text-amber-400"
                  : "bg-red-500/10 text-red-400"
              }`}
            >
              {Math.round(analysis.risk_score)}
            </div>

            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-slate-200 truncate group-hover:text-white transition-colors">
                {analysis.file_name}
              </p>
              <p className="text-xs text-slate-500">
                {analysis.material} • {formatDate(analysis.created_at)}
              </p>
            </div>

            <span className={`badge ${getRiskColor(analysis.risk_label)}`}>
              {analysis.risk_label}
            </span>

            <svg
              className="w-4 h-4 text-slate-600 group-hover:text-brand-400 transition-colors"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M8.25 4.5l7.5 7.5-7.5 7.5"
              />
            </svg>
          </div>
        </Link>
      ))}
    </div>
  );
}
