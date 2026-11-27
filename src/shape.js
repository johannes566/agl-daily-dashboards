/**
 * Shaping Xero records for Claude.
 *
 * Three rules, all learned from live data:
 *
 *  1. NUMBERS STAY NUMBERS. The human-readable test scripts format amounts
 *     with en-ZA separators, which uses a NON-BREAKING space (U+00A0). Handing
 *     that to a model invites parsing mistakes, so tools emit raw numbers.
 *
 *  2. NOTHING IS AGGREGATED AWAY. Every identifier Xero provides is preserved,
 *     including line-level detail. Xero exposes no quote-to-invoice link, so
 *     matching later depends on identifiers this layer must not discard.
 *
 *  3. DATES ARE NORMALISED. Xero emits "/Date(1571875200000+0000)/", which is
 *     not usable as-is. Converted to YYYY-MM-DD; nothing else is reinterpreted.
 */
import { xeroDate, paymentDirection } from './format.js';

const num = (v) => (v === undefined || v === null || v === '' ? null : Number(v));

/**
 * References in live data carry trailing spaces ("JOB123 "), which silently
 * break exact-match joins. The trimmed value is returned for matching, and the
 * original preserved as referenceRaw ONLY when it actually differs - so no
 * information is lost and the common case stays uncluttered.
 */
function reference(value) {
  if (value === undefined || value === null) return { reference: null };
  const raw = String(value);
  const trimmed = raw.trim();
  return trimmed === raw ? { reference: trimmed } : { reference: trimmed, referenceRaw: raw };
}

const contact = (c) => (c ? { contactId: c.ContactID ?? null, name: c.Name ?? null } : null);

const lineItems = (items) =>
  (items || []).map((li) => ({
    lineItemId: li.LineItemID ?? null,
    description: li.Description ?? null,
    quantity: num(li.Quantity),
    unitAmount: num(li.UnitAmount),
    lineAmount: num(li.LineAmount),
    itemCode: li.ItemCode ?? null,
    accountCode: li.AccountCode ?? null,
    taxType: li.TaxType ?? null,
    taxAmount: num(li.TaxAmount),
    discountRate: num(li.DiscountRate),
    tracking: li.Tracking ?? [],
  }));

export function shapeQuote(q) {
  return {
    quoteId: q.QuoteID ?? null,
    quoteNumber: q.QuoteNumber ?? null,
    status: q.Status ?? null,
    date: xeroDate(q.DateString || q.Date) || null,
    expiryDate: xeroDate(q.ExpiryDateString || q.ExpiryDate) || null,
    ...reference(q.Reference),
    contact: contact(q.Contact),
    currencyCode: q.CurrencyCode ?? null,
    currencyRate: num(q.CurrencyRate),
    subTotalExcludingTax: num(q.SubTotal),
    totalTax: num(q.TotalTax),
    totalIncludingTax: num(q.Total),
    totalDiscount: num(q.TotalDiscount),
    // Says whether LINE amounts include or exclude tax. Differs by record type
    // in live data (quotes EXCLUSIVE, bank transactions Inclusive), so it must
    // never be assumed.
    lineAmountTypes: q.LineAmountTypes ?? null,
    title: q.Title ?? null,
    summary: q.Summary ?? null,
    updatedDateUtc: xeroDate(q.UpdatedDateUTC) || null,
    lineItems: lineItems(q.LineItems),
  };
}

export function shapePayment(p) {
  return {
    paymentId: p.PaymentID ?? null,
    date: xeroDate(p.Date) || null,
    amount: num(p.Amount),
    bankAmount: num(p.BankAmount),
    currencyRate: num(p.CurrencyRate),
    paymentType: p.PaymentType ?? null,
    // IN = received from a customer, OUT = paid to a supplier. Xero returns
    // both in one feed; adding them together produces a meaningless figure.
    direction: paymentDirection(p.PaymentType),
    status: p.Status ?? null,
    isReconciled: p.IsReconciled ?? null,
    ...reference(p.Reference),
    account: p.Account
      ? { accountId: p.Account.AccountID ?? null, code: p.Account.Code ?? null, name: p.Account.Name ?? null }
      : null,
    // Xero does NOT link a quote to its invoice, but it DOES link a payment to
    // the invoice it settled. These identifiers are that link - keep them.
    invoice: p.Invoice
      ? {
          invoiceId: p.Invoice.InvoiceID ?? null,
          invoiceNumber: p.Invoice.InvoiceNumber ?? null,
          type: p.Invoice.Type ?? null,
          currencyCode: p.Invoice.CurrencyCode ?? null,
          contact: contact(p.Invoice.Contact),
        }
      : null,
    creditNote: p.CreditNote
      ? { creditNoteId: p.CreditNote.CreditNoteID ?? null, creditNoteNumber: p.CreditNote.CreditNoteNumber ?? null }
      : null,
  };
}

export function shapeBankTransaction(t) {
  return {
    bankTransactionId: t.BankTransactionID ?? null,
    type: t.Type ?? null,
    status: t.Status ?? null,
    date: xeroDate(t.Date) || null,
    ...reference(t.Reference),
    isReconciled: t.IsReconciled ?? null,
    contact: contact(t.Contact),
    bankAccount: t.BankAccount
      ? { accountId: t.BankAccount.AccountID ?? null, code: t.BankAccount.Code ?? null, name: t.BankAccount.Name ?? null }
      : null,
    currencyCode: t.CurrencyCode ?? null,
    currencyRate: num(t.CurrencyRate),
    subTotalExcludingTax: num(t.SubTotal),
    totalTax: num(t.TotalTax),
    totalIncludingTax: num(t.Total),
    lineAmountTypes: t.LineAmountTypes ?? null,
    updatedDateUtc: xeroDate(t.UpdatedDateUTC) || null,
    lineItems: lineItems(t.LineItems),
  };
}

export function shapeOrganisation(o) {
  return {
    name: o.Name ?? null,
    legalName: o.LegalName ?? null,
    countryCode: o.CountryCode ?? null,
    baseCurrency: o.BaseCurrency ?? null,
    timezone: o.TimeZone ?? null,
    financialYearEndDay: o.FinancialYearEndDay ?? null,
    financialYearEndMonth: o.FinancialYearEndMonth ?? null,
    organisationType: o.OrganisationType ?? null,
    organisationStatus: o.OrganisationStatus ?? null,
    isDemoCompany: o.IsDemoCompany ?? null,
    registrationNumber: o.RegistrationNumber ?? null,
  };
}

// ------------------------------------------------------------------------
// Bank statement report
// ------------------------------------------------------------------------

const MONTHS = { jan: 1, feb: 2, mar: 3, apr: 4, may: 5, jun: 6, jul: 7, aug: 8, sep: 9, oct: 10, nov: 11, dec: 12 };

/**
 * Report cells carry dates as text in more than one style. Parsed by hand,
 * never via new Date("1 Oct 2026"): that parses as LOCAL midnight and, in
 * South Africa (UTC+2), toISOString() would shift it back to 30 Sep.
 */
function reportDate(value) {
  if (value === undefined || value === null || value === '') return null;
  const s = String(value).trim();
  let m = /^(\d{4})-(\d{2})-(\d{2})/.exec(s);
  if (m) return `${m[1]}-${m[2]}-${m[3]}`;
  if (/\/Date\(/.test(s)) return xeroDate(s) || null;
  m = /^(\d{1,2})\s+([A-Za-z]{3})[a-z]*\s+(\d{4})$/.exec(s);
  if (m && MONTHS[m[2].toLowerCase()]) {
    return `${m[3]}-${String(MONTHS[m[2].toLowerCase()]).padStart(2, '0')}-${m[1].padStart(2, '0')}`;
  }
  return null;
}

/** "1,234.56", "(1,234.56)" or "-1234.56" to a number; blank to null. */
function reportNumber(value) {
  if (value === undefined || value === null) return null;
  let s = String(value).trim();
  if (s === '') return null;
  let negative = false;
  if (/^\(.*\)$/.test(s)) {
    negative = true;
    s = s.slice(1, -1);
  }
  const n = Number(s.replace(/[,\s ]/g, ''));
  if (Number.isNaN(n)) return null;
  return negative ? -n : n;
}

function reportBool(value) {
  const s = String(value ?? '').trim().toLowerCase();
  if (['yes', 'true', 'y', '1'].includes(s)) return true;
  if (['no', 'false', 'n', '0'].includes(s)) return false;
  return null;
}

/** Walk every row in a Xero report, however deeply sectioned. */
function* walkRows(rows, sectionTitle = null) {
  for (const row of rows || []) {
    if (row.RowType === 'Section') {
      yield* walkRows(row.Rows, row.Title || sectionTitle);
    } else {
      yield { row, sectionTitle };
    }
  }
}

/**
 * Turn Xero's report grid into statement lines.
 *
 * Columns are matched by their header text rather than by position, so a
 * reordered or extra column does not silently shift amounts into the wrong
 * field. Anything that cannot be read as a statement line is returned in
 * otherRows rather than dropped, so nothing disappears unseen.
 */
export function shapeBankStatement(body) {
  const report = body?.Reports?.[0];
  if (!report) {
    return { parsed: false, reason: 'Xero returned no report.', lines: [], otherRows: [] };
  }

  const all = [...walkRows(report.Rows)];
  const header = all.find(({ row }) => row.RowType === 'Header');
  const columns = (header?.row.Cells || []).map((c) => String(c.Value ?? '').trim());
  const col = (...names) =>
    columns.findIndex((c) => names.some((n) => c.toLowerCase() === n || c.toLowerCase().startsWith(n)));

  const idx = {
    date: col('date'),
    description: col('description', 'payee', 'details'),
    reference: col('reference'),
    reconciled: col('reconciled', 'status'),
    source: col('source'),
    amount: col('amount'),
    spent: col('spent', 'debit', 'withdrawal'),
    received: col('received', 'credit', 'deposit'),
    balance: col('balance', 'running balance'),
  };

  const cell = (row, i) => (i >= 0 ? row.Cells?.[i]?.Value ?? null : null);

  const lines = [];
  const otherRows = [];
  let openingBalance = null;
  let closingBalance = null;

  for (const { row, sectionTitle } of all) {
    if (row.RowType === 'Header') continue;
    const text = (row.Cells || []).map((c) => String(c.Value ?? '')).join(' ').toLowerCase();
    const date = reportDate(cell(row, idx.date));

    // Amount: one signed column, or separate spent/received columns.
    let amount = reportNumber(cell(row, idx.amount));
    if (amount === null && (idx.spent >= 0 || idx.received >= 0)) {
      const spent = reportNumber(cell(row, idx.spent)) || 0;
      const received = reportNumber(cell(row, idx.received)) || 0;
      if (spent || received) amount = received - spent;
    }
    const balance = reportNumber(cell(row, idx.balance));

    if (/opening balance/.test(text)) {
      openingBalance = { date, balance: balance ?? amount };
      continue;
    }
    if (/closing balance/.test(text)) {
      closingBalance = { date, balance: balance ?? amount };
      continue;
    }

    if (row.RowType === 'Row' && date && amount !== null) {
      lines.push({
        date,
        description: cell(row, idx.description),
        reference: cell(row, idx.reference),
        amount,
        direction: amount >= 0 ? 'IN' : 'OUT',
        runningBalance: balance,
        isReconciled: reportBool(cell(row, idx.reconciled)),
        source: cell(row, idx.source),
        section: sectionTitle,
      });
    } else {
      otherRows.push({
        rowType: row.RowType ?? null,
        section: sectionTitle,
        cells: (row.Cells || []).map((c) => c.Value ?? null),
      });
    }
  }

  return {
    parsed: columns.length > 0,
    reportName: report.ReportName ?? null,
    reportTitles: report.ReportTitles ?? [],
    reportDate: report.ReportDate ?? null,
    columns,
    openingBalance,
    closingBalance,
    lines,
    otherRows,
  };
}


/** Sales invoices and supplier bills. netAmount is the line value EXCLUDING VAT. */
export function shapeInvoice(i) {
  const inclusive = i.LineAmountTypes === 'Inclusive';
  return {
    invoiceId: i.InvoiceID ?? null,
    invoiceNumber: i.InvoiceNumber ?? null,
    type: i.Type ?? null,
    status: i.Status ?? null,
    date: xeroDate(i.DateString || i.Date) || null,
    dueDate: xeroDate(i.DueDateString || i.DueDate) || null,
    ...reference(i.Reference),
    contact: contact(i.Contact),
    lineAmountTypes: i.LineAmountTypes ?? null,
    subTotal: num(i.SubTotal),
    totalTax: num(i.TotalTax),
    total: num(i.Total),
    amountDue: num(i.AmountDue),
    amountPaid: num(i.AmountPaid),
    lineItems: (i.LineItems || []).map((li) => ({
      itemCode: li.ItemCode ?? null,
      description: li.Description ?? null,
      quantity: num(li.Quantity),
      unitAmount: num(li.UnitAmount),
      lineAmount: num(li.LineAmount),
      taxAmount: num(li.TaxAmount),
      netAmount: inclusive ? num(li.LineAmount) - (num(li.TaxAmount) || 0) : num(li.LineAmount),
      accountCode: li.AccountCode ?? null,
    })),
  };
}
