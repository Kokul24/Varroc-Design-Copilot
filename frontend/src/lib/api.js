/**
 * api.js — API client for communicating with the FastAPI backend.
 * Handles all HTTP requests and error handling.
 */

import { authenticatedFetch } from "@/lib/auth";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  "http://localhost:8000";

/**
 * Upload a file for DFM analysis.
 * @param {File} file - The CAD file to analyze
 * @param {string} material - Selected material type
 * @returns {Promise<object>} Analysis results
 */
export async function analyzeFile(file, material) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("material", material);

  const response = await authenticatedFetch(`/api/analyze`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Analysis failed (${response.status})`);
  }

  return response.json();
}

/**
 * Get a specific analysis by ID.
 * @param {string} id - Analysis UUID
 * @returns {Promise<object>} Analysis record
 */
export async function getAnalysis(id) {
  const response = await authenticatedFetch(`/api/analyses/${id}`);

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error("Analysis not found");
    }
    throw new Error(`Failed to fetch analysis (${response.status})`);
  }

  return response.json();
}

/**
 * Get recent analyses for the dashboard.
 * @param {number} limit - Max number of results
 * @returns {Promise<object[]>} List of analysis summaries
 */
export async function getRecentAnalyses(limit = 10) {
  const response = await authenticatedFetch(`/api/analyses?limit=${limit}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch recent analyses (${response.status})`);
  }

  const data = await response.json();
  return data.analyses || [];
}

/**
 * Get available materials list.
 * @returns {Promise<object[]>} List of materials
 */
export async function getMaterials() {
  const response = await fetch(`${API_BASE}/api/materials`);

  if (!response.ok) {
    throw new Error(`Failed to fetch materials (${response.status})`);
  }

  const data = await response.json();
  return data.materials || [];
}

/**
 * Check backend health.
 * @returns {Promise<boolean>}
 */
export async function checkHealth() {
  try {
    const response = await fetch(`${API_BASE}/api/health`);
    return response.ok;
  } catch {
    return false;
  }
}

/**
 * Login against backend auth endpoint.
 * @param {string} email
 * @param {string} password
 * @returns {Promise<object>}
 */
export async function login(email, password) {
  const response = await fetch(`${API_BASE}/login`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Login failed (${response.status})`);
  }

  return response.json();
}
