"use client";

import { useState, useEffect, useRef } from "react";

/**
 * MaterialSelector — Dropdown with visual material cards.
 */

const FALLBACK_MATERIALS = [
  { value: "aluminum", label: "Aluminum" },
  { value: "steel", label: "Steel" },
  { value: "titanium", label: "Titanium" },
  { value: "plastic_abs", label: "Plastic (ABS)" },
  { value: "plastic_nylon", label: "Plastic (Nylon)" },
  { value: "copper", label: "Copper" },
  { value: "brass", label: "Brass" },
  { value: "stainless_steel", label: "Stainless Steel" },
];

const MATERIAL_ICONS = {
  aluminum: "🪶",
  steel: "⚙️",
  titanium: "💎",
  plastic_abs: "🧊",
  plastic_nylon: "🧵",
  copper: "🔶",
  brass: "🟡",
  stainless_steel: "🛡️",
};

const MATERIAL_DESCRIPTIONS = {
  aluminum: "Lightweight, corrosion-resistant",
  steel: "High strength, durable",
  titanium: "Premium strength-to-weight",
  plastic_abs: "Impact-resistant polymer",
  plastic_nylon: "Flexible engineering plastic",
  copper: "Excellent conductivity",
  brass: "Machinability, decorative",
  stainless_steel: "Corrosion-resistant alloy",
};

export default function MaterialSelector({ value, onChange, disabled }) {
  const [materials, setMaterials] = useState(FALLBACK_MATERIALS);
  const [isOpen, setIsOpen] = useState(false);
  const rootRef = useRef(null);

  useEffect(() => {
    // Try to fetch materials from API, fallback to defaults
    fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/materials`)
      .then((res) => res.json())
      .then((data) => {
        if (data.materials?.length) setMaterials(data.materials);
      })
      .catch(() => {
        /* Use fallback */
      });
  }, []);

  useEffect(() => {
    if (!isOpen) return;

    const handleOutsideClick = (event) => {
      if (rootRef.current && !rootRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleOutsideClick);
    return () => {
      document.removeEventListener("mousedown", handleOutsideClick);
    };
  }, [isOpen]);

  const selected = materials.find((m) => m.value === value) || materials[0];

  return (
    <div className="relative" ref={rootRef}>
      <label className="block text-sm font-medium text-slate-300 mb-2">
        Material Type
      </label>

      {/* Selected display */}
      <button
        type="button"
        onClick={() => !disabled && setIsOpen(!isOpen)}
        className={`w-full glass-card-light p-3.5 flex items-center gap-3 text-left transition-all duration-200 ${
          disabled
            ? "opacity-50 cursor-not-allowed"
            : "hover:border-brand-500/30 cursor-pointer"
        } ${isOpen ? "border-brand-500/40 !bg-brand-500/5" : ""}`}
        id="material-selector"
      >
        <span className="text-xl">{MATERIAL_ICONS[selected.value] || "⬜"}</span>
        <div className="flex-1">
          <span className="text-sm font-medium text-slate-200">
            {selected.label}
          </span>
          <span className="block text-xs text-slate-500">
            {MATERIAL_DESCRIPTIONS[selected.value] || ""}
          </span>
        </div>
        <svg
          className={`w-4 h-4 text-slate-500 transition-transform duration-200 ${
            isOpen ? "rotate-180" : ""
          }`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M19.5 8.25l-7.5 7.5-7.5-7.5"
          />
        </svg>
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div className="w-full mt-2 glass-card p-2 animate-fade-in max-h-64 overflow-y-auto border border-brand-500/20">
          {materials.map((mat) => (
            <button
              key={mat.value}
              onClick={() => {
                onChange?.(mat.value);
                setIsOpen(false);
              }}
              className={`w-full flex items-center gap-3 p-3 rounded-lg text-left transition-all duration-150 ${
                mat.value === value
                  ? "bg-brand-500/10 border border-brand-500/20"
                  : "hover:bg-slate-800/50"
              }`}
              id={`material-option-${mat.value}`}
            >
              <span className="text-lg">
                {MATERIAL_ICONS[mat.value] || "⬜"}
              </span>
              <div>
                <span className="text-sm font-medium text-slate-200">
                  {mat.label}
                </span>
                <span className="block text-xs text-slate-500">
                  {MATERIAL_DESCRIPTIONS[mat.value] || ""}
                </span>
              </div>
              {mat.value === value && (
                <svg
                  className="w-4 h-4 text-brand-400 ml-auto"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M4.5 12.75l6 6 9-13.5"
                  />
                </svg>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
