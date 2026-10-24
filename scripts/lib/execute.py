"""TestHive execution (stage 5): test cycles. A cycle is one round of testing of a module on one environment; every stored run
of the module on that environment after the cycle started belongs to it. Each functional case of the approved design gets its
result in the cycle: automated cases from the runs, the others recorded by a person. Failures carry a bug ID, a case that both
passed and failed without a fixed bug is flaky (a person may quarantine it with a reason), fixed bugs are retested, and the
stage is approved on the cycle's results. Called by scripts/cycle.sh, retest.sh, stage.sh (check --for-approval, baseline) and Studio.
Formats: docs/FORMATS.md (execution)."""
import sys, os, re, csv, json, glob, time, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analysis import die, stage_status
import design, tools, automate
from pyrun import lib_cmd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
DIR = os.environ.get("TH_EXECUTION", "execution")
LOG_COLS = ["At", "By", "Action", "ID", "Result", "Bug", "Note"]  # append-only: the latest row of a case wins
RESULTS = ("Passed", "Failed", "Blocked")
BUG = re.compile(r"BUG-[A-Z0-9][A-Z0-9-]{0,40}")
ENV = re.compile(r"[A-Za-z0-9._-]{0,40}")
MAX_TEXT = tools.MAX_TEXT


def now(): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def text(t):
    """One line of text a person typed, safe in a CSV opened in Excel."""
    t = automate.line(t)[:MAX_TEXT]
    return "'" + t if t[:1] in ("=", "+", "-", "@") else t


def signed(by):
    if not by or not by.strip() or re.search(r"[\r\n|]", by) or len(by) > MAX_TEXT: die(f"--by <your name> is needed (no line breaks or |, at most {MAX_TEXT} characters)")
    return text(by)


MODULE = re.compile(r"[A-Z0-9]+")


def cycles(module):
    if not MODULE.fullmatch(module): die(f"Unknown module {module}: letters and digits only")
    d = os.path.join(DIR, module)
    return sorted((int(x[1:]) for x in os.listdir(d) if re.fullmatch(r"C\d+", x)), reverse=True) if os.path.isdir(d) else []


def current(module):
    """The module's latest cycle ({id, name, env, started_at, started_by}), or None."""
    cs = cycles(module)
    if not cs: return None
    with open(os.path.join(DIR, module, f"C{cs[0]}", "cycle.json"), encoding="utf-8") as f: return json.load(f)


def log_path(module, c): return os.path.join(DIR, module, c["id"], "log.csv")


def read_log(module, c):
    p = log_path(module, c)
    if not os.path.exists(p): return []
    with open(p, encoding="utf-8-sig", newline="") as f: return [{k: (r.get(k) or "") for k in LOG_COLS} for r in csv.DictReader(f)]


def append(module, c, rows):
    p, new = log_path(module, c), not os.path.exists(log_path(module, c))
    with open(p, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, LOG_COLS, lineterminator="\n")
        if new: w.writeheader()
        w.writerows(rows)


def scope(module, au=None):
    """The cases the cycle needs a result for: active functional cases of the approved design, with how each is run."""
    b = tools.design_baseline(module)
    if not b: return []
    auto = {c["ID"]: c for c in ((au if au is not None else automate.status(module)) or {}).get("cases") or []}
    out = []
    for c in b[1]:
        if not design.active(c) or c["Type"] not in tools.FUNCTIONAL: continue
        a = auto.get(c["ID"])
        out.append({"ID": c["ID"], "Title": c["Title"], "Priority": c["Priority"], "Tags": " ".join(automate.tags(c)), "Type": c["Type"],
                    "kind": a["kind"] if a and a["kind"] else "manual", "known_bug": a["bug"] if a else ""})
    return out


def cycle_runs(module, c):
    """The module's stored runs on the cycle's environment since it started, oldest first: [(meta, results)]."""
    out = []
    for d in glob.glob(os.path.join(os.environ.get("TH_RUNS", "runs"), "R-*")):
        if not automate.RUN_ID.fullmatch(os.path.basename(d)): continue
        try:
            with open(os.path.join(d, "meta.json"), encoding="utf-8") as f: meta = json.load(f)
            if meta.get("module") != module or meta.get("collected_at", "") < c["started_at"] or (meta.get("env") or "") != c["env"]: continue
            with open(os.path.join(d, "results.json"), encoding="utf-8") as f: res = json.load(f)
        except (OSError, ValueError): continue
        out.append((meta, res))
    return sorted(out, key=lambda x: (x[0].get("collected_at", ""), x[0].get("run_id", "")))


def status(module, c=None):
    """The cycle and the result of every case in scope; None before a cycle starts."""
    c = c or current(module)
    if not c: return None
    log, runs, au = read_log(module, c), cycle_runs(module, c), automate.status(module) or {}
    fixed = {r["Bug"]: r["At"] for r in log if r["Action"] == "fixed"}
    hist = {}  # case ID -> [(run, passed?, at)]
    for meta, res in runs:
        if meta.get("kind") == "contract": continue
        per = {}
        for x in res.get("cases", []):
            if x.get("id") and x.get("status") != "skipped": per[x["id"]] = per.get(x["id"], True) and x.get("status") == "passed"  # a request: every check
        for i, ok in per.items(): hist.setdefault(i, []).append({"run": meta["run_id"], "ok": ok, "at": meta.get("collected_at", "")})
    last = {}  # case ID -> what people recorded, latest first wins
    for r in log:
        if not r["ID"]: continue
        m = last.setdefault(r["ID"], {})
        if r["Action"] == "result": m.update(result=r["Result"], bug=r["Bug"], note=r["Note"], by=r["By"], at=r["At"])
        elif r["Action"] == "bug": m["bug"] = r["Bug"]
        elif r["Action"] == "quarantine": m["quarantine"] = {"reason": r["Note"], "by": r["By"], "at": r["At"]}
        elif r["Action"] == "unquarantine": m.pop("quarantine", None)
    rows = []
    for s in scope(module, au):
        m, h = last.get(s["ID"], {}), hist.get(s["ID"], [])
        bug = m.get("bug") or s["known_bug"]
        if s["kind"] == "manual": result = {"Passed": "passed", "Failed": "failed", "Blocked": "blocked"}.get(m.get("result"), "not-run")
        elif not h: result = "not-run"
        else: result = "known-bug" if h[-1]["ok"] and s["known_bug"] else "passed" if h[-1]["ok"] else "failed"
        fix = fixed.get(bug, "")
        flaky = any(x["ok"] for x in h) and any(not x["ok"] for x in h) and not (fix and all(x["ok"] for x in h if x["at"] > fix))
        if not fix: retest = False
        elif s["kind"] == "manual": retest = m.get("at", "") < fix  # recorded before the fix
        else: retest = not any(x["ok"] for x in h if x["at"] > fix)  # no pass since the fix (shortcut: times are to the second; a run in the fix's second does not count)
        rows.append(dict(s, result=result, bug=bug, bug_fixed=fix, flaky=flaky, quarantine=m.get("quarantine"), retest=retest,
                         history=["P" if x["ok"] else "F" for x in h][-10:], note=m.get("note", ""), by=m.get("by", "")))
    ct = None
    if au.get("contract"):
        cr = [(m, r) for m, r in runs if m.get("kind") == "contract"]
        bugs = automate.contract.known_bugs(module)
        failed = sorted({x["suite"] for x in cr[-1][1].get("cases", []) if x.get("status") != "passed" and x.get("suite")}) if cr else []
        ct = {"run": cr[-1][0]["run_id"] if cr else "", "failed": [{"endpoint": e, "bug": bugs.get(e, "")} for e in failed]}
    other = sum(1 for d in glob.glob(os.path.join(os.environ.get("TH_RUNS", "runs"), "R-*", "meta.json")) if _other_env(d, module, c))
    return {"cycle": c, "cases": rows, "runs": [m["run_id"] for m, _ in runs], "contract": ct, "fixed": fixed, "other_env_runs": other}


def _other_env(meta_path, module, c):
    try:
        with open(meta_path, encoding="utf-8") as f: m = json.load(f)
    except (OSError, ValueError): return False
    return m.get("module") == module and m.get("collected_at", "") >= c["started_at"] and (m.get("env") or "") != c["env"]


def problems(module, for_approval=False, s=None):
    """(errors, warnings) of the current cycle."""
    s = s or status(module)
    if not s: return ["no test cycle yet: start one (cycle.sh start)"], []
    err, warn, cs = [], [], s["cases"]
    for c in cs:
        q = c["quarantine"]
        if c["result"] == "not-run": err.append(f"{c['ID']}: no result in cycle {s['cycle']['id']} yet ({'record it by hand' if c['kind'] == 'manual' else 'run the ' + c['kind'] + ' tests'})")
        elif c["result"] == "failed" and not c["bug"] and not q: err.append(f"{c['ID']}: failed without a bug ID (report it, then link it)")
        if c["flaky"] and not q: err.append(f"{c['ID']}: flaky (passed and failed: {''.join(c['history'])}): fix the test, or quarantine it with a reason")
        if c["retest"] and not q: err.append(f"{c['ID']}: {c['bug']} is fixed: retest it")
        if q: warn.append(f"{c['ID']}: quarantined by {q['by']}: {q['reason']}")
        if c["result"] == "blocked": warn.append(f"{c['ID']}: blocked: {c['note']}")
        if c["result"] in ("failed", "known-bug") and c["bug"] and not c["bug_fixed"]: warn.append(f"{c['ID']}: fails on {c['bug']} (open bug)")
    ct = s["contract"]
    if ct and not ct["run"]: err.append(f"contract tests: not run in cycle {s['cycle']['id']} (run-api.sh <module> --contract)")
    elif ct: err += [f"contract tests: {f['endpoint']} answers differently from the spec without a bug ID" for f in ct["failed"] if not f["bug"]]
    if s["other_env_runs"]: warn.append(f"{s['other_env_runs']} runs since the cycle started were on another environment: they do not count")
    if not cs: warn.append("no functional case in the approved design: nothing to execute")
    return err, warn


def check_case(module, ids, manual=None):
    s = {c["ID"]: c for c in scope(module)}
    for i in ids:
        if i not in s: die(f"{i} is not a functional case of the approved design of {module}")
        if manual is not None and (s[i]["kind"] == "manual") != manual:
            die(f"{i} is {'recorded by hand' if s[i]['kind'] == 'manual' else 'an automated ' + s[i]['kind'] + ' test: its result comes from the runs'}")


def need_cycle(module):
    st = stage_status(module, "execution")
    if st in ("approved", "awaiting_approval"): die(f"BLOCKED: the execution of {module} is {st.replace('_', ' ')}: {'reopen' if st == 'approved' else 'reject'} it to change its results", 2)
    c = current(module)
    if not c: die(f"No test cycle for {module} yet: cycle.sh start {module} \"<name>\" --env <name> --by <you>")
    return c


def human(cmd):
    if os.environ.get("TH_JOB"): die(f"BLOCKED: {cmd} is a human decision; an agent started from TestHive Studio cannot make it", 2)


def opts(a, names):
    pos, o, i = [], {}, 0
    while i < len(a):
        if a[i] in names:
            if i + 1 >= len(a): die(f"{a[i]} needs a value")
            o[a[i][2:]] = a[i + 1]; i += 2
        else: pos.append(a[i]); i += 1
    return pos, o


def cmd_start(a):
    pos, o = opts(a, ("--env", "--by"))
    if len(pos) != 2: die('Usage: cycle.sh start <MODULE> "<name>" --env <TEST_ENV name, or "" for .env> --by <you>')
    human("starting a cycle")
    module, name, env, by = pos[0].upper(), text(pos[1]), o.get("env", ""), signed(o.get("by"))
    if not name: die("The cycle needs a name (for example \"1.4 UAT\")")
    if not ENV.fullmatch(env) or env.startswith("."): die("--env: letters, digits, . _ - only (the name of .env.<name>; empty for .env)")
    if env and not os.path.exists(f".env.{env}"): print(f"  note: .env.{env} does not exist yet on this PC: create it before running the tests")
    if stage_status(module, "automation") != "approved": die(f"BLOCKED: the automation of {module} is not approved yet (stage 4)", 2)
    if stage_status(module, "execution") in ("approved", "awaiting_approval"): die(f"BLOCKED: the execution of {module} is {stage_status(module, 'execution').replace('_', ' ')}: reopen it for a new cycle", 2)
    n = (cycles(module) or [0])[0] + 1
    c = {"id": f"C{n}", "module": module, "name": name, "env": env, "started_at": now(), "started_by": by}
    os.makedirs(os.path.join(DIR, module, c["id"]))
    automate.write_json(os.path.join(DIR, module, c["id"], "cycle.json"), c)
    if stage_status(module, "execution") == "pending": subprocess.run(lib_cmd("stage.py", "start", module, "execution"))
    print(f"CYCLE {module} {c['id']} \"{name}\" on {env or 'the default .env'}: started by {by}. Runs on that environment from now on count.")


def cmd_result(a):
    pos, o = opts(a, ("--bug", "--note", "--by"))
    if len(pos) != 3 or pos[2] not in RESULTS: die("Usage: cycle.sh result <MODULE> <TC-ID>[,<TC-ID>...] Passed|Failed|Blocked [--bug BUG-<n>] [--note \"...\"] --by <you>")
    human("recording a result")
    module = pos[0].upper(); c = need_cycle(module); ids = [x.strip() for x in pos[1].split(",") if x.strip()]
    bug, note, by = o.get("bug", ""), text(o.get("note", "")), signed(o.get("by"))
    if bug and not BUG.fullmatch(bug): die("--bug: BUG-<id> (letters, digits and -)")
    if pos[2] == "Failed" and not bug: die("A failed case needs --bug BUG-<n>: report the bug first")
    if pos[2] == "Blocked" and not note: die("A blocked case needs --note saying what blocks it")
    check_case(module, ids, manual=True)
    append(module, c, [{"At": now(), "By": by, "Action": "result", "ID": i, "Result": pos[2], "Bug": bug, "Note": note} for i in ids])
    print(f"RESULT {module} {c['id']}: {len(ids)} cases {pos[2]}" + (f" ({bug})" if bug else ""))


def cmd_bug(a):
    pos, o = opts(a, ("--by",))
    if len(pos) != 3 or not BUG.fullmatch(pos[2]): die("Usage: cycle.sh bug <MODULE> <TC-ID> BUG-<n> --by <name>   (links a bug to a failed automated test)")
    human("linking a bug")
    module = pos[0].upper(); c = need_cycle(module); check_case(module, [pos[1]], manual=False)
    append(module, c, [{"At": now(), "By": signed(o.get("by")), "Action": "bug", "ID": pos[1], "Result": "", "Bug": pos[2], "Note": ""}])
    print(f"BUG {module} {c['id']}: {pos[1]} fails on {pos[2]}")


def cmd_fixed(a):
    pos, o = opts(a, ("--by", "--note"))
    if len(pos) != 2 or not BUG.fullmatch(pos[1]): die("Usage: cycle.sh fixed <MODULE> BUG-<n> --by <you> [--note \"build 1.4.2\"]")
    human("marking a bug fixed")
    module = pos[0].upper(); c = need_cycle(module)
    append(module, c, [{"At": now(), "By": signed(o.get("by")), "Action": "fixed", "ID": "", "Result": "", "Bug": pos[1], "Note": text(o.get("note", ""))}])
    import report  # the register says Fixed too (the same as bug.sh status ... Fixed); here, not at the top: report imports this file
    rows = report.read_csv(report.BUG_FILE, report.BUG_COLS)
    for r in rows:
        if r["ID"] == pos[1] and r["Module"].upper() == module and r["Status"] == "Open":
            r.update({"Status": "Fixed", "Updated By": signed(o.get("by")), "Updated At": now(), "Note": text(o.get("note", "")) or r["Note"]})
            report.write_csv(report.BUG_FILE, report.BUG_COLS, rows)
    n = [x["ID"] for x in status(module)["cases"] if x["bug"] == pos[1]]
    print(f"FIXED {module} {c['id']}: {pos[1]}; retest {', '.join(n) or 'its cases'} (retest.sh <kind> {module}; cases by hand: record them again)")


def cmd_quarantine(a, on=True):
    pos, o = opts(a, ("--reason", "--by"))
    if len(pos) != 2 or (on and not o.get("reason")): die(f"Usage: cycle.sh {'quarantine' if on else 'unquarantine'} <MODULE> <TC-ID> {'--reason \"why\" ' if on else ''}--by <you>")
    human("quarantine")
    module = pos[0].upper(); c = need_cycle(module); check_case(module, [pos[1]], manual=False)
    append(module, c, [{"At": now(), "By": signed(o.get("by")), "Action": "quarantine" if on else "unquarantine", "ID": pos[1], "Result": "", "Bug": "",
                        "Note": text(o.get("reason", ""))}])
    print(f"{'QUARANTINED' if on else 'RELEASED'} {module} {c['id']}: {pos[1]}" + (": it still runs, but does not block the cycle" if on else ""))


def retest_ids(module, kind):
    s = status(module)
    if not s: return []
    return [c["ID"] for c in s["cases"] if c["kind"] == kind and (c["retest"] or (c["result"] == "failed" and not c["quarantine"]))]


def cmd_retest(a):
    if len(a) != 2 or a[0] not in ("web", "api", "mobile"): die("Usage: retest.sh web|api|mobile <MODULE>")
    print(",".join(retest_ids(a[1].upper(), a[0])))


def cmd_status(a):
    if len(a) != 1: die("Usage: cycle.sh status <MODULE>")
    module = a[0].upper(); s = status(module)
    if not s: die(f"No test cycle for {module} yet.", 0)
    c, cs = s["cycle"], s["cases"]
    count = ", ".join(f"{k} {n}" for k in ("passed", "known-bug", "failed", "blocked", "not-run") if (n := sum(1 for x in cs if x["result"] == k)))
    print(f"CYCLE {module} {c['id']} \"{c['name']}\" on {c['env'] or 'the default .env'} (since {c['started_at']}, {len(s['runs'])} runs): {count}")
    for x in cs:
        if x["result"] != "passed" or x["flaky"] or x["quarantine"]:
            print(f"  {x['ID']:<16} {x['kind']:<7} {x['result']:<9} {x['bug']:<14} {'flaky ' if x['flaky'] else ''}{'quarantined ' if x['quarantine'] else ''}"
                  f"{'retest ' if x['retest'] else ''}{''.join(x['history'])}")


def cmd_check(a):
    module = next((x.upper() for x in a if not x.startswith("--")), None)
    if not module: die("Usage: cycle.sh check <MODULE> [--for-approval]")
    err, warn = problems(module, "--for-approval" in a)
    for w in warn: print("  warning: " + w)
    if err: print(f"EXECUTION NOT OK (module {module}):\n" + "\n".join("- " + e for e in err[:40]) + (f"\n- … {len(err) - 40} more" if len(err) > 40 else "")); sys.exit(1)
    print(f"EXECUTION OK (module {module}): cycle {current(module)['id']}")


def cmd_baseline(a):
    if len(a) < 2: die("Usage: execute.py baseline <MODULE> <approved-by>")
    module, by = a[0].upper(), a[1]
    s = status(module) or {"cycle": {}, "cases": [], "runs": []}
    base = os.path.join(DIR, "baseline", module); os.makedirs(base, exist_ok=True)
    v = f"v{max((int(d[1:]) for d in os.listdir(base) if re.fullmatch(r'v\d+', d)), default=0) + 1}"
    os.makedirs(os.path.join(base, v))
    try: commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    except OSError: commit = ""
    automate.write_json(os.path.join(base, v, "meta.json"), {"module": module, "version": v, "approved_by": by, "approved_at": now(), "git_commit": commit,
        "cycle": s["cycle"], "runs": s["runs"], "contract": s.get("contract"),
        "cases": {c["ID"]: {k: c[k] for k in ("kind", "result", "bug", "flaky") if c[k]} | ({"quarantine": c["quarantine"]["reason"]} if c["quarantine"] else {}) for c in s["cases"]}})
    print(f"EXECUTION BASELINE {module} {v}: cycle {s['cycle'].get('id')}, {len(s['cases'])} cases, {len(s['runs'])} runs -> {os.path.join(base, v).replace(os.sep, '/')}")


COMMANDS = {"start": cmd_start, "status": cmd_status, "result": cmd_result, "bug": cmd_bug, "fixed": cmd_fixed, "quarantine": cmd_quarantine,
            "unquarantine": lambda a: cmd_quarantine(a, False), "retest": cmd_retest, "check": cmd_check, "baseline": cmd_baseline}
if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS: die("Usage: execute.py " + "|".join(COMMANDS) + " ...")
    COMMANDS[sys.argv[1]](sys.argv[2:])
