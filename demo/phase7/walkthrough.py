"""Drives Studio through its API for the phase 7 demo (demo/phase7/run.sh), as the page does.
Usage: python walkthrough.py <studio address> ask|explore
  ask      a recorded agent asks twice; the person allows the first and denies the second, signed; the refusals around it
  explore  the APK is uploaded, the device picked from those adb sees, the recorded analyst walks two screens, Studio shows them"""
import sys, json, time, urllib.request, urllib.error
from urllib.parse import urlparse, parse_qs

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
u = urlparse(sys.argv[1]); BASE = f"{u.scheme}://{u.netloc}"; TOKEN = parse_qs(u.query)["t"][0]; PART = sys.argv[2]
failed = []


def call(path, body=None, raw=None):
    data = raw if raw is not None else None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(BASE + path, data=data, method="GET" if data is None else "POST",
                                 headers={"X-TestHive-Token": TOKEN, "Content-Type": "application/octet-stream" if raw is not None else "application/json"})
    try:
        with urllib.request.urlopen(req) as r: return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e: return e.code, dict(e.headers), e.read()


def js(path, body=None, raw=None):
    code, _, b = call(path, body, raw)
    try: return code, json.loads(b or b"{}")
    except ValueError: return code, {}


def step(text, ok):
    print(("  ok    " if ok else "  WRONG ") + text)
    if not ok: failed.append(text)


def until(cond, secs=60):
    end = time.time() + secs
    while time.time() < end:
        r = js("/api/jobs?m=SIGNUP")[1]
        if cond(r): return r
        time.sleep(0.3)
    return js("/api/jobs?m=SIGNUP")[1]


def ask(i, decision, note="", by="Sara (QA lead)"):
    return js("/api/ask", {"module": "SIGNUP", "id": i, "decision": decision, "note": note, "by": by})


if PART == "ask":
    step("no question to answer while no agent works", ask("001", "allow")[0] == 409)
    code, r = js("/api/run", {"module": "SIGNUP", "action": "analyse"}); step(f"an agent starts: {r.get('message')}", code == 200)
    j = until(lambda r: r["job"] and r["job"]["asks"])["job"]
    a = (j or {}).get("asks") or [{}]
    step(f"Studio shows its question: {a[0].get('tool')} {a[0].get('input', '')[:60].strip()}", a[0].get("tool") == "Bash" and "npx playwright" in a[0].get("input", ""))
    step("an answer needs a name", ask("001", "allow", by="")[0] == 400)
    step("an unknown answer is refused", ask("001", "maybe")[0] == 400)
    step("Allow once", ask("001", "allow")[0] == 200)
    step("the same question cannot be answered twice", ask("001", "deny")[0] == 409)
    j = until(lambda r: r["job"] and any(x["id"] == "002" for x in r["job"]["asks"]))["job"]
    a = (j or {}).get("asks") or [{}]
    step(f"the second question: {a[0].get('tool')} {a[0].get('input', '')[:50].strip()}", a[0].get("tool") == "Write" and "playwright.config.ts" in a[0].get("input", ""))
    step("Deny with a note", ask("002", "deny", "keep the config as it is")[0] == 200)
    r = until(lambda r: not r["job"])
    last = r.get("last") or {}
    step(f"the agent got both answers: {last.get('summary')}", last.get("status") == "done" and last.get("summary") == "Asked twice: allow, deny")
    log = js(f"/api/job?id={last.get('id')}")[1]
    lines = "\n".join(log.get("lines") or log.get("progress") or [])
    step("the answers are in the job's log, signed", "? Sara (QA lead) allowed question 001" in lines and "? Sara (QA lead) denied question 002: keep the config as it is" in lines)
else:
    code, r = js("/api/run", {"module": "SIGNUP", "action": "explore-android"})
    step(f"Explore the app without an APK is refused: {r.get('message')}", code == 409 and "APK" in r.get("message", ""))
    code, r = js("/api/source?m=SIGNUP&kind=apk&name=nakhla-1.0.apk&by=Sara", raw=b"PK\x03\x04 not a real app")
    step(f"the APK is uploaded: {r.get('message')}", code == 200)
    devs = js("/api/devices")[1].get("devices")
    step(f"devices adb sees: {devs}", devs == ["emulator-5554"])
    step("a device adb does not see is refused", js("/api/run", {"module": "SIGNUP", "action": "explore-android", "options": {"device": "R58N-other"}})[0] == 400)
    code, r = js("/api/run", {"module": "SIGNUP", "action": "explore-android", "options": {"device": "emulator-5554"}})
    step(f"Explore the app: {r.get('message')}", code == 200 and "emulator-5554" in r.get("message", ""))
    r = until(lambda r: not r["job"])
    step(f"the analyst explored: {(r.get('last') or {}).get('summary')}", (r.get("last") or {}).get("status") == "done")
    x = js("/api/module?m=SIGNUP")[1].get("android_exploration") or {}
    step(f"Sources shows the screens: {x.get('screens')}", x.get("screens") == ["01-sign-up.png", "02-otp.png"])
    code, h, b = call("/api/exploration-shot?m=SIGNUP&name=01-sign-up.png")
    step(f"a screen opens ({h.get('Content-Type')})", code == 200 and h.get("Content-Type") == "image/png" and b[:4] == b"\x89PNG")
    step("a path outside the screens is refused", call("/api/exploration-shot?m=SIGNUP&name=../../../workflow/state.json")[0] == 404)
    code, r = js("/api/exploration?m=SIGNUP&kind=android")
    step("the exploration report opens", code == 200 and "OBSERVED behaviour" in r.get("text", ""))
print(f"STUDIO {PART.upper()} CHECK " + ("PASS" if not failed else "FAIL"))
js("/api/shutdown", {})
sys.exit(1 if failed else 0)
