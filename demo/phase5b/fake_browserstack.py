"""A local stand-in for BrowserStack's App Automate Maestro API (demo and CI only; the real service is not called).
Usage: python fake_browserstack.py <user> <key>      prints "FAKEBS http://127.0.0.1:<port>" when ready
Answers the calls scripts/lib/browserstack.py makes: upload app, upload test suite (a zip: its flows become the test cases),
start an Android or iOS build, build status (running once, then done), session details. A flow containing
"demo: fails at BrowserStack" fails. It refuses a wrong login, and a build whose environment carries the access key."""
import sys, io, re, json, base64, zipfile
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

USER, KEY = sys.argv[1], sys.argv[2]
SUITES, BUILDS = {}, {}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def send(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(data)))
        self.end_headers(); self.wfile.write(data)

    def authed(self):
        if self.headers.get("Authorization") == "Basic " + base64.b64encode(f"{USER}:{KEY}".encode()).decode(): return True
        self.send(401, {"message": "Authentication failed"}); return False

    def do_POST(self):
        if not self.authed(): return
        raw = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        p = self.path
        if p == "/app-automate/maestro/v2/app": return self.send(200, {"app_url": "bs://fakeapp", "app_name": "app"})
        if p == "/app-automate/maestro/v2/test-suite":
            z = raw[raw.index(b"\r\n\r\n") + 4: raw.rindex(b"\r\n--")]  # the one file part
            flows = {}
            with zipfile.ZipFile(io.BytesIO(z)) as zf:
                for n in zf.namelist():
                    if re.match(r"tests/flows/[^/]+/[^/]+\.ya?ml$", n): flows[n.rsplit("/", 1)[1]] = "demo: fails at BrowserStack" in zf.read(n).decode("utf-8", "replace")
            SUITES["bs://fakesuite"] = flows
            return self.send(200, {"test_suite_url": "bs://fakesuite"})
        m = re.fullmatch(r"/app-automate/maestro/v2/(android|ios)/build", p)
        if m:
            b = json.loads(raw)
            if KEY in json.dumps(b): return self.send(400, {"message": "the build request carries the access key"})
            if not (b.get("app") and b.get("testSuite") in SUITES and b.get("devices")): return self.send(422, {"message": "app, testSuite and devices are required"})
            BUILDS["fakebuild1"] = {"polls": 0, "device": b["devices"][0], "flows": SUITES[b["testSuite"]]}
            return self.send(200, {"message": "Success", "build_id": "fakebuild1"})
        self.send(404, {"message": "not found"})

    def do_GET(self):
        if not self.authed(): return
        m = re.fullmatch(r"/app-automate/maestro/v2/builds/(\w+)(?:/sessions/(\w+))?", self.path)
        if not m or m[1] not in BUILDS: return self.send(404, {"message": "not found"})
        b = BUILDS[m[1]]
        if m[2]:
            cases = [{"name": f.rsplit(".", 1)[0], "status": "failed" if bad else "passed", "duration": 7, "id": f"t{i}",
                      "video": f"https://app-automate.browserstack.com/fake/video/{i}", "maestro_log": f"https://app-automate.browserstack.com/fake/log/{i}"}
                     for i, (f, bad) in enumerate(sorted(b["flows"].items()), 1)]
            return self.send(200, {"id": m[2], "status": "done", "testcases": {"count": len(cases), "data": [{"class": "flows", "testcases": cases}]}})
        b["polls"] += 1
        done = b["polls"] > 1
        status = ("failed" if any(b["flows"].values()) else "passed") if done else "running"
        self.send(200, {"id": m[1], "status": status, "devices": [{"device": b["device"], "sessions": [{"id": "fakesession1", "status": status}]}]})


srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
print(f"FAKEBS http://127.0.0.1:{srv.server_address[1]}", flush=True)
srv.serve_forever()
