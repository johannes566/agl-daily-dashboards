/**
 * Read-only Xero MCP server (stdio).
 *
 * Exposes SIX read tools to Claude and nothing else. There is no create,
 * update, delete or approve tool, and no code path that could add one at
 * runtime - the tool list below is the complete surface.
 *
 * Chart of accounts, bank account details and tracking categories are
 * deliberately absent: Xero's own official Claude connector already serves
 * those correctly, so duplicating them would add code and no capability.
 *
 * Five independent layers keep this read-only:
 *   1. Xero-enforced read-only OAuth scopes (holds even if this code is wrong)
 *   2. xeroGet() takes no HTTP-method argument - no write path exists
 *   3. only read tools are registered here
 *   4. no SDK write methods are present in the process
 *   5. every tool is annotated readOnlyHint/destructiveHint at MCP level, so
 *      the client is told these cannot modify anything
 *
 * Run: node src/mcp-server.js      (Claude launches this; not run by hand)
 */
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';

import { loadConfig } from './config.js';
import { readTokens } from './tokens.js';
import { getOrganisation, listQuotes, listPayments, listBankTransactions, getBankStatement } from './tools.js';
import { dateWhere } from './format.js';
import { shapeQuote, shapePayment, shapeBankTransaction, shapeOrganisation, shapeBankStatement } from './shape.js';

const READ_ONLY = Object.freeze({
  readOnlyHint: true,
  destructiveHint: false,
  idempotentHint: true,
  openWorldHint: true,
});

const dateArgs = {
  from: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).optional()
    .describe('Only include records on or after this date (YYYY-MM-DD). Omit for no lower bound.'),
  to: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).optional()
    .describe('Only include records on or before this date (YYYY-MM-DD). Omit for no upper bound.'),
};

/** Wrap a payload as MCP tool output. Numbers stay numbers; nothing is prose. */
function reply(payload) {
  return { content: [{ type: 'text', text: JSON.stringify(payload, null, 2) }] };
}

function failure(err) {
  // Never leaks tokens: the error types in xero.js carry human-readable text
  // and status codes only, never headers or credentials.
  return {
    isError: true,
    content: [{ type: 'text', text: `Xero read failed.\n\n${err.message}` }],
  };
}

async function main() {
  const config = loadConfig();

  const server = new McpServer({
    name: 'agl-xero-readonly-bridge',
    version: '0.5.0',
  });

  // ---------------------------------------------------------------- org ---
  server.registerTool(
    'xero_get_organisation',
    {
      title: 'Get Xero organisation',
      description:
        'Return details of the single Xero organisation this bridge is pinned to: ' +
        'name, legal name, country, base currency, timezone and financial year end. ' +
        'Use this to confirm which company the figures belong to before relying on them. ' +
        'The bridge is pinned to one organisation and cannot read any other.',
      inputSchema: {},
      annotations: READ_ONLY,
    },
    async () => {
      try {
        const org = await getOrganisation(config);
        const stored = readTokens();
        return reply({
          organisation: shapeOrganisation(org),
          pinnedOrganisationName: stored?.tenantName ?? null,
          nameMatchesPinned: !stored?.tenantName || stored.tenantName === org.Name,
        });
      } catch (err) {
        return failure(err);
      }
    }
  );

  // ----------------------------------------------------- accepted quotes ---
  server.registerTool(
    'xero_list_accepted_quotes',
    {
      title: 'List accepted Xero quotes',
      description:
        'Return every quote with Xero status ACCEPTED, with full line-item detail, across all pages.\n\n' +
        'CRITICAL MEANING: in Xero, ACCEPTED means won work that has NOT yet been turned into an ' +
        'invoice. Converting a quote to an invoice changes its status to INVOICED, which removes it ' +
        'from this list. So these values do NOT overlap with invoice totals, and adding them to ' +
        'invoiced revenue does not double-count. Quotes with status INVOICED would double-count and ' +
        'are not returned here (use xero_list_quotes to see them).\n\n' +
        'Use subTotalExcludingTax for values excluding VAT. Do NOT compute VAT as 15% of the ' +
        'subtotal: zero-rated lines exist and totalTax is what Xero actually recorded.\n\n' +
        'Xero provides NO link from a quote to the invoice it became. Matching must be inferential ' +
        'using reference, contact.contactId, quoteNumber and amounts. Every identifier needed for ' +
        'that is preserved here, including line-level detail.',
      inputSchema: dateArgs,
      annotations: READ_ONLY,
    },
    async ({ from, to }) => {
      try {
        const { items, requests } = await listQuotes(config, { status: 'ACCEPTED', from, to });
        return reply({
          meta: {
            statusFilter: 'ACCEPTED',
            dateFrom: from ?? null,
            dateTo: to ?? null,
            quoteCount: items.length,
            apiCallsMade: requests,
            note: 'ACCEPTED = won but not yet invoiced. Does not overlap with invoice totals.',
          },
          quotes: items.map(shapeQuote),
        });
      } catch (err) {
        return failure(err);
      }
    }
  );

  // -------------------------------------------------------- all quotes ---
  server.registerTool(
    'xero_list_quotes',
    {
      title: 'List Xero quotes (any status)',
      description:
        'Return quotes of any status, or filtered to one status, with full line-item detail across ' +
        'all pages. Valid statuses: DRAFT, SENT, DECLINED, ACCEPTED, INVOICED, DELETED.\n\n' +
        'Status meanings that matter financially: ACCEPTED = won, not yet invoiced. INVOICED = won ' +
        'and already converted to an invoice, so its value is ALREADY counted in invoice figures - ' +
        'adding INVOICED quotes to invoiced revenue double-counts. DELETED records are still ' +
        'returned by Xero and must be excluded from any total.\n\n' +
        'For the common "what have we won but not yet billed" question, prefer ' +
        'xero_list_accepted_quotes.',
      inputSchema: {
        status: z.enum(['DRAFT', 'SENT', 'DECLINED', 'ACCEPTED', 'INVOICED', 'DELETED']).optional()
          .describe('Restrict to one Xero quote status. Omit to return every status.'),
        ...dateArgs,
      },
      annotations: READ_ONLY,
    },
    async ({ status, from, to }) => {
      try {
        const { items, requests } = await listQuotes(config, { status, from, to });
        return reply({
          meta: {
            statusFilter: status ?? 'ALL',
            dateFrom: from ?? null,
            dateTo: to ?? null,
            quoteCount: items.length,
            apiCallsMade: requests,
            note: 'INVOICED quotes are already reflected in invoice totals. DELETED must be excluded from totals.',
          },
          quotes: items.map(shapeQuote),
        });
      } catch (err) {
        return failure(err);
      }
    }
  );

  // ----------------------------------------------------------- payments ---
  server.registerTool(
    'xero_list_payments',
    {
      title: 'List Xero payments',
      description:
        'Return payments against invoices and credit notes across all pages.\n\n' +
        'CRITICAL: Xero returns BOTH DIRECTIONS in one feed. Each record carries a "direction" ' +
        'field: IN means money received from a customer (ACCREC/AR types), OUT means money paid to ' +
        'a supplier (ACCPAY/AP types). NEVER add IN and OUT together - the combined figure ' +
        'represents nothing real. Report them separately, or net them explicitly and say so.\n\n' +
        'Records with status DELETED or VOIDED are returned but must be excluded from totals; a ' +
        'deleted payment is often re-entered, so counting both double-counts.\n\n' +
        'Each payment carries invoice.invoiceId and invoice.invoiceNumber, which is an exact link ' +
        'to the document it settled - unlike quotes, which Xero does not link to invoices.',
      inputSchema: dateArgs,
      annotations: READ_ONLY,
    },
    async ({ from, to }) => {
      try {
        const where = dateWhere(from, to);
        const { items, requests } = await listPayments(config, { where });
        const shaped = items.map(shapePayment);
        return reply({
          meta: {
            dateFrom: from ?? null,
            dateTo: to ?? null,
            paymentCount: shaped.length,
            countIn: shaped.filter((p) => p.direction === 'IN').length,
            countOut: shaped.filter((p) => p.direction === 'OUT').length,
            countExcludedStatus: shaped.filter((p) => ['DELETED', 'VOIDED'].includes(String(p.status).toUpperCase())).length,
            apiCallsMade: requests,
            note: 'Never sum direction IN and OUT together. Exclude DELETED/VOIDED from totals.',
          },
          payments: shaped,
        });
      } catch (err) {
        return failure(err);
      }
    }
  );

  // ------------------------------------------------- bank transactions ---
  server.registerTool(
    'xero_list_bank_transactions',
    {
      title: 'List Xero bank transactions',
      description:
        'Return spent and received money transactions across all pages, with line-item detail, ' +
        'covering BOTH reconciled and unreconciled entries.\n\n' +
        'This exists because the other Xero connector exposes only UNRECONCILED bank transactions, ' +
        'which hides almost all history - in live testing it showed 2 of 233 transactions for the ' +
        'same period. Use this tool for any question about what actually happened in the bank.\n\n' +
        'Types: RECEIVE / RECEIVE-TRANSFER (money in) and SPEND / SPEND-TRANSFER (money out). ' +
        'Report them separately rather than netting silently. Records with status DELETED or VOIDED ' +
        'are returned but must be excluded from totals.\n\n' +
        'Note lineAmountTypes: on these records line amounts are typically INCLUSIVE of tax, whereas ' +
        'quote line amounts are EXCLUSIVE. Never compare line amounts across the two without ' +
        'checking that field.\n\n' +
        'This does NOT include payments against invoices - those are a separate Xero concept, ' +
        'available via xero_list_payments.',
      inputSchema: dateArgs,
      annotations: READ_ONLY,
    },
    async ({ from, to }) => {
      try {
        const where = dateWhere(from, to);
        const { items, requests } = await listBankTransactions(config, { where });
        const shaped = items.map(shapeBankTransaction);
        return reply({
          meta: {
            dateFrom: from ?? null,
            dateTo: to ?? null,
            transactionCount: shaped.length,
            countReconciled: shaped.filter((t) => t.isReconciled === true).length,
            countUnreconciled: shaped.filter((t) => t.isReconciled !== true).length,
            countExcludedStatus: shaped.filter((t) => ['DELETED', 'VOIDED'].includes(String(t.status).toUpperCase())).length,
            apiCallsMade: requests,
            note: 'Includes reconciled history. Exclude DELETED/VOIDED from totals. Check lineAmountTypes before comparing line amounts.',
          },
          bankTransactions: shaped,
        });
      } catch (err) {
        return failure(err);
      }
    }
  );

  // ---------------------------------------------------- bank statement ---
  server.registerTool(
    'xero_get_bank_statement',
    {
      title: 'Get Xero bank statement lines',
      description:
        'Return the bank statement lines for ONE bank account and date range, as the bank reported ' +
        'them to Xero through the bank feed or a statement import: date, description, reference, ' +
        'signed amount (positive = money in, negative = money out), Xero\'s running statement ' +
        'balance, and whether each line has been reconciled in Xero yet.\n\n' +
        'This is the BANK side of the reconciliation, so it includes lines nobody has reconciled ' +
        'yet. Use it for "what went through the bank" and "what is the bank balance". Use ' +
        'xero_list_bank_transactions for the ledger side.\n\n' +
        'BALANCE WARNING: the running balance is calculated by Xero from the opening balance that ' +
        'was set when the feed started. If that opening balance was wrong, every balance is wrong ' +
        'by the same amount while the movements are still correct. Check the balance against an ' +
        'actual bank statement before quoting it, and report the movements separately from the ' +
        'balance.\n\n' +
        'bankAccountId is the Xero AccountID of a BANK-type account (from the chart of accounts). ' +
        'Xero limits the range to 365 days. Lines that could not be read as statement lines are ' +
        'returned in otherRows, never dropped. Set includeRaw to true to also get Xero\'s raw ' +
        'report, for checking the parsing.',
      inputSchema: {
        bankAccountId: z.string().uuid()
          .describe('Xero AccountID of the bank account (a UUID).'),
        from: z.string().regex(/^\d{4}-\d{2}-\d{2}$/)
          .describe('First statement date to include (YYYY-MM-DD).'),
        to: z.string().regex(/^\d{4}-\d{2}-\d{2}$/)
          .describe('Last statement date to include (YYYY-MM-DD). At most 365 days after from.'),
        includeRaw: z.boolean().optional()
          .describe('Also return the raw Xero report. Default false.'),
      },
      annotations: READ_ONLY,
    },
    async ({ bankAccountId, from, to, includeRaw }) => {
      try {
        const days = (Date.parse(`${to}T00:00:00Z`) - Date.parse(`${from}T00:00:00Z`)) / 86400000;
        if (!(days >= 0)) throw new Error(`"to" (${to}) is before "from" (${from}).`);
        if (days > 365) throw new Error(`Xero allows at most 365 days per request; ${days} were asked for.`);

        const body = await getBankStatement(config, { bankAccountId, from, to });
        const s = shapeBankStatement(body);
        const round = (n) => Math.round(n * 100) / 100;
        const moneyIn = s.lines.filter((l) => l.amount > 0).reduce((a, l) => a + l.amount, 0);
        const moneyOut = s.lines.filter((l) => l.amount < 0).reduce((a, l) => a + l.amount, 0);
        const lastWithBalance = [...s.lines].reverse().find((l) => l.runningBalance !== null);

        return reply({
          meta: {
            bankAccountId,
            dateFrom: from,
            dateTo: to,
            reportName: s.reportName,
            reportTitles: s.reportTitles,
            columnsFound: s.columns,
            parsed: s.parsed,
            lineCount: s.lines.length,
            countReconciled: s.lines.filter((l) => l.isReconciled === true).length,
            countUnreconciled: s.lines.filter((l) => l.isReconciled === false).length,
            totalIn: round(moneyIn),
            totalOut: round(moneyOut),
            netMovement: round(moneyIn + moneyOut),
            openingBalance: s.openingBalance,
            closingBalance: s.closingBalance,
            lastRunningBalance: lastWithBalance
              ? { date: lastWithBalance.date, balance: lastWithBalance.runningBalance }
              : null,
            otherRowCount: s.otherRows.length,
            note:
              'Balances are Xero statement balances and depend on the feed opening balance; verify ' +
              'against the bank before quoting. totalIn and totalOut are reported separately; ' +
              'netMovement is their explicit net.',
          },
          lines: s.lines,
          otherRows: s.otherRows,
          ...(includeRaw ? { raw: body } : {}),
        });
      } catch (err) {
        return failure(err);
      }
    }
  );

  // stdio only: no network listener, nothing exposed to the internet.
  await server.connect(new StdioServerTransport());
}

main().catch((err) => {
  // stderr, never stdout: stdout carries the MCP protocol stream.
  console.error(`MCP server failed to start: ${err.message}`);
  process.exit(1);
});
