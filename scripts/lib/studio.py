"""TestHive Studio lite: a local web page over the project files, for people who do not use a terminal.
Started by scripts/studio.sh. Serves studio/index.html and a small JSON API on 127.0.0.1 only.
Every write goes through the same code as the Excel imports (analysis.apply_answers, design.apply_review) or through
scripts/lib/stage.py (what scripts/stage.sh runs), so the rules are identical. Every API call needs the random token printed at start.
A save is refused (409) when the files changed since the page read them (an agent or Excel wrote in between)."""
import sys, os, re, glob, json, time, hashlib, secrets, shutil, socket, subprocess, tempfile, threading, webbrowser
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, quote
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analysis, design, intake, jobs, projects, pyrun, tools, automate, execute, targets, report
import modules as archive
from analysis import read_csv, refs

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
PAGE_DIR = pyrun.bundle_dir("studio")  # the page: in the repository, or inside the Studio program
STAGES = ["analysis", "design", "tools", "automation", "execution", "reporting"]
STATE = os.environ.get("TH_STATE", "workflow/state.json")
LOG = os.path.join(os.path.dirname(STATE) or ".", "APPROVALS.md")
RUN = os.environ.get("TH_CMD") or (".\\hive" if os.name == "nt" else "bash scripts/hive.sh")
TOKEN = secrets.token_urlsafe(18)
WRITE = threading.Lock()


def read_bytes(p):
    with open(p, "rb") as f: return f.read()


def digest(*paths):
    h = hashlib.sha1()
    for p in paths:
        h.update(read_bytes(p) if os.path.exists(p) else b"-")
    return h.hexdigest()[:16]


def version(kind):
    return {"analysis": lambda: digest(analysis.GAP_FILE), "design": lambda: digest(design.CASE_FILE, design.ASK_FILE),
            "tools": lambda: digest(tools.CHOICE_FILE, tools.SETTINGS_FILE)}[kind]()


def load_state():
    if not os.path.exists(STATE): return {"modules": {}}
    with open(STATE, encoding="utf-8") as f: return json.load(f)


def project_name():
    if os.path.exists("PROJECT_BRIEF.md"):
        with open("PROJECT_BRIEF.md", encoding="utf-8") as f: m = re.match(r"#\s*Project brief:\s*(.+)", f.readline())
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
        elif kind == "tools":
            err, warn = tools.problems(module, True)
        elif kind == "automation":
            err, warn = automate.problems(module, True)
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
    changed = info["sources"]["changed_after_approval"]
    if changed and m["stages"]["analysis"]["status"] == "approved":
        names = ", ".join(f"{c['name']} ({c['action']})" for c in changed[:4]) + (", …" if len(changed) > 4 else "")
        return step(f"{len(changed)} requirement document(s) changed after the analysis was approved: {names}. Reopen the analysis "
                    "(Sources tab) so the analyst reads them; after the new approval TestHive shows which test cases are affected.")
    for st in STAGES:
        status = m["stages"][st]["status"]
        if status == "approved": continue
        if status == "awaiting_approval":
            chk = info.get(st, {}).get("check")
            if chk and not chk["ok"] and st == "tools":
                return step(f"The tool choice waits for approval, but {len(chk['errors'])} things must be handled first (see Approvals and the Tools tab).")
            if chk and not chk["ok"]:
                act = "analyst-recheck" if st == "analysis" else "design-recheck"
                return step(f"The {st} waits for approval, but {len(chk['errors'])} things must be handled first (see Approvals).", ACTIONS[act]["command"].format(m=module), act)
            return step(f"The {'tool choice' if st == 'tools' else st} is ready: check it and approve or reject it in the Approvals tab.")
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
        if st == "tools":
            n = len(info["tools"]["advice"]["types"]) if info["tools"]["advice"] else 0
            return step(f"Choose the automation tool for each of the {n} test types in the Tools tab: TestHive recommends one; "
                        "saving every choice submits it for approval." if n else "No functional cases are marked for automation: "
                        "submit the tools stage in the Tools tab with nothing to choose, or mark cases for automation (reopen the design).",
                        f"{RUN} tool-advice {module}")
        if st == "automation":
            a = info["automation"]
            if not a: return step("The tools must be approved first.")
            if status == "pending" or any(c["state"] == "missing" for c in a["cases"]):
                return step("Set up the test project: TestHive writes one placeholder test per approved case to automate (free, no AI).",
                            f"{RUN} scaffold {module}", "scaffold")
            ct = a.get("contract")
            if ct and ct["state"] != "current":
                return step("The API spec is new or changed: TestHive rebuilds the contract tests from it (free, no AI).", f"{RUN} contract {module}", "scaffold")
            if ct and not ct["run"]:
                return step(f"Run the {ct['operations']} contract tests: each endpoint must answer as the API spec says (no test data needed).",
                            f"{RUN} run-api {module} --contract", "run-contract")
            for kind in ("web", "api", "mobile"):
                todo = [c for c in a["cases"] if c["kind"] == kind and c["state"] in ("stub", "written-no-check")]
                if todo: return step(f"{len(todo)} {KIND_LABEL[kind]} tests are still placeholders: the engineer writes them, smoke first.",
                                     ACTIONS[f"automate-{kind}"]["command"].format(m=module), f"automate-{kind}")
            for kind in ("web", "api", "mobile"):
                todo = [c for c in a["cases"] if c["kind"] == kind and c["state"] == "written"]
                if todo: return step(f"{len(todo)} {KIND_LABEL[kind]} tests are written but not proven yet: run them 3 times in a row.",
                                     f"{RUN} stable {kind} {module}", f"stable-{kind}")
            if ct and any(not f["bug"] for f in ct["failed"]):
                return step("Some endpoints answer differently from the API spec: report each as a bug and list it in "
                            f"api/collections/{module}.contract-bugs.txt (\"<METHOD> <path> <BUG-ID>\"), or fix the spec, then run the contract tests again.",
                            f"{RUN} run-api {module} --contract", "run-contract")
            return step("Every test is written and stable: submit the automation in the Approvals tab.")
        if st == "execution":
            x = info["execution"]
            if not x or not x.get("cycle"): return step("Start a test cycle in the Execution tab: its name and the environment it runs on.", f"{RUN} cycle start {module} \"<name>\" --env <name> --by <you>")
            cs = x["cases"]
            for kind in ("web", "api", "mobile"):
                if any(c["kind"] == kind and c["result"] == "not-run" for c in cs):
                    return step(f"Run the {KIND_LABEL[kind]} tests of the cycle on {x['cycle']['env'] or 'the default .env'}.", f"{RUN} run-{kind} {module}", f"cycle-{kind}")
            if x.get("contract") is not None and not x["contract"]["run"]: return step("Run the contract tests of the cycle.", f"{RUN} run-api {module} --contract", "cycle-contract")
            for kind in ("web", "api"):
                if any(c["kind"] == kind and c["retest"] for c in cs): return step(f"Retest the {KIND_LABEL[kind]} tests of the fixed bugs.", f"{RUN} retest {kind} {module}", f"retest-{kind}")
            todo = [c for c in cs if c["kind"] == "manual" and (c["result"] == "not-run" or c["retest"])]
            if todo: return step(f"{len(todo)} cases are run by hand: record each result in the Execution tab (Passed, Failed with its bug, or Blocked).")
            if x["check"]["errors"]: return step(f"{len(x['check']['errors'])} things to settle in the Execution tab (failures without a bug, flaky tests): see the list there.")
            return step("Every case has its result: submit the execution in the Approvals tab.")
        if st == "reporting":
            r = info["reporting"]
            if not r or not r["report"] or any("build it again" in e or "no report yet" in e for e in r["check"]["errors"]):
                return step("Build the test report from the approved cycle: one page to share, with TestHive's Go / No-go suggestion (free, no AI).", f"{RUN} report {module}", "report")
            if not r["decision"] or any("decide again" in e for e in r["check"]["errors"]):
                return step(f"TestHive suggests {r['report']['suggestion']}: decide Go or No-go in the Reports tab, with your reason (signed).")
            if r["check"]["errors"]: return step(f"{len(r['check']['errors'])} things to settle in the Reports tab.")
            return step("The report and the decision are ready: submit the reporting in the Approvals tab (the sign-off).")
        return step(f"Stage '{st}' comes in a later TestHive phase.")
    return step("All stages are approved.")


def explore_note(mt):
    extra = ""
    if mt.get("url"): extra += f" url={mt['url']}" + (", test environment" if mt.get("test_env") else ", not a test environment: do not submit forms")
    if mt.get("apk"): extra += f" apk={mt['apk']}"
    return extra


# What each Run button does: the agent, a task in the words of the demos, how long it usually takes.
ACTIONS = {
    "analyse": {"agent": "business-analyst", "title": "Analyse the documents", "minutes": "15-25", "command": "/th-analyst {m}",
                "task": "Module {m} (started from TestHive Studio). Analyse the documents in requirements/sources/{m}/; they are already read into analysis/sources-text/{m}/.{explore} Produce the registers and the workbook as your rules say."},
    "analyst-recheck": {"agent": "business-analyst", "title": "Analyst: check my answers", "minutes": "5-15", "command": "/th-analyst re-check {m}",
                        "task": "Module {m} (started from TestHive Studio). The human answered questions in TestHive Studio: they are in analysis/gaps.csv with Status Answered. If the analysis was reopened, read the last entries of workflow/APPROVALS.md for why and re-read analysis/sources-text/{m}/. Re-check as your rules say, then run the checks, rebuild the workbook, and submit if ready."},
    "design": {"agent": "manual-tester", "title": "Design the test cases", "minutes": "15-30", "command": "/th-manual {m}",
               "task": "Module {m} (started from TestHive Studio). Design the test cases from the approved analysis baseline as your rules say (platforms in CONTEXT.md). Run the checks and create the workbook. Do not submit."},
    "prereview": {"agent": "qa-reviewer", "model": "sonnet", "title": "Review the cases (QA reviewer)", "minutes": "5-10", "command": "/th-review design pre-review of {m}",
                  "task": "Design pre-review of module {m} as your rules say (started from TestHive Studio)."},
    "design-fix": {"agent": "manual-tester", "title": "Fix the reviewer's findings", "minutes": "10-25", "command": "/th-manual fix the review findings of {m}",
                   "task": "Module {m} (started from TestHive Studio). The QA reviewer wrote {review}. Fix every Blocker and Major finding and every Minor one that is right, then run the checks and rebuild the workbook. Do not submit."},
    "design-recheck": {"agent": "manual-tester", "title": "Tester: apply my review", "minutes": "5-20", "command": "/th-manual re-check {m}",
                       "task": "Module {m} (started from TestHive Studio). The human reviewed the cases in TestHive Studio (Review column of test-cases/TestCases.csv and test-cases/requests.csv). Handle it as your rules say, then run the checks, rebuild the workbook, and submit if ready."},
    "design-impact": {"agent": "manual-tester", "title": "Update the cases for the new requirements", "minutes": "5-20", "command": "/th-manual update the cases of {m}",
                      "task": "Module {m} (started from TestHive Studio). Requirements changed: run bash scripts/design-impact.sh {m} --apply, update the cases marked Needs update as your rules say, add cases for new requirements, run the checks, and submit if ready."},
    "explore-web": {"title": "Explore the built product", "minutes": "1-5", "command": ""},
    "explore-android": {"agent": "business-analyst", "title": "Explore the Android app", "minutes": "10-30", "command": "/th-analyst explore the Android app of {m}",
                        "task": "Module {m} (started from TestHive Studio). Explore the Android app only; do not write the registers. Install \"{apk}\" with "
                                "bash scripts/explore-android.sh {m} install \"{apk}\", find its package with bash scripts/explore-android.sh {m} packages, launch it, "
                                "then walk its main screens with snap, tap, type and back as your rules say (snap every new screen with a short name). "
                                "Never type real personal data; use made-up test values. When done, add a short summary of the screens and paths "
                                "at the end of analysis/exploration/{m}/android/exploration.md."},
    "scaffold": {"title": "Set up the test project", "minutes": "1", "command": "", "script": lambda m, o: ["scripts/scaffold.sh", m]},
    "run-tests": {"title": "Run the tests", "minutes": "1-15", "command": "",
                  "script": lambda m, o: run_cmd(o["kind"], m, o)},
    "run-contract": {"title": "Run the contract tests", "minutes": "1", "command": "", "script": lambda m, o: ["scripts/run-api.sh", m, "--contract"]},
    "report": {"title": "Build the test report", "minutes": "1", "command": "", "script": lambda m, o: ["scripts/report.sh", m]},
}
for _k in ("web", "api", "contract", "mobile"):  # the test cycle's runs: on the cycle's environment
    ACTIONS[f"cycle-{_k}"] = {"title": f"Run the {dict(api='API').get(_k, _k)} tests of the cycle",
                              "minutes": "1-15", "command": "", "cycle": True,
                              "script": (lambda k: lambda m, o: run_cmd(k, m, o))(_k)}
for _k in ("web", "api"):
    ACTIONS[f"retest-{_k}"] = {"title": f"Retest the {_k if _k == 'web' else 'API'} failures", "minutes": "1-10", "command": "", "cycle": True,
                               "script": (lambda k: lambda m, o: ["scripts/retest.sh", k, m] + (["--target", o["target"]] if o["target"] else []))(_k)}


def run_cmd(kind, m, o):
    """The run script for a kind of tests with the picked tag, target and (local Android) device."""
    if kind == "contract": return ["scripts/run-api.sh", m, "--contract"]
    return [f"scripts/run-{kind}.sh", m] + (["--tag", o["tag"]] if o["tag"] else []) + (["--target", o["target"]] if o["target"] else []) + ([o["device"]] if o["device"] else [])


def envs():
    """The named environments of this project: the names of its .env.<name> files (their contents are never read here)."""
    return sorted(n[5:] for n in os.listdir(".") if n.startswith(".env.") and execute.ENV.fullmatch(n[5:]) and n[5:] not in ("example",) and os.path.isfile(n))
KIND_LABEL = {"web": "web", "api": "API", "mobile": "mobile"}
ENGINEER = {"web": "web-automation-engineer", "api": "api-backend-test-engineer", "mobile": "mobile-automation-engineer"}
WHERE = {"web": "web/tests/{m}/ (page objects in web/pages/{m}/)", "api": "api/collections/{m}.postman_collection.json", "mobile": "mobile/flows/{m}/"}
for _k in ("web", "api", "mobile"):
    ACTIONS[f"automate-{_k}"] = {"agent": ENGINEER[_k], "title": f"Automate the {KIND_LABEL[_k]} tests", "minutes": "20-90",
        "command": f"/th-{'web' if _k == 'web' else 'api' if _k == 'api' else 'mobile'} automate the {KIND_LABEL[_k]} tests of {{m}}",
        "task": f"Module {{m}} (started from TestHive Studio). Write the automated {KIND_LABEL[_k]} tests: replace every TESTHIVE:STUB placeholder in "
                f"{WHERE[_k]} following your rules and the case steps written in each placeholder, smoke first. Run them with "
                f"bash scripts/run-{_k}.sh {{m}} --tag smoke (then the other tags) and prove them with bash scripts/stable.sh {_k} {{m}}. "
                "A real bug: keep the test, mark it as expected to fail with the bug ID, and report it. Do not submit."}
    ACTIONS[f"stable-{_k}"] = {"title": f"Prove the {KIND_LABEL[_k]} tests (3 runs)", "minutes": "2-30", "command": "",
                               "script": (lambda k: lambda m, o: ["scripts/stable.sh", k, m])(_k)}


def start_action(module, action, info, opts=None):
    """Starts the Run button's job. Returns (job, error). opts: kind and tag for run-tests."""
    if action not in ACTIONS: return None, "unknown action"
    o = {k: str((opts or {}).get(k, "")) for k in ("kind", "tag", "env", "target", "device")}
    if action == "run-tests" and (o["kind"] not in ("web", "api", "contract", "mobile") or o["tag"] not in [""] + design.TAGS): return None, "unknown action"
    if o["tag"] not in [""] + design.TAGS or o["env"] and o["env"] not in envs(): return None, "unknown action"
    kind = o["kind"] if action == "run-tests" else action.split("-", 1)[1] if action.startswith(("cycle-", "retest-")) else ""
    t = targets.load().get(o["target"]) if o["target"] else None
    if o["target"] and (not t or t["kind"] != kind): return None, "unknown action"
    if o["device"] and (kind != "mobile" and action != "explore-android" or (t and t["where"] != "local") or o["device"] not in targets.adb_devices()): return None, "unknown action"
    if t and t["where"] == "browserstack" and not targets.keys_set(o["env"] or ((execute.current(module) or {}).get("env", "") if ACTIONS[action].get("cycle") else "")): return None, "Add BROWSERSTACK_USERNAME and BROWSERSTACK_ACCESS_KEY to .env first (you, in the file; Studio never shows them)."
    if ACTIONS[action].get("cycle"):
        c = execute.current(module)
        if not c: return None, "Start a test cycle first (Execution tab)."
        if load_state()["modules"][module]["stages"]["execution"]["status"] in ("approved", "awaiting_approval"):
            return None, "The cycle is submitted or approved: its results are frozen (reopen or reject it in Approvals to run more)."
        o["env"] = c["env"]
    if agents_missing(): return None, (f"Review mode: {' and '.join(agents_missing())} {'is' if len(agents_missing()) == 1 else 'are'} not on this PC, "
                                       "so agents cannot run here. Someone with Claude Code runs the command shown; everything else works here.")
    a, mt = ACTIONS[action], info["meta"]
    if action == "explore-web":
        if not mt.get("url"): return None, "Give the web address of the built product first (Sources tab)."
        if not web_tools(): return None, WEB_TOOLS_MISSING
        cmd = [intake.bash(), "scripts/explore-web.sh", module, mt["url"]] + (["--submit-valid"] if mt.get("test_env") else [])
        return jobs.start(module, "script", a["title"], cmd, task=" ".join(cmd[1:]))
    if "script" in a:
        if load_state()["modules"][module]["stages"]["tools"]["status"] != "approved": return None, "Approve the tools first."  # the test scripts
        cmd = [intake.bash()] + a["script"](module, o)
        where = (f" on {o['env']}" if o["env"] else "") + (f" ({o['target']}{' ' + o['device'] if o['device'] else ''})" if o["target"] or o["device"] else "")
        return jobs.start(module, "script", a["title"] + (f" ({o['kind']}{', ' + o['tag'] if o['tag'] else ''})" if action == "run-tests" else "") + where,
                          cmd, task=(f"TEST_ENV={o['env']} " if o["env"] else "") + " ".join(cmd[1:]), env={"TEST_ENV": o["env"]} if o["env"] else None)
    if action == "explore-android":  # the analyst drives the phone through explore-android.sh; the device is picked (or the only one)
        if not mt.get("apk"): return None, "Upload the module's APK first (Sources, Android app)."
        devs = targets.adb_devices()
        dev = o["device"] or (devs[0] if len(devs) == 1 else "")
        if not dev: return None, "No Android device found (adb): connect a phone with USB debugging or start an emulator." if not devs else "Pick the device to explore on."
        task = a["task"].format(m=module, apk=mt["apk"])
        cmd = jobs.claude_command(a["agent"], task, a.get("model"))
        if not cmd: return None, "Claude Code is not installed here. Run setup --install, then type claude once in a terminal to sign in."
        return jobs.start(module, "agent", f"{a['title']} ({dev})", cmd, task=task, agent=a["agent"], env={"ANDROID_DEVICE_ID": dev})
    review = (sorted(glob.glob(os.path.join("reviews", f"DESIGN-{module}-*.md")), key=os.path.getmtime) or [""])[-1].replace(os.sep, "/")
    if action == "design-fix" and not review: return None, "There is no pre-review to fix yet."
    task = a["task"].format(m=module, review=review, explore=(" Explore the built product too:" + explore_note(mt) + ".") if mt.get("url") or mt.get("apk") else "")
    if action == "analyse" and not info["sources"]["files"]:  # only a URL or APK: the requirements come from the built product
        task = (f"Module {module} (started from TestHive Studio). There are no requirement documents: explore the built product:{explore_note(mt)}. "
                "Draft the requirements as observed behaviour and the questions, and produce the registers and the workbook as your rules say.")
    cmd = jobs.claude_command(a["agent"], task, a.get("model"))
    if not cmd: return None, "Claude Code is not installed here. Run setup --install, then type claude once in a terminal to sign in."
    return jobs.start(module, "agent", a["title"], cmd, task=task, agent=a["agent"])


WEB_TOOLS_MISSING = ("Explore needs the web tools on this PC. Someone at a terminal runs, once: "
                     f"{RUN} setup --install --web (see docs/TEAM-GUIDE.md).")


def web_tools(): return os.path.isdir(os.path.join("web", "node_modules", "@playwright", "test"))


def exploration(module):
    """The last web exploration of the module: when, how many pages opened, the address; or None."""
    p = os.path.join(analysis.DIR, "exploration", module, "web", "exploration.json")
    if not os.path.exists(p): return None
    try:
        with open(p, encoding="utf-8") as f: pages = json.load(f)
    except ValueError: return None
    return {"at": time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(p))), "pages": sum(1 for x in pages if not x.get("error")),
            "failed": sum(1 for x in pages if x.get("error")), "url": (pages[0].get("url") if pages else "")}


SHOT = re.compile(r"\d{2}-[A-Za-z0-9_-]{1,80}\.png")


def android_exploration(module):
    """The screens the Android exploration recorded: [names], and when; or None."""
    d = os.path.join(analysis.DIR, "exploration", module, "android")
    shots = sorted(f for f in os.listdir(d) if SHOT.fullmatch(f)) if os.path.isdir(d) else []
    if not shots: return None
    return {"screens": shots, "at": time.strftime("%Y-%m-%d %H:%M", time.localtime(max(os.path.getmtime(os.path.join(d, f)) for f in shots)))}


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
    adv = tools.advice(module)
    info["tools"] = {"version": version("tools"), "advice": adv, "choices": tools.choices(module), "criteria": tools.CRITERIA, "langs": tools.LANGS,
                     "settings": tools.settings(), "check": check("tools", module) if adv else None}
    au = automate.status(module)
    if au:
        err, warn = automate.problems(module, True, au)
        info["automation"] = dict(au, runs=last_runs(module), check={"ok": not err, "errors": err, "warnings": warn})
    else: info["automation"] = None
    ex = execute.status(module) if m["stages"]["automation"]["status"] == "approved" or execute.current(module) else None
    if ex:
        err, warn = execute.problems(module, True, ex)
        info["execution"] = dict(ex, check={"ok": not err, "errors": err, "warnings": warn}, envs=envs())
    else: info["execution"] = {"cycle": None, "envs": envs()} if m["stages"]["automation"]["status"] == "approved" else None
    if info["automation"]: info["automation"]["envs"] = envs()
    info["bugs"] = {"rows": report.bugs(module), "problems": report.bug_problems(module), "severity": report.SEVERITY, "status": report.STATUS}
    if m["stages"]["execution"]["status"] == "approved":
        err, warn = report.problems(module, True)
        info["reporting"] = {"report": report.report_meta(report.report_path(module), module), "decision": report.read_json(os.path.join(report.DIR, module, "decision.json")),
                             "check": {"ok": not err, "errors": err, "warnings": warn}}
    else: info["reporting"] = None
    info["approvals"] = approvals(module)
    a_hist = [h for h in m["stages"]["analysis"]["history"] if h["status"] == "approved"]
    info["meta"] = intake.meta(module)
    info["sources"] = intake.sources(module, a_hist[-1]["at"] if a_hist and m["stages"]["analysis"]["status"] == "approved" else "")
    info["readiness"] = readiness(module, m, info)
    info["next"] = next_step(module, m, info)
    if info["next"]["run"]: info["next"].update(title=ACTIONS[info["next"]["run"]]["title"], minutes=ACTIONS[info["next"]["run"]]["minutes"])
    if info["next"]["run"] == "analyse" and not info["sources"]["files"]: info["next"]["title"] = "Analyse the built product"
    info["exploration"], info["web_tools"], info["project_url"] = exploration(module), web_tools(), intake.project()["base_url"]
    info["android_exploration"] = android_exploration(module)
    info["test_login"] = intake.test_login_set()
    info["targets"], info["browserstack_keys"] = targets.load(), targets.keys_set()
    info["jobs"], info["agents"], info["agents_missing"] = jobs.listing(module)[:15], agents_mode(), agents_missing()
    job = jobs.running(module)
    info["job"] = job_view(job)
    return info


RUN_ID, last_runs = automate.RUN_ID, automate.last_runs


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
         "detail": "; ".join(f"{c['Test Type']}: {c['Chosen']}" for c in info["tools"]["choices"]) or "nothing to automate"
                   if st["tools"] == "approved" else "tools " + st["tools"].replace("_", " ")}]
    notes = []
    if act:
        notes.append(f"{sum(1 for c in act if 'smoke' in refs(c['Tags']))} smoke cases to automate first")
        nu = sum(1 for c in act if c["Status"] == "Needs update")
        if nu: notes.append(f"{nu} cases need an update after a requirement change")
    if info["design"]["assumptions"]: notes.append(f"{len(info['design']['assumptions'])} open questions the cases still rely on")
    changed = info["sources"]["changed_after_approval"] if st["analysis"] == "approved" else []
    if changed: notes.insert(0, f"{len(changed)} requirement document(s) changed after the analysis was approved: reopen the analysis first")
    return {"ready": all(i["ok"] for i in items) and not changed, "items": items, "notes": notes}


def agents_missing():
    """What this PC lacks to run the agents from Studio: Claude Code, and the bash their scripts run in (Git Bash on Windows)."""
    if os.environ.get("TH_CLAUDE_FAKE"): return []
    b = intake.bash()
    return [name for name, ok in (("Claude Code", shutil.which("claude")), ("Git Bash", os.path.isfile(b) or shutil.which(b))) if not ok]


def agents_mode():
    """'recorded' when the Run buttons replay recorded runs (demos, CI); 'live' when they start Claude Code for real;
    'review' when this PC cannot run agents: everything else works (documents, answers, reviews, approvals, Excel)."""
    return "recorded" if os.environ.get("TH_CLAUDE_FAKE") else "review" if agents_missing() else "live"


def busy(module):
    return f"{jobs.running(module)['title']} is working on {module}: saving is paused until it finishes (or stop it)."


def approvals(module):
    if not os.path.exists(LOG): return []
    out = []
    with open(LOG, encoding="utf-8") as f:
        for line in f:
            p = [x.strip() for x in line.strip().strip("|").split("|")]
            if len(p) == 6 and p[1] == module: out.append(dict(zip(["When", "Module", "Stage", "Decision", "By", "Comment"], p)))
    return out[::-1]


def run_stage(args):
    return intake.run_py("stage.py", args)  # the same rules as scripts/stage.sh, with no bash needed


# ---------- API ----------
# Each route is a function f(h, q, body, module) registered with @api. The dispatcher (Handler.handle_api) checks the token,
# reads the body, refuses an unknown module and, for writes, holds the write lock and refuses while an agent works on the module.
ROUTES = {}
# The page: index.html, its styles, scripts (studio/js/) and fonts (studio/fonts/). Only these names and types are served.
PAGE_TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8", ".woff2": "font/woff2"}
PAGE_FILE = re.compile(r"/(?:(?:js|fonts)/)?[a-z0-9][a-z0-9-]*\.(?:js|css|woff2)")
CSP = ("default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; img-src 'self' data:; font-src 'self'; "
       "frame-ancestors 'none'; base-uri 'none'; form-action 'self'")


def page_file(path):
    """The file of the page for a URL path, or None. The path already matched PAGE_FILE; it must still resolve inside studio/."""
    root = os.path.realpath(PAGE_DIR)
    p = os.path.realpath(os.path.join(root, "index.html" if path == "/" else path.lstrip("/")))
    return p if p.startswith(root + os.sep) and os.path.isfile(p) else None


def api(method, path, module=None, lock=False, busy_check=False, raw=False):
    """module: 'query' (?m=) or 'body' ("module") holds the module code, which must exist. lock: hold the write lock.
    busy_check: refuse (423) while an agent works on the module. raw: the POST body is passed as bytes, not JSON."""
    def reg(fn):
        ROUTES[(method, path)] = (fn, {"module": module, "lock": lock or busy_check, "busy": busy_check, "raw": raw})
        return fn
    return reg


def arg(q, name): return q.get(name, [""])[0]


# ---------- which project: one Studio program serves any project folder ----------
PROJECT = {"path": None}  # set at start (projects.choose) or by /api/open-project; Studio works in that folder
NO_PROJECT_OK = {"/api/projects", "/api/open-project", "/api/shutdown"}


def open_project(path):
    os.chdir(path); PROJECT["path"] = os.path.realpath(path); projects.remember(path)
    jobs.JOBS.clear()  # the runs of the project left behind (none is running: switching waits for them)


@api("GET", "/api/projects")
def get_projects(h, q, body, module):
    return h.send(200, {"current": PROJECT["path"], "recent": projects.recent()})


@api("POST", "/api/open-project", lock=True)
def post_open_project(h, q, body, module):
    p = os.path.expanduser(str(body.get("path", "")).strip().strip('"'))
    if p.startswith(("\\\\", "//")):  # a network share: Windows would send your sign-in to that server just to look
        return h.send(400, {"ok": False, "message": "Open a project folder on this PC (copy it here with git), not on a network share."})
    if not projects.is_project(p):
        return h.send(400, {"ok": False, "message": "That folder is not a TestHive project: it needs the scripts and templates folders of TestHive "
                                                     "(clone your team's project repository, then open its folder)."})
    if any(j["status"] == "running" for j in jobs.JOBS.values()):
        return h.send(409, {"ok": False, "message": "An agent is working: wait until it finishes (or stop it) before opening another project."})
    if os.path.realpath(p) not in projects.recent() and body.get("confirm") is not True:  # never opened here before
        return h.send(409, {"ok": False, "confirm": True, "message": f"Open {os.path.realpath(p)} for the first time? Its scripts and agents "
                            "run on this PC when you press Run: open only a copy of your team's own project repository."})
    open_project(p)
    return h.send(200, {"ok": True, "message": f"Opened {os.path.basename(PROJECT['path'])}.", "current": PROJECT["path"]})


@api("GET", "/api/overview")
def get_overview(h, q, body, module):
    mods = []
    for name in load_state()["modules"]:
        info = module_info(name)
        mods.append({"module": name, "title": info["meta"].get("title", ""), "stages": info["stages"], "next": info["next"],
                     "open_gaps": sum(1 for g in info["analysis"]["gaps"] if g["Status"] == "Open"),
                     "cases": sum(1 for c in info["design"]["cases"] if design.active(c)),
                     "job": info["job"]["title"] if info["job"] else ""})
    return h.send(200, {"project": project_name(), "setup": intake.project(), "modules": mods, "command": RUN, "agents": agents_mode(), "agents_missing": agents_missing()})


@api("GET", "/api/project")
def get_project(h, q, body, module): return h.send(200, intake.project())


@api("GET", "/api/job")
def get_job(h, q, body, module):
    j = next((x for x in jobs.listing() if x["id"] == arg(q, "id")), None)
    return h.send(200, dict(j, lines=jobs.progress(j["id"]))) if j else h.send(404, {"error": "unknown job"})


def job_view(job):
    """A running job for the page: its fields, the last progress lines, and the questions its agent waits on."""
    if not job: return None
    return dict({k: v for k, v in job.items() if not k.startswith("_")}, lines=jobs.progress(job["id"], 30),
                asks=[{"id": a["id"], "tool": a["tool"], "input": json.dumps(a.get("input"), ensure_ascii=False, indent=1)[:4000], "asked_at": a.get("asked_at", "")}
                      for a in jobs.asks(job)] if job.get("kind") == "agent" else [])


@api("GET", "/api/jobs", module="query")
def get_jobs(h, q, body, module):
    return h.send(200, {"job": job_view(jobs.running(module)), "last": (jobs.listing(module) or [None])[0]})


@api("POST", "/api/ask", module="body")
def post_ask(h, q, body, module):
    """A person answers a question the module's running agent waits on (Allow once / Deny), signed."""
    job, by, note = jobs.running(module), str(body.get("by", "")).strip(), str(body.get("note", "")).strip()[:300]
    if not job or job.get("kind") != "agent": return h.send(409, {"ok": False, "message": "No agent is working on this module now."})
    if not by or re.search(r"[\r\n|]", by + note): return h.send(400, {"ok": False, "message": "your name is needed (no line breaks or |): answers are signed"})
    err = jobs.answer(job, str(body.get("id", "")), str(body.get("decision", "")), by, note)
    if err: return h.send(400 if err == "bad request" else 409, {"ok": False, "message": err})
    return h.send(200, {"ok": True, "message": "Allowed once: the agent goes on." if body.get("decision") == "allow" else "Denied: the agent is told no."})


@api("GET", "/api/mask-preview", module="query")
def get_mask_preview(h, q, body, module): return h.send(200, intake.mask_preview(module))


@api("GET", "/api/module", module="query")
def get_module(h, q, body, module): return h.send(200, module_info(module))


@api("GET", "/api/workbook", module="query")
def get_workbook(h, q, body, module):
    kind = arg(q, "kind")
    if kind not in ("analysis", "design"): return h.send(400, {"error": "bad request"})
    lib = analysis if kind == "analysis" else design
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, f"{module}-{kind}.xlsx")
        try: lib.cmd_workbook([module, out])
        except SystemExit: return h.send(400, {"error": f"no {kind} workbook for {module} yet"})
        data = read_bytes(out)
    return h.send(200, data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                  {"Content-Disposition": f'attachment; filename="{module}-{kind}.xlsx"'})


@api("POST", "/api/shutdown", raw=True)
def post_shutdown(h, q, body, module):
    h.send(200, {"ok": True}); threading.Thread(target=h.server.shutdown, daemon=True).start()


@api("POST", "/api/upload", module="query", busy_check=True, raw=True)
def post_upload(h, q, body, module):  # a filled workbook, read with the normal import scripts
    kind = arg(q, "kind")
    if kind not in ("analysis", "design"): return h.send(400, {"error": "bad request"})
    if arg(q, "version") != version(kind): return h.send(409, {"error": "the files changed since you opened the page; reload"})
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "upload.xlsx"); open(path, "wb").write(body)
        r = subprocess.run(pyrun.lib_cmd("analysis.py" if kind == "analysis" else "design.py", "import", module, path), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return h.send(200 if r.returncode == 0 else 400, {"ok": r.returncode == 0, "message": (r.stdout + r.stderr).strip()})


@api("POST", "/api/source", module="query", busy_check=True, raw=True)
def post_source(h, q, body, module):  # one uploaded document or APK as raw bytes; its name comes in the address
    ok, msg = intake.save_upload(module, arg(q, "name"), body, arg(q, "kind") or "source", signer({"by": arg(q, "by")})[0] or "")
    return h.send(200 if ok else 400, {"ok": ok, "message": msg})


VIEW = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif",
        ".bmp": "image/bmp", ".webp": "image/webp", **{e: "text/plain; charset=utf-8" for e in (".txt", ".md", ".csv", ".json", ".yaml", ".yml")}}


@api("GET", "/api/source-file", module="query")
def get_source_file(h, q, body, module):  # the original document (or an earlier version) to open in the browser
    p = intake.old_file(module, arg(q, "version"), arg(q, "name")) if arg(q, "version") else intake.source_file(module, arg(q, "name"))
    if not p: return h.send(404, {"error": "unknown document"})
    ctype = VIEW.get(os.path.splitext(p)[1].lower())
    extra = {"Content-Disposition": f"{'inline' if ctype else 'attachment'}; filename*=UTF-8''{quote(os.path.basename(p))}"}
    if ctype != "application/pdf": extra["Content-Security-Policy"] = "sandbox"  # nothing in a document runs (the PDF viewer needs scripts)
    return h.send(200, read_bytes(p), ctype or "application/octet-stream", extra)


EVIDENCE = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webm": "video/webm", ".mp4": "video/mp4", ".txt": "text/plain; charset=utf-8",
            ".log": "text/plain; charset=utf-8", ".json": "text/plain; charset=utf-8", ".zip": "application/zip"}


@api("GET", "/api/run-file", module="query")
def get_run_file(h, q, body, module):  # a screenshot, video, log or trace kept with a stored run of this module
    base = os.path.realpath(os.environ.get("TH_RUNS", "runs"))
    run, name = arg(q, "run"), arg(q, "name")
    if not RUN_ID.fullmatch(run) or not name.startswith("evidence/"): return h.send(404, {"error": "not found"})
    d = os.path.join(base, run)
    p = os.path.realpath(os.path.join(d, name))
    if not p.startswith(os.path.join(os.path.realpath(d), "evidence") + os.sep) or not os.path.isfile(p): return h.send(404, {"error": "not found"})
    try:
        with open(os.path.join(d, "meta.json"), encoding="utf-8") as f:
            if json.load(f).get("module") != module: return h.send(404, {"error": "not found"})
    except (OSError, ValueError): return h.send(404, {"error": "not found"})
    ctype = EVIDENCE.get(os.path.splitext(p)[1].lower())
    extra = {"Content-Security-Policy": "sandbox", "Content-Disposition": f"{'inline' if ctype and ctype != 'application/zip' else 'attachment'}; filename*=UTF-8''{quote(os.path.basename(p))}"}
    return h.send(200, read_bytes(p), ctype or "application/octet-stream", extra)


@api("GET", "/api/source-text", module="query")
def get_source_text(h, q, body, module): return h.send(200, intake.source_text(module, arg(q, "name")))


@api("GET", "/api/devices")
def get_devices(h, q, body, module):
    """The Android devices adb sees now (asked when the Run picker needs them: adb can take a moment)."""
    return h.send(200, {"devices": targets.adb_devices()})


@api("GET", "/api/exploration-shot", module="query")
def get_exploration_shot(h, q, body, module):
    """One screen the Android exploration recorded (a PNG of that folder only)."""
    name, d = arg(q, "name"), os.path.realpath(os.path.join(analysis.DIR, "exploration", module, "android"))
    p = os.path.realpath(os.path.join(d, name))
    if not SHOT.fullmatch(name) or not p.startswith(d + os.sep) or not os.path.isfile(p): return h.send(404, {"error": "not found"})
    return h.send(200, read_bytes(p), "image/png", {"Content-Security-Policy": "sandbox"})


@api("GET", "/api/exploration", module="query")
def get_exploration(h, q, body, module):  # the explorer's report, as text (screenshots stay in the folder; Android's are shown in Sources)
    p = os.path.join(analysis.DIR, "exploration", module, "android" if arg(q, "kind") == "android" else "web", "exploration.md")
    if not os.path.exists(p): return h.send(404, {"error": "not explored yet"})
    with open(p, encoding="utf-8", errors="replace") as f: return h.send(200, {"text": f.read(), "folder": os.path.dirname(p).replace(os.sep, "/")})


@api("GET", "/api/source-versions", module="query")
def get_source_versions(h, q, body, module):
    return h.send(200, {"versions": intake.versions(module), "history": intake.history(module)[::-1][:100]})


def signer(body):
    """The name that signs a change, or an error."""
    by = " ".join(str(body.get("by", "")).split())
    if not by: return None, "Your name is needed: changes are signed."
    if "|" in by or len(by) > 60: return None, "Name: one line, without |, up to 60 characters."
    return by, None


@api("POST", "/api/source-remove", module="body", busy_check=True)
def post_source_remove(h, q, body, module):
    by, err = signer(body)
    ok, msg = (False, err) if err else intake.remove_source(module, body.get("name", ""), by)
    return h.send(200 if ok else 400, {"ok": ok, "message": msg})


@api("POST", "/api/source-restore", module="body", busy_check=True)
def post_source_restore(h, q, body, module):
    by, err = signer(body)
    ok, msg = (False, err) if err else intake.restore_source(module, str(body.get("version", "")), body.get("name", ""), by)
    return h.send(200 if ok else 400, {"ok": ok, "message": msg})


@api("GET", "/api/archive")
def get_archive(h, q, body, module): return h.send(200, {"archived": archive.listing()})


@api("POST", "/api/module-archive", module="body", busy_check=True)
def post_module_archive(h, q, body, module):
    by, err = signer(body)
    why = " ".join(str(body.get("comment", "")).split())
    if not err and str(body.get("confirm", "")).strip().upper() != module: err = f"Type {module} to confirm."
    if not err and (not why or "|" in why): err = "Say why (one line, without |)."
    if err: return h.send(400, {"ok": False, "message": err})
    code, out = run_stage(["archive", module, "--by", by, "--comment", why])
    return h.send(200 if code == 0 else 400, {"ok": code == 0, "message": out})


@api("POST", "/api/module-restore", lock=True)
def post_module_restore(h, q, body, module):
    by, err = signer(body)
    name = str(body.get("archive", ""))
    if not err and not archive.NAME.fullmatch(name): err = "Unknown archive."
    if err: return h.send(400, {"ok": False, "message": err})
    code, out = run_stage(["restore", name, "--by", by])
    return h.send(200 if code == 0 else 400, {"ok": code == 0, "message": out})


@api("POST", "/api/project", lock=True)
def post_project(h, q, body, module):
    ok, msg = intake.save_project(body)
    return h.send(200 if ok else 400, {"ok": ok, "message": msg})


@api("POST", "/api/module-new", lock=True)
def post_module_new(h, q, body, module):
    code = str(body.get("module", "")).strip().upper()
    if not re.fullmatch(r"[A-Z][A-Z0-9]{1,19}", code):
        return h.send(400, {"ok": False, "message": "Module code: 2 to 20 letters and digits, starting with a letter."})
    if code in load_state()["modules"]: return h.send(400, {"ok": False, "message": f"{code} already exists."})
    m, err = intake.clean_meta(code, body)
    if err: return h.send(400, {"ok": False, "message": err})
    rc, out = run_stage(["init", code])
    if rc: return h.send(400, {"ok": False, "message": out})
    intake.save_meta(code, m); os.makedirs(os.path.join(intake.SOURCES, code), exist_ok=True)
    return h.send(200, {"ok": True, "module": code, "message": f"Module {code} added. Now add its documents, or the URL or APK to explore."})


@api("POST", "/api/run", module="body", lock=True)
def post_run(h, q, body, module):  # under the lock: no save can slip in between the checks and the start
    job, err = start_action(module, str(body.get("action", "")), module_info(module), body.get("options") if isinstance(body.get("options"), dict) else None)
    if err: return h.send(400 if "unknown" in err else 409, {"ok": False, "message": err})
    return h.send(200, {"ok": True, "message": f"{job['title']} started.", "job": {k: v for k, v in job.items() if not k.startswith("_")}})


@api("POST", "/api/stop", module="body")
def post_stop(h, q, body, module):
    j = jobs.JOBS.get(str(body.get("id", "")))
    if j and j["status"] == "running" and not j.get("_proc"):
        return h.send(409, {"ok": False, "message": "Another Studio window started this job: stop it there (or wait for it to finish)."})
    ok = jobs.stop(str(body.get("id", "")))
    return h.send(200 if ok else 400, {"ok": ok, "message": "Stopped. Files the agent already wrote stay as they are." if ok else "That job is not running."})


@api("POST", "/api/answers", module="body", busy_check=True)
def post_answers(h, q, body, module):
    if body.get("version") != version("analysis"): return h.send(409, {"error": "the questions changed since you opened the page (an agent or Excel saved them); reload and try again"})
    rows = [("question" if r.get("ID") else "new question", r) for r in body.get("rows", [])]
    changed, added, errors = analysis.apply_answers(module, rows)
    if errors: return h.send(400, {"ok": False, "errors": errors})
    return h.send(200, {"ok": True, "message": f"Saved: {changed} answer(s), {added} new question(s).", "version": version("analysis")})


@api("POST", "/api/review", module="body", busy_check=True)
def post_review(h, q, body, module):
    if body.get("version") != version("design"): return h.send(409, {"error": "the cases changed since you opened the page (an agent or Excel saved them); reload and try again"})
    cases = [("case" if r.get("ID") else "new case", r) for r in body.get("cases", [])]
    asks = [(f"request '{str(r.get('Request', ''))[:30]}'", r) for r in body.get("requests", [])]
    decided, edited, new_cases, new_asks, errors = design.apply_review(module, cases, asks, source="Studio")
    if errors: return h.send(400, {"ok": False, "errors": errors})
    return h.send(200, {"ok": True, "version": version("design"), "message":
                        f"Saved: {decided['Accepted']} accepted, {decided['Change']} to change, {decided['Remove']} to remove, {new_cases} new cases, {new_asks} new requests."})


@api("POST", "/api/tools", module="body", busy_check=True)
def post_tools(h, q, body, module):
    """Saves the tool choices (and the project's weights and skills); when every test type has a valid choice, submits the stage."""
    if body.get("version") != version("tools"): return h.send(409, {"error": "the tool choices changed since you opened the page; reload and try again"})
    st = load_state()["modules"][module]["stages"]
    if st["design"]["status"] != "approved": return h.send(409, {"ok": False, "message": "Approve the test cases (design) first."})
    if st["tools"]["status"] == "approved": return h.send(409, {"ok": False, "message": "The tool choice is approved: reopen the tools stage (Approvals) to change it."})
    cfg, picks = body.get("settings"), body.get("picks") or []
    if not isinstance(picks, list) or cfg is not None and not (isinstance(cfg, dict) and isinstance(cfg.get("weights", {}), dict) and isinstance(cfg.get("skills", []), list)):
        return h.send(400, {"ok": False, "errors": ["bad request"]})
    old = read_bytes(tools.SETTINGS_FILE) if os.path.exists(tools.SETTINGS_FILE) else None
    if cfg is not None:
        err = tools.save_settings(cfg.get("weights", {}), [str(x) for x in cfg.get("skills", [])])
        if err: return h.send(400, {"ok": False, "errors": err})
    err = tools.choose(module, [(str(p.get("type", "")), str(p.get("tool", "")), str(p.get("reason", ""))) for p in picks if isinstance(p, dict)], str(body.get("by", "")))
    if err:  # nothing saved: the weights and skills go back too, so the page's version stays right
        if old is None: os.path.exists(tools.SETTINGS_FILE) and os.remove(tools.SETTINGS_FILE)
        else:
            with open(tools.SETTINGS_FILE, "wb") as f: f.write(old)
        return h.send(400, {"ok": False, "errors": err})
    if st["tools"]["status"] == "pending":
        code, out = run_stage(["start", module, "tools"])
        if code: return h.send(200, {"ok": True, "version": version("tools"), "message": "Saved, but the tools stage did not start: " + out})
    chk = check("tools", module)
    if chk["ok"] and load_state()["modules"][module]["stages"]["tools"]["status"] == "in_progress":
        code, out = run_stage(["submit", module, "tools"])
        if code == 0: return h.send(200, {"ok": True, "version": version("tools"), "message": "Saved and submitted: approve the tool choice in the Approvals tab."})
    left = "" if chk["ok"] else f" Still to do: {len(chk['errors'])} (see the Tools tab)."
    return h.send(200, {"ok": True, "version": version("tools"), "message": "Saved." + left})


@api("POST", "/api/module-meta", module="body", busy_check=True)
def post_module_meta(h, q, body, module):
    m, err = intake.clean_meta(module, body)
    if err: return h.send(400, {"ok": False, "message": err})
    intake.save_meta(module, m); return h.send(200, {"ok": True, "message": "Saved."})


@api("POST", "/api/ingest", module="body", busy_check=True)
def post_ingest(h, q, body, module):
    code, out = intake.ingest(module, bool(body.get("mask")))
    return h.send(200 if code == 0 else 400, {"ok": code == 0, "message": out})


@api("POST", "/api/mask-lists", module="body", busy_check=True)
def post_mask_lists(h, q, body, module):
    t, a = intake.save_mask_lists(body.get("terms") or [], body.get("allow") or [])
    return h.send(200, {"ok": True, "message": f"Saved: {t} names to hide, {a} values to leave as they are. Read the documents again to apply."})


@api("POST", "/api/execution", module="body", busy_check=True)
def post_execution(h, q, body, module):
    """The test cycle: start one, record results of cases run by hand, link bugs, mark bugs fixed, quarantine flaky tests.
    The rules are execute.py's (the same as scripts/cycle.sh); the page sends the person's name with each."""
    action, by = body.get("action"), str(body.get("by", "")).strip()
    s = lambda k: str(body.get(k, "")).strip()
    args = {"start": lambda: [module, s("name"), "--env", s("env")],
            "result": lambda: [module, ",".join(str(x) for x in body.get("ids") or []), s("result")] + (["--bug", s("bug")] if s("bug") else []) + (["--note", s("note")] if s("note") else []),
            "bug": lambda: [module, s("id"), s("bug")], "fixed": lambda: [module, s("bug")] + (["--note", s("note")] if s("note") else []),
            "quarantine": lambda: [module, s("id"), "--reason", s("reason")], "unquarantine": lambda: [module, s("id")]}.get(action)
    if not args or not isinstance(body.get("ids", []), list): return h.send(400, {"error": "bad request"})
    if any(v.startswith("-") for v in args()[1:] if v not in ("--env", "--bug", "--note", "--reason")): return h.send(400, {"ok": False, "message": "A value cannot start with -"})
    if not by: return h.send(400, {"ok": False, "message": "your name is needed: results are signed"})
    code, out = intake.run_py("execute.py", [action] + args() + ["--by", by])
    return h.send(200 if code == 0 else 400, {"ok": code == 0, "message": out.strip()})


@api("POST", "/api/bugs", module="body", busy_check=True)
def post_bugs(h, q, body, module):
    """The bug register: report a bug (from a failed case: its steps and evidence), or change a bug's status. The rules are report.py's."""
    s = lambda k: str(body.get(k, "")).strip()
    if body.get("action") == "add":
        args = ["bug-add", module] + [x for k in ("title", "severity", "cases", "steps", "expected", "actual", "evidence", "target") if s(k) for x in (f"--{k}", s(k))]
    elif body.get("action") == "status": args = ["bug-status", module, s("id"), s("status")] + (["--note", s("note")] if s("note") else [])
    else: return h.send(400, {"error": "bad request"})
    if not s("by"): return h.send(400, {"ok": False, "message": "your name is needed: bugs are signed"})
    if any(v.startswith("-") for v in (s(k) for k in ("title", "cases", "steps", "expected", "actual", "evidence", "target", "id", "status", "note")) if v):
        return h.send(400, {"ok": False, "message": "A value cannot start with -"})
    code, out = intake.run_py("report.py", args + ["--by", s("by")])
    return h.send(200 if code == 0 else 400, {"ok": code == 0, "message": out.strip()})


@api("POST", "/api/report-decision", module="body", busy_check=True)
def post_decision(h, q, body, module):
    s = lambda k: str(body.get(k, "")).strip()
    if s("decision") not in ("Go", "No-go"): return h.send(400, {"error": "bad request"})
    if not s("by") or not s("reason"): return h.send(400, {"ok": False, "message": "your name and the reason are needed: the decision is signed"})
    if s("reason").startswith("-"): return h.send(400, {"ok": False, "message": "A value cannot start with -"})
    code, out = intake.run_py("report.py", ["decide", module, s("decision"), "--reason", s("reason"), "--by", s("by")])
    return h.send(200 if code == 0 else 400, {"ok": code == 0, "message": out.strip()})


@api("GET", "/api/report-file", module="query")
def get_report_file(h, q, body, module):
    """The module's HTML report, sandboxed (its own scripts run, nothing else; no requests leave it)."""
    p = report.report_path(module)
    if not os.path.isfile(p): return h.send(404, {"error": "not found"})
    return h.send(200, read_bytes(p), "text/html; charset=utf-8", {"Content-Security-Policy": "sandbox allow-scripts; " + report.CSP})


@api("POST", "/api/stage", module="body", busy_check=True)
def post_stage(h, q, body, module):
    action, st, by, comment = body.get("action"), body.get("stage"), str(body.get("by", "")).strip(), str(body.get("comment", "")).strip()
    if action not in ("approve", "reject", "reopen", "submit") or st not in STAGES: return h.send(400, {"error": "bad request"})
    if action == "submit":  # not a decision: the stage's own check runs, and a person still approves
        code, out = run_stage(["submit", module, st])
        return h.send(200 if code == 0 else 400, {"ok": code == 0, "message": out})
    if not by: return h.send(400, {"error": "your name is needed: decisions are signed"})
    if re.search(r"[\r\n|]", by + comment): return h.send(400, {"ok": False, "message": "Name and comment cannot contain line breaks or |"})
    code, out = run_stage([action, module, st, "--by", by] + (["--comment", comment] if comment else []))
    return h.send(200 if code == 0 else 400, {"ok": code == 0, "message": out})


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

    def local(self): return (self.headers.get("Host") or "").split(":")[0] in ("127.0.0.1", "localhost")  # blocks DNS-rebinding pages

    def allowed(self, q):
        if not self.local(): return False
        given = (self.headers.get("X-TestHive-Token") or arg(q, "t")).encode("utf-8", "replace")
        return secrets.compare_digest(given, TOKEN.encode())

    def do_GET(self): self.handle_api("GET")

    def do_POST(self): self.handle_api("POST")

    def handle_api(self, method):
        u = urlparse(self.path); q = parse_qs(u.query)
        if method == "GET" and (u.path == "/" or PAGE_FILE.fullmatch(u.path)):  # the page carries no data: no token needed, but only on this PC
            if not self.local(): return self.send(403, {"error": "forbidden"})
            p = page_file(u.path)
            if not p: return self.send(404, {"error": "not found"})
            return self.send(200, read_bytes(p), PAGE_TYPES[os.path.splitext(p)[1]], {"Content-Security-Policy": CSP})
        if not self.allowed(q): return self.send(403, {"error": "missing or wrong token: open the address printed by studio"})
        fn, o = ROUTES.get((method, u.path), (None, None))
        if fn and not PROJECT["path"] and u.path not in NO_PROJECT_OK:
            return self.send(409, {"no_project": True, "error": "Open a TestHive project first."})
        body = None
        if method == "POST":
            try: n = int(self.headers.get("Content-Length") or 0)
            except ValueError: n = -1
            if n < 0: return self.send(400, {"ok": False, "message": "bad Content-Length"})
            limit = intake.MAX_APK if u.path == "/api/source" and arg(q, "kind") == "apk" else intake.MAX_DOC
            if n > limit:  # read and drop the body first, so the browser receives the message instead of a broken connection
                while n > 0: n -= len(self.rfile.read(min(n, 1 << 20)) or b"x" * n)
                return self.send(413, {"ok": False, "message": f"The file is larger than {limit // 1_000_000} MB."})
            body = self.rfile.read(n)
            if fn and not o["raw"]:
                if (self.headers.get("Content-Type") or "").split(";")[0] != "application/json": return self.send(415, {"error": "JSON only"})
                try: body = json.loads(body or b"{}")
                except ValueError: return self.send(400, {"error": "bad JSON"})
                if not isinstance(body, dict): return self.send(400, {"error": "bad JSON"})
        if not fn: return self.send(404, {"error": "not found"})
        module = None
        if o["module"]:
            module = (arg(q, "m") if o["module"] == "query" else str(body.get("module", ""))).strip().upper()
            if module not in load_state()["modules"]: return self.send(404, {"error": "unknown module"})
        if not o["lock"]: return fn(self, q, body, module)
        with WRITE:
            if o["busy"] and module and jobs.running(module): return self.send(423, {"ok": False, "message": busy(module)})
            return fn(self, q, body, module)


class Server(ThreadingHTTPServer):
    """Owns its port alone. On Windows the usual address reuse lets a second program open the same port and receive
    some of the requests (an old Studio answering the new one's browser), so the port is taken exclusively there."""
    allow_reuse_address = os.name != "nt"

    def server_bind(self):
        if os.name == "nt": self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def main():
    a = sys.argv[1:]
    port = int(a[a.index("--port") + 1]) if "--port" in a else 8765
    try: srv = Server(("127.0.0.1", port), Handler)
    except OSError: srv = Server(("127.0.0.1", 0), Handler)  # port in use (another Studio): take a free one
    url = f"http://127.0.0.1:{srv.server_address[1]}/?t={TOKEN}"
    p = projects.choose(a, os.getcwd())
    if p: open_project(p)
    print(f"STUDIO {url}", flush=True)
    print(f"Project: {PROJECT['path']}" if PROJECT["path"] else "No project yet: choose its folder in the browser.", flush=True)
    print("TestHive Studio is running on this PC only. Keep this window open; press Ctrl+C to stop.", flush=True)
    if "--no-browser" not in a: webbrowser.open(url)
    try: srv.serve_forever()
    except KeyboardInterrupt: pass
    for j in [j for j in jobs.JOBS.values() if j["status"] == "running" and j.get("_proc")]:  # this window's agents only
        jobs.stop(j["id"], "stopped because Studio was closed")
    print("Studio stopped.")


if __name__ == "__main__":
    main()
