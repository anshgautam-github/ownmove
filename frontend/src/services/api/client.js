import { env } from '../../config/env';
import { supabase } from '../supabase/client';

/**
 * HTTP client for the FastAPI backend.
 *
 * Auth model: Supabase issues the JWT (Google OAuth or email/password), the
 * browser holds the session, and we forward the access token as a Bearer
 * header. FastAPI then verifies that token against Supabase's JWKS / JWT
 * secret. This keeps Supabase as the single identity provider while letting
 * FastAPI own authorisation for its own endpoints.
 *
 * Used by the Career AI dashboards (Profile Analysis, Career Roadmap,
 * Career Simulation, AI Coach) — see services/api/{profileAnalysis,
 * careerRoadmap,careerSimulation,aiCoach}.js. Everything else still goes
 * straight to Supabase (see services/supabase/*).
 */

const DEFAULT_TIMEOUT_MS = 15000;
// Retries only apply to network failures and 5xx responses — never to 4xx,
// which mean the request itself was wrong and retrying it changes nothing.
const RETRYABLE_STATUS = new Set([502, 503, 504]);
const MAX_RETRIES = 2;
const RETRY_BASE_DELAY_MS = 400;

export class ApiError extends Error {
  constructor(message, { status, code, details } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

async function getAccessToken() {
  // getSession() reads the locally cached session synchronously-ish; it does
  // NOT make a network round-trip the way getUser() does.
  const { data: { session } } = await supabase.auth.getSession();
  return session?.access_token ?? null;
}

function sleep(ms) {
  return new Promise((resolve) => { setTimeout(resolve, ms); });
}

// Combines the caller's own AbortSignal (if any) with an internal timeout,
// so a request can still be cancelled early (tab-switch, unmount) while also
// giving up on its own after DEFAULT_TIMEOUT_MS instead of hanging forever
// on a stalled connection.
function withTimeout(signal, timeoutMs) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(new DOMException('Timeout', 'TimeoutError')), timeoutMs);

  if (signal) {
    if (signal.aborted) controller.abort(signal.reason);
    else signal.addEventListener('abort', () => controller.abort(signal.reason), { once: true });
  }

  return { signal: controller.signal, cancel: () => clearTimeout(timer) };
}

/**
 * @param {string} path      Path beginning with "/", e.g. "/api/v1/profiles/me"
 * @param {object} [options]
 * @param {string} [options.method='GET']
 * @param {any}    [options.body]      Serialised as JSON when present
 * @param {object} [options.params]    Appended as a query string
 * @param {boolean}[options.auth=true] Attach the Supabase bearer token
 * @param {AbortSignal} [options.signal]
 * @param {number} [options.timeoutMs=15000]
 * @param {number} [options.retries=2] Only applied to network errors / 502-504
 */
export async function request(path, options = {}) {
  const {
    method = 'GET',
    body,
    params,
    auth = true,
    signal,
    timeoutMs = DEFAULT_TIMEOUT_MS,
    retries = MAX_RETRIES,
    headers: extraHeaders = {},
  } = options;

  if (!env.apiBaseUrl) {
    // Fail fast and explicitly rather than constructing a URL against
    // `undefined` and producing a confusing browser-level network error —
    // this is the one message a developer actually needs to see.
    throw new ApiError(
      'The app is not configured to reach its backend (VITE_API_BASE_URL is missing). ' +
        (env.isDev ? 'Set it in frontend/.env and restart the dev server.' : 'Set it in this deployment\'s environment configuration.'),
      { status: 0, code: 'missing_config' }
    );
  }

  const url = new URL(path, env.apiBaseUrl);
  if (params) {
    Object.entries(params)
      .filter(([, v]) => v !== undefined && v !== null)
      .forEach(([k, v]) => url.searchParams.set(k, String(v)));
  }

  const headers = { Accept: 'application/json', ...extraHeaders };
  if (body !== undefined) headers['Content-Type'] = 'application/json';

  if (auth) {
    const token = await getAccessToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  let attempt = 0;
  for (;;) {
    const { signal: timedSignal, cancel } = withTimeout(signal, timeoutMs);
    let response;
    try {
      response = await fetch(url.toString(), {
        method,
        headers,
        signal: timedSignal,
        body: body === undefined ? undefined : JSON.stringify(body),
      });
    } catch (cause) {
      cancel();

      // Caller explicitly cancelled (e.g. unmount, superseded request) —
      // never retry, and don't disguise it as a generic failure.
      if (signal?.aborted) {
        throw new ApiError('Request cancelled.', { status: 0, code: 'cancelled' });
      }

      const timedOut = cause?.name === 'TimeoutError' || cause?.name === 'AbortError';
      if (attempt < retries) {
        attempt += 1;
        await sleep(RETRY_BASE_DELAY_MS * 2 ** (attempt - 1));
        continue;
      }

      throw new ApiError(
        timedOut
          ? 'The server took too long to respond. Please try again.'
          : 'Could not reach the server. Check your connection and try again.',
        { status: 0, code: timedOut ? 'timeout' : 'network_error', details: cause?.message }
      );
    }
    cancel();

    if (response.status === 204) return null;

    if (RETRYABLE_STATUS.has(response.status) && attempt < retries) {
      attempt += 1;
      await sleep(RETRY_BASE_DELAY_MS * 2 ** (attempt - 1));
      continue;
    }

    const payload = await response.json().catch(() => null);

    if (!response.ok) {
      throw new ApiError(payload?.detail || payload?.message || 'Request failed. Please try again.', {
        status: response.status,
        code: payload?.code,
        details: payload,
      });
    }

    return payload;
  }
}

export const api = {
  get: (path, options) => request(path, { ...options, method: 'GET' }),
  post: (path, body, options) => request(path, { ...options, method: 'POST', body }),
  patch: (path, body, options) => request(path, { ...options, method: 'PATCH', body }),
  put: (path, body, options) => request(path, { ...options, method: 'PUT', body }),
  delete: (path, options) => request(path, { ...options, method: 'DELETE' }),
};

export default api;
