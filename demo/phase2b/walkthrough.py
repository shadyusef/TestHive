"""Drives TestHive Studio's API the way a person would in the browser, and prints each result (demo --check, CI).
Usage: python walkthrough.py <studio address with ?t=token>. Exit 1 if Studio does not behave as expected."""
import sys, json, urllib.request, urllib.error
from urllib.parse import urlparse, parse_qs

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
u = urlparse(sys.argv[1]); BASE = f"{u.scheme}://{u.netloc}"; TOKEN = parse_qs(u.query)["t"][0]
failed = []


def call(path, body=None, token=TOKEN):
    req = urllib.request.Request(BASE + path, data=None if body is None else json.dumps(body).encode(), method="GET" if body is None else "POST",
                                 headers={"X-TestHive-Token": token, **({"Content-Type": "application/json"} if body is not None else {})})
    try:
        with urllib.request.urlopen(req) as r: raw = r.read(); code = r.status
    except urllib.error.HTTPError as e: raw = e.read(); code = e.code
    try: return code, json.loads(raw)
    except ValueError: return code, raw


def step(text, ok):
    print(("  ok    " if ok else "  WRONG ") + text)
    if not ok: failed.append(text)


code, _ = call("/api/overview", token="wrong")
step("a request without the access key is refused (403)", code == 403)
code, o = call("/api/overview")
m = o["modules"][0]
print(f"Home: project '{o['project']}', module {m['module']}: " + ", ".join(f"{s['stage']} {s['status']}" for s in m["stages"][:2]) + f"; {m['open_gaps']} open questions")
print(f"  next: {m['next']['text']} {m['next']['command']}")
code, d = call("/api/module?m=SIGNUP")
a, ds = d["analysis"], d["design"]
step(f"module page: {len(a['requirements'])} requirements, {len(a['gaps'])} questions, {len(ds['cases'])} cases, {len(ds['coverage'])} requirements in coverage", code == 200)

gap = next((g for g in a["gaps"] if g["ID"] == "GAP-SIGNUP-041" and g["Status"] == "Open"), None) or next(g for g in a["gaps"] if g["Status"] == "Open")
code, r = call("/api/answers", {"module": "SIGNUP", "version": a["version"], "rows": [
    {"ID": gap["ID"], "Answer": "Yes: the demo issues a new random code after a resend.", "Answered By": "Sara (QA lead)", "Status": "Answered"}]})
step(f"Analysis tab: answer {gap['ID']} -> {r.get('message')}", code == 200 and r.get("ok"))
code, r = call("/api/answers", {"module": "SIGNUP", "version": a["version"], "rows": [{"ID": gap["ID"], "Answer": "x", "Answered By": "Sara", "Status": "Answered"}]})
step(f"saving from a page that is out of date is refused (409): {r.get('error', '')[:70]}...", code == 409)

code, r = call("/api/review", {"module": "SIGNUP", "version": ds["version"], "cases": [{"ID": "TC-SIGNUP-002", "Review": "Change", "Review Comment": ""}]})
step(f"Design tab: 'Change' without a comment is refused, nothing saved: {r.get('errors')}", code == 400)
todo = [c["ID"] for c in ds["cases"] if not c["Review"] and c["Status"] != "Removed"][:20]
code, r = call("/api/review", {"module": "SIGNUP", "version": ds["version"], "cases": [{"ID": i, "Review": "Accepted", "Review Comment": ""} for i in todo]})
step(f"Design tab: accept {len(todo)} cases not reviewed yet -> {r.get('message')}", code == 200 and r.get("ok"))

code, d = call("/api/module?m=SIGNUP")
step(f"Approvals tab: design check {'passes' if d['design']['check']['ok'] else 'fails'} ({len(d['design']['check']['warnings'])} warnings)", d["design"]["check"]["ok"])
code, r = call("/api/stage", {"module": "SIGNUP", "stage": "design", "action": "approve", "by": "Sara (QA lead)", "comment": "Reviewed in Studio"})
step("Approve the design -> " + " | ".join(l for l in r.get("message", "").splitlines() if "approved" in l or "BASELINE" in l), code == 200 and r.get("ok"))
code, r = call("/api/stage", {"module": "SIGNUP", "stage": "analysis", "action": "reopen", "by": "Sara (QA lead)", "comment": ""})
step(f"reopen without a comment is refused: {r.get('message', '').splitlines()[-1] if r.get('message') else r.get('error')}", code == 400)
req = urllib.request.Request(f"{BASE}/api/workbook?m=SIGNUP&kind=design&t={TOKEN}")
with urllib.request.urlopen(req) as w: data = w.read()
step(f"download the design workbook ({len(data) // 1024} KB Excel file)", data[:2] == b"PK")
code, d = call("/api/module?m=SIGNUP")
print("Now: " + ", ".join(f"{s['stage']} {s['status']}" + (f" by {s['by']}" if s["by"] else "") for s in d["stages"][:2]) + f"; next: {d['next']['text']}")
call("/api/shutdown", {})
print("STUDIO CHECK " + ("PASS" if not failed else f"FAIL ({len(failed)})"))
sys.exit(1 if failed else 0)
