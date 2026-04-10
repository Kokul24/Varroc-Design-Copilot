"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import toast from "react-hot-toast";
import RiskGauge from "@/components/RiskGauge";
import ShapChart from "@/components/ShapChart";
import ViolationsList from "@/components/ViolationsList";
import Recommendations from "@/components/Recommendations";
import FeatureTable from "@/components/FeatureTable";
import { authenticatedFetch, clearAuthSession, isAuthenticated, validateSession } from "@/lib/auth";

/**
 * Results Page — Display comprehensive analysis results.
 */
export default function ResultsPage() {
  const params = useParams();
  const router = useRouter();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const run = async () => {
      try {
        const authenticated = await isAuthenticated();
        if (!authenticated) {
          await clearAuthSession();
          router.replace("/login");
          return;
        }

        const valid = await validateSession();
        if (!valid) {
          await clearAuthSession();
          router.replace("/login");
          return;
        }
      } catch {
        await clearAuthSession();
        router.replace("/login");
        return;
      }

      if (params?.id) {
        fetchResults(params.id);
      }
    };

    run();
  }, [params?.id]);

  async function fetchResults(id) {
    try {
      const res = await authenticatedFetch(`/api/analyses/${id}`);

      if (res.status === 401) {
        await clearAuthSession();
        router.replace("/login");
        return;
      }

      if (!res.ok) {
        if (res.status === 404) throw new Error("Analysis not found");
        throw new Error(`Failed to load results (${res.status})`);
      }

      const result = await res.json();
      setData(result);
    } catch (err) {
      setError(err.message);
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="animate-pulse space-y-6">
          <div className="h-8 w-48 rounded shimmer" />
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="h-72 rounded-2xl shimmer" />
            <div className="lg:col-span-2 h-72 rounded-2xl shimmer" />
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="h-64 rounded-2xl shimmer" />
            <div className="h-64 rounded-2xl shimmer" />
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="glass-card p-12 text-center">
          <div className="w-16 h-16 mx-auto rounded-2xl bg-red-500/10 flex items-center justify-center mb-4">
            <svg className="w-8 h-8 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-slate-200 mb-2">
            {error}
          </h2>
          <p className="text-slate-500 mb-6">
            The analysis could not be loaded. It may have expired or the ID is invalid.
          </p>
          <Link href="/" className="btn-primary">
            ← Back to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  if (!data) return null;

  const formatDate = (dateStr) => {
    if (!dateStr) return "Just now";
    return new Date(dateStr).toLocaleString();
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-8 animate-fade-in">
        <div>
          <Link
            href="/"
            className="text-xs text-brand-400 hover:text-brand-300 flex items-center gap-1 mb-2 transition-colors"
          >
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
            </svg>
            Back to Dashboard
          </Link>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-3">
            <svg className="w-6 h-6 text-brand-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
            </svg>
            {data.file_name}
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            {data.material} • Analyzed {formatDate(data.created_at)}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link href="/" className="btn-secondary text-sm py-2 px-4">
            New Analysis
          </Link>
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        {/* Risk Gauge */}
        <div className="glass-card p-6 flex items-center justify-center glow-brand animate-slide-up">
          <RiskGauge
            score={data.risk_score}
            label={data.risk_label}
            size={220}
          />
        </div>

        {/* SHAP Chart */}
        <div className="lg:col-span-2 glass-card p-6 animate-slide-up" style={{ animationDelay: "100ms" }}>
          <ShapChart
            shapValues={data.shap_values}
            featureValues={data.features}
          />
        </div>
      </div>

      {/* Features + Violations Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Features */}
        <div className="glass-card p-6 animate-slide-up" style={{ animationDelay: "200ms" }}>
          <FeatureTable features={data.features} />
        </div>

        {/* Violations */}
        <div className="glass-card p-6 animate-slide-up" style={{ animationDelay: "300ms" }}>
          <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2 mb-4">
            <svg className="w-4 h-4 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
            </svg>
            DFM Violations
            {data.violations?.length > 0 && (
              <span className="badge badge-high ml-2">{data.violations.length} found</span>
            )}
          </h3>
          <ViolationsList violations={data.violations} />
        </div>
      </div>

      {/* Recommendations */}
      <div className="glass-card p-6 animate-slide-up" style={{ animationDelay: "400ms" }}>
        <Recommendations data={data.recommendations} />
      </div>

      {/* Analysis Metadata Footer */}
      <div className="mt-6 flex items-center justify-center gap-6 text-xs text-slate-600 animate-fade-in" style={{ animationDelay: "500ms" }}>
        <span>Analysis ID: {data.id}</span>
        <span>•</span>
        <span>Risk Probability: {(data.probability || data.risk_score / 100).toFixed(4)}</span>
        <span>•</span>
        <span>SHAP Base: {data.shap_values?.base_value?.toFixed(4) || "N/A"}</span>
      </div>
    </div>
  );
}
