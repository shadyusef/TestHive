"""Drives Studio's automation stage through its API (demo/phase4/run.sh --check): the Automation data, Run the tests by tag,
the last run, the evidence route's refusals, the contract tests, a recorded engineer run, and the gate. Usage: python walkthrough.py <studio address>."""
import sys, json, time, urllib.request, urllib.error
from urllib.parse import urlparse, parse_qs

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
u = urlparse(sys.argv[1]); BASE = f"{u.scheme}://{u.netloc}"; TOKEN = parse_qs(u.query)["t"][0]
failed = []


def call(path, body=None):
    req = urllib.request.Request(BASE + path, data=None if body is None else json.dumps(body).encode(), method="GET" if body is None else "POST",
                                 headers={"X-TestHive-Token": TOKEN, **({"Content-Type": "application/json"} if body is not None else {})})
    try:
        with urllib.request.urlopen(req) as r: return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e: return e.code, json.loads(e.read() or b"{}")


def step(text, ok):
    print(("  ok    " if ok else "  WRONG ") + text)
    if not ok: failed.append(text)


def module(): return call("/api/module?m=SIGNUP")[1]


def wait():
    for _ in range(600):
        time.sleep(0.5); j = call("/api/jobs?m=SIGNUP")[1]
        if not j["job"]: return j["last"]


d = module(); a = d["automation"]
count = lambda st: sum(1 for c in a["cases"] if c["state"] == st)
step(f"Automation tab: {len(a['cases'])} cases, {count('stable')} stable, {count('stub')} placeholders", (len(a["cases"]), count("stable"), count("stub")) == (89, 11, 78))
step(f"Next says: {d['next']['text']} -> button '{d['next'].get('title')}'", d["next"]["run"] == "automate-web")
step("a run with an unknown kind or tag is refused", call("/api/run", {"module": "SIGNUP", "action": "run-tests", "options": {"kind": "web; rm", "tag": ""}})[0] == 400
     and call("/api/run", {"module": "SIGNUP", "action": "run-tests", "options": {"kind": "api", "tag": "nope"}})[0] == 400)
code, r = call("/api/run", {"module": "SIGNUP", "action": "run-tests", "options": {"kind": "api", "tag": "smoke"}})
step(f"Run the API smoke tests: {r.get('message')}", code == 200)
last = wait()
run = module()["automation"]["runs"].get("api", {})
step(f"{last['title']}: {last['status']}; last API run {run.get('run')}: {run.get('totals')} (Newman counts each check)", last["status"] == "done" and run.get("totals", {}).get("passed") == 7)
for bad in ("evidence/../meta.json", "meta.json", "evidence/../../../workflow/state.json"):
    code, _ = call(f"/api/run-file?m=SIGNUP&run={run.get('run')}&name={bad}")
    step(f"evidence route refuses {bad}", code == 404)
step("evidence route refuses another run id form", call("/api/run-file?m=SIGNUP&run=..&name=evidence/x")[0] == 404)
ct = module()["automation"]["contract"]
step(f"Contract: {ct['operations']} endpoints, {ct['state']}; known bugs {[f['bug'] for f in ct['failed']]}",
     (ct["operations"], ct["state"], sorted(f["bug"] for f in ct["failed"])) == (3, "current", ["BUG-SIGNUP-201", "BUG-SIGNUP-202"]))
code, r = call("/api/run", {"module": "SIGNUP", "action": "run-tests", "options": {"kind": "contract", "tag": ""}})
last = wait(); run = module()["automation"]["runs"].get("contract", {})
step(f"Run the contract tests: {last['title']}: {last['status']}; {run.get('totals')}", code == 200 and run.get("totals", {}).get("passed") == 2)
code, r = call("/api/run", {"module": "SIGNUP", "action": "automate-web"})
last = wait()
step(f"{last['title']} (recorded): {last['summary'][:110]}", code == 200 and last["status"] == "done")
code, r = call("/api/stage", {"module": "SIGNUP", "stage": "automation", "action": "submit", "by": "Sara"})
step(f"Submit is refused while placeholders remain: {r.get('message', '').splitlines()[-1] if r.get('message') else r}", code == 400)
print("STUDIO AUTOMATION CHECK " + ("PASS" if not failed else "FAIL"))
call("/api/shutdown", {})
sys.exit(1 if failed else 0)
