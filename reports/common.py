"""Talks to the local service (read-only Xero reader) and holds shared helpers."""
import os, json, urllib.request, urllib.parse, datetime as dt

BASE = f"http://127.0.0.1:{os.environ.get('PORT', '8080')}"
KEY = os.environ.get('INTERNAL_KEY', '')
SAST = dt.timezone(dt.timedelta(hours=2))
CONFIG = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'config.json')))


def xero(company, path, **params):
    q = urllib.parse.urlencode({'company': company, 'path': path, **params})
    req = urllib.request.Request(f'{BASE}/internal/xero?{q}', headers={'x-internal-key': KEY})
    with urllib.request.urlopen(req, timeout=300) as r:
        body = json.load(r)
    return body['items']


def today():
    o = os.environ.get('REPORT_DATE')
    return dt.date.fromisoformat(o) if o else dt.datetime.now(SAST).date()


def is_trading_day(d):
    return d.weekday() < 5 and d.isoformat() not in CONFIG['holidays']


def month_days(d):
    first = d.replace(day=1)
    nxt = (first + dt.timedelta(days=32)).replace(day=1)
    return [first + dt.timedelta(days=i) for i in range((nxt - first).days)]


def trading_calendar(d):
    """(elapsed trading days including d if trading, total trading days, remaining incl. d)"""
    days = [x for x in month_days(d) if is_trading_day(x)]
    elapsed = sum(1 for x in days if x < d)
    return elapsed, len(days), len(days) - elapsed
