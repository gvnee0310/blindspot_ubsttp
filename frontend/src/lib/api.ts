import type {
  Debrief,
  DecisionInput,
  Session,
  SessionContext,
  Token,
  User,
} from '@/types';

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? '/api';

// --- Token storage -----------------------------------------------------------

const TOKEN_KEY = 'blindspot.token';
const USER_KEY = 'blindspot.user';

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function getStoredUser(): User | null {
  const raw = localStorage.getItem(USER_KEY);
  return raw ? (JSON.parse(raw) as User) : null;
}

export function storeAuth(token: Token): void {
  localStorage.setItem(TOKEN_KEY, token.access_token);
  localStorage.setItem(USER_KEY, JSON.stringify(token.user));
}

export function clearAuth(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

// --- Low-level fetch wrapper -------------------------------------------------

class ApiError extends Error {
  constructor(public status: number, public detail: string) {
    super(detail);
    this.name = 'ApiError';
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  { auth = true }: { auth?: boolean } = {},
): Promise<T> {
  const headers = new Headers(options.headers ?? {});
  if (!headers.has('Content-Type') && options.body) {
    headers.set('Content-Type', 'application/json');
  }
  if (auth) {
    const token = getStoredToken();
    if (token) headers.set('Authorization', `Bearer ${token}`);
  }
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const data = await response.json();
      detail = (data as { detail?: string }).detail ?? detail;
    } catch {
      // ignore
    }
    throw new ApiError(response.status, detail);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export { ApiError };

// --- Endpoints ---------------------------------------------------------------

export const api = {
  register: (email: string, display_name: string, password: string) =>
    request<Token>(
      '/auth/register',
      { method: 'POST', body: JSON.stringify({ email, display_name, password }) },
      { auth: false },
    ),
  login: (email: string, password: string) =>
    request<Token>(
      '/auth/login',
      { method: 'POST', body: JSON.stringify({ email, password }) },
      { auth: false },
    ),
  createSession: (context: SessionContext) =>
    request<Session>('/sessions/', { method: 'POST', body: JSON.stringify({ context }) }),
  listSessions: () => request<Session[]>('/sessions/'),
  getSession: (id: number) => request<Session>(`/sessions/${id}`),
  completeSession: (id: number) =>
    request<Session>(`/sessions/${id}/complete`, { method: 'POST' }),
  submitDecision: (input: DecisionInput) =>
    request<unknown>('/decisions/', { method: 'POST', body: JSON.stringify(input) }),
  getDebrief: (sessionId: number) => request<Debrief>(`/debrief/${sessionId}`),
};
