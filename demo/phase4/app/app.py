"""A small stand-in for the fictional Nakhla Rewards sign-up (demo only): the web pages and the API the phase 4 tests run against.
Usage: python app.py [port] [--resend-cooldown seconds] [--break-contract]      prints "APP http://127.0.0.1:<port>" when it is ready
--break-contract: the sign-up answers signupId as a number, not the string the spec gives (the contract tests catch it).
Web: /signup -> /otp -> /welcome. API: POST /v1/signup, /v1/otp/verify, /v1/otp/resend (demo/phase1/sources/openapi.yaml).
Numbers 0500000037 and 0500000087 are already registered; the OTP is always 123456. Everything is kept in memory."""
import sys, json, re, time, secrets
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

REGISTERED = {"0500000037", "0500000087"}
PENDING = {}  # signupId -> {"mobile", "sent"}
a = sys.argv[1:]
COOLDOWN = float(a[a.index("--resend-cooldown") + 1]) if "--resend-cooldown" in a else 30.0
BROKEN = "--break-contract" in a

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{title} - Nakhla Rewards</title>
<style>body{{font:16px system-ui;max-width:420px;margin:40px auto;padding:0 16px}}label{{display:block;margin-top:12px}}input,select{{width:100%;padding:8px}}
input[type=checkbox]{{width:auto}}.err{{color:#b00020;min-height:1.4em}}.otp input{{width:2.2em;text-align:center}}button{{margin-top:16px;padding:10px 18px}}</style></head>
<body><h1>{title}</h1>{body}</body></html>"""

SIGNUP = """<form id="f" novalidate>
<label for="name">Full name</label><input id="name" data-qa="full-name" autocomplete="off">
<label for="mobile">Mobile number</label><input id="mobile" data-qa="mobile" inputmode="numeric">
<label for="pw">Password</label><input id="pw" data-qa="password" type="password">
<label for="dob">Date of birth</label><input id="dob" data-qa="birth-date" type="date">
<label for="lang">Language</label><select id="lang" data-qa="language"><option value="en">English</option><option value="ar">العربية</option></select>
<label><input id="terms" data-qa="terms" type="checkbox"> I accept the terms and conditions</label>
<p class="err" role="alert" data-qa="error"></p><button type="submit" data-qa="sign-up">Sign up</button></form>
<script>
const $ = s => document.querySelector(s);
$('#f').onsubmit = async e => {
  e.preventDefault(); $('.err').textContent = '';
  if (!$('#terms').checked) return $('.err').textContent = 'Please accept the terms and conditions';
  const r = await fetch('/v1/signup', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({
    fullName: $('#name').value, mobile: $('#mobile').value, password: $('#pw').value, birthDate: $('#dob').value, language: $('#lang').value, termsVersion: 1})});
  const b = await r.json();
  if (r.status === 201) location.href = '/otp?id=' + encodeURIComponent(b.signupId);
  else $('.err').textContent = r.status === 409 ? 'This mobile number is already registered. Log in instead?' : (b.error || 'Something went wrong');
};
</script>"""

OTP = """<p>We sent a 6-digit code to your mobile.</p><form id="f" class="otp">
<div>""" + "".join(f'<input maxlength="1" inputmode="numeric" aria-label="Digit {i}" data-qa="otp-{i}">' for i in range(1, 7)) + """</div>
<p class="err" role="alert" data-qa="error"></p><button type="submit" data-qa="verify">Verify</button></form>
<script>
document.querySelector('#f').onsubmit = async e => {
  e.preventDefault();
  const code = [...document.querySelectorAll('.otp input')].map(i => i.value).join('');
  const r = await fetch('/v1/otp/verify', {method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({signupId: new URLSearchParams(location.search).get('id'), code})});
  const b = await r.json();
  if (r.status === 200) location.href = '/welcome?points=' + b.points;
  else document.querySelector('.err').textContent = 'The code is incorrect.';
};
</script>"""

WELCOME = """<p data-qa="balance">Your balance: <b id="points"></b> points</p>
<script>document.querySelector('#points').textContent = new URLSearchParams(location.search).get('points');</script>"""


class App(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def send(self, code, body, ctype="application/json"):
        data = body.encode() if isinstance(body, str) else json.dumps(body).encode()
        self.send_response(code); self.send_header("Content-Type", ctype + "; charset=utf-8"); self.send_header("Content-Length", str(len(data)))
        self.end_headers(); self.wfile.write(data)

    def do_GET(self):
        p = urlparse(self.path).path
        pages = {"/signup": ("Create your account", SIGNUP), "/otp": ("Verify your mobile number", OTP), "/welcome": ("Welcome to Nakhla Rewards", WELCOME)}
        if p == "/": p = "/signup"
        if p not in pages: return self.send(404, {"error": "not found"})
        self.send(200, PAGE.format(title=pages[p][0], body=pages[p][1]), "text/html")

    def do_POST(self):
        try: b = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        except ValueError: return self.send(400, {"error": "bad JSON"})
        p = urlparse(self.path).path
        if p == "/v1/signup":
            missing = [k for k in ("fullName", "mobile", "password", "birthDate", "language") if not str(b.get(k, "")).strip()]
            if missing: return self.send(400, {"error": "missing " + ", ".join(missing)})
            if not re.fullmatch(r"05\d{8}", str(b["mobile"])): return self.send(400, {"error": "The mobile number must be 10 digits starting with 05."})
            if len(str(b["password"])) < 8: return self.send(400, {"error": "The password must have at least 8 characters."})
            if b["mobile"] in REGISTERED: return self.send(409, {"error": "already registered"})
            sid = secrets.token_hex(8); PENDING[sid] = {"mobile": b["mobile"], "sent": time.time()}
            return self.send(201, {"signupId": int(sid, 16) if BROKEN else sid})
        if p == "/v1/otp/verify":
            if b.get("signupId") not in PENDING: return self.send(404, {"error": "unknown signupId"})
            if b.get("code") != "123456": return self.send(400, {"error": "The code is incorrect."})
            REGISTERED.add(PENDING.pop(b["signupId"])["mobile"])
            return self.send(200, {"accessToken": secrets.token_hex(16), "points": 50})
        if p == "/v1/otp/resend":
            s = PENDING.get(b.get("signupId"))
            if not s: return self.send(404, {"error": "unknown signupId"})
            if time.time() - s["sent"] < COOLDOWN: return self.send(429, {"error": "wait before asking for a new code"})
            s["sent"] = time.time(); return self.send(202, {"sent": True})
        self.send(404, {"error": "not found"})


if __name__ == "__main__":
    port = int(a[0]) if a and a[0].isdigit() else 0
    ThreadingHTTPServer.request_queue_size = 128  # the default 5 refuses connections when every test worker opens a page at once
    srv = ThreadingHTTPServer(("127.0.0.1", port), App)
    print(f"APP http://127.0.0.1:{srv.server_address[1]}", flush=True)
    srv.serve_forever()
