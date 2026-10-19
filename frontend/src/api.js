
const API_BASE_URL = "";

// Send requests to the FastAPI backend
export async function apiRequest(path, options = {}) {
  const token = localStorage.getItem("access_token");

  const headers = {
    ...(options.body
      ? { "Content-Type": "application/json" }
      : {}),
    ...(token
      ? { Authorization: `Bearer ${token}` }
      : {}),
    ...options.headers,
  };

  let response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers,
    });
  } catch {
    throw new Error(
      "Cannot connect to the backend. Make sure FastAPI is running on port 8000."
    );
  }

  // Handle responses that do not contain JSON
  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const detail = data?.detail;

    let message = "Request failed. Please try again.";

    if (typeof detail === "string") {
      message = detail;
    } else if (Array.isArray(detail)) {
      message = detail.map((item) => item.msg).join(", ");
    }

    if (response.status === 401) {
      localStorage.removeItem("access_token");
    }

    throw new Error(message);
  }

  return data;
}

// Register a new user
export async function register(name, email, password) {
  return apiRequest("/auth/register", {
    method: "POST",
    body: JSON.stringify({
      name,
      email,
      password,
    }),
  });
}

// Log in and save the access token
export async function login(email, password) {
  const data = await apiRequest("/auth/login", {
    method: "POST",
    body: JSON.stringify({
      email,
      password,
    }),
  });

  localStorage.setItem("access_token", data.access_token);

  return data;
}

// Get the currently logged-in user
export async function getCurrentUser() {
  return apiRequest("/auth/me");
}

// Log out the current user
export function logout() {
  localStorage.removeItem("access_token");
}

// Get work items from the backend
export async function getWorkItems(skip = 0, limit = 100) {
  return apiRequest(
    `/work-items/?skip=${skip}&limit=${limit}`
  );
}

// Get teams that the current user belongs to
export async function getTeams() {
  return apiRequest("/teams/");
}

// Create a work item
export async function createWorkItem(workItem) {
  return apiRequest("/work-items/", {
    method: "POST",
    headers: {
      "Idempotency-Key": crypto.randomUUID(),
    },
    body: JSON.stringify(workItem),
  });
}

// Update an existing work item
export async function updateWorkItem(itemId, workItem) {
  return apiRequest(`/work-items/${itemId}`, {
    method: "PUT",
    body: JSON.stringify(workItem),
  });
}

// Get one work item by ID
export async function getWorkItem(itemId) {
  return apiRequest(`/work-items/${itemId}`);
}
