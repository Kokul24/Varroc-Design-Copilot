export const AUTH_TOKEN_KEY = "cadguard_token";
export const AUTH_USER_KEY = "cadguard_user";
export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  "http://localhost:8000";

export function getAuthToken() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(AUTH_TOKEN_KEY);
}

export function isAuthenticated() {
  return Boolean(getAuthToken());
}

export function setAuthSession(token, user) {
  if (typeof window === "undefined") return;
  localStorage.setItem(AUTH_TOKEN_KEY, token);
  localStorage.setItem(AUTH_USER_KEY, JSON.stringify(user));
}

export function clearAuthSession() {
  if (typeof window === "undefined") return;
  localStorage.removeItem(AUTH_TOKEN_KEY);
  localStorage.removeItem(AUTH_USER_KEY);
}

export async function authenticatedFetch(path, options = {}) {
  const token = getAuthToken();
  if (!token) {
    throw new Error("Missing authentication token");
  }

  const mergedOptions = {
    ...options,
    headers: {
      ...(options.headers || {}),
      Authorization: `Bearer ${token}`,
    },
  };

  return fetch(`${API_BASE}${path}`, mergedOptions);
}

export async function validateSession() {
  const response = await authenticatedFetch("/dashboard-data", {
    method: "GET",
  });
  return response.ok;
}
