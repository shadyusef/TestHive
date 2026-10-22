"""Drives TestHive Studio's intake API the way a newcomer would in the browser, and prints each result (demo --check, CI).
Usage: python walkthrough.py <studio address with ?t=token> <folder with documents to upload> <project folder>
Exit 1 if Studio does not behave as expected."""
import sys, os, json, urllib.request, urllib.error
from urllib.parse import urlparse, parse_qs, quote

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
u = urlparse(sys.argv[1]); BASE = f"{u.scheme}://{u.netloc}"; TOKEN = parse_qs(u.query)["t"][0]
DOCS, PROJECT = sys.argv[2], sys.argv[3]
failed = []


def call(path, body=None, raw=None):
    data = raw if raw is not None else (None if body is None else json.dumps(body).encode())
    ctype = "application/octet-stream" if raw is not None else "application/json"
    req = urllib.request.Request(BASE + path, data=data, method="GET" if data is None else "POST",
                                 headers={"X-TestHive-Token": TOKEN, **({"Content-Type": ctype} if data is not None else {})})
    try:
        with urllib.request.urlopen(req) as r: payload = r.read(); code = r.status
    except urllib.error.HTTPError as e: payload = e.read(); code = e.code
    try: return code, json.loads(payload)
    except ValueError: return code, {}


def step(text, ok):
    print(("  ok    " if ok else "  WRONG ") + text)
    if not ok: failed.append(text)


def upload(name, data, kind="source"):
    return call(f"/api/source?m=SIGNUP&kind={kind}&name={quote(name)}", raw=data)


code, o = call("/api/overview")
step("first opening: Studio asks for the project details (no project yet)", o["setup"]["setup_needed"])
code, r = call("/api/project", {"project": "Nakhla Rewards", "app": "Nakhla", "platforms": []})
step(f"setup without a platform is refused: {r.get('message')}", code == 400)
code, r = call("/api/project", {"project": "Nakhla Rewards", "app": "Nakhla", "platforms": ["Web", "API"], "test_env": "staging",
                                "base_url": "http://127.0.0.1:9/signup", "api_url": "", "app_id": ""})
step(f"project created: {r.get('message', '')[:80]}...", code == 200)
env = open(os.path.join(PROJECT, ".env"), encoding="utf-8").read()
step("the brief, CONTEXT.md and .env hold the facts; the password line in .env is left for the human",
     "Nakhla" in open(os.path.join(PROJECT, "CONTEXT.md"), encoding="utf-8").read() and "BASE_URL=http://127.0.0.1:9/signup" in env and "TEST_USER_PASSWORD=change-me" in env)
code, o = call("/api/overview")
step(f"home now shows project '{o['project']}' and no modules yet", not o["setup"]["setup_needed"] and o["modules"] == [])

code, r = call("/api/module-new", {"module": "sign up!"})
step(f"a bad module code is refused: {r.get('message')}", code == 400)
code, r = call("/api/module-new", {"module": "SIGNUP", "title": "Sign-up and mobile verification", "url": "http://127.0.0.1:9/signup", "test_env": True})
step(f"module added: {r.get('message')}", code == 200)
code, d = call("/api/module?m=SIGNUP")
print(f"  next: {d['next']['text']}")

for name, data, why in ((".env", b"x", "a hidden file name"), ("tool.exe", b"MZ", "a program"), ("old.doc", b"x", "old Word format")):
    code, r = upload(name, data)
    step(f"upload of {why} is refused: {r.get('message')}", code == 400)
code, r = upload("big.pdf", b"0" * 26_000_000)
step(f"a file over 25 MB is refused: {r.get('message')}", code == 413)
for f in sorted(os.listdir(DOCS)):
    code, r = upload(f, open(os.path.join(DOCS, f), "rb").read())
    step(f"upload {f}: {r.get('message')}", code == 200)
code, r = upload("prd.pdf", open(os.path.join(DOCS, "prd.pdf"), "rb").read())
step(f"uploading prd.pdf again keeps the earlier version: {r.get('message')}", code == 200 and "_old" in r.get("message", ""))
code, d = call("/api/module?m=SIGNUP")
step(f"Sources tab lists {len(d['sources']['files'])} documents, none read yet", len(d["sources"]["files"]) == 4 and not any(f["read"] for f in d["sources"]["files"]))
print(f"  next: {d['next']['text']}")

code, m = call("/api/mask-preview?m=SIGNUP")
step(f"personal-data check: {len(m['names'])} possible names, values found: {m['counts'] or 'none'}", code == 200)
code, r = call("/api/mask-lists", {"module": "SIGNUP", "terms": [], "allow": []})
step("saving the masking choices works", code == 200)
code, r = call("/api/ingest", {"module": "SIGNUP", "mask": False})
step("Read the documents -> " + (r.get("message", "").splitlines() or ["?"])[0], code == 200)
code, d = call("/api/module?m=SIGNUP")
step("every document is now read", all(f["read"] for f in d["sources"]["files"]))
print(f"  next: {d['next']['text']} {d['next']['command']}")
step("the analyst command carries the URL and says it is a test environment", "url=http://127.0.0.1:9/signup, test environment" in d["next"]["command"])
rd = d["readiness"]
print("  readiness: " + "; ".join(f"{i['label']}: {'yes' if i['ok'] else 'no'} ({i['detail']})" for i in rd["items"]))
step("not ready for automation yet (nothing approved)", not rd["ready"])
if "--keep" not in sys.argv: call("/api/shutdown", {})
print("STUDIO INTAKE CHECK " + ("PASS" if not failed else f"FAIL ({len(failed)})"))
sys.exit(1 if failed else 0)
