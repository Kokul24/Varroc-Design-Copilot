"use client";

import { useEffect, useState } from "react";

/**
 * RiskGauge — Animated circular gauge showing risk score (0–100).
 * Color transitions from green → amber → red based on risk level.
 */
export default function RiskGauge({ score = 0, label = "LOW", size = 200 }) {
  const [animatedScore, setAnimatedScore] = useState(0);

  useEffect(() => {
    // Animate score from 0 to target
    const duration = 1500;
    const startTime = Date.now();
    const animate = () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // Ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setAnimatedScore(Math.round(score * eased));
      if (progress < 1) requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);
  }, [score]);

  const radius = (size - 24) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset =
    circumference - (animatedScore / 100) * circumference;

  const getColor = () => {
    if (label === "LOW") return { stroke: "#10b981", glow: "rgba(16,185,129,0.3)" };
    if (label === "MEDIUM") return { stroke: "#f59e0b", glow: "rgba(245,158,11,0.3)" };
    return { stroke: "#ef4444", glow: "rgba(239,68,68,0.3)" };
  };

  const color = getColor();

  const getGlowClass = () => {
    if (label === "LOW") return "glow-green";
    if (label === "MEDIUM") return "glow-amber";
    return "glow-red";
  };

  const getRiskDescription = () => {
    if (label === "LOW") return "Low manufacturing risk";
    if (label === "MEDIUM") return "Moderate risk — review needed";
    return "High risk — critical issues found";
  };

  return (
    <div className="flex flex-col items-center gap-4">
      <div className={`relative ${getGlowClass()} rounded-full`}>
        <svg
          width={size}
          height={size}
          className="transform -rotate-90"
        >
          {/* Background track */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            className="risk-gauge-track"
          />
          {/* Animated fill */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            className="risk-gauge-fill"
            stroke={color.stroke}
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            style={{
              filter: `drop-shadow(0 0 8px ${color.glow})`,
            }}
          />
        </svg>

        {/* Center text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span
            className="text-5xl font-bold tabular-nums"
            style={{ color: color.stroke }}
          >
            {animatedScore}
          </span>
          <span className="text-xs text-slate-500 mt-1 font-medium tracking-wider uppercase">
            / 100
          </span>
        </div>
      </div>

      {/* Risk label badge */}
      <div className="text-center">
        <span
          className={`badge text-sm px-4 py-1.5 ${
            label === "LOW"
              ? "badge-low"
              : label === "MEDIUM"
              ? "badge-medium"
              : "badge-high"
          }`}
        >
          {label} RISK
        </span>
        <p className="text-xs text-slate-500 mt-2">{getRiskDescription()}</p>
      </div>
    </div>
  );
}
