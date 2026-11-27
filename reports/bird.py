"""Bird (WhatsApp) helpers: upload a PDF, send a template message. Uses only the standard library."""
import os, json, uuid, urllib.request, urllib.error

HOST = os.environ.get('BIRD_API_HOST', 'https://eu1.platform.bird.com')
KEY = os.environ.get('BIRD_API_KEY', '')
FROM = os.environ.get('BIRD_FROM', '+27828195950')


def _req(method, path, body=None, headers=None):
    h = {'Authorization': f'Bearer {KEY}', 'Accept': 'application/json'}
    h.update(headers or {})
    req = urllib.request.Request(HOST + path, data=body, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b'{}')
        except Exception:
            return e.code, {}


def upload_pdf(path):
    boundary = uuid.uuid4().hex
    name = os.path.basename(path)
    data = open(path, 'rb').read()
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{name}"\r\nContent-Type: application/pdf\r\n\r\n').encode() \
        + data + f'\r\n--{boundary}--\r\n'.encode()
    code, js = _req('POST', '/v1/assets', body, {'Content-Type': f'multipart/form-data; boundary={boundary}'})
    url = js.get('url') or (js.get('asset') or {}).get('url')
    if code >= 300 or not url:
        raise RuntimeError(f'Bird upload failed (HTTP {code}): ' + json.dumps({k: js.get(k) for k in ('code', 'message', 'error', 'detail', 'title') if js.get(k)})[:300])
    return url


def send_template(to, slug, parameters, key, tags=None):
    payload = {'from': FROM, 'to': to, 'template': {'slug': slug, 'language': 'en', 'parameters': parameters}, 'tags': tags or ['daily_report']}
    code, js = _req('POST', '/v1/whatsapp/messages', json.dumps(payload).encode(),
                    {'Content-Type': 'application/json', 'Idempotency-Key': key})
    if code >= 300:
        print('Bird rejected the message (HTTP %s): %s' % (code, json.dumps(js)[:900]))
    return code, js


def public_link(path):
    """Link served by this service (needs PUBLIC_BASE_URL). Unguessable: HMAC of the file name."""
    import hmac, hashlib
    base = os.environ.get('PUBLIC_BASE_URL', '').rstrip('/')
    if not base:
        return None
    name = os.path.basename(path)
    sig = hmac.new(os.environ['INTERNAL_KEY'].encode(), name.encode(), hashlib.sha256).hexdigest()[:40]
    return f'{base}/r/{sig}/{name}'
