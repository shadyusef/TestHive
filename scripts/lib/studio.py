"""TestHive Studio lite: a local web page over the project files, for people who do not use a terminal.
Started by scripts/studio.sh. Serves studio/index.html and a small JSON API on 127.0.0.1 only.
Every write goes through the same code as the Excel imports (analysis.apply_answers, design.apply_review) or through
scripts/stage.sh, so the rules are identical. Every API call needs the random token printed at start.
A save is refused (409) when the files changed since the page read them (an agent or Excel wrote in between)."""
import sys, os, re, json, time, hashlib, secrets, subprocess, tempfile, threading, webbrowser
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analysis, design
from analysis import read_csv, refs

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(HERE, "..", "..", "studio", "index.html")
STAGES = ["analysis", "design", "tools", "automation", "execution", "reporting"]
STATE = os.environ.get("TH_STATE", "workflow/state.json")
LOG = os.path.join(os.path.dirname(STATE) or ".", "APPROVALS.md")
RUN = os.environ.get("TH_CMD", "bash scripts/hive.sh")
TOKEN = secrets.token_urlsafe(18)
WRITE = threading.Lock()


def digest(*paths):
    h = hashlib.sha1()
    for p in paths:
        h.update(open(p, "rb").read() if os.path.exists(p) else b"-")
    return h.hexdigest()[:16]


def version(kind): return digest(analysis.GAP_FILE) if kind == "analysis" else digest(design.CASE_FILE, design.ASK_FILE)


def load_state():
    if not os.path.exists(STATE): return {"modules": {}}
    with open(STATE, encoding="utf-8") as f: return json.load(f)


def project_name():
    if os.path.exists("PROJECT_BRIEF.md"):
        m = re.match(r"#\s*Project brief:\s*(.+)", open("PROJECT_BRIEF.md", encoding="utf-8").readline())
        if m and "<" not in m.group(1): return m.group(1).strip()
    return os.path.basename(os.getcwd())


def stage_rows(m):
    out = []
    for st in STAGES:
        e = m["stages"][st]; last = e["history"][-1] if e["history"] else {}
        out.append({"stage": st, "status": e["status"], "by": last.get("by") or "", "at": (last.get("at") or "")[:10]})
    return out


def check(kind, module):
    """The --for-approval check of a stage, as lists (the same rules as the scripts)."""
    try:
        if kind == "analysis":
            err, warn = analysis.problems(module, True)[:2]
        else:
            err, warn = design.problems(module, True)[:2]
    except Exception as e:  # a broken file must not stop the page
        err, warn = [f"could not read the files: {e}"], []
    return {"ok": not err, "errors": err, "warnings": warn}


def next_step(module, m, info):
    """What the human (or an agent) does next, in plain words, with the command to copy."""
    for st in STAGES:
        status = m["stages"][st]["status"]
        if status == "approved": continue
        if status == "awaiting_approval":
            chk = info.get(st, {}).get("check")
            if chk and not chk["ok"]:
                agent = "/th-analyst" if st == "analysis" else "/th-manual"
                return {"text": f"The {st} waits for approval, but {len(chk['errors'])} things must be handled first (see Approvals). In Claude Code:",
                        "command": f"{agent} re-check {module}"}
            return {"text": f"The {st} is ready: check it and approve or reject it in the Approvals tab.", "command": ""}
        if st == "analysis":
            if status == "pending":
                return {"text": f"Put the module's documents in requirements/sources/{module}/ (or have a URL or APK), then in Claude Code ask the analyst:",
                        "command": f"/th-analyst {module}"}
            mine = [g for g in info["analysis"]["gaps"] if g["Status"] == "Answered"]
            open_q = [g for g in info["analysis"]["gaps"] if g["Status"] == "Open"]
            if mine: return {"text": f"You answered {len(mine)} questions. In Claude Code ask the analyst to re-check them:", "command": f"/th-analyst re-check {module}"}
            if open_q: return {"text": f"{len(open_q)} questions are open: answer them in the Analysis tab, then ask the analyst to re-check.", "command": f"/th-analyst re-check {module}"}
            return {"text": "In Claude Code ask the analyst to finish and submit:", "command": f"/th-analyst re-check {module}"}
        if st == "design":
            if status == "pending" or not info["design"]["cases"]:
                return {"text": "In Claude Code ask the manual-tester to design the test cases:", "command": f"/th-manual {module}"}
            todo = [c for c in info["design"]["cases"] if c["Review"] in ("Change", "Remove") or c["Origin"] == "Human" and not c["Type"]]
            asks = [q for q in info["design"]["requests"] if q["Status"] == "Open"]
            if todo or asks:
                return {"text": f"Your review is saved ({len(todo)} cases to handle, {len(asks)} open requests). In Claude Code ask the manual-tester to re-check:",
                        "command": f"/th-manual re-check {module}"}
            return {"text": "Review the cases in the Design tab (Accept, Change or Remove; add cases or requests), then ask the manual-tester to re-check:",
                    "command": f"/th-manual re-check {module}"}
        return {"text": f"Stage '{st}' comes in a later TestHive phase.", "command": ""}
    return {"text": "All stages are approved.", "command": ""}


def module_info(module):
    s = load_state()
    m = s["modules"].get(module)
    if m is None: return None
    reqs = [r for r in read_csv(analysis.REQ_FILE, analysis.REQ_COLS) if r["Module"].upper() == module]
    gaps = [g for g in read_csv(analysis.GAP_FILE, analysis.GAP_COLS) if g["Module"].upper() == module]
    info = {"module": module, "stages": stage_rows(m),
            "analysis": {"version": version("analysis"), "requirements": reqs, "gaps": gaps, "check": check("analysis", module)},
            "design": {"version": version("design"), "cases": [], "requests": [], "coverage": [], "assumptions": [], "baseline": None}}
    b = design.baseline(module)
    if b:
        ver, breqs, bgaps = b
        cases = design.module_rows(read_csv(design.CASE_FILE, design.CASE_COLS), module)
        allg = design.all_gaps(module, bgaps)
        cov = design.coverage(breqs, cases)
        act = [c for c in cases if design.active(c)]
        info["design"].update({
            "baseline": ver, "cases": cases, "requirements": [r for r in breqs if r["Status"] != "Removed"],
            "requests": [q for q in read_csv(design.ASK_FILE, design.ASK_COLS) if q["Module"].upper() == module],
            "coverage": [{"ID": r["ID"], "Priority": r["Priority"], "Type": r["Type"], "Text": r["Text"], "Cases": [c["ID"] for c in cov[r["ID"]]],
                          "Negative": ("yes" if any(design.is_negative(c) for c in cov[r["ID"]]) else "NO") if design.needs_negative(r) else "-",
                          "Boundary": ("yes" if any(c["Technique"] == "Boundary" for c in cov[r["ID"]]) else "NO") if design.needs_boundary(r) else "-"}
                         for r in breqs if r["Status"] != "Removed"],
            "assumptions": [{"ID": g["ID"], "Severity": g["Severity"], "Question": g["Question"],
                             "Cases": [c["ID"] for c in act if g["ID"] in refs(c["Assumption"])]} for g in allg if g["Status"] == "Open"],
            "check": check("design", module)})
    info["approvals"] = approvals(module)
    info["next"] = next_step(module, m, info)
    return info


def approvals(module):
    if not os.path.exists(LOG): return []
    out = []
    for line in open(LOG, encoding="utf-8"):
        p = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(p) == 6 and p[1] == module: out.append(dict(zip(["When", "Module", "Stage", "Decision", "By", "Comment"], p)))
    return out[::-1]


def run_stage(args):
    bash = os.environ.get("TH_BASH") or "bash"
    r = subprocess.run([bash, os.path.join("scripts", "stage.sh")] + args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout + r.stderr).strip()


class Handler(BaseHTTPRequestHandler):
    server_version = "TestHiveStudio"

    def log_message(self, fmt, *a): pass

    def send(self, code, body, ctype="application/json; charset=utf-8", extra=None):
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store"); self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        for k, v in (extra or {}).items(): self.send_header(k, v)
        self.end_headers(); self.wfile.write(data)

    def allowed(self, q):
        host = (self.headers.get("Host") or "").split(":")[0]
        if host not in ("127.0.0.1", "localhost"): return False  # blocks DNS-rebinding pages
        return secrets.compare_digest(self.headers.get("X-TestHive-Token") or q.get("t", [""])[0], TOKEN)

    def do_GET(self):
        u = urlparse(self.path); q = parse_qs(u.query)
        if u.path == "/":
            host = (self.headers.get("Host") or "").split(":")[0]
            if host not in ("127.0.0.1", "localhost"): return self.send(403, {"error": "forbidden"})
            return self.send(200, open(PAGE, "rb").read(), "text/html; charset=utf-8",
                             {"Content-Security-Policy": "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; img-src 'self' data:"})
        if not self.allowed(q): return self.send(403, {"error": "missing or wrong token: open the address printed by studio"})
        if u.path == "/api/overview":
            s = load_state()
            mods = []
            for name, m in s["modules"].items():
                info = module_info(name)
                mods.append({"module": name, "stages": info["stages"], "next": info["next"],
                             "open_gaps": sum(1 for g in info["analysis"]["gaps"] if g["Status"] == "Open"),
                             "cases": sum(1 for c in info["design"]["cases"] if design.active(c))})
            return self.send(200, {"project": project_name(), "modules": mods, "command": RUN})
        if u.path == "/api/module":
            info = module_info((q.get("m", [""])[0]).upper())
            return self.send(200, info) if info else self.send(404, {"error": "unknown module"})
        if u.path == "/api/workbook":
            module, kind = q.get("m", [""])[0].upper(), q.get("kind", [""])[0]
            if kind not in ("analysis", "design") or module not in load_state()["modules"]: return self.send(400, {"error": "bad request"})
            out = os.path.join(tempfile.mkdtemp(), f"{module}-{kind}.xlsx")
            lib = analysis if kind == "analysis" else design
            try: lib.cmd_workbook([module, out])
            except SystemExit: return self.send(400, {"error": f"no {kind} workbook for {module} yet"})
            return self.send(200, open(out, "rb").read(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             {"Content-Disposition": f'attachment; filename="{module}-{kind}.xlsx"'})
        self.send(404, {"error": "not found"})

    def do_POST(self):
        u = urlparse(self.path); q = parse_qs(u.query)
        if not self.allowed(q): return self.send(403, {"error": "missing or wrong token"})
        n = int(self.headers.get("Content-Length") or 0)
        if n > 20_000_000: return self.send(413, {"error": "too large"})
        raw = self.rfile.read(n)
        if u.path == "/api/shutdown":
            self.send(200, {"ok": True}); threading.Thread(target=self.server.shutdown, daemon=True).start(); return
        if u.path == "/api/upload":  # a filled workbook, read with the normal import scripts
            module, kind = q.get("m", [""])[0].upper(), q.get("kind", [""])[0]
            if kind not in ("analysis", "design") or module not in load_state()["modules"]: return self.send(400, {"error": "bad request"})
            with WRITE:
                if q.get("version", [""])[0] != version(kind): return self.send(409, {"error": "the files changed since you opened the page; reload"})
                path = os.path.join(tempfile.mkdtemp(), "upload.xlsx"); open(path, "wb").write(raw)
                lib = os.path.join(HERE, "analysis.py" if kind == "analysis" else "design.py")
                r = subprocess.run([sys.executable, lib, "import", module, path], capture_output=True, text=True, encoding="utf-8", errors="replace")
            return self.send(200 if r.returncode == 0 else 400, {"ok": r.returncode == 0, "message": (r.stdout + r.stderr).strip()})
        if (self.headers.get("Content-Type") or "").split(";")[0] != "application/json": return self.send(415, {"error": "JSON only"})
        try: body = json.loads(raw or b"{}")
        except ValueError: return self.send(400, {"error": "bad JSON"})
        module = str(body.get("module", "")).upper()
        if module not in load_state()["modules"]: return self.send(404, {"error": "unknown module"})
        with WRITE:
            if u.path == "/api/answers":
                if body.get("version") != version("analysis"): return self.send(409, {"error": "the questions changed since you opened the page (an agent or Excel saved them); reload and try again"})
                rows = [("question" if r.get("ID") else "new question", r) for r in body.get("rows", [])]
                changed, added, errors = analysis.apply_answers(module, rows)
                if errors: return self.send(400, {"ok": False, "errors": errors})
                return self.send(200, {"ok": True, "message": f"Saved: {changed} answer(s), {added} new question(s).", "version": version("analysis")})
            if u.path == "/api/review":
                if body.get("version") != version("design"): return self.send(409, {"error": "the cases changed since you opened the page (an agent or Excel saved them); reload and try again"})
                cases = [("case" if r.get("ID") else "new case", r) for r in body.get("cases", [])]
                asks = [(f"request '{str(r.get('Request', ''))[:30]}'", r) for r in body.get("requests", [])]
                decided, edited, new_cases, new_asks, errors = design.apply_review(module, cases, asks, source="Studio")
                if errors: return self.send(400, {"ok": False, "errors": errors})
                return self.send(200, {"ok": True, "version": version("design"), "message":
                                       f"Saved: {decided['Accepted']} accepted, {decided['Change']} to change, {decided['Remove']} to remove, {new_cases} new cases, {new_asks} new requests."})
            if u.path == "/api/stage":
                action, st, by, comment = body.get("action"), body.get("stage"), str(body.get("by", "")).strip(), str(body.get("comment", "")).strip()
                if action not in ("approve", "reject", "reopen") or st not in STAGES: return self.send(400, {"error": "bad request"})
                if not by: return self.send(400, {"error": "your name is needed: decisions are signed"})
                args = [action, module, st, "--by", by] + (["--comment", comment] if comment else [])
                code, out = run_stage(args)
                return self.send(200 if code == 0 else 400, {"ok": code == 0, "message": out})
        self.send(404, {"error": "not found"})


def main():
    a = sys.argv[1:]
    port = int(a[a.index("--port") + 1]) if "--port" in a else 8765
    try: srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    except OSError: srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)  # port in use: take a free one
    url = f"http://127.0.0.1:{srv.server_address[1]}/?t={TOKEN}"
    print(f"STUDIO {url}", flush=True)
    print("TestHive Studio is running on this PC only. Keep this window open; press Ctrl+C to stop.", flush=True)
    if "--no-browser" not in a: webbrowser.open(url)
    try: srv.serve_forever()
    except KeyboardInterrupt: pass
    print("Studio stopped.")


if __name__ == "__main__":
    main()
