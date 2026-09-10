/**
 * Single place where `import.meta.env` is read.
 *
 * Keeping env access centralised means: one place to validate, one place to
 * change when we add staging/prod targets, and no scattered
 * `import.meta.env.VITE_...` string literals across components.
 */

export const env = {
  supabaseUrl: import.meta.env.VITE_SUPABASE_URL,
  supabaseAnonKey: import.meta.env.VITE_SUPABASE_ANON_KEY,

  // Base URL of the FastAPI backend. No hardcoded localhost fallback here on
  // purpose — a missing value in a production build must fail loudly (see
  // services/api/client.js, which refuses to make a request rather than
  // silently pointing at localhost:8000 from a real user's browser). `null`
  // is a deliberate, explicit "not configured" value rather than a guess.
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || null,

  isDev: import.meta.env.DEV,
  isProd: import.meta.env.PROD,
};

/**
 * Warn loudly in dev if required config is missing, rather than failing with
 * a confusing runtime error deep inside a network call.
 */
export function assertEnv() {
  const missing = [];
  if (!env.supabaseUrl) missing.push('VITE_SUPABASE_URL');
  if (!env.supabaseAnonKey) missing.push('VITE_SUPABASE_ANON_KEY');
  if (!env.apiBaseUrl) missing.push('VITE_API_BASE_URL');

  if (missing.length > 0) {
    console.warn(
      `Missing env vars: ${missing.join(', ')}. ` +
        (env.isDev
          ? 'Set them in frontend/.env and restart the Vite dev server.'
          : 'Set them in your production build/deploy environment before shipping.')
    );
  }

  return missing.length === 0;
}

export default env;
