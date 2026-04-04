"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from "recharts";

/**
 * ShapChart — Horizontal bar chart of SHAP feature contributions.
 * Positive values (increasing risk) are shown in red, negative in green.
 */

const FEATURE_LABELS = {
  wall_thickness: "Wall Thickness",
  draft_angle: "Draft Angle",
  corner_radius: "Corner Radius",
  aspect_ratio: "Aspect Ratio",
  undercut_present: "Undercut",
  wall_uniformity: "Wall Uniformity",
  material_encoded: "Material",
};

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const data = payload[0].payload;

  return (
    <div className="glass-card p-3 !rounded-lg text-xs">
      <p className="font-semibold text-slate-200 mb-1">{data.label}</p>
      <div className="flex items-center gap-2">
        <span className="text-slate-400">Contribution:</span>
        <span
          className={`font-mono font-bold ${
            data.value > 0 ? "text-red-400" : "text-emerald-400"
          }`}
        >
          {data.value > 0 ? "+" : ""}
          {data.value.toFixed(4)}
        </span>
      </div>
      <div className="flex items-center gap-2 mt-1">
        <span className="text-slate-400">Feature value:</span>
        <span className="font-mono text-slate-300">
          {data.featureValue ?? "N/A"}
        </span>
      </div>
      <p className="text-slate-500 mt-1.5 border-t border-slate-700 pt-1.5">
        {data.value > 0
          ? "↑ Increases manufacturing risk"
          : "↓ Decreases manufacturing risk"}
      </p>
    </div>
  );
}

export default function ShapChart({ shapValues, featureValues }) {
  if (!shapValues) return null;

  const shap = shapValues.shap_values || shapValues;
  const values = featureValues || shapValues.feature_values || {};

  // Build chart data sorted by absolute contribution
  const data = Object.entries(shap)
    .map(([key, val]) => ({
      feature: key,
      label: FEATURE_LABELS[key] || key,
      value: val,
      featureValue: values[key],
      absValue: Math.abs(val),
    }))
    .sort((a, b) => b.absValue - a.absValue);

  return (
    <div className="w-full">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-slate-300">
          Feature Contributions (SHAP)
        </h3>
        <div className="flex items-center gap-3 text-xs">
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-2 rounded-sm bg-red-400" />
            <span className="text-slate-500">Increases risk</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-2 rounded-sm bg-emerald-400" />
            <span className="text-slate-500">Decreases risk</span>
          </span>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={280}>
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 5, right: 30, left: 100, bottom: 5 }}
        >
          <CartesianGrid
            strokeDasharray="3 3"
            horizontal={false}
            stroke="rgba(51,65,85,0.3)"
          />
          <XAxis
            type="number"
            tick={{ fill: "#94a3b8", fontSize: 11 }}
            axisLine={{ stroke: "rgba(51,65,85,0.5)" }}
            tickFormatter={(v) => v.toFixed(3)}
          />
          <YAxis
            type="category"
            dataKey="label"
            tick={{ fill: "#cbd5e1", fontSize: 12 }}
            axisLine={false}
            tickLine={false}
            width={95}
          />
          <Tooltip content={<CustomTooltip />} cursor={false} />
          <ReferenceLine
            x={0}
            stroke="rgba(148,163,184,0.3)"
            strokeDasharray="3 3"
          />
          <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={18}>
            {data.map((entry, index) => (
              <Cell
                key={index}
                fill={
                  entry.value > 0
                    ? "rgba(239, 68, 68, 0.7)"
                    : "rgba(16, 185, 129, 0.7)"
                }
                stroke={
                  entry.value > 0
                    ? "rgba(239, 68, 68, 0.9)"
                    : "rgba(16, 185, 129, 0.9)"
                }
                strokeWidth={1}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {shapValues.base_value !== undefined && (
        <p className="text-xs text-slate-600 mt-2 text-center">
          Base value: {shapValues.base_value.toFixed(4)} • Values show contribution to risk probability
        </p>
      )}
    </div>
  );
}
