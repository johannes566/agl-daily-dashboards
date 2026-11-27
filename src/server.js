/**
 * AGL daily dashboards service (read-only toward Xero).
 *  - GET /health                      liveness and token status (no secrets)
 *  - GET /internal/xero               read one Xero collection for the report builder
 *                                     (requires the x-internal-key header; localhost use only)
 * The accounting API is only ever read through xeroGetAllPages (GET only).
 */
import { createServer } from 'node:http';
import { createHmac, timingSafeEqual } from 'node:crypto';
import { existsSync, readFileSync } from 'node:fs';
import { join, basename } from 'node:path';
import { loadConfig } from './config.js';
import { xeroGetAllPages } from './xero.js';
import { withCompany, COMPANIES } from './company.js';
import { hasTokens, readTokens } from './tokens.js';
import { seedTokens } from './seed.js';
import { shapeInvoice, shapeQuote, shapeBankTransaction } from './shape.js';
import { selfTest } from './selftest.js';
import { startScheduler } from './scheduler.js';

const PORT = Number(process.env.PORT || 8080);
const INTERNAL_KEY = process.env.INTERNAL_KEY || '';
const ALLOWED = { // path -> collection key in Xero's reply
  '/Invoices': 'Invoices', '/Quotes': 'Quotes', '/Payments': 'Payments',
  '/BankTransactions': 'BankTransactions', '/Contacts': 'Contacts',
};

const SHAPE = { '/Invoices': shapeInvoice, '/Quotes': shapeQuote, '/BankTransactions': shapeBankTransaction };

const seedReport = seedTokens();
console.log('token seed:', JSON.stringify(seedReport));
const config = loadConfig();

const send = (res, code, body) => res.writeHead(code, { 'Content-Type': 'application/json' }).end(JSON.stringify(body));

createServer(async (req, res) => {
  const url = new URL(req.url, 'http://x');
  try {
    if (url.pathname === '/health') {
      const out = {};
      for (const c of COMPANIES) out[c] = withCompany(c, () => {
        if (!hasTokens()) return 'no tokens';
        const t = readTokens();
        return { organisation: t.tenantName, scope_count: String(t.scope || '').split(' ').length };
      });
      return send(res, 200, { ok: true, companies: out });
    }
    // Report PDFs: /r/<signature>/<file>.pdf. The signature is an HMAC of the file name made with INTERNAL_KEY,
    // so a link cannot be guessed. Only PDFs in the reports folder are ever served.
    if (url.pathname.startsWith('/r/')) {
      const [, , sig, file] = url.pathname.split('/');
      const name = basename(file || '');
      const want = createHmac('sha256', INTERNAL_KEY).update(name).digest('hex').slice(0, 40);
      const ok = INTERNAL_KEY && sig && sig.length === want.length && timingSafeEqual(Buffer.from(sig), Buffer.from(want));
      const path = join(process.env.TOKEN_DIR || '/tmp', 'state', 'out', name);
      if (!ok || !name.endsWith('.pdf') || !existsSync(path)) return send(res, 404, { error: 'not found' });
      return res.writeHead(200, { 'Content-Type': 'application/pdf', 'Content-Disposition': `inline; filename="${name}"` }).end(readFileSync(path));
    }
    if (url.pathname === '/internal/xero') {
      if (!INTERNAL_KEY || req.headers['x-internal-key'] !== INTERNAL_KEY) return send(res, 401, { error: 'unauthorised' });
      const company = url.searchParams.get('company');
      const path = url.searchParams.get('path');
      if (!ALLOWED[path]) return send(res, 400, { error: 'path not allowed' });
      const params = {};
      for (const [k, v] of url.searchParams) if (!['company', 'path'].includes(k)) params[k] = v;
      const result = await withCompany(company, () => xeroGetAllPages(config, path, ALLOWED[path], params));
      return send(res, 200, { company, path, requests: result.requests, count: result.items.length, items: SHAPE[path] ? result.items.map(SHAPE[path]) : result.items });
    }
    send(res, 404, { error: 'not found' });
  } catch (e) {
    send(res, 500, { error: e.message });
  }
}).listen(PORT, () => { console.log(`listening on ${PORT}`); selfTest(config); startScheduler(); });
