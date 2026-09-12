export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message); }
}

const BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');
let sessionVersion = 0;
let refreshPromise: Promise<boolean> | null = null;

export function saveTokens(access: string, refresh: string) {
  sessionVersion += 1;
  localStorage.setItem('access_token', access);
  localStorage.setItem('refresh_token', refresh);
}

export function clearSession() {
  sessionVersion += 1;
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('user');
  window.dispatchEvent(new Event('plantdoc:logout'));
}

function errorText(value: unknown): string {
  if (typeof value === 'string') return value;
  if (Array.isArray(value)) return value.map(errorText).join(' ');
  if (value && typeof value === 'object') return Object.values(value).map(errorText).join(' ');
  return '';
}

async function refreshToken(): Promise<boolean> {
  if (refreshPromise) return refreshPromise;
  const refresh = localStorage.getItem('refresh_token');
  if (!refresh) { clearSession(); return false; }
  const version = sessionVersion;
  refreshPromise = (async () => {
    const response = await fetch(BASE_URL + '/api/users/refresh/', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh }), signal: AbortSignal.timeout(30000),
    });
    if (version !== sessionVersion) return false;
    if (response.ok) {
      const data = await response.json();
      if (version !== sessionVersion) return false;
      localStorage.setItem('access_token', data.access);
      return true;
    }
    if (response.status === 400 || response.status === 401) clearSession();
    throw new ApiError('Unable to renew your session. Please try again.', response.status);
  })().finally(() => { refreshPromise = null; });
  return refreshPromise;
}

type RequestOptions = RequestInit & { auth?: boolean };

export async function apiResponse(path: string, options: RequestOptions = {}): Promise<Response> {
  const { auth = true, ...init } = options;
  const version = sessionVersion;
  const send = () => {
    const headers = new Headers(init.headers);
    if (!headers.has('Language')) headers.set('Language', localStorage.getItem('i18nextLng') || 'en');
    const token = localStorage.getItem('access_token');
    if (auth && token) headers.set('Authorization', 'Bearer ' + token);
    if (init.body && !(init.body instanceof FormData)) headers.set('Content-Type', 'application/json');
    return fetch(BASE_URL + path, { ...init, headers, signal: init.signal ? AbortSignal.any([init.signal, AbortSignal.timeout(90000)]) : AbortSignal.timeout(90000) });
  };
  let response: Response;
  try {
    response = await send();
    if (auth && version !== sessionVersion) throw new ApiError('Your session changed. Please sign in again.', 401);
    if (auth && response.status === 401 && await refreshToken()) {
      if (version !== sessionVersion) throw new ApiError('Your session changed. Please sign in again.', 401);
      response = await send();
    }
  } catch (error) {
    if (error instanceof ApiError || (error instanceof DOMException && error.name === 'AbortError')) throw error;
    throw new ApiError('Could not reach PlantDoc. The server may be waking up; please try again shortly.', 0);
  }
  if (auth && version !== sessionVersion) throw new ApiError('Your session changed. Please sign in again.', 401);
  if (!response.ok) {
    const data: unknown = await response.json().catch(() => null);
    throw new ApiError(errorText(data) || 'Request failed. Please try again.', response.status);
  }
  return response;
}

export async function api<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await apiResponse(path, options);
  return response.status === 204 ? undefined as T : response.json();
}

export function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : 'Something went wrong. Please try again.';
}

export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
