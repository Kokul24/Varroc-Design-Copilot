"use client";

/**
 * FeatureTable — Display extracted manufacturing features in a styled table.
 */

const FEATURE_CONFIG = {
  wall_thickness: { label: "Wall Thickness", unit: "mm", icon: "📏" },
  draft_angle: { label: "Draft Angle", unit: "°", icon: "📐" },
  corner_radius: { label: "Corner Radius", unit: "mm", icon: "⭕" },
  aspect_ratio: { label: "Aspect Ratio", unit: ":1", icon: "📊" },
  undercut_present: { label: "Undercut Present", unit: "", icon: "🔽" },
  wall_uniformity: { label: "Wall Uniformity", unit: "", icon: "🎯" },
  material_encoded: { label: "Material Code", unit: "", icon: "🧱" },
};

// Thresholds for color coding
const THRESHOLDS = {
  wall_thickness: { min: 1.0, max: 8.0 },
  draft_angle: { min: 1.5 },
  corner_radius: { min: 0.5 },
  aspect_ratio: { max: 8.0 },
  wall_uniformity: { min: 0.6 },
};

function getStatus(feature, value) {
  const t = THRESHOLDS[feature];
  if (!t) return "neutral";
  if (feature === "undercut_present") return value === 1 ? "warning" : "good";
  if (t.min && value < t.min) return "bad";
  if (t.max && value > t.max) return "warning";
  return "good";
}

const STATUS_STYLES = {
  good: "text-emerald-400",
  warning: "text-amber-400",
  bad: "text-red-400",
  neutral: "text-slate-300",
};

export default function FeatureTable({ features }) {
  if (!features) return null;

  const entries = Object.entries(features).filter(
    ([key]) => FEATURE_CONFIG[key]
  );

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
        <svg className="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z" />
        </svg>
        Extracted Features
      </h3>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {entries.map(([key, value], index) => {
          const config = FEATURE_CONFIG[key];
          const status = getStatus(key, value);
          const displayValue =
            key === "undercut_present"
              ? value === 1
                ? "Yes"
                : "No"
              : typeof value === "number"
              ? value.toFixed(2)
              : value;

          return (
            <div
              key={key}
              className="glass-card-light p-3 flex items-center gap-3 animate-fade-in"
              style={{ animationDelay: `${index * 40}ms` }}
            >
              <span className="text-lg">{config.icon}</span>
              <div className="flex-1 min-w-0">
                <span className="text-xs text-slate-500 block">
                  {config.label}
                </span>
                <span className={`text-sm font-semibold font-mono ${STATUS_STYLES[status]}`}>
                  {displayValue}
                  {config.unit && (
                    <span className="text-slate-600 ml-0.5 text-xs font-normal">
                      {config.unit}
                    </span>
                  )}
                </span>
              </div>
              {/* Status dot */}
              <div
                className={`w-2 h-2 rounded-full ${
                  status === "good"
                    ? "bg-emerald-400"
                    : status === "warning"
                    ? "bg-amber-400"
                    : status === "bad"
                    ? "bg-red-400"
                    : "bg-slate-600"
                }`}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}
