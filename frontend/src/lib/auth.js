export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  "http://localhost:8000";

export async function isAuthenticated() {
  return validateSession();
}

export async function clearAuthSession() {
  try {
    await fetch(`${API_BASE}/logout`, {
      method: "POST",
      credentials: "include",
    });
  } catch {
    // Ignore network errors during logout cleanup.
  }
}

async function refreshSession() {
  const response = await fetch(`${API_BASE}/refresh`, {
    method: "POST",
    credentials: "include",
  });
  return response.ok;
}

export async function authenticatedFetch(path, options = {}, retry = true) {
  const mergedOptions = {
    ...options,
    credentials: "include",
    headers: {
      ...(options.headers || {}),
    },
  };

  const response = await fetch(`${API_BASE}${path}`, mergedOptions);
  if (response.status === 401 && retry) {
    const refreshed = await refreshSession();
    if (refreshed) {
      return authenticatedFetch(path, options, false);
    }
  }

  return response;
}

export async function validateSession() {
  const response = await authenticatedFetch("/dashboard-data", {
    method: "GET",
  });
  return response.ok;
}
