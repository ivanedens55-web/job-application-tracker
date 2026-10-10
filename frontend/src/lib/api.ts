// The only place the frontend talks to the backend. No database access, no secrets.
import type { Application, ApplicationInput, Token, User, FieldError } from "./types";

const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
const TOKEN_KEY = "jobtracker_token";

/** An error the UI can show as-is. */
export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details: FieldError[] = [],
  ) {
    super(message);
  }
}

// ----- Token storage (see README: "Token storage trade-off") -----

export function getToken(): string | null {
  return typeof window === "undefined" ? null : sessionStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  sessionStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  sessionStorage.removeItem(TOKEN_KEY);
}

// ----- Request helper -----

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, { ...options, headers });
  } catch {
    throw new ApiError(
      0,
      "network_error",
      "Can't reach the server. If it was asleep it can take up to a minute to wake up, so try again shortly.",
    );
  }

  if (response.status === 204) return undefined as T;

  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const error = body?.error;
    throw new ApiError(
      response.status,
      error?.code ?? "unknown_error",
      error?.message ?? "Something went wrong. Please try again.",
      error?.details ?? [],
    );
  }
  return body as T;
}

// ----- Endpoints -----

export const api = {
  register: (email: string, password: string) =>
    request<User>("/auth/register", { method: "POST", body: JSON.stringify({ email, password }) }),

  login: (email: string, password: string) =>
    request<Token>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),

  me: () => request<User>("/auth/me"),

  listApplications: () => request<{ items: Application[] }>("/applications"),

  createApplication: (input: ApplicationInput) =>
    request<Application>("/applications", { method: "POST", body: JSON.stringify(input) }),

  updateApplication: (id: number, changes: Partial<ApplicationInput>) =>
    request<Application>(`/applications/${id}`, { method: "PATCH", body: JSON.stringify(changes) }),

  deleteApplication: (id: number) => request<void>(`/applications/${id}`, { method: "DELETE" }),
};
