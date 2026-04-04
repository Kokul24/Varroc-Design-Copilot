"use client";

import { useState, useCallback, useEffect } from "react";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import FileUpload from "@/components/FileUpload";
import MaterialSelector from "@/components/MaterialSelector";
import RecentAnalyses from "@/components/RecentAnalyses";
import { clearAuthSession, isAuthenticated, validateSession, authenticatedFetch } from "@/lib/auth";

/**
 * Home Page — Upload CAD file, select material, analyze.
 */
export default function HomePage() {
  const router = useRouter();
  const [authChecked, setAuthChecked] = useState(false);
  const [file, setFile] = useState(null);
  const [material, setMaterial] = useState("aluminum");
  const [analyzing, setAnalyzing] = useState(false);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const checkAuth = async () => {
      if (!isAuthenticated()) {
        router.replace("/login");
        return;
      }

      try {
        const valid = await validateSession();
        if (!valid) {
          clearAuthSession();
          router.replace("/login");
          return;
        }
        setAuthChecked(true);
      } catch {
        clearAuthSession();
        router.replace("/login");
      }
    };

    checkAuth();
  }, [router]);

  const handleAnalyze = useCallback(async () => {
    if (!file) {
      toast.error("Please select a file to analyze");
      return;
    }

    setAnalyzing(true);
    setProgress(0);

    // Simulate progress stages
    const stages = [
      { p: 15, label: "Uploading file..." },
      { p: 35, label: "Extracting features..." },
      { p: 55, label: "Running AI prediction..." },
      { p: 75, label: "Computing SHAP values..." },
      { p: 90, label: "Generating recommendations..." },
    ];

    let stageIndex = 0;
    const progressInterval = setInterval(() => {
      if (stageIndex < stages.length) {
        setProgress(stages[stageIndex].p);
        stageIndex++;
      }
    }, 500);

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("material", material);

      const response = await authenticatedFetch("/api/analyze", {
        method: "POST",
        body: formData,
      });

      clearInterval(progressInterval);
      setProgress(100);

      if (response.status === 401) {
        clearAuthSession();
        router.replace("/login");
        return;
      }

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || `Analysis failed (${response.status})`);
      }

      const result = await response.json();
      toast.success("Analysis complete!");

      // Navigate to results page
      setTimeout(() => {
        router.push(`/results/${result.id}`);
      }, 300);
    } catch (error) {
      clearInterval(progressInterval);
      toast.error(error.message || "Analysis failed. Is the backend running?");
      setProgress(0);
      setAnalyzing(false);
    }
  }, [file, material, router]);

  if (!authChecked) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="glass-card p-8 text-center text-slate-300">Checking session...</div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Hero Section */}
      <div className="text-center mb-12 animate-fade-in">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand-500/10 border border-brand-500/20 text-xs font-medium text-brand-400 mb-4">
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
          </svg>
          Explainable AI · SHAP Analysis · DFM Rules
        </div>
        <h1 className="text-4xl sm:text-5xl font-bold mb-3">
          <span className="gradient-text">AI-Powered</span>{" "}
          <span className="text-slate-100">CAD Validation</span>
        </h1>
        <p className="text-slate-400 max-w-2xl mx-auto text-lg">
          Upload your CAD file to instantly analyze manufacturability risks,
          understand AI decisions with SHAP, and get actionable engineering
          recommendations.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Main Upload Panel */}
        <div className="lg:col-span-2 space-y-6">
          {/* Upload Card */}
          <div className="glass-card p-6 glow-brand animate-slide-up">
            <div className="flex items-center gap-2 mb-5">
              <div className="w-8 h-8 rounded-lg bg-brand-500/10 flex items-center justify-center">
                <svg
                  className="w-4 h-4 text-brand-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
                  />
                </svg>
              </div>
              <h2 className="text-lg font-semibold text-slate-200">
                Upload & Analyze
              </h2>
            </div>

            <FileUpload onFileSelect={setFile} disabled={analyzing} />

            <div className="mt-5">
              <MaterialSelector
                value={material}
                onChange={setMaterial}
                disabled={analyzing}
              />
            </div>

            {/* Analyze Button */}
            <div className="mt-6">
              {analyzing ? (
                <div className="space-y-3">
                  {/* Progress bar */}
                  <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-brand-500 to-brand-400 transition-all duration-500 ease-out"
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                  <div className="flex items-center justify-between text-xs text-slate-500">
                    <span className="flex items-center gap-2">
                      <svg
                        className="w-3.5 h-3.5 animate-spin text-brand-400"
                        fill="none"
                        viewBox="0 0 24 24"
                      >
                        <circle
                          className="opacity-25"
                          cx="12"
                          cy="12"
                          r="10"
                          stroke="currentColor"
                          strokeWidth="4"
                        />
                        <path
                          className="opacity-75"
                          fill="currentColor"
                          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                        />
                      </svg>
                      Analyzing...
                    </span>
                    <span>{progress}%</span>
                  </div>
                </div>
              ) : (
                <button
                  onClick={handleAnalyze}
                  disabled={!file}
                  className={`btn-primary w-full text-base py-3.5 ${
                    !file ? "opacity-50 cursor-not-allowed" : ""
                  }`}
                  id="analyze-btn"
                >
                  <svg
                    className="w-5 h-5 mr-2"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23.693L5 14.5m14.8.8l1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0112 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5"
                    />
                  </svg>
                  Analyze Manufacturability
                </button>
              )}
            </div>
          </div>

          {/* How it works */}
          <div className="glass-card p-6 animate-slide-up" style={{ animationDelay: "200ms" }}>
            <h3 className="text-sm font-semibold text-slate-300 mb-4">
              How It Works
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
              {[
                {
                  step: "01",
                  title: "Upload",
                  desc: "Upload STL or any CAD file",
                  icon: "📤",
                },
                {
                  step: "02",
                  title: "Extract",
                  desc: "AI extracts manufacturing features",
                  icon: "🔬",
                },
                {
                  step: "03",
                  title: "Analyze",
                  desc: "ML model predicts risk score",
                  icon: "🧠",
                },
                {
                  step: "04",
                  title: "Explain",
                  desc: "SHAP reveals feature impacts",
                  icon: "📊",
                },
              ].map((item) => (
                <div
                  key={item.step}
                  className="text-center p-3 rounded-lg hover:bg-slate-800/30 transition-colors"
                >
                  <span className="text-2xl mb-2 block">{item.icon}</span>
                  <span className="text-[10px] text-brand-500 font-bold block mb-1">
                    STEP {item.step}
                  </span>
                  <span className="text-sm font-medium text-slate-200 block">
                    {item.title}
                  </span>
                  <span className="text-xs text-slate-500">{item.desc}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Sidebar — Recent Analyses */}
        <div className="space-y-6 animate-slide-up" style={{ animationDelay: "100ms" }}>
          <div className="glass-card p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
                <svg
                  className="w-4 h-4 text-slate-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                Recent Analyses
              </h2>
            </div>
            <RecentAnalyses />
          </div>

          {/* Stats Cards */}
          <div className="grid grid-cols-2 gap-3">
            <div className="glass-card-light p-4 text-center">
              <span className="text-2xl font-bold gradient-text block">7</span>
              <span className="text-xs text-slate-500">Features Analyzed</span>
            </div>
            <div className="glass-card-light p-4 text-center">
              <span className="text-2xl font-bold gradient-text block">5+</span>
              <span className="text-xs text-slate-500">DFM Rules</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
