/** First start only: turn the XERO_SEED_* variables into token files on the volume. */
import { existsSync } from 'node:fs';
import { COMPANIES, withCompany } from './company.js';
import { hasTokens, writeTokens } from './tokens.js';

export function seedTokens() {
  const report = {};
  for (const c of COMPANIES) {
    withCompany(c, () => {
      if (hasTokens()) { report[c] = 'tokens already on volume'; return; }
      const raw = process.env[`XERO_SEED_${c.toUpperCase()}`];
      if (!raw) { report[c] = 'NO SEED and no tokens: sign-in needed'; return; }
      try {
        const s = JSON.parse(Buffer.from(raw.trim(), 'base64').toString('utf8'));
        writeTokens({
          access_token: '', refresh_token: s.refresh_token, expires_at: 0,
          scope: s.scope, tenantId: s.tenantId, tenantName: s.tenantName,
          connected_at: s.created,
        });
        report[c] = `seeded ${s.tenantName}`;
      } catch { report[c] = 'SEED UNREADABLE'; }
    });
  }
  return report;
}
