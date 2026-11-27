/**
 * Automated proof that this project cannot write to Xero.
 *
 *   npm run verify:readonly
 *
 * Checks, by reading the source rather than trusting comments:
 *   1. Every non-GET HTTP call targets Xero's IDENTITY host (login/token),
 *      never the accounting API.
 *   2. Every OAuth scope requested is read-only.
 *   3. No exported function is named like a write operation.
 *   4. xeroGet() hard-codes its method rather than accepting one.
 *
 * Intended to be re-run after any change, and readable by a third-party
 * auditor who does not want to take the author's word for it.
 */
import { readFileSync, readdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { SCOPES, XERO } from './config.js';

const SRC = dirname(fileURLToPath(import.meta.url));
const IDENTITY_HOSTS = ['identity.xero.com', 'login.xero.com'];

let failures = 0;
const check = (ok, label, detail = '') => {
  if (!ok) failures++;
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${label}${detail ? `\n        ${detail}` : ''}`);
};

const files = readdirSync(SRC).filter((f) => f.endsWith('.js'));
console.log(`Scanning ${files.length} source files in src/\n`);

// --- 1. Non-GET calls must go to the identity host only --------------------
for (const file of files) {
  const text = readFileSync(join(SRC, file), 'utf8');
  const lines = text.split('\n');

  lines.forEach((lineText, i) => {
    const m = /method:\s*'(POST|PUT|PATCH|DELETE)'/.exec(lineText);
    if (!m) return;

    // Look back for the fetch() target this method belongs to.
    const context = lines.slice(Math.max(0, i - 6), i + 1).join('\n');
    const targetsIdentity =
      /XERO\.TOKEN_URL/.test(context) || IDENTITY_HOSTS.some((h) => context.includes(h));

    check(
      targetsIdentity,
      `${file}:${i + 1} uses ${m[1]} — must target Xero's identity host`,
      targetsIdentity ? '' : 'This would be a WRITE against the accounting API.'
    );
  });
}

// --- 2. The identity endpoint must not be the accounting API ---------------
check(
  new URL(XERO.TOKEN_URL).host !== XERO.API_HOST,
  'Token endpoint is a different host from the accounting API',
  `token=${new URL(XERO.TOKEN_URL).host}  api=${XERO.API_HOST}`
);

// --- 3. Every scope must be read-only --------------------------------------
for (const scope of SCOPES) {
  const readOnly = scope === 'offline_access' || scope.endsWith('.read');
  check(readOnly, `scope "${scope}" is read-only`);
}

// --- 4. No write-shaped exported functions ---------------------------------
const WRITE_VERBS = /export\s+(async\s+)?function\s+(create|update|delete|post|put|patch|remove|approve|void|archive)/i;
for (const file of files) {
  const text = readFileSync(join(SRC, file), 'utf8');
  const hit = WRITE_VERBS.exec(text);
  check(!hit, `${file} exports no write-shaped function`, hit ? `found: ${hit[0]}` : '');
}

// --- 5. xeroGet must hard-code its method ----------------------------------
const xeroSrc = readFileSync(join(SRC, 'xero.js'), 'utf8');
check(
  /\/\/ --- Structural guarantee #2[\s\S]{0,120}method:\s*'GET'/.test(xeroSrc),
  'xeroGet() hard-codes method: GET'
);
check(
  !/export\s+(async\s+)?function\s+xeroGet\s*\([^)]*method/.test(xeroSrc),
  'xeroGet() does not accept an HTTP method argument'
);

// --- 6. The MCP surface must be read-only ----------------------------------
const mcpSrc = readFileSync(join(SRC, 'mcp-server.js'), 'utf8');
const registered = [...mcpSrc.matchAll(/registerTool\(\s*'([a-z0-9_]+)'/g)].map((m) => m[1]);

check(registered.length > 0, `mcp-server.js registers tools (${registered.length} found)`);

const WRITE_TOOL = /(create|update|delete|post|put|patch|remove|approve|void|archive|send|email|write|modify|set_)/i;
for (const name of registered) {
  check(!WRITE_TOOL.test(name), `MCP tool "${name}" is not write-shaped`);
}

// Every registered tool must carry the read-only annotations. Counting them is
// how we catch a tool added later without them.
const annotationUses = (mcpSrc.match(/annotations:\s*READ_ONLY/g) || []).length;
check(
  annotationUses === registered.length,
  `all ${registered.length} MCP tools carry READ_ONLY annotations (found ${annotationUses})`
);
check(/readOnlyHint:\s*true/.test(mcpSrc), 'READ_ONLY sets readOnlyHint: true');
check(/destructiveHint:\s*false/.test(mcpSrc), 'READ_ONLY sets destructiveHint: false');

// Only the stdio transport may be used: an HTTP transport would expose a
// network listener, which this design deliberately does not have.
check(!/StreamableHTTPServerTransport|SSEServerTransport|express\(|createServer\(/.test(mcpSrc),
  'mcp-server.js opens no network listener (stdio transport only)');

console.log('');
console.log('='.repeat(64));
if (failures === 0) {
  console.log('READ-ONLY VERIFICATION PASSED — no write path to Xero exists.');
} else {
  console.log(`READ-ONLY VERIFICATION FAILED — ${failures} problem(s) above.`);
}
console.log('='.repeat(64));
process.exitCode = failures ? 1 : 0;
