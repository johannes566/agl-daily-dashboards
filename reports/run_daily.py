"""Build the BCS dashboard, run the send gate, upload the PDF and WhatsApp it.
Environment: TEST_ONLY=true sends to the first recipient only. HOLD notices always go to the first recipient only."""
import os, sys, json, subprocess, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import CONFIG, today
import bird

STATE = os.path.join(os.environ.get('TOKEN_DIR', '/tmp/state'), 'state'); os.makedirs(STATE, exist_ok=True)
OUT_DIR = os.path.join(STATE, 'out'); os.makedirs(OUT_DIR, exist_ok=True)
D = today()
TEST_ONLY = os.environ.get('TEST_ONLY', 'true').lower() == 'true'
RECIP = CONFIG['recipients'][:1] if TEST_ONLY else CONFIG['recipients']
OWNER = CONFIG['recipients'][0]
R = lambda v: 'R{:,.0f}'.format(v)

def hold(reason):
    print('HOLD:', reason)
    code, js = bird.send_template(OWNER, 'agl_daily_report', {
        'report_name': 'Butlers Catering Daily Finance Dashboard', 'report_date': D.strftime('%d %b %Y'),
        'headline': 'NOT SENT. The data checks failed: ' + reason, 'report_link': 'No report today'},
        f'hold-bcs-{D.isoformat()}')
    print('hold notice HTTP', code)
    sys.exit(1)

env = dict(os.environ, OUT_DIR=OUT_DIR, REPORT_DATE=D.isoformat())
p = subprocess.run([sys.executable, os.path.join(HERE, 'bcs', 'bcs_mk2.py')], env=env, capture_output=True, text=True)
if p.returncode != 0:
    print(p.stdout[-1500:], p.stderr[-1500:])
    hold('the report builder crashed (' + (p.stderr.strip().splitlines() or ['unknown'])[-1][:120] + ')')
s = json.load(open(os.path.join(OUT_DIR, 'bcs_summary.json')))
print('built:', json.dumps({k: s[k] for k in ('basket', 'gp_pct', 'fixed_spent', 'gap', 'invoice_total', 'quote_total')}))
print('detail:', json.dumps(s.get('detail', {})))

# ---- send gate ----
problems = list(s['issues'])
prev_path = os.path.join(STATE, 'bcs_prev.json')
if os.path.exists(prev_path):
    pv = json.load(open(prev_path))
    if pv.get('date', '')[:7] == D.isoformat()[:7] and pv['date'] != D.isoformat():
        if s['basket'] < pv['basket'] * 0.95:
            problems.append(f"the sales basket fell from {R(pv['basket'])} to {R(s['basket'])}")
        for k in ('priced_share_general', 'priced_share_general_quote', 'priced_share_hamper', 'priced_share_hamper_quote'):
            if s[k] < pv[k] - 2:
                problems.append(f"priced share {k} fell from {pv[k]}% to {s[k]}%")
        if s['fixed_spent'] < pv['fixed_spent'] * 0.99:
            problems.append('fixed costs to date went down against yesterday')
if problems:
    hold('; '.join(problems)[:600])

# ---- deliver ----
url = bird.public_link(s['pdf']) or bird.upload_pdf(s['pdf'])
fname = os.path.basename(s['pdf'])
name = 'Butlers Catering Daily Finance Dashboard'
headline = f"Sales basket {R(s['basket'])} ex VAT at {s['gp_pct']}% GP. {R(s['gap'])} short of the {R(s['target'])} target, {s['trading_days_left']} trading days left."
ok = 0
for to in RECIP:
    key = f'bcs-{D.isoformat()}-{to}'
    code, js = bird.send_template(to, 'agl_report_pdf', {'header_url': url, 'header_filename': fname, 'report_name': name, 'report_date': D.strftime('%d %b %Y')}, key + '-pdf')
    if code >= 300:
        print('PDF template not usable yet (HTTP %s), sending link version' % code)
        code, js = bird.send_template(to, 'agl_daily_report', {'report_name': name, 'report_date': D.strftime('%d %b %Y'), 'headline': headline, 'report_link': url}, key + '-link')
    print('sent to', to[:-4] + '****', 'HTTP', code)
    ok += code < 300
if ok:
    json.dump(s, open(prev_path, 'w'))
print('done, delivered:', ok, 'of', len(RECIP))
