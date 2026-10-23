"""Stage gates and approvals for TestHive (the logic behind scripts/stage.sh; Studio calls it too).
Usage: python scripts/lib/stage.py <command> ...   (the commands are listed at the top of scripts/stage.sh)
Runs with Python only, so Studio needs no bash for viewing, answering, reviewing and approving."""
import sys, json, os, re, time, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pyrun import lib_cmd  # runs analysis.py, design.py, modules.py from source or inside the Studio program
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
STAGES = ["analysis", "design", "tools", "automation", "execution", "reporting"]
SF = os.environ.get("TH_STATE", "workflow/state.json")
LOG = os.path.join(os.path.dirname(SF) or ".", "APPROVALS.md")
RUN = os.environ["TH_CMD"] + " stage" if os.environ.get("TH_CMD") else "bash scripts/stage.sh"  # how the user types it
USAGE = f"Usage: {RUN} init|status|start|submit|approve|reject|reopen|check|archive|restore ...  (see the top of scripts/stage.sh)"

def now(): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
def die(msg, code=1): print(msg); sys.exit(code)
def load():
    if not os.path.exists(SF): return {"format": "testhive-state/1", "modules": {}}
    with open(SF, encoding="utf-8") as f: return json.load(f)
def save(s):
    os.makedirs(os.path.dirname(SF) or ".", exist_ok=True)
    with open(SF + ".tmp", "w", encoding="utf-8", newline="\n") as f: json.dump(s, f, indent=2, ensure_ascii=False)
    os.replace(SF + ".tmp", SF)
LIBS = {"analysis": ("analysis.py", os.path.join(os.environ.get("TH_ANALYSIS", "analysis"), "requirements.csv")),
        "design": ("design.py", os.path.join(os.environ.get("TH_CASES", "test-cases"), "TestCases.csv"))}
def ready(name, st):
    """Runs the stage's own --for-approval check when the stage has one and its files exist. True if fine."""
    if st not in LIBS or not os.path.exists(LIBS[st][1]): return True
    sys.stdout.flush()
    return subprocess.run(lib_cmd(LIBS[st][0], "check", name, "--for-approval")).returncode == 0
def log(module, st, decision, by, comment):
    new = not os.path.exists(LOG)
    with open(LOG, "a", encoding="utf-8", newline="\n") as f:
        if new: f.write("# Approvals log\nAppend-only, written by scripts/stage.sh. Do not edit by hand.\n\n| When (UTC) | Module | Stage | Decision | By | Comment |\n|---|---|---|---|---|---|\n")
        f.write(f"| {now()} | {module} | {st} | {decision} | {by} | {(comment or '').replace('|', '/')} |\n")

a = sys.argv[1:]
if not a: die(USAGE)
cmd, pos, opt, i = a[0], [], {}, 1
while i < len(a):
    if a[i] in ("--by", "--comment"):
        if i + 1 >= len(a) or not a[i + 1].strip(): die(f"{a[i]} needs a value")
        if re.search(r"[\r\n|]", a[i + 1]): die(f"{a[i]} cannot contain line breaks or |")
        opt[a[i][2:]] = a[i + 1]; i += 2
    else: pos.append(a[i]); i += 1
s = load()

def module(name):
    m = s["modules"].get(name.upper())
    if m is None: die(f"Unknown module {name}. Run: {RUN} init {name}")
    return m
def stage(name):
    if name not in STAGES: die(f"Unknown stage {name}. Stages in order: {' '.join(STAGES)}")
    return name
def blocker(m, st):
    i = STAGES.index(st)
    if m["stages"][st]["status"] == "approved": return f"{st} is already approved"
    if i and m["stages"][STAGES[i - 1]]["status"] != "approved":
        return f"{STAGES[i - 1]} is not approved yet (it is {m['stages'][STAGES[i - 1]]['status']})"
    return None
def mark(m, st, status, by=None, comment=None):
    e = m["stages"][st]; e["status"] = status
    e["history"].append({"at": now(), "status": status, "by": by, "comment": comment})
def show(name, m):
    print(name)
    nxt = None
    for st in STAGES:
        e = m["stages"][st]; last = e["history"][-1] if e["history"] else {}
        who = f"  by {last['by']} {last['at'][:10]}" if e["status"] == "approved" and last.get("by") else ""
        print(f"  {st:<11} {e['status'].replace('_', ' ')}{who}")
        if nxt is None and e["status"] != "approved":
            nxt = {"pending": f"start {st}", "in_progress": f"finish {st}, then submit it",
                   "awaiting_approval": f"a human approves or rejects {st}"}[e["status"]]
    print(f"  next: {nxt or 'all stages approved'}")

if cmd == "init":
    if len(pos) != 1: die("Usage: stage.sh init <MODULE>")
    name = pos[0].upper()
    if not re.fullmatch(r"[A-Z0-9]+", name): die("Module code: letters and digits only")
    if name in s["modules"]: die(f"{name} already exists", 0)
    s["modules"][name] = {"created": now(), "stages": {st: {"status": "pending", "history": []} for st in STAGES}}
    save(s); print(f"Module {name} added. Next: {RUN} start {name} analysis")
elif cmd == "status":
    if pos: show(pos[0].upper(), module(pos[0]))
    elif not s["modules"]: print(f"No modules yet. Run: {RUN} init <MODULE>")
    else:
        for n, m in s["modules"].items(): show(n, m)
elif cmd in ("start", "check"):
    if len(pos) != 2: die(f"Usage: stage.sh {cmd} <MODULE> <stage>")
    m, st = module(pos[0]), stage(pos[1])
    b = blocker(m, st)
    if cmd == "check": die("BLOCKED: " + b, 2) if b else die("OK", 0)
    if b: die("BLOCKED: " + b, 2)
    if m["stages"][st]["status"] == "in_progress": die(f"{st} is already in progress", 0)
    if m["stages"][st]["status"] == "awaiting_approval": die(f"{st} is waiting for approval", 2)
    mark(m, st, "in_progress"); save(s); print(f"{pos[0].upper()} {st}: in progress")
elif cmd == "submit":
    if len(pos) != 2: die("Usage: stage.sh submit <MODULE> <stage>")
    m, st = module(pos[0]), stage(pos[1])
    if m["stages"][st]["status"] != "in_progress": die(f"{st} must be in progress to submit (it is {m['stages'][st]['status']})", 2)
    i = STAGES.index(st)
    if i and m["stages"][STAGES[i - 1]]["status"] != "approved": die(f"BLOCKED: {STAGES[i - 1]} is not approved (it was reopened); approve it first", 2)
    if not ready(pos[0].upper(), st):
        die("BLOCKED: not ready to submit. Give the workbook to the human, import the review, re-check, then submit.", 2)
    mark(m, st, "awaiting_approval"); save(s); print(f"{pos[0].upper()} {st}: waiting for human approval")
elif cmd in ("approve", "reject", "reopen", "archive", "restore") and os.environ.get("TH_JOB"):
    die(f"BLOCKED: {cmd} is a human decision; an agent started from TestHive Studio cannot make it", 2)
elif cmd in ("approve", "reject"):
    if len(pos) != 2: die(f"Usage: stage.sh {cmd} <MODULE> <stage> --by <name> [--comment ...]")
    m, st = module(pos[0]), stage(pos[1])
    if "by" not in opt: die(f"{cmd} needs --by <name>: decisions are made by a named human")
    if cmd == "reject" and "comment" not in opt: die("reject needs --comment saying what to change")
    if m["stages"][st]["status"] != "awaiting_approval": die(f"{st} is not waiting for approval (it is {m['stages'][st]['status']})", 2)
    has_files = st in LIBS and os.path.exists(LIBS[st][1])
    if cmd == "approve" and not ready(pos[0].upper(), st): die(f"BLOCKED: the {st} is not ready for approval (see above)", 2)
    status = "approved" if cmd == "approve" else "in_progress"
    mark(m, st, status, opt["by"], opt.get("comment")); save(s)
    log(pos[0].upper(), st, "Approved" if cmd == "approve" else "Rejected", opt["by"], opt.get("comment"))
    print(f"{pos[0].upper()} {st}: {'approved' if cmd == 'approve' else 'rejected, back to in progress'} by {opt['by']}")
    if cmd == "approve" and has_files:
        sys.stdout.flush()
        subprocess.run(lib_cmd(LIBS[st][0], "baseline", pos[0].upper(), opt["by"]))
elif cmd == "reopen":
    if len(pos) != 2: die("Usage: stage.sh reopen <MODULE> <stage> --by <name> --comment \"why\"")
    m, st = module(pos[0]), stage(pos[1])
    if "by" not in opt or "comment" not in opt: die("reopen needs --by <name> and --comment saying what changes")
    if m["stages"][st]["status"] != "approved": die(f"{st} is not approved (it is {m['stages'][st]['status'].replace('_', ' ')}); nothing to reopen", 2)
    mark(m, st, "in_progress", opt["by"], "reopened: " + opt["comment"])
    later = [x for x in STAGES[STAGES.index(st) + 1:] if m["stages"][x]["status"] in ("awaiting_approval", "approved")]
    for x in later: mark(m, x, "in_progress", opt["by"], f"{st} reopened")
    save(s); log(pos[0].upper(), st, "Reopened", opt["by"], opt["comment"])
    print(f"{pos[0].upper()} {st}: reopened by {opt['by']}" + (f"; {', '.join(later)} back to in progress (needs a new approval)" if later else ""))
elif cmd in ("archive", "restore"):
    if len(pos) != 1 or "by" not in opt or (cmd == "archive" and "comment" not in opt):
        die(f"Usage: stage.sh archive <MODULE> --by <name> --comment \"why\"  |  stage.sh restore <MODULE>-<time> --by <name>")
    arch = os.environ.get("TH_ARCHIVE", "archive")
    sys.stdout.flush()
    if cmd == "archive":
        name = pos[0].upper(); m = module(name)
        dest = os.path.join(arch, f"{name}-{time.strftime('%Y%m%d-%H%M%S')}")
        if subprocess.run(lib_cmd("modules.py", "archive", name, dest, opt["by"], opt["comment"])).returncode: die("Not archived.", 2)
        with open(os.path.join(dest, "state.json"), "w", encoding="utf-8", newline="\n") as f: json.dump(m, f, indent=2, ensure_ascii=False)
        fp = subprocess.run(lib_cmd("modules.py", "fingerprint", dest), capture_output=True, text=True).stdout.strip()
        del s["modules"][name]; save(s)  # the fingerprint lets restore refuse a folder changed or planted later
        log(name, "-", "Archived", opt["by"], f"{opt['comment']} (kept in {dest.replace(os.sep, '/')}/, fingerprint {fp})")
        print(f"{name}: archived by {opt['by']}. Restore with: {RUN} restore {os.path.basename(dest)} --by <name>")
    else:
        if not re.fullmatch(r"[A-Z][A-Z0-9]*-\d{8}-\d{6}", pos[0]): die(f"Unknown archive {pos[0]}: give the folder name (module code, date and time, as listed by the archive)")
        dest = os.path.join(arch, pos[0])
        if not os.path.exists(os.path.join(dest, "state.json")): die(f"No archived module in {dest}/")
        with open(os.path.join(dest, "state.json"), encoding="utf-8") as f: m = json.load(f)
        name = pos[0].rsplit("-", 2)[0]
        if name in s["modules"]: die(f"{name} exists again: archive or rename it first", 2)
        if subprocess.run(lib_cmd("modules.py", "restore", dest)).returncode: die("Not restored.", 2)
        s["modules"][name] = m; save(s)
        log(name, "-", "Restored", opt["by"], opt.get("comment") or f"from {dest.replace(os.sep, '/')}/")
        print(f"{name}: restored by {opt['by']}")
else:
    die(USAGE)
