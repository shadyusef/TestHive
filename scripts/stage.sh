#!/usr/bin/env bash
# Stage gates: no stage starts until the stage before it is approved by a human.
# Usage: bash scripts/stage.sh <command> ...
#   init    <MODULE>                     add a module (all stages pending)
#   status  [MODULE]                     show every stage and what comes next
#   start   <MODULE> <stage>             begin a stage (refused unless the previous stage is approved)
#   submit  <MODULE> <stage>             output is ready: the stage now waits for a human
#   approve <MODULE> <stage> --by <name> [--comment "..."]
#   reject  <MODULE> <stage> --by <name> --comment "why"      sends the stage back to in progress
#   check   <MODULE> <stage>             exit 0 if the stage may start, 2 if not
# Stages, in order: analysis design tools automation execution reporting
# State lives in workflow/state.json; every decision is appended to workflow/APPROVALS.md.
# Submitting or approving "analysis" first runs check-analysis --for-approval (when analysis/requirements.csv exists) and then
# freezes the module's registers as a baseline in analysis/baseline/<MODULE>/v<n>/.
. "$(dirname "$0")/_py.sh"
export TH_SCRIPTS="$(dirname "$0")"
$PY - "$@" <<'PY'
import sys, json, os, re, time, subprocess
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
STAGES = ["analysis", "design", "tools", "automation", "execution", "reporting"]
SF = os.environ.get("TH_STATE", "workflow/state.json")
LOG = os.path.join(os.path.dirname(SF) or ".", "APPROVALS.md")
RUN = os.environ["TH_CMD"] + " stage" if os.environ.get("TH_CMD") else "bash scripts/stage.sh"  # how the user types it
USAGE = f"Usage: {RUN} init|status|start|submit|approve|reject|check ...  (see the top of scripts/stage.sh)"

def now(): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
def die(msg, code=1): print(msg); sys.exit(code)
def load():
    if not os.path.exists(SF): return {"format": "testhive-state/1", "modules": {}}
    with open(SF, encoding="utf-8") as f: return json.load(f)
def save(s):
    os.makedirs(os.path.dirname(SF) or ".", exist_ok=True)
    with open(SF + ".tmp", "w", encoding="utf-8", newline="\n") as f: json.dump(s, f, indent=2, ensure_ascii=False)
    os.replace(SF + ".tmp", SF)
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
    if not re.fullmatch(r"[A-Z0-9]+", name): die("Module code: letters and digits only, e.g. SIGNUP")
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
    lib = os.path.join(os.environ.get("TH_SCRIPTS", "scripts"), "lib", "analysis.py")
    if st == "analysis" and os.path.exists(os.path.join(os.environ.get("TH_ANALYSIS", "analysis"), "requirements.csv")):
        if subprocess.run([sys.executable, lib, "check", pos[0].upper(), "--for-approval"]).returncode != 0:
            die("BLOCKED: not ready to submit. Give the workbook to the human, import the answers, re-check, then submit.", 2)
    mark(m, st, "awaiting_approval"); save(s); print(f"{pos[0].upper()} {st}: waiting for human approval")
elif cmd in ("approve", "reject"):
    if len(pos) != 2: die(f"Usage: stage.sh {cmd} <MODULE> <stage> --by <name> [--comment ...]")
    m, st = module(pos[0]), stage(pos[1])
    if "by" not in opt: die(f"{cmd} needs --by <name>: decisions are made by a named human")
    if cmd == "reject" and "comment" not in opt: die("reject needs --comment saying what to change")
    if m["stages"][st]["status"] != "awaiting_approval": die(f"{st} is not waiting for approval (it is {m['stages'][st]['status']})", 2)
    lib = os.path.join(os.environ.get("TH_SCRIPTS", "scripts"), "lib", "analysis.py")
    has_registers = os.path.exists(os.path.join(os.environ.get("TH_ANALYSIS", "analysis"), "requirements.csv"))
    if cmd == "approve" and st == "analysis" and has_registers:
        sys.stdout.flush(); r = subprocess.run([sys.executable, lib, "check", pos[0].upper(), "--for-approval"])
        if r.returncode != 0: die("BLOCKED: the analysis is not ready for approval (see above)", 2)
    status = "approved" if cmd == "approve" else "in_progress"
    mark(m, st, status, opt["by"], opt.get("comment")); save(s)
    log(pos[0].upper(), st, "Approved" if cmd == "approve" else "Rejected", opt["by"], opt.get("comment"))
    print(f"{pos[0].upper()} {st}: {'approved' if cmd == 'approve' else 'rejected, back to in progress'} by {opt['by']}")
    if cmd == "approve" and st == "analysis" and has_registers:
        sys.stdout.flush()
        subprocess.run([sys.executable, lib, "baseline", pos[0].upper(), opt["by"]])
else:
    die(USAGE)
PY
