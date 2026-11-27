/**
 * The ONLY code that talks to the Xero accounting API.
 *
 * ===================================================================
 * READ-ONLY CHOKE-POINT
 * ===================================================================
 * This module exports exactly one way to reach the accounting API:
 * xeroGet(). It takes no HTTP-method argument, so there is no code path
 * anywhere in this project that can POST, PUT, PATCH or DELETE an
 * accounting record. Two assertions below make that structural rather
 * than a matter of convention.
 *
 * Token refresh does POST, but only to identity.xero.com (Xero's login
 * service, not the accounting API) and only from refreshAccessToken().
 * That function cannot be pointed at api.xero.com.
 *
 * This is one of four independent layers. The others: read-only OAuth
 * scopes enforced by Xero itself, only read tools exposed over MCP, and
 * no SDK write methods present in the process.
 * ===================================================================
 */
import { XERO } from './config.js';
import { readTokens, writeTokens, withRefreshLock } from './tokens.js';

/** Refresh when fewer than this many seconds of validity remain. */
const REFRESH_MARGIN_SECONDS = 60;

/** Xero returns at most this many records per page. */
const PAGE_SIZE = 100;

export class XeroError extends Error {
  constructor(message, { status, xeroCode } = {}) {
    super(message);
    this.name = 'XeroError';
    this.status = status;
    this.xeroCode = xeroCode;
  }
}

export class NotAuthorisedError extends XeroError {}

/**
 * Exchange the refresh token for a new access token.
 * Hard-wired to Xero's identity host; it cannot reach the accounting API.
 */
async function refreshAccessToken(config, stored) {
  const basic = Buffer.from(`${config.clientId}:${config.clientSecret}`).toString('base64');

  const res = await fetch(XERO.TOKEN_URL, {
    method: 'POST',
    headers: {
      Authorization: `Basic ${basic}`,
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: new URLSearchParams({
      grant_type: 'refresh_token',
      refresh_token: stored.refresh_token,
    }),
  });

  if (!res.ok) {
    // Deliberately does NOT include the response body: it can echo token
    // material. The status and Xero's error code are enough to diagnose.
    let code = '';
    try {
      code = (await res.json())?.error || '';
    } catch {
      /* non-JSON error body: ignore rather than risk logging token material */
    }
    throw new NotAuthorisedError(
      `Could not refresh Xero authorisation (HTTP ${res.status}${code ? `, ${code}` : ''}).\n\n` +
        `This usually means the connection has expired or was revoked in Xero.\n` +
        `Fix: run "npm run auth" again to reconnect.`,
      { status: res.status, xeroCode: code }
    );
  }

  const fresh = await res.json();

  const updated = {
    ...stored,
    access_token: fresh.access_token,
    refresh_token: fresh.refresh_token ?? stored.refresh_token,
    expires_at: Date.now() + fresh.expires_in * 1000,
    scope: fresh.scope ?? stored.scope,
  };

  // Persist BEFORE using the new access token. The old refresh token is
  // already dead at this point, so saving first is what prevents lockout.
  writeTokens(updated);
  return updated;
}

/** Return a valid access token, refreshing first if it is about to expire. */
async function getValidTokens(config) {
  const stored = readTokens();
  if (!stored) {
    throw new NotAuthorisedError(
      `Not connected to Xero yet.\n\nFix: run "npm run auth" to authorise once in your browser.`
    );
  }

  const secondsLeft = (stored.expires_at - Date.now()) / 1000;
  if (secondsLeft > REFRESH_MARGIN_SECONDS) return stored;

  return withRefreshLock(async () => {
    // Re-read inside the lock: another process may have refreshed already.
    const latest = readTokens();
    const latestSecondsLeft = (latest.expires_at - Date.now()) / 1000;
    if (latestSecondsLeft > REFRESH_MARGIN_SECONDS) return latest;
    return refreshAccessToken(config, latest);
  });
}

/**
 * Perform a read from the Xero accounting API.
 *
 * @param {object} config      from loadConfig()
 * @param {string} path        e.g. "/Quotes" (appended to the API base)
 * @param {object} [params]    query string parameters
 * @returns {Promise<object>}  parsed JSON response
 */
export async function xeroGet(config, path, params = {}) {
  const tokens = await getValidTokens(config);

  const url = new URL(XERO.API_BASE + path);
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') {
      url.searchParams.set(key, String(value));
    }
  }

  // --- Structural guarantee #1: never leave the Xero accounting API host.
  if (url.host !== XERO.API_HOST) {
    throw new XeroError(`Refusing to call a non-Xero host: ${url.host}`);
  }

  if (!tokens.tenantId) {
    throw new NotAuthorisedError(
      `No Xero organisation is pinned to this connection.\n` +
        `Fix: run "npm run auth" again and choose the organisation.`
    );
  }

  const res = await fetch(url, {
    // --- Structural guarantee #2: the method is a literal, not a parameter.
    method: 'GET',
    headers: {
      Authorization: `Bearer ${tokens.access_token}`,
      'Xero-Tenant-Id': tokens.tenantId,
      Accept: 'application/json',
    },
  });

  if (res.status === 429) {
    const retryAfter = Number(res.headers.get('Retry-After') || 60);
    throw new XeroError(
      `Xero rate limit reached. Xero asks us to wait ${retryAfter} seconds before retrying.\n` +
        `(Limits are 60 calls/minute and 5000/day per organisation.)`,
      { status: 429 }
    );
  }

  if (res.status === 401) {
    throw new NotAuthorisedError(
      `Xero rejected the access token (HTTP 401).\nFix: run "npm run auth" again to reconnect.`,
      { status: 401 }
    );
  }

  if (res.status === 403) {
    throw new XeroError(
      `Xero refused this read (HTTP 403 - not permitted).\n\n` +
        `The most likely cause is that the granted scopes do not cover this\n` +
        `endpoint (${path}). This is harmless - nothing in Xero was changed.\n\n` +
        `Tell Claude which endpoint returned 403 and the scope list can be corrected.`,
      { status: 403 }
    );
  }

  if (!res.ok) {
    let detail = '';
    try {
      const body = await res.json();
      // Xero's own human-readable message only. Never headers, never tokens.
      detail = body?.Message || body?.Detail || body?.Title || '';
    } catch {
      /* ignore unparseable error bodies */
    }
    throw new XeroError(
      `Xero returned HTTP ${res.status} for ${path}${detail ? `: ${detail}` : ''}`,
      { status: res.status }
    );
  }

  return res.json();
}

/**
 * Read every page of a paginated endpoint.
 *
 * Xero signals "no more data" with an empty array - there is no total count
 * and no next-page marker. A caller that fetched page 1 and stopped would
 * silently under-report, and the result would look perfectly normal. This
 * loops until a page comes back empty and reports how many pages it read,
 * so truncation is visible rather than invisible.
 */
export async function xeroGetAllPages(config, path, collectionKey, params = {}, { maxPages = 200 } = {}) {
  const items = [];
  let requests = 0;
  let hitLimit = true;

  for (let page = 1; page <= maxPages; page++) {
    requests++;
    const body = await xeroGet(config, path, { ...params, page });
    const batch = body?.[collectionKey] ?? [];

    if (batch.length === 0) {
      hitLimit = false;
      break;
    }

    items.push(...batch);

    // Xero returns up to 100 per page; a short page means this was the last.
    if (batch.length < PAGE_SIZE) {
      hitLimit = false;
      break;
    }
  }

  if (hitLimit) {
    throw new XeroError(
      `Stopped after ${maxPages} pages as a safety limit, so the results may be incomplete.\n` +
        `Please tell Claude - this needs a date filter rather than a bigger limit.`
    );
  }

  return { items, requests };
}

/** List the Xero organisations this connection can see. */
export async function listConnections(accessToken) {
  const res = await fetch(XERO.CONNECTIONS_URL, {
    method: 'GET',
    headers: { Authorization: `Bearer ${accessToken}`, Accept: 'application/json' },
  });
  if (!res.ok) {
    throw new XeroError(`Could not list Xero organisations (HTTP ${res.status}).`, { status: res.status });
  }
  return res.json();
}
