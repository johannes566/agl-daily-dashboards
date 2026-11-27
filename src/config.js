/**
 * Configuration loading and validation.
 *
 * Secrets come from a .env file in the project root, which is blocked by
 * .gitignore. Nothing in this file ever prints a secret.
 */
import { existsSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const PROJECT_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const ENV_PATH = resolve(PROJECT_ROOT, '.env');

/** Xero's fixed endpoints. Hard-coded so they can never be redirected elsewhere. */
export const XERO = Object.freeze({
  AUTHORIZE_URL: 'https://login.xero.com/identity/connect/authorize',
  TOKEN_URL: 'https://identity.xero.com/connect/token',
  CONNECTIONS_URL: 'https://api.xero.com/connections',
  API_HOST: 'api.xero.com',
  API_BASE: 'https://api.xero.com/api.xro/2.0',
});

/**
 * Stage 2 scopes — the MINIMUM needed to authenticate, identify the
 * organisation, and read quotes. Every entry is read-only.
 *
 *   offline_access             stay connected without logging in again
 *   accounting.settings.read   organisation details (and later: accounts,
 *                              tracking categories)
 *   accounting.invoices.read   sales documents, which is where Quotes live
 *
 * VERIFIED 2026-09-15 against a live South African organisation: Xero
 * accepted accounting.invoices.read and GET /Quotes returned HTTP 200 with
 * full quote and line-item data. This settles a question that could NOT be
 * answered from Xero's published documentation, whose OpenAPI spec still
 * lists the legacy accounting.transactions.read for Quotes.
 *
 * Stage 3 adds accounting.payments.read and accounting.banktransactions.read.
 * Chart of accounts, bank account details and tracking categories are NOT
 * covered here: Xero's official connector already serves those correctly, so
 * duplicating them would add code for no benefit. Bank transactions ARE built
 * here because the official connector exposes only UNRECONCILED entries,
 * which hides nearly all history.
 */
export const SCOPES = Object.freeze([
  'offline_access',
  'accounting.settings.read',
  'accounting.invoices.read',
  // Stage 3 additions:
  'accounting.payments.read',
  'accounting.banktransactions.read',
  // Stage 6 addition: bank reports. Xero REJECTED the undocumented
  // 'accounting.reports.bankstatement.read' (invalid_scope, 2026-10-07).
  // banksummary is Xero's documented granular scope for its bank reports;
  // whether it also opens the BankStatement report is tested live.
  'accounting.reports.banksummary.read',
]);

export function loadConfig() {
  if (existsSync(ENV_PATH)) {
    // Built into Node 20.12+ — avoids a third-party dotenv dependency.
    process.loadEnvFile(ENV_PATH);
  }

  const clientId = (process.env.XERO_CLIENT_ID || '').trim();
  const clientSecret = (process.env.XERO_CLIENT_SECRET || '').trim();
  const redirectUri = (process.env.XERO_REDIRECT_URI || 'http://localhost:8787/callback').trim();

  // Both are always required. Even a pure read can trigger a token refresh,
  // and refresh authenticates to Xero with clientId:clientSecret - so a config
  // that omits the secret fails later with an opaque "invalid_client" instead
  // of saying what is actually wrong.
  const missing = [];
  if (!clientId) missing.push('XERO_CLIENT_ID');
  if (!clientSecret) missing.push('XERO_CLIENT_SECRET');

  if (missing.length) {
    throw new ConfigError(
      `Missing required setting(s): ${missing.join(', ')}\n\n` +
        `Expected them in:\n  ${ENV_PATH}\n\n` +
        `Fix: copy .env.example to .env and paste the values from your Xero\n` +
        `app page at https://developer.xero.com/app/manage`
    );
  }

  let parsedRedirect;
  try {
    parsedRedirect = new URL(redirectUri);
  } catch {
    throw new ConfigError(`XERO_REDIRECT_URI is not a valid URL: ${redirectUri}`);
  }

  return {
    clientId,
    clientSecret,
    redirectUri,
    callbackPort: Number(parsedRedirect.port || 80),
    callbackPath: parsedRedirect.pathname,
    projectRoot: PROJECT_ROOT,
    envPath: ENV_PATH,
  };
}

export class ConfigError extends Error {
  constructor(message) {
    super(message);
    this.name = 'ConfigError';
  }
}

/** Show only enough of an identifier to confirm it, never the whole value. */
export function maskIdentifier(value) {
  if (!value) return '(not set)';
  const s = String(value);
  if (s.length <= 8) return '*'.repeat(s.length);
  return `${s.slice(0, 4)}…${s.slice(-4)} (${s.length} chars)`;
}
