"""Checks Studio's execution stage through its API (demo/phase5/run.sh --check): the Execution data of the approved cycle, the
environments offered, the evidence route, and the refusals. Usage: python walkthrough.py <studio address> <web run> <api run>."""
import sys, json, urllib.request, urllib.error
from urllib.parse import urlparse, parse_qs, quote

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
u = urlparse(sys.argv[1]); BASE = f"{u.scheme}://{u.netloc}"; TOKEN = parse_qs(u.query)["t"][0]
WEBRUN, APIRUN = sys.argv[2], sys.argv[3]
failed = []


def call(path, body=None, raw=False):
    req = urllib.request.Request(BASE + path, data=None if body is None else json.dumps(body).encode(), method="GET" if body is None else "POST",
                                 headers={"X-TestHive-Token": TOKEN, **({"Content-Type": "application/json"} if body is not None else {})})
    try:
        with urllib.request.urlopen(req) as r: return r.status, (r.headers.get("Content-Type"), r.read()) if raw else json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e: return e.code, (None, b"") if raw else json.loads(e.read() or b"{}")


def step(text, ok):
    print(("  ok    " if ok else "  WRONG ") + text)
    if not ok: failed.append(text)


d = call("/api/module?m=SIGNUP")[1]; x = d["execution"]; cs = x["cases"]
n = lambda r: sum(1 for c in cs if c["result"] == r)
step(f"Execution tab: cycle {x['cycle']['id']} \"{x['cycle']['name']}\" on {x['cycle']['env']}, {len(cs)} cases, {n('passed')} passed, "
     f"{n('failed')} failed, {n('blocked')} blocked, {n('not-run')} not run", x["cycle"]["id"] == "C1" and n("not-run") == 0 and n("failed") == 1 and n("blocked") == 1)
q = [c["ID"] for c in cs if c["quarantine"]]
step(f"quarantined: {q}; fixed bugs: {sorted(x['fixed'])}; ready: {x['check']['ok']}", q == ["TC-SIGNUP-098"] and list(x["fixed"]) == ["BUG-SIGNUP-301"] and x["check"]["ok"])
step(f"environments offered: {x['envs']} (names only)", x["envs"] == ["demo"])
step(f"the stage is {d['stages'][4]['status']}; next: {d['next']['text']}", d["stages"][4]["status"] == "approved")
code, r = call("/api/execution", {"module": "SIGNUP", "action": "result", "ids": ["TC-SIGNUP-062"], "result": "Passed", "by": "Sara"})
step(f"a result after the approval is refused: {r.get('message', '')[:90]}", code == 400 and "approved" in r.get("message", ""))
step("a result without a name is refused", call("/api/execution", {"module": "SIGNUP", "action": "result", "ids": ["TC-SIGNUP-062"], "result": "Passed"})[0] == 400)
step("an unknown action is refused", call("/api/execution", {"module": "SIGNUP", "action": "delete", "by": "Sara"})[0] == 400)
step("a run on an environment that does not exist is refused",
     call("/api/run", {"module": "SIGNUP", "action": "run-tests", "options": {"kind": "web", "tag": "", "env": "../x"}})[0] == 400)
ev = [e for e in json.loads(open(f"runs/{WEBRUN}/results.json", encoding="utf-8").read())["cases"] if e["id"] == "TC-SIGNUP-051"][0]["evidence"]
video = next((e for e in ev if e.endswith(".webm")), "")
code, (ctype, body) = call(f"/api/run-file?m=SIGNUP&run={WEBRUN}&name={quote(video)}", raw=True)
step(f"the failed web test's video opens from Studio ({ctype}, {len(body)} bytes)", code == 200 and ctype == "video/webm" and len(body) > 1000)
ev = [e for e in json.loads(open(f"runs/{APIRUN}/results.json", encoding="utf-8").read())["cases"] if e["id"] == "TC-SIGNUP-072"][0]["evidence"]
code, (ctype, body) = call(f"/api/run-file?m=SIGNUP&run={APIRUN}&name={quote(ev[0])}", raw=True) if ev else (0, (None, b""))
step(f"an API request and response opens from Studio ({ctype}), password masked", code == 200 and b'"password": "***"' in body)
print("STUDIO EXECUTION CHECK " + ("PASS" if not failed else "FAIL"))
call("/api/shutdown", {})
sys.exit(1 if failed else 0)
