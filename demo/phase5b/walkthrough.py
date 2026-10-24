"""Checks Studio's Run picker for targets through its API (demo/phase5b/run.sh --check): the targets and the keys status, the
devices route, the refusals, a run on a picked target, and that the access key never reaches the page.
Usage: python walkthrough.py <studio address> <the demo's made-up access key>"""
import sys, json, time, urllib.request, urllib.error
from urllib.parse import urlparse, parse_qs

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
u = urlparse(sys.argv[1]); BASE = f"{u.scheme}://{u.netloc}"; TOKEN = parse_qs(u.query)["t"][0]; KEY = sys.argv[2]
failed = []


def call(path, body=None):
    req = urllib.request.Request(BASE + path, data=None if body is None else json.dumps(body).encode(), method="GET" if body is None else "POST",
                                 headers={"X-TestHive-Token": TOKEN, **({"Content-Type": "application/json"} if body is not None else {})})
    try:
        with urllib.request.urlopen(req) as r: raw = r.read(); return r.status, json.loads(raw or b"{}"), raw
    except urllib.error.HTTPError as e: raw = e.read(); return e.code, json.loads(raw or b"{}"), raw


def step(text, ok):
    print(("  ok    " if ok else "  WRONG ") + text)
    if not ok: failed.append(text)


def run(options):
    return call("/api/run", {"module": "SIGNUP", "action": "run-tests", "options": dict({"kind": "web", "tag": "smoke"}, **options)})


code, d, raw = call("/api/module?m=SIGNUP")
step(f"targets offered: {', '.join(d['targets'])}; BrowserStack keys set: {d['browserstack_keys']}", "bs-pixel7" in d["targets"] and d["browserstack_keys"] is True)
step("the access key is nowhere in the page data", KEY.encode() not in raw)
code, r, _ = call("/api/devices"); step(f"devices route answers: {r.get('devices')}", code == 200 and isinstance(r.get("devices"), list))
step("a mobile target for web tests is refused", run({"target": "bs-pixel7"})[0] == 400)
step("an unknown target is refused", run({"target": "nope"})[0] == 400)
step("a device adb does not see is refused", call("/api/run", {"module": "SIGNUP", "action": "run-tests", "options": {"kind": "mobile", "tag": "", "target": "android", "device": "emulator-9999"}})[0] == 400)
code, r, _ = run({"target": "edge"}); step(f"Run on a picked target: {r.get('message')}", code == 200)
for _ in range(600):
    time.sleep(0.5); j = call("/api/jobs?m=SIGNUP")[1]
    if not j["job"]: break
web = call("/api/module?m=SIGNUP")[1]["automation"]["runs"].get("web", {})
step(f"the last web run shows its target: {web.get('target')} ({web.get('totals')})", web.get("target") == "edge" and web.get("totals", {}).get("passed") == 7)
print("STUDIO TARGETS CHECK " + ("PASS" if not failed else "FAIL"))
call("/api/shutdown", {})
sys.exit(1 if failed else 0)
