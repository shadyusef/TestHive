"""Checks a built TestHive Studio program on a fresh copy of this project: the page loads, and the actions that start other
libraries inside the program work (project setup, a new module, archive and restore), the bundled packages read PDF, Word
and YAML documents and write Excel, and a recorded agent run (demo/phase2d/fake-claude.py, needs bash) runs through the
program. Used by CI after the build.
Usage: python tests/studio_program_check.py dist/testhive-studio[.exe]
       python tests/studio_program_check.py scripts/lib/studio_app.py      (the same route from source, no build needed)"""
import sys, os, json, shutil, subprocess, tempfile, time, urllib.request
from urllib.parse import urlparse, parse_qs

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
prog = os.path.abspath(sys.argv[1])
env = dict(os.environ, TH_STUDIO_CONFIG=os.path.join(tempfile.mkdtemp(), "studio.json"))
if prog.endswith(".py"): cmd = [sys.executable, prog]; env["TH_LAUNCHER"] = prog
else: cmd = [prog]
proj = os.path.join(tempfile.mkdtemp(), "project")
shutil.copytree(ROOT, proj, ignore=shutil.ignore_patterns(".git", "dist", "build", "node_modules", "runs", "archive", "output", "__pycache__",
                                                         ".env", ".mask-*", ".private-names", "HANDOVER.md"))
for p in ("workflow/state.json", "PROJECT_BRIEF.md", "CONTEXT.md"):
    if os.path.exists(os.path.join(proj, p)): os.remove(os.path.join(proj, p))
env["TH_CLAUDE_FAKE"] = os.path.join(proj, "demo", "phase2d", "fake-claude.py"); env["TH_FAKE_DELAY"] = "0.05"
failed = []
def step(text, ok):
    print(("  ok    " if ok else "  WRONG ") + text, flush=True)
    if not ok: failed.append(text)

p = subprocess.Popen(cmd + ["--no-browser", "--port", "0", "--project", proj], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                     text=True, encoding="utf-8", errors="replace", env=env, cwd=tempfile.gettempdir())
url = None
for _ in range(400):
    line = p.stdout.readline()
    if not line: break
    if line.startswith("STUDIO "): url = line.split(" ", 1)[1].strip(); break
step("the program starts and prints its address", bool(url))
if not url: print(p.stdout.read()); sys.exit(1)
u = urlparse(url); BASE = f"{u.scheme}://{u.netloc}"; TOKEN = parse_qs(u.query)["t"][0]

def call(path, body=None):
    req = urllib.request.Request(BASE + path, data=None if body is None else json.dumps(body).encode(), method="GET" if body is None else "POST",
                                 headers={"X-TestHive-Token": TOKEN, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r: return r.status, r.read()
    except urllib.error.HTTPError as e:
        with e: return e.code, e.read()
def js(path, body=None):
    code, raw = call(path, body); return code, json.loads(raw or b"{}")
def upload(name):
    with open(os.path.join(proj, "demo", "phase1", "sources", name), "rb") as f: data = f.read()
    req = urllib.request.Request(f"{BASE}/api/source?m=SIGNUP&name={name}&by=CI", data=data, method="POST",
                                 headers={"X-TestHive-Token": TOKEN, "Content-Type": "application/octet-stream"})
    with urllib.request.urlopen(req) as r: return r.status

code, page = call("/?t=" + TOKEN); step("the page loads from inside the program", code == 200 and b"app.js" in page)
code, _ = call("/js/core.js"); step("its scripts load", code == 200)
code, r = js("/api/projects"); step("the project given with --project is open", code == 200 and os.path.samefile(r["current"], proj))
code, r = js("/api/project", {"project": "Check", "app": "Check", "platforms": ["Web"]}); step(f"project setup: {r.get('message', r)}", code == 200)
code, r = js("/api/module-new", {"module": "LOGIN", "title": "Log in"}); step(f"new module (stage rules run as a library): {r.get('message', r)}", code == 200)
code, r = js("/api/module-archive", {"module": "LOGIN", "by": "CI", "comment": "check", "confirm": "LOGIN"})
step("archive (a library starting another one)", code == 200)
arch = js("/api/archive")[1].get("archived", [])
code, r = js("/api/module-restore", {"archive": arch[0]["name"] if arch else "", "by": "CI"}); step("restore", code == 200)
print("--- documents, a recorded agent run and Excel (packages bundled in the program)")
js("/api/module-new", {"module": "SIGNUP", "title": "Sign-up"})
step("upload a PDF, a Word file and an OpenAPI file", all(upload(n) == 200 for n in ("prd.pdf", "user-stories.docx", "openapi.yaml")))
code, r = js("/api/ingest", {"module": "SIGNUP", "mask": False}); step(f"read them: {r.get('message', r)}", code == 200)
for n in ("prd.pdf", "user-stories.docx", "openapi.yaml"):
    words = len(js(f"/api/source-text?m=SIGNUP&name={n}")[1].get("text", "").split()); step(f"{n}: {words} words of text", words > 100)
code, r = js("/api/run", {"module": "SIGNUP", "action": "analyse"}); step("Run: Analyse the documents (recorded agent)", code == 200)
for _ in range(240):
    time.sleep(0.5); j = js("/api/jobs?m=SIGNUP")[1]
    if not j.get("job"): break
last = j.get("last") or {}
step(f"the run finished: {last.get('status')} -> {last.get('summary')}", last.get("status") == "done")
code, raw = call("/api/workbook?m=SIGNUP&kind=analysis"); step(f"the analysis workbook downloads ({len(raw)} bytes)", code == 200 and raw[:2] == b"PK")
js("/api/shutdown", {})
try: p.wait(timeout=20)
except subprocess.TimeoutExpired: p.kill()
shutil.rmtree(os.path.dirname(proj), ignore_errors=True)
print("STUDIO PROGRAM CHECK " + ("PASS" if not failed else f"FAIL ({len(failed)})"))
sys.exit(1 if failed else 0)
