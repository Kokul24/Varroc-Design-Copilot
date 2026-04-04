"use client";

/**
 * ViolationsList — Displays DFM violations with severity indicators.
 */

const TYPE_CONFIG = {
  CRITICAL: {
    color: "text-red-400",
    bg: "bg-red-500/10",
    border: "border-red-500/20",
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
      </svg>
    ),
    label: "Critical",
  },
  WARNING: {
    color: "text-amber-400",
    bg: "bg-amber-500/10",
    border: "border-amber-500/20",
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
      </svg>
    ),
    label: "Warning",
  },
  INFO: {
    color: "text-blue-400",
    bg: "bg-blue-500/10",
    border: "border-blue-500/20",
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" />
      </svg>
    ),
    label: "Info",
  },
};

export default function ViolationsList({ violations = [] }) {
  if (violations.length === 0) {
    return (
      <div className="glass-card-light p-6 text-center">
        <div className="w-12 h-12 mx-auto rounded-xl bg-emerald-500/10 flex items-center justify-center mb-3">
          <svg className="w-6 h-6 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <p className="text-sm font-medium text-emerald-400">No violations detected</p>
        <p className="text-xs text-slate-500 mt-1">Design meets all DFM thresholds</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Summary bar */}
      <div className="flex items-center gap-3 text-xs">
        {["CRITICAL", "WARNING", "INFO"].map((type) => {
          const count = violations.filter((v) => v.type === type).length;
          if (count === 0) return null;
          const cfg = TYPE_CONFIG[type];
          return (
            <span
              key={type}
              className={`flex items-center gap-1.5 px-2 py-1 rounded-md ${cfg.bg} ${cfg.color} border ${cfg.border}`}
            >
              {cfg.icon}
              {count} {cfg.label}
            </span>
          );
        })}
      </div>

      {/* Violation cards */}
      {violations.map((violation, index) => {
        const cfg = TYPE_CONFIG[violation.type] || TYPE_CONFIG.INFO;

        return (
          <div
            key={index}
            className={`glass-card-light p-4 border-l-2 ${cfg.border} animate-slide-up`}
            style={{ animationDelay: `${index * 80}ms` }}
            id={`violation-${index}`}
          >
            <div className="flex items-start gap-3">
              <div className={`mt-0.5 ${cfg.color}`}>{cfg.icon}</div>
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`text-sm font-medium ${cfg.color}`}>
                    {violation.message}
                  </span>
                </div>
                <p className="text-xs text-slate-400 mb-2">
                  {violation.detail}
                </p>

                {/* Suggestion */}
                <div className="flex items-start gap-2 p-2 rounded-lg bg-slate-800/50 mt-2">
                  <svg
                    className="w-3.5 h-3.5 text-brand-400 mt-0.5 flex-shrink-0"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M12 18v-5.25m0 0a6.01 6.01 0 001.5-.189m-1.5.189a6.01 6.01 0 01-1.5-.189m3.75 7.478a12.06 12.06 0 01-4.5 0m3.75 2.383a14.406 14.406 0 01-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 10-7.517 0c.85.493 1.509 1.333 1.509 2.316V18"
                    />
                  </svg>
                  <span className="text-xs text-slate-300">
                    {violation.suggestion}
                  </span>
                </div>

                {/* Severity bar */}
                {violation.severity != null && (
                  <div className="mt-2 flex items-center gap-2">
                    <span className="text-[10px] text-slate-600 uppercase tracking-wider">
                      Severity
                    </span>
                    <div className="flex-1 h-1 rounded-full bg-slate-800 overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${
                          violation.severity > 60
                            ? "bg-red-400"
                            : violation.severity > 30
                            ? "bg-amber-400"
                            : "bg-blue-400"
                        }`}
                        style={{
                          width: `${Math.min(violation.severity, 100)}%`,
                        }}
                      />
                    </div>
                    <span className="text-[10px] text-slate-500 font-mono">
                      {violation.severity.toFixed(0)}%
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
