/**
 * The read functions behind the MCP tools.
 *
 * Every function here reads through xeroGet()/xeroGetAllPages(), which cannot
 * issue anything but GET against the Xero accounting API. There is no create,
 * update or delete function in this file, and there never should be.
 *
 * These return Xero's records essentially untouched. Identifiers and
 * line-level detail are deliberately preserved rather than aggregated away,
 * because the Financial Director will later need them to relate records to
 * one another - Xero provides no quote-to-invoice link of its own.
 */
import { xeroGetAllPages, xeroGet, NotAuthorisedError, XeroError } from './xero.js';
import { readTokens } from './tokens.js';

/**
 * Fail early and clearly if the stored authorisation predates a scope we now
 * need. Without this the user would get an opaque HTTP 403 from Xero and no
 * hint that re-authorising is the fix.
 */
export function requireScope(scope) {
  const stored = readTokens();
  if (!stored) {
    throw new NotAuthorisedError(`Not connected to Xero yet.\n\nFix: run "npm run auth".`);
  }
  const granted = String(stored.scope || '').split(/\s+/).filter(Boolean);
  if (granted.length && !granted.includes(scope)) {
    throw new NotAuthorisedError(
      `This read needs the "${scope}" permission, which the current Xero\n` +
        `connection does not have.\n\n` +
        `Granted at last authorisation:\n  ${granted.join('\n  ')}\n\n` +
        `Fix: run "npm run auth" again and approve access. Nothing in Xero\n` +
        `changes - this only widens what may be READ.`
    );
  }
}

/** Organisation details, used to confirm which books are being read. */
export async function getOrganisation(config) {
  const body = await xeroGet(config, '/Organisation');
  const org = body?.Organisations?.[0];
  if (!org) {
    throw new Error('Xero returned no organisation. The connection may have been revoked.');
  }
  return org;
}

/**
 * Quotes, optionally filtered by status (e.g. "ACCEPTED").
 * Xero returns up to 100 per page WITH line items.
 */
export async function listQuotes(config, { status, from, to } = {}) {
  requireScope('accounting.invoices.read');
  const params = {};
  if (status) params.Status = status;
  if (from) params.DateFrom = from;
  if (to) params.DateTo = to;
  return xeroGetAllPages(config, '/Quotes', 'Quotes', params);
}

/**
 * Payments against invoices and credit notes.
 *
 * Note: Xero returns up to 100 payments per page and payments have no line
 * items - the linked Invoice/CreditNote carries the detail.
 */
export async function listPayments(config, { where } = {}) {
  requireScope('accounting.payments.read');
  return xeroGetAllPages(config, '/Payments', 'Payments', where ? { where } : {});
}

/**
 * Spent and received money transactions.
 *
 * This exists because Xero's official connector exposes only UNRECONCILED
 * bank transactions, which hides essentially all historical activity. This
 * reads Xero's real BankTransactions endpoint, which returns reconciled and
 * unreconciled alike, up to 100 per page WITH line item details.
 */
export async function listBankTransactions(config, { where } = {}) {
  requireScope('accounting.banktransactions.read');
  return xeroGetAllPages(config, '/BankTransactions', 'BankTransactions', where ? { where } : {});
}

/**
 * Bank statement lines for ONE bank account, as imported into Xero from the
 * bank feed (or statement import), with Xero's running statement balance.
 *
 * This is the statement side of a bank reconciliation, not the ledger side:
 * it shows what the BANK reported, whether or not each line has been
 * reconciled yet. That makes it the closest thing Xero holds to the actual
 * bank balance.
 *
 * Endpoint: GET /Reports/BankStatement. Xero still serves this report but no
 * longer documents it, so the response shape is parsed defensively and the
 * raw report can be returned on request for checking.
 *
 * No scope pre-check here on purpose: which scope Xero wants for this report
 * is not documented, so the call is attempted and a 403 is explained with
 * the scopes currently granted.
 */
export async function getBankStatement(config, { bankAccountId, from, to }) {
  try {
    return await xeroGet(config, '/Reports/BankStatement', {
      bankAccountID: bankAccountId,
      fromDate: from,
      toDate: to,
    });
  } catch (err) {
    if (err instanceof XeroError && err.status === 403) {
      const stored = readTokens();
      const granted = String(stored?.scope || '').split(/\s+/).filter(Boolean);
      throw new XeroError(
        `Xero refused the bank statement report (HTTP 403).\n\n` +
          `The current connection does not have the permission this report needs.\n` +
          `Granted at last authorisation:\n  ${granted.join('\n  ') || '(not recorded)'}\n\n` +
          `Fix: run "npm run auth" again and approve access. The new request\n` +
          `includes the read-only bank statement permission. Nothing in Xero\n` +
          `changes - this only widens what may be READ.`,
        { status: 403 }
      );
    }
    throw err;
  }
}
