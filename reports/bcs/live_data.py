"""Live BCS data from Xero, in the same shapes the dashboard script already uses."""
import sys, os, datetime as dt
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common import xero, today, CONFIG

CO = 'bcs'
TODAY = today()
MSTART = TODAY.replace(day=1)
ISSUES = []     # hold-the-send problems
NOTES = []      # shown, but do not block

def _lines(inv):
    return [(l.get('itemCode') or '', l.get('description') or '', float(l.get('quantity') or 0), float(l.get('netAmount') or 0))
            for l in inv['lineItems']]

_w = f'Type=="ACCREC"&&Date>=DateTime({MSTART.year},{MSTART.month},{MSTART.day})'
_inv = [i for i in xero(CO, '/Invoices', where=_w) if i['status'] not in ('VOIDED', 'DELETED', 'DRAFT')]
if not _inv:
    ISSUES.append('No sales invoices came back from Xero for this month.')
INV = [(i['invoiceNumber'], i['date'], _lines(i)) for i in sorted(_inv, key=lambda i: (i['date'], i['invoiceNumber']))]
_META = {i['invoiceNumber']: (i['contact']['contactId'] if i['contact'] else None, (i.get('reference') or '').strip().lower()) for i in _inv}
il_all = [(('LECTURE' if (l[1].strip().startswith('LPFNQF6') or l[1].strip().startswith('ASSESSMENT:')) else l[0]),) + tuple(l[1:])
          for _, _, ls in INV for l in ls]

# ---- accepted quotes (API date is one day earlier than the Xero screen) ----
_qfrom = (MSTART - dt.timedelta(days=1)).isoformat()
QS = [q for q in xero(CO, '/Quotes', Status='ACCEPTED', DateFrom=_qfrom) if q['status'] == 'ACCEPTED' and q['date'] >= _qfrom]

def qlines(qs):
    return [(l.get('itemCode') or '', l.get('description') or '', float(l.get('quantity') or 0), float(l.get('lineAmount') or 0))
            for q in qs for l in q['lineItems']]

_OK = {tuple(x) for x in CONFIG['verified_quote_matches']}
_used = set(); MATCHED = []

def _is_inv(qn, qdate, l):
    d = (l.get('description') or '').strip().lower(); qty = round(float(l.get('quantity') or 0), 2); amt = float(l.get('lineAmount') or 0)
    if not d or 'delivery' in d:
        return None
    for num, dt_, lines in INV:
        if dt_ < qdate:
            continue
        for j, (c, n, q, a) in enumerate(lines):
            if (num, j) in _used or (qn, num) not in _OK:
                continue
            if n.strip().lower() == d and round(q, 2) == qty and abs(a - amt) <= 0.12 * max(amt, 1):
                _used.add((num, j)); return num
    return None

QS_ALL = QS; _QSX = []
for q in QS:
    keep = []
    for l in q['lineItems']:
        n = _is_inv(q['quoteNumber'], q['date'], l)
        if n:
            MATCHED.append((q['quoteNumber'], n, l.get('description'), float(l.get('lineAmount') or 0)))
        else:
            keep.append(l)
    _QSX.append(dict(q, lineItems=keep))
QS = _QSX

# A quote that looks invoiced (same contact AND same reference) but is not on the verified list: hold and ask.
for q in QS_ALL:
    ref = (q.get('reference') or '').strip().lower()
    cid = q['contact']['contactId'] if q.get('contact') else None
    if not ref:
        continue
    for num, (icid, iref) in _META.items():
        if icid == cid and iref == ref and (q['quoteNumber'], num) not in _OK:
            idate = next(d for n, d, _ in INV if n == num)
            if idate >= q['date']:
                ISSUES.append(f"Quote {q['quoteNumber']} may already be invoiced as {num} (same customer and reference). Not on the verified list, so it is still counted. Please confirm.")

ql_all = qlines(QS)
_yday = (TODAY - dt.timedelta(days=1)).isoformat()
QT = [q for q in QS if q['date'] == _yday]
tl = qlines(QT)

# ---- bank postings (spend) this month ----
rows = []
_bw = f'Type=="SPEND"&&Date>=DateTime({MSTART.year},{MSTART.month},{MSTART.day})'
for t in xero(CO, '/BankTransactions', where=_bw):
    if t['status'] in ('DELETED', 'VOIDED'):
        continue
    inc = t.get('lineAmountTypes') == 'Inclusive'
    for l in t['lineItems']:
        rows.append((t['date'], (t.get('contact') or {}).get('name') or '', str(l.get('accountCode')),
                     l['lineAmount'] - ((l.get('taxAmount') or 0) if inc else 0), l.get('description') or ''))
if not rows:
    ISSUES.append('No bank spend postings came back from Xero for this month, so fixed costs cannot be evidenced.')

def refresh_prices(K):
    """Update known item costs from the latest supplier bills (ex VAT). Unit sanity band 60% to 160% of the baseline."""
    since = TODAY - dt.timedelta(days=75)
    w = f'Type=="ACCPAY"&&Date>=DateTime({since.year},{since.month},{since.day})'
    bills = [b for b in xero(CO, '/Invoices', where=w) if b['status'] not in ('VOIDED', 'DELETED', 'DRAFT')]
    latest = {}
    for b in sorted(bills, key=lambda b: b['date']):
        for l in b['lineItems']:
            c = l.get('itemCode'); q = float(l.get('quantity') or 0)
            if c and q > 0 and l.get('netAmount'):
                latest[c] = (float(l['netAmount']) / q, b['date'])
    changed = skipped = 0
    for c, (p, d) in latest.items():
        if c in K.P:
            base = K.P[c]
            if base and 0.6 <= p / base <= 1.6:
                if abs(p - base) > 0.005:
                    changed += 1
                K.P[c] = p
            else:
                skipped += 1
    NOTES.append(f'Supplier bills read: {len(bills)}. Prices refreshed on {changed} items, {skipped} bill prices skipped as outside the sanity band.')
