"""TestHive Studio lite: a local web page over the project files, for people who do not use a terminal.
Started by scripts/studio.sh. Serves studio/index.html and a small JSON API on 127.0.0.1 only.
Every write goes through the same code as the Excel imports (analysis.apply_answers, design.apply_review) or through
scripts/stage.sh, so the rules are identical. Every API call needs the random token printed at start.
A save is refused (409) when the files changed since the page read them (an agent or Excel wrote in between)."""
import sys, os, re, glob, json, time, hashlib, secrets, subprocess, tempfile, threading, webbrowser
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analysis, design, intake, jobs
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


def review_needs_fix(module):
    """The latest design pre-review is newer than the case sheet: the manual-tester has not handled it yet."""
    files = sorted(glob.glob(os.path.join("reviews", f"DESIGN-{module}-*.md")), key=os.path.getmtime)
    if not files: return None
    return files[-1] if not os.path.exists(design.CASE_FILE) or os.path.getmtime(files[-1]) > os.path.getmtime(design.CASE_FILE) else ""


def step(text, command="", run=""):
    return {"text": text, "command": command, "run": run}


def next_step(module, m, info):
    """What the human does next, in plain words; 'run' names the action behind the Run button, 'command' the same in Claude Code."""
    for st in STAGES:
        status = m["stages"][st]["status"]
        if status == "approved": continue
        if status == "awaiting_approval":
            chk = info.get(st, {}).get("check")
            if chk and not chk["ok"]:
                act = "analyst-recheck" if st == "analysis" else "design-recheck"
                return step(f"The {st} waits for approval, but {len(chk['errors'])} things must be handled first (see Approvals).", ACTIONS[act]["command"].format(m=module), act)
            return step(f"The {st} is ready: check it and approve or reject it in the Approvals tab.")
        if st == "analysis":
            if status == "pending":
                src, mt = info["sources"], info["meta"]
                if not src["files"] and not mt.get("url") and not mt.get("apk"):
                    return step("Add the module's requirement documents in the Sources tab, or give the address (URL) or APK of the built product.")
                if src["files"] and not all(f["read"] for f in src["files"]):
                    return step("Read the documents in the Sources tab (button 'Read the documents'), so the analyst can use them.")
                return step("Everything is ready for the analyst.", f"/th-analyst {module}{explore_note(mt)}", "analyse")
            mine = [g for g in info["analysis"]["gaps"] if g["Status"] == "Answered"]
            open_q = [g for g in info["analysis"]["gaps"] if g["Status"] == "Open"]
            if mine: return step(f"You answered {len(mine)} questions: the analyst re-checks them.", f"/th-analyst re-check {module}", "analyst-recheck")
            if open_q: return step(f"{len(open_q)} questions are open: answer them in the Analysis tab, then run the analyst's re-check.", f"/th-analyst re-check {module}", "analyst-recheck")
            if not info["analysis"]["requirements"]: return step("The analyst has not written the requirements yet.", f"/th-analyst {module}{explore_note(info['meta'])}", "analyse")
            return step("The analyst finishes and submits the analysis.", f"/th-analyst re-check {module}", "analyst-recheck")
        if st == "design":
            cases = info["design"]["cases"]
            if status == "pending" or not cases:
                return step("The manual-tester designs the test cases from the approved requirements.", f"/th-manual {module}", "design")
            if any(c["Status"] == "Needs update" for c in cases if design.active(c)):
                return step("Requirements changed: the manual-tester updates the affected cases.", f"/th-manual update the cases of {module} after the requirement change", "design-impact")
            fix = review_needs_fix(module)
            if fix is None:
                return step("The QA reviewer audits the cases before you review them.", f"/th-review design pre-review of {module}", "prereview")
            if fix:
                return step(f"The manual-tester fixes the reviewer's findings ({os.path.basename(fix)}).", f"/th-manual fix the findings in {fix.replace(os.sep, '/')}", "design-fix")
            todo = [c for c in cases if c["Review"] in ("Change", "Remove") or c["Origin"] == "Human" and not c["Type"]]
            asks = [q for q in info["design"]["requests"] if q["Status"] == "Open"]
            if todo or asks:
                return step(f"Your review is saved ({len(todo)} cases to handle, {len(asks)} open requests): the manual-tester re-checks.", f"/th-manual re-check {module}", "design-recheck")
            return step("Review the cases in the Design tab (Accept, Change or Remove; add cases or requests), then run the manual-tester's re-check.", f"/th-manual re-check {module}", "design-recheck")
        return step(f"Stage '{st}' comes in a later TestHive phase.")
    return step("All stages are approved.")


def explore_note(mt):
    extra = ""
    if mt.get("url"): extra += f" url={mt['url']}" + (", test environment" if mt.get("test_env") else ", not a test environment: do not submit forms")
    if mt.get("apk"): extra += f" apk={mt['apk']}"
    return extra


# What each Run button does: the agent, a task in the words of the demos, how long it usually takes.
ACTIONS = {
    "analyse": {"agent": "business-analyst", "title": "Business analyst: first pass", "minutes": "15-25", "command": "/th-analyst {m}",
                "task": "Module {m} (started from TestHive Studio). Analyse the documents in requirements/sources/{m}/; they are already read into analysis/sources-text/{m}/.{explore} Produce the registers and the workbook as your rules say."},
    "analyst-recheck": {"agent": "business-analyst", "title": "Business analyst: re-check", "minutes": "5-15", "command": "/th-analyst re-check {m}",
                        "task": "Module {m} (started from TestHive Studio). The human answered questions in TestHive Studio: they are in analysis/gaps.csv with Status Answered. If the analysis was reopened, read the last entries of workflow/APPROVALS.md for why and re-read analysis/sources-text/{m}/. Re-check as your rules say, then run the checks, rebuild the workbook, and submit if ready."},
    "design": {"agent": "manual-tester", "title": "Manual tester: design the cases", "minutes": "15-30", "command": "/th-manual {m}",
               "task": "Module {m} (started from TestHive Studio). Design the test cases from the approved analysis baseline as your rules say (platforms in CONTEXT.md). Run the checks and create the workbook. Do not submit."},
    "prereview": {"agent": "qa-reviewer", "model": "sonnet", "title": "QA reviewer: design pre-review", "minutes": "5-10", "command": "/th-review design pre-review of {m}",
                  "task": "Design pre-review of module {m} as your rules say (started from TestHive Studio)."},
    "design-fix": {"agent": "manual-tester", "title": "Manual tester: fix the reviewer's findings", "minutes": "10-25", "command": "/th-manual fix the review findings of {m}",
                   "task": "Module {m} (started from TestHive Studio). The QA reviewer wrote {review}. Fix every Blocker and Major finding and every Minor one that is right, then run the checks and rebuild the workbook. Do not submit."},
    "design-recheck": {"agent": "manual-tester", "title": "Manual tester: re-check your review", "minutes": "5-20", "command": "/th-manual re-check {m}",
                       "task": "Module {m} (started from TestHive Studio). The human reviewed the cases in TestHive Studio (Review column of test-cases/TestCases.csv and test-cases/requests.csv). Handle it as your rules say, then run the checks, rebuild the workbook, and submit if ready."},
    "design-impact": {"agent": "manual-tester", "title": "Manual tester: update cases after a requirement change", "minutes": "5-20", "command": "/th-manual update the cases of {m}",
                      "task": "Module {m} (started from TestHive Studio). Requirements changed: run bash scripts/design-impact.sh {m} --apply, update the cases marked Needs update as your rules say, add cases for new requirements, run the checks, and submit if ready."},
    "explore-web": {"title": "Web exploration", "minutes": "1-5", "command": ""},
}


def start_action(module, action, info):
    """Starts the Run button's job. Returns (job, error)."""
    if action not in ACTIONS: return None, "unknown action"
    a, mt = ACTIONS[action], info["meta"]
    if action == "explore-web":
        if not mt.get("url"): return None, "Give the web address of the built product first (Sources tab)."
        cmd = [intake.bash(), "scripts/explore-web.sh", module, mt["url"]] + (["--submit-valid"] if mt.get("test_env") else [])
        return jobs.start(module, "script", a["title"], cmd, task=" ".join(cmd[1:]))
    review = (sorted(glob.glob(os.path.join("reviews", f"DESIGN-{module}-*.md")), key=os.path.getmtime) or [""])[-1].replace(os.sep, "/")
    if action == "design-fix" and not review: return None, "There is no pre-review to fix yet."
    task = a["task"].format(m=module, review=review, explore=(" Explore the built product too:" + explore_note(mt) + ".") if mt.get("url") or mt.get("apk") else "")
    cmd = jobs.claude_command(a["agent"], task, a.get("model"))
    if not cmd: return None, "Claude Code is not installed here. Run setup --install, then type claude once in a terminal to sign in."
    return jobs.start(module, "agent", a["title"], cmd, task=task, agent=a["agent"])


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
    a_hist = [h for h in m["stages"]["analysis"]["history"] if h["status"] == "approved"]
    info["meta"] = intake.meta(module)
    info["sources"] = intake.sources(module, a_hist[-1]["at"] if a_hist and m["stages"]["analysis"]["status"] == "approved" else "")
    info["readiness"] = readiness(module, m, info)
    info["next"] = next_step(module, m, info)
    if info["next"]["run"]: info["next"].update(title=ACTIONS[info["next"]["run"]]["title"], minutes=ACTIONS[info["next"]["run"]]["minutes"])
    info["jobs"] = jobs.listing(module)[:15]
    job = jobs.running(module)
    info["job"] = dict({k: v for k, v in job.items() if not k.startswith("_")}, lines=jobs.progress(job["id"], 30)) if job else None
    return info


def latest_meta(folder):
    """meta.json of the newest baseline in folder (analysis/baseline/<M> or test-cases/baseline/<M>), or None."""
    vs = sorted(int(d[1:]) for d in os.listdir(folder) if re.fullmatch(r"v\d+", d)) if os.path.isdir(folder) else []
    if not vs: return None
    p = os.path.join(folder, f"v{vs[-1]}", "meta.json")
    if not os.path.exists(p): return {"version": f"v{vs[-1]}"}
    with open(p, encoding="utf-8") as f: return json.load(f)


def readiness(module, m, info):
    """Is the module ready for automation: the three approvals, and what is still assumed."""
    st = {s: m["stages"][s]["status"] for s in STAGES}
    ab, db = latest_meta(os.path.join(analysis.DIR, "baseline", module)), latest_meta(os.path.join(design.TC_DIR, "baseline", module))
    act = [c for c in info["design"]["cases"] if design.active(c)]
    items = [
        {"label": "Requirements approved", "ok": st["analysis"] == "approved",
         "detail": f"baseline {ab['version']}, approved by {ab.get('approved_by', '?')}" if ab and st["analysis"] == "approved" else "analysis " + st["analysis"].replace("_", " ")},
        {"label": "Test cases approved", "ok": st["design"] == "approved",
         "detail": f"design baseline {db['version']}, {db.get('active', len(act))} cases" if db and st["design"] == "approved" else "design " + st["design"].replace("_", " ")},
        {"label": "Tools chosen", "ok": st["tools"] == "approved",
         "detail": "tool advice comes in phase 3" if st["tools"] == "pending" else "tools " + st["tools"].replace("_", " ")}]
    notes = []
    if act:
        notes.append(f"{sum(1 for c in act if 'smoke' in refs(c['Tags']))} smoke cases to automate first")
        nu = sum(1 for c in act if c["Status"] == "Needs update")
        if nu: notes.append(f"{nu} cases need an update after a requirement change")
    if info["design"]["assumptions"]: notes.append(f"{len(info['design']['assumptions'])} open questions the cases still rely on")
    return {"ready": all(i["ok"] for i in items), "items": items, "notes": notes}


def busy(module):
    return f"{jobs.running(module)['title']} is working on {module}: saving is paused until it finishes (or stop it)."


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
                             "cases": sum(1 for c in info["design"]["cases"] if design.active(c)),
                             "job": info["job"]["title"] if info["job"] else ""})
            return self.send(200, {"project": project_name(), "setup": intake.project(), "modules": mods, "command": RUN})
        if u.path == "/api/project":
            return self.send(200, intake.project())
        if u.path == "/api/job":
            jid = q.get("id", [""])[0]
            j = next((x for x in jobs.listing() if x["id"] == jid), None)
            return self.send(200, dict(j, lines=jobs.progress(jid))) if j else self.send(404, {"error": "unknown job"})
        if u.path == "/api/jobs":
            module = q.get("m", [""])[0].upper()
            job = jobs.running(module)
            return self.send(200, {"job": dict({k: v for k, v in job.items() if not k.startswith("_")}, lines=jobs.progress(job["id"], 30)) if job else None,
                                   "last": (jobs.listing(module) or [None])[0]})
        if u.path == "/api/mask-preview":
            module = q.get("m", [""])[0].upper()
            if module not in load_state()["modules"]: return self.send(404, {"error": "unknown module"})
            return self.send(200, intake.mask_preview(module))
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
        limit = intake.MAX_APK if u.path == "/api/source" and q.get("kind", [""])[0] == "apk" else intake.MAX_DOC
        if n > limit:  # read and drop the body first, so the browser receives the message instead of a broken connection
            while n > 0: n -= len(self.rfile.read(min(n, 1 << 20)) or b"x" * n)
            return self.send(413, {"ok": False, "message": f"The file is larger than {limit // 1_000_000} MB."})
        raw = self.rfile.read(n)
        if u.path == "/api/shutdown":
            self.send(200, {"ok": True}); threading.Thread(target=self.server.shutdown, daemon=True).start(); return
        if u.path == "/api/upload":  # a filled workbook, read with the normal import scripts
            module, kind = q.get("m", [""])[0].upper(), q.get("kind", [""])[0]
            if kind not in ("analysis", "design") or module not in load_state()["modules"]: return self.send(400, {"error": "bad request"})
            if jobs.running(module): return self.send(423, {"ok": False, "message": busy(module)})
            with WRITE:
                if q.get("version", [""])[0] != version(kind): return self.send(409, {"error": "the files changed since you opened the page; reload"})
                path = os.path.join(tempfile.mkdtemp(), "upload.xlsx"); open(path, "wb").write(raw)
                lib = os.path.join(HERE, "analysis.py" if kind == "analysis" else "design.py")
                r = subprocess.run([sys.executable, lib, "import", module, path], capture_output=True, text=True, encoding="utf-8", errors="replace")
            return self.send(200 if r.returncode == 0 else 400, {"ok": r.returncode == 0, "message": (r.stdout + r.stderr).strip()})
        if u.path == "/api/source":  # one uploaded document or APK as raw bytes; its name comes in the address
            module = q.get("m", [""])[0].upper()
            if module not in load_state()["modules"]: return self.send(404, {"error": "unknown module"})
            if jobs.running(module): return self.send(423, {"ok": False, "message": busy(module)})
            with WRITE: ok, msg = intake.save_upload(module, q.get("name", [""])[0], raw, q.get("kind", ["source"])[0])
            return self.send(200 if ok else 400, {"ok": ok, "message": msg})
        if (self.headers.get("Content-Type") or "").split(";")[0] != "application/json": return self.send(415, {"error": "JSON only"})
        try: body = json.loads(raw or b"{}")
        except ValueError: return self.send(400, {"error": "bad JSON"})
        if u.path == "/api/project":
            with WRITE: ok, msg = intake.save_project(body)
            return self.send(200 if ok else 400, {"ok": ok, "message": msg})
        if u.path == "/api/module-new":
            code = str(body.get("module", "")).strip().upper()
            if not re.fullmatch(r"[A-Z][A-Z0-9]{1,19}", code):
                return self.send(400, {"ok": False, "message": "Module code: 2 to 20 letters and digits, starting with a letter (for example SIGNUP)."})
            if code in load_state()["modules"]: return self.send(400, {"ok": False, "message": f"{code} already exists."})
            m, err = intake.clean_meta(code, body)
            if err: return self.send(400, {"ok": False, "message": err})
            with WRITE:
                rc, out = run_stage(["init", code])
                if rc: return self.send(400, {"ok": False, "message": out})
                intake.save_meta(code, m); os.makedirs(os.path.join(intake.SOURCES, code), exist_ok=True)
            return self.send(200, {"ok": True, "module": code, "message": f"Module {code} added. Now add its documents, or the URL or APK to explore."})
        module = str(body.get("module", "")).upper()
        if module not in load_state()["modules"]: return self.send(404, {"error": "unknown module"})
        if u.path == "/api/run":
            info = module_info(module)
            job, err = start_action(module, str(body.get("action", "")), info)
            if err: return self.send(400 if "unknown" in err else 409, {"ok": False, "message": err})
            return self.send(200, {"ok": True, "message": f"{job['title']} started.", "job": {k: v for k, v in job.items() if not k.startswith("_")}})
        if u.path == "/api/stop":
            ok = jobs.stop(str(body.get("id", "")))
            return self.send(200 if ok else 400, {"ok": ok, "message": "Stopped. Files the agent already wrote stay as they are." if ok else "That job is not running."})
        if jobs.running(module): return self.send(423, {"ok": False, "message": busy(module)})
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
            if u.path == "/api/module-meta":
                m, err = intake.clean_meta(module, body)
                if err: return self.send(400, {"ok": False, "message": err})
                intake.save_meta(module, m); return self.send(200, {"ok": True, "message": "Saved."})
            if u.path == "/api/ingest":
                code, out = intake.ingest(module, bool(body.get("mask")))
                return self.send(200 if code == 0 else 400, {"ok": code == 0, "message": out})
            if u.path == "/api/mask-lists":
                t, a = intake.save_mask_lists(body.get("terms") or [], body.get("allow") or [])
                return self.send(200, {"ok": True, "message": f"Saved: {t} names to hide, {a} values to leave as they are. Read the documents again to apply."})
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
    for j in [j for j in jobs.JOBS.values() if j["status"] == "running"]:  # no agent keeps writing unseen
        jobs.stop(j["id"], "stopped because Studio was closed")
    print("Studio stopped.")


if __name__ == "__main__":
    main()
