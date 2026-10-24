"""Runs a module's Maestro flows on a BrowserStack device (App Automate REST API) and writes the results as junit, so the run is
stored like a local one. Called by scripts/run-mobile.sh --target <BrowserStack target>; the keys come from the environment
(BROWSERSTACK_USERNAME, BROWSERSTACK_ACCESS_KEY, set by run-mobile.sh from .env) and are sent only to BrowserStack's address
(or a local stand-in on 127.0.0.1, targets.endpoint). Nothing it prints or writes contains them.
Usage: python browserstack.py <module> <app file> <junit out> <evidence dir> [tag]
Steps: upload the app, zip and upload the flows (with mobile/subflows/), start a build on TH_BS_DEVICE, wait for it
(TH_BS_MAX_MINUTES, default 60), read each session's test cases, write junit and one evidence file per test case (its video and logs)."""
import sys, os, re, io, json, time, base64, secrets, zipfile, urllib.request, urllib.error
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import targets

ID = re.compile(r"TC-[A-Z0-9]+(?:-[A-Z0-9]+)*-\d{3}")
DONE = ("passed", "failed", "error", "timedout", "timeout", "done", "stopped", "skipped")


def die(m): print(m); sys.exit(1)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a): return None  # a redirect is an error: the keys never follow it to another address


OPEN = urllib.request.build_opener(NoRedirect).open


class BS:
    def __init__(self):
        u, k = os.environ.get("BROWSERSTACK_USERNAME", ""), os.environ.get("BROWSERSTACK_ACCESS_KEY", "")
        if not (u and k): die("The BrowserStack keys are not set: add BROWSERSTACK_USERNAME and BROWSERSTACK_ACCESS_KEY to .env (you, not an agent).")
        self.base, self.auth = targets.endpoint("mobile"), "Basic " + base64.b64encode(f"{u}:{k}".encode()).decode()

    def call(self, method, path, body=None, ctype="application/json"):
        data = json.dumps(body).encode() if ctype == "application/json" and body is not None else body
        req = urllib.request.Request(self.base + path, data=data, method=method, headers={"Authorization": self.auth, **({"Content-Type": ctype} if data else {})})
        try:
            with OPEN(req, timeout=300) as r: return json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:  # BrowserStack's message, never the request (it carries the keys)
            die(f"BrowserStack answered {e.code} to {method} {path}: {e.read()[:300].decode('utf-8', 'replace')}")
        except (urllib.error.URLError, OSError) as e: die(f"Cannot reach BrowserStack ({self.base}): {getattr(e, 'reason', e)}")

    def upload(self, path, name, data):
        b = "----TestHive" + secrets.token_hex(8)
        body = (f"--{b}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{name}\"\r\nContent-Type: application/octet-stream\r\n\r\n").encode() + data + f"\r\n--{b}--\r\n".encode()
        return self.call("POST", path, body, f"multipart/form-data; boundary={b}")


def suite(module):
    """The flows as BrowserStack wants them: one zip with a parent folder (tests/flows/<M>/ and tests/subflows/)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for top in (os.path.join("mobile", "flows", module), os.path.join("mobile", "subflows")):
            for d, _, files in os.walk(top):
                for f in files: z.write(os.path.join(d, f), os.path.join("tests", os.path.relpath(os.path.join(d, f), "mobile")))
    return buf.getvalue()


def main():
    a = sys.argv[1:]
    if len(a) not in (4, 5): die(__doc__.splitlines()[4].strip())
    module, app, junit, evdir, tag = a[0], a[1], a[2], a[3], (a[4] if len(a) == 5 else "")
    device, platform = os.environ.get("TH_BS_DEVICE", ""), os.environ.get("PLATFORM", "android")
    if not device or platform not in ("android", "ios"): die("No BrowserStack device: run it through run-mobile.sh --target <name>")
    if not os.path.isfile(app): die(f"The app file is not there: {app} (APP_FILE in .env, or --app <file>)")
    if os.path.splitext(app)[1].lower() not in (".apk", ".aab", ".ipa") or os.path.basename(app).lower().startswith((".env", ".mask", ".private")):
        die(f"Only an app (.apk, .aab or .ipa) is uploaded to BrowserStack, not {os.path.basename(app)}")
    if not os.path.isdir(os.path.join("mobile", "flows", module)): die(f"No flows in mobile/flows/{module}/")
    bs = BS()
    print(f"BrowserStack: uploading the app ({os.path.getsize(app) // 1024} KB) and the flows of {module}", flush=True)
    with open(app, "rb") as f: app_url = bs.upload("/app-automate/maestro/v2/app", os.path.basename(app), f.read())["app_url"]
    suite_url = bs.upload("/app-automate/maestro/v2/test-suite", f"{module}-flows.zip", suite(module))["test_suite_url"]
    env = {k: v for k, v in os.environ.items() if k == "APP_ID" or k.startswith("TEST_") and not re.search(r"TOKEN|SECRET|KEY", k)}  # what the flows read as ${...}: the test account goes to BrowserStack, keys and tokens never
    body = {"app": app_url, "testSuite": suite_url, "devices": [device], "project": "TestHive", "buildTag": module, "customBuildName": f"TestHive {module}",
            "execute": [f"tests/flows/{module}"],  # shortcut: BrowserStack does not document what execute paths are relative to; check on the first real run
            "setEnvVariables": env}
    if tag: body["tags"] = {"includeTags": [tag]}
    build = bs.call("POST", f"/app-automate/maestro/v2/{platform}/build", body)["build_id"]
    print(f"BrowserStack build {build} started on {device}", flush=True)
    end, st = time.time() + 60 * float(os.environ.get("TH_BS_MAX_MINUTES", "60")), {}
    while time.time() < end:
        st = bs.call("GET", f"/app-automate/maestro/v2/builds/{build}")
        if str(st.get("status", "")).lower() in DONE: break
        time.sleep(float(os.environ.get("TH_BS_POLL_SECONDS", "15")))
    else: die(f"BrowserStack build {build} did not finish within TH_BS_MAX_MINUTES: see the App Automate dashboard")
    cases = []; os.makedirs(evdir, exist_ok=True)
    for dev in st.get("devices") or []:
        for s in dev.get("sessions") or []:
            det = bs.call("GET", f"/app-automate/maestro/v2/builds/{build}/sessions/{s['id']}")
            for cl in (det.get("testcases") or {}).get("data") or []:
                for t in cl.get("testcases") or []:
                    name = f"{cl.get('class', '')} {t.get('name', '')}".strip()
                    cases.append((name, str(t.get("status", "")).lower(), float(t.get("duration") or 0), dev.get("device", device)))
                    m = ID.search(name)
                    links = "\n".join(f"{k}: {t[k]}" for k in ("video", "maestro_log", "device_log", "network_log", "screenshots") if t.get(k))
                    fname = f"{len(cases):03d}-{m[0] if m else 'case'}-browserstack.txt"
                    with open(os.path.join(evdir, fname), "w", encoding="utf-8", newline="\n") as f:
                        f.write(f"{name}\nBrowserStack build {build}, session {s['id']}, {dev.get('device', device)}: {t.get('status')}\n{links}\n")
    from xml.sax.saxutils import quoteattr
    bad = {"failed": "failure", "error": "error", "timedout": "failure", "skipped": "skipped", "queued": "skipped", "running": "skipped"}
    xml = [f'<?xml version="1.0" encoding="UTF-8"?>\n<testsuites name="BrowserStack {build}">\n<testsuite name={quoteattr(module + " on " + device)} tests="{len(cases)}">']
    for name, s, dur, dev in cases:
        tag_ = bad.get(s)
        xml.append(f'<testcase name={quoteattr(name)} classname={quoteattr(dev)} time="{dur}">' + (f'<{tag_} message={quoteattr("BrowserStack: " + s)}/>' if tag_ else "") + "</testcase>")
    xml.append("</testsuite>\n</testsuites>\n")
    with open(junit, "w", encoding="utf-8", newline="\n") as f: f.write("\n".join(xml))
    n_bad = sum(1 for c in cases if c[1] in bad)
    print(f"BrowserStack build {build}: {len(cases)} test cases, {n_bad} not passed ({st.get('status')})")
    sys.exit(1 if n_bad or not cases else 0)


if __name__ == "__main__":
    main()
