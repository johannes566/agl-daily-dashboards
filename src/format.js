/**
 * Shared output helpers for the test scripts.
 *
 * Masking exists so output can be pasted into a chat or screenshot without
 * disclosing customer identities. It deliberately does NOT mask monetary
 * amounts - those are usually the point of the test. Decide per situation
 * whether amounts are safe to share.
 */

/** Mask a name or reference, keeping first and last character for sanity checks. */
export function maskValue(value, enabled) {
  if (!enabled || !value) return value ?? '';
  const s = String(value);
  if (s.length <= 2) return '**';
  return `${s[0]}${'*'.repeat(Math.min(s.length - 2, 8))}${s[s.length - 1]}`;
}

/** Mask a UUID, keeping the first block so records stay distinguishable. */
export function maskUuid(value, enabled) {
  if (!enabled || !value) return value ?? '';
  return `${String(value).slice(0, 8)}-****-****-****-************`;
}

/**
 * Xero sends dates as "/Date(1571875200000+0000)/" in JSON responses.
 * Falls back to normal date parsing for the plain "YYYY-MM-DD" fields.
 */
export function xeroDate(value) {
  if (!value) return '';
  const m = /\/Date\((-?\d+)/.exec(String(value));
  const d = m ? new Date(Number(m[1])) : new Date(value);
  return Number.isNaN(d.getTime()) ? String(value) : d.toISOString().slice(0, 10);
}

export function money(n) {
  return (Number(n) || 0).toLocaleString('en-ZA', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export const line = (c = '-', n = 74) => console.log(c.repeat(n));

/**
 * Build a Xero "where" filter for a date range.
 * Xero expects e.g.  Date >= DateTime(2026,01,31)
 */
export function dateWhere(from, to) {
  const clauses = [];
  const asDateTime = (iso) => {
    const [y, m, d] = iso.split('-');
    return `DateTime(${Number(y)},${Number(m)},${Number(d)})`;
  };
  if (from) clauses.push(`Date >= ${asDateTime(from)}`);
  if (to) clauses.push(`Date <= ${asDateTime(to)}`);
  return clauses.join(' && ');
}

/** Read --flag value pairs and boolean flags from argv. */
export function parseArgs(argv) {
  const out = { mask: argv.includes('--mask') };
  for (const name of ['from', 'to']) {
    const i = argv.indexOf(`--${name}`);
    if (i !== -1 && argv[i + 1]) {
      const value = argv[i + 1];
      if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) {
        throw new Error(`--${name} must be a date like 2026-01-31, got "${value}"`);
      }
      out[name] = value;
    }
  }
  return out;
}

/**
 * Classify a Xero payment type as money in or money out.
 *
 * Xero mixes both directions in one Payments feed. ACCREC and AR types
 * are receipts from customers; ACCPAY and AP types are payments to
 * suppliers.
 * Summing the two together produces a figure that means nothing, so callers
 * must always split on this.
 */
export function paymentDirection(paymentType) {
  const t = String(paymentType || '').toUpperCase();
  if (t.startsWith('ACCREC') || t.startsWith('AR')) return 'IN';
  if (t.startsWith('ACCPAY') || t.startsWith('AP')) return 'OUT';
  return 'UNKNOWN';
}

/**
 * Statuses that must be excluded from financial totals.
 * A DELETED or VOIDED record is still returned by Xero and must still be
 * visible, but counting it inflates the numbers - a deleted transaction is
 * often re-entered, so including both double-counts it.
 */
export const EXCLUDED_FROM_TOTALS = new Set(['DELETED', 'VOIDED']);

export function countsTowardTotals(status) {
  return !EXCLUDED_FROM_TOTALS.has(String(status || '').toUpperCase());
}
