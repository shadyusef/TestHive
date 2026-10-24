"""Checks Studio's reporting stage through its API (demo/phase6/run.sh --check): the Reports data of the signed-off module, the
report file route, and the refusals. Usage: python walkthrough.py <studio address>."""
import sys, json, urllib.request, urllib.error
from urllib.parse import urlparse, parse_qs

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
u = urlparse(sys.argv[1]); BASE = f"{u.scheme}://{u.netloc}"; TOKEN = parse_qs(u.query)["t"][0]
failed = []


def call(path, body=None):
    req = urllib.request.Request(BASE + path, data=None if body is None else json.dumps(body).encode(), method="GET" if body is None else "POST",
                                 headers={"X-TestHive-Token": TOKEN, **({"Content-Type": "application/json"} if body is not None else {})})
    try:
        with urllib.request.urlopen(req) as r: return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e: return e.code, dict(e.headers), e.read()


def js(path, body=None):
    code, _, raw = call(path, body); return code, json.loads(raw or b"{}")


def step(text, ok):
    print(("  ok    " if ok else "  WRONG ") + text)
    if not ok: failed.append(text)


d = js("/api/module?m=SIGNUP")[1]; r = d["reporting"]
step(f"Reports tab: TestHive suggests {r['report']['suggestion']}; decided {r['decision']['decision']} by {r['decision']['by']}; ready: {r['check']['ok']}",
     r["report"]["suggestion"] == "No-go" and r["decision"]["decision"] == "Go" and r["check"]["ok"])
step(f"bugs: {[(b['ID'], b['Status']) for b in d['bugs']['rows']]}", [(b["ID"], b["Status"]) for b in d["bugs"]["rows"]] == [("BUG-SIGNUP-001", "Verified"), ("BUG-SIGNUP-002", "Open")])
step(f"every stage approved; next: {d['next']['text']}", all(s["status"] == "approved" for s in d["stages"]))
code, h, body = call("/api/report-file?m=SIGNUP")
step(f"the report opens from Studio, sandboxed ({h.get('Content-Type')}; {h.get('Content-Security-Policy', '')[:24]}...)",
     code == 200 and "sandbox" in h.get("Content-Security-Policy", "") and b"TestHive suggests: No-go" in body and b"Mona (product owner)" in body)
step("a decision after the sign-off is refused", js("/api/report-decision", {"module": "SIGNUP", "decision": "No-go", "reason": "late", "by": "Sara"})[0] == 400)
step("a decision without a reason is refused", js("/api/report-decision", {"module": "SIGNUP", "decision": "Go", "by": "Sara"})[0] == 400)
step("a bug without a name is refused", js("/api/bugs", {"module": "SIGNUP", "action": "add", "title": "x", "severity": "Minor", "cases": "TC-SIGNUP-001"})[0] == 400)
step("a bug on a case that is not in the design is refused", js("/api/bugs", {"module": "SIGNUP", "action": "add", "title": "x", "severity": "Minor", "cases": "TC-SIGNUP-999", "by": "Sara"})[0] == 400)
step("a value starting with - is refused", js("/api/bugs", {"module": "SIGNUP", "action": "status", "id": "--by", "status": "Fixed", "by": "Sara"})[0] == 400)
print("STUDIO REPORTING CHECK " + ("PASS" if not failed else "FAIL"))
js("/api/shutdown", {})
sys.exit(1 if failed else 0)
