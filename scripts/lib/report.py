"""TestHive reporting (stage 6): the bug register (reports/bugs.csv), the HTML report of a module's approved test cycle (one
self-contained file to share or print), the Go / No-go decision signed by a person, the check before approval and the baseline.
Called by scripts/bug.sh, report.sh, stage.sh (check --for-approval, baseline) and Studio. Formats: docs/FORMATS.md (reporting)."""
import sys, os, re, csv, json, glob, html, base64, hashlib, time, shutil, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analysis import read_csv, write_csv, die, stage_status, refs
import analysis, design, tools, automate, execute
from pyrun import lib_cmd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
DIR = os.environ.get("TH_REPORTING", "reporting")
BUG_FILE = os.path.join("reports", "bugs.csv")
BUG_COLS = ["ID", "Module", "Title", "Severity", "Status", "Cases", "Cycle", "Env", "Target", "Steps", "Expected", "Actual", "Evidence",
            "Reported By", "Reported At", "Updated By", "Updated At", "Note", "External"]
SEVERITY, STATUS = ("Blocker", "Major", "Minor"), ("Open", "Fixed", "Verified", "Won't fix")
HIGH = ("P0", "P1")  # case priorities a failure of blocks a Go
STAGE_OF = {"business-analyst": "analysis", "manual-tester": "design", "qa-reviewer": "design", "web-automation-engineer": "automation",
            "api-backend-test-engineer": "automation", "mobile-automation-engineer": "automation", "test-data-env-manager": "automation",
            "defect-triage": "execution", "testhive-lead": "lead"}
EVIDENCE = re.compile(r"(R-\d{8}-\d{2,})/(evidence/[A-Za-z0-9._/ -]{1,200})")
MAX_IMAGE = 300_000  # bytes of a failure screenshot embedded in the report; larger ones stay links


def now(): return execute.now()
text = execute.text


def latest(folder):
    """(version, folder) of the newest v<n> in folder, or (None, None)."""
    vs = sorted(int(d[1:]) for d in os.listdir(folder) if re.fullmatch(r"v\d+", d)) if os.path.isdir(folder) else []
    return (f"v{vs[-1]}", os.path.join(folder, f"v{vs[-1]}")) if vs else (None, None)


def read_json(p, default=None):
    try:
        with open(p, encoding="utf-8") as f: return json.load(f)
    except (OSError, ValueError): return default


def bugs(module=None):
    rows = read_csv(BUG_FILE, BUG_COLS)
    return [b for b in rows if module is None or b["Module"].upper() == module]


def bug_problems(module):
    """Rows of the register that break its rules (an agent may write the file directly)."""
    out, seen = [], set()
    out += [f"{b['ID'] or '(no ID)'}: no Module" for b in read_csv(BUG_FILE, BUG_COLS) if not b["Module"] and b["ID"].startswith(f"BUG-{module}-")]
    for b in bugs(module):
        if not re.fullmatch(rf"BUG-{module}-\d{{3,}}", b["ID"]): out.append(f"{b['ID'] or '(no ID)'}: the ID must be BUG-{module}-<NNN>")
        if b["ID"] in seen: out.append(f"{b['ID']}: the ID is used twice")
        seen.add(b["ID"])
        if b["Severity"] not in SEVERITY: out.append(f"{b['ID']}: Severity must be one of {', '.join(SEVERITY)}")
        if b["Status"] not in STATUS: out.append(f"{b['ID']}: Status must be one of {', '.join(STATUS)}")
        if not b["Title"]: out.append(f"{b['ID']}: no title")
        if not refs(b["Cases"]): out.append(f"{b['ID']}: no case")
        if b["Status"] != "Open" and not b["Updated By"]: out.append(f"{b['ID']}: {b['Status']} without the name of who changed it")
        if any(v[:1] in ("=", "+", "-", "@") for v in b.values()): out.append(f"{b['ID']}: a cell starts with = + - or @ (Excel would read a formula)")
    return out


def frozen(module): return stage_status(module, "execution") in ("approved", "awaiting_approval")


def opts(a, names): return execute.opts(a, names)


def cmd_bug_add(a):
    pos, o = opts(a, ("--title", "--severity", "--cases", "--steps", "--expected", "--actual", "--evidence", "--target", "--by"))
    if len(pos) != 1 or not o.get("title") or o.get("severity") not in SEVERITY or not o.get("cases"):
        die('Usage: bug.sh add <MODULE> --title "..." --severity Blocker|Major|Minor --cases TC-X-001[,...] [--steps --expected --actual "..."] [--evidence R-<run>/evidence/<file>] [--target <name>] --by <name>')
    module, by = pos[0].upper(), execute.signed(o.get("by"))
    if not execute.MODULE.fullmatch(module): die("Module code: letters and digits only")
    b = tools.design_baseline(module)
    known = {c["ID"] for c in (b[1] if b else []) if design.active(c)}
    cases = refs(o["cases"])
    bad = [c for c in cases if c not in known]
    if bad: die(f"Not active cases of the approved design of {module}: {', '.join(bad)}")
    ev = o.get("evidence", "")
    if ev and not EVIDENCE.fullmatch(ev): die("--evidence: R-<yyyymmdd>-<nn>/evidence/<file> (a file kept with a run)")
    rows = read_csv(BUG_FILE, BUG_COLS)
    n = max((int(r["ID"].rsplit("-", 1)[1]) for r in rows if re.fullmatch(rf"BUG-{module}-\d+", r["ID"])), default=0) + 1
    c = execute.current(module) or {}
    bid = f"BUG-{module}-{n:03d}"
    rows.append({"ID": bid, "Module": module, "Title": text(o["title"]), "Severity": o["severity"], "Status": "Open", "Cases": "; ".join(cases),
                 "Cycle": c.get("id", ""), "Env": c.get("env", ""), "Target": re.sub(r"[^a-z0-9._-]", "", o.get("target", ""))[:40],
                 "Steps": text(o.get("steps", "")), "Expected": text(o.get("expected", "")), "Actual": text(o.get("actual", "")), "Evidence": ev,
                 "Reported By": by, "Reported At": now(), "Updated By": "", "Updated At": "", "Note": "", "External": ""})
    os.makedirs(os.path.dirname(BUG_FILE), exist_ok=True); write_csv(BUG_FILE, BUG_COLS, rows)
    linked = []
    if c and not frozen(module) and not os.environ.get("TH_JOB"):  # a person reports it: the cycle's failed automated tests get the bug too
        auto = {x["ID"] for x in execute.scope(module) if x["kind"] != "manual"}
        ln = [{"At": now(), "By": by, "Action": "bug", "ID": i, "Result": "", "Bug": bid, "Note": ""} for i in cases if i in auto]
        if ln: execute.append(module, c, ln); linked = [r["ID"] for r in ln]
    print(f"BUG {bid} ({o['severity']}): {text(o['title'])}" + (f"; linked in cycle {c['id']} to {', '.join(linked)}" if linked else ""))


def cmd_bug_status(a):
    pos, o = opts(a, ("--by", "--note"))
    if len(pos) != 3 or pos[2] not in STATUS: die("Usage: bug.sh status <MODULE> BUG-<MODULE>-<NNN> Open|Fixed|Verified|\"Won't fix\" --by <you> [--note \"...\"]")
    execute.human("changing a bug's status")
    module, bid, st, by = pos[0].upper(), pos[1], pos[2], execute.signed(o.get("by"))
    rows = read_csv(BUG_FILE, BUG_COLS)
    row = next((r for r in rows if r["ID"] == bid and r["Module"].upper() == module), None)
    if not row: die(f"No bug {bid} in {BUG_FILE} for {module}")
    row.update({"Status": st, "Updated By": by, "Updated At": now(), "Note": text(o.get("note", "")) or row["Note"]})
    write_csv(BUG_FILE, BUG_COLS, rows)
    c = execute.current(module)
    if st == "Fixed" and c and not frozen(module):
        execute.append(module, c, [{"At": now(), "By": by, "Action": "fixed", "ID": "", "Result": "", "Bug": bid, "Note": text(o.get("note", ""))}])
        print(f"BUG {bid}: Fixed by {by}; its cases are due for a retest in cycle {c['id']}")
    else: print(f"BUG {bid}: {st} by {by}")


def cmd_bug_list(a):
    if len(a) != 1: die("Usage: bug.sh list <MODULE>")
    module = a[0].upper()
    for b in bugs(module): print(f"{b['ID']:<16} {b['Severity']:<8} {b['Status']:<10} {b['Cases']:<30} {b['Title']}")
    for p in bug_problems(module): print("  problem: " + p)


# ---------- the report ----------

def gather(module):
    """Everything the report shows, from the approved test cycle (execution baseline), the design, the requirements and the register."""
    ev, ed = latest(os.path.join(execute.DIR, "baseline", module))
    if not ev: return None
    meta = read_json(os.path.join(ed, "meta.json"), {})
    dv = tools.design_baseline(module)
    cases = {c["ID"]: c for c in (dv[1] if dv else [])}
    av, ad = latest(os.path.join(analysis.DIR, "baseline", module))
    reqs = read_csv(os.path.join(ad, "requirements.csv"), analysis.REQ_COLS) if ad else []
    rows = []
    for i, r in meta.get("cases", {}).items():
        c = cases.get(i, {})
        rows.append({"ID": i, "Title": c.get("Title", ""), "Priority": c.get("Priority", ""), "Type": c.get("Type", ""), "Requirements": refs(c.get("Requirements", "")),
                     "kind": r.get("kind", ""), "result": r.get("result", ""), "bug": r.get("bug", ""), "flaky": r.get("flaky", False), "quarantine": r.get("quarantine", "")})
    bs = bugs(module)
    open_ = [b for b in bs if b["Status"] in ("Open",)]
    sev = {s: [b for b in open_ if b["Severity"] == s] for s in SEVERITY}
    high_cases = {r["ID"] for r in rows if r["Priority"] in HIGH}
    nogo = [f"{b['ID']} (Blocker) is open: {b['Title']}" for b in sev["Blocker"]]
    nogo += [f"{b['ID']} (Major) is open on a {'/'.join(HIGH)} case: {b['Title']}" for b in sev["Major"] if set(refs(b["Cases"])) & high_cases]
    nogo += [f"{r['ID']} ({r['Priority']}) {'failed' if r['result'] == 'failed' else 'fails on a known bug'}: {r['Title']}" for r in rows if r["Priority"] in HIGH and r["result"] in ("failed", "known-bug")]
    nogo += [f"{r['ID']} was not run" for r in rows if r["result"] == "not-run"]
    risks = [f"{r['ID']} is quarantined: {r['quarantine']}" for r in rows if r["quarantine"]] + [f"{r['ID']} was blocked" for r in rows if r["result"] == "blocked"]
    risks += [f"{b['ID']} ({b['Severity']}) is open: {b['Title']}" for b in sev["Major"] + sev["Minor"] if not any(b["ID"] in n for n in nogo)]
    risks += [f"contract: {f['endpoint']} fails on {f['bug']}" for f in (meta.get("contract") or {}).get("failed", []) if f.get("bug")]
    cover = []
    for q in reqs:
        if q["Status"] == "Removed": continue
        cs = [r for r in rows if q["ID"] in r["Requirements"]]
        state = "not covered" if not cs else "failing" if any(r["result"] in ("failed", "known-bug") for r in cs) else \
                "partly run" if any(r["result"] in ("blocked", "not-run") for r in cs) else "passed"
        cover.append({"ID": q["ID"], "Text": q["Text"], "Priority": q["Priority"], "cases": [r["ID"] for r in cs], "state": state})
    trend = []
    for n in sorted(execute.cycles(module)):
        c = read_json(os.path.join(execute.DIR, module, f"C{n}", "cycle.json"))
        s = execute.status(module, c) if c else None
        if s: trend.append({"cycle": c["id"], "name": c["name"], "cases": len(s["cases"]), "passed": sum(1 for x in s["cases"] if x["result"] == "passed")})
    runs = []
    for d in sorted(glob.glob(os.path.join(os.environ.get("TH_RUNS", "runs"), "R-*", "meta.json"))):
        m = read_json(d, {})
        if m.get("module") == module and m.get("kind") in ("web", "api", "mobile", "contract"):
            t = m.get("totals", {}); runs.append({"run": m.get("run_id"), "at": m.get("collected_at", ""), "kind": m["kind"], "passed": t.get("passed", 0), "total": t.get("total", 0)})
    cost = {}
    for d in glob.glob(os.path.join("runs", "agents", "*", "meta.json")):
        j = read_json(d, {})
        if j.get("module") == module and j.get("cost_usd") is not None:
            k = STAGE_OF.get(j.get("agent", ""), "other"); cost.setdefault(k, [0.0, 0]); cost[k][0] += float(j["cost_usd"]); cost[k][1] += 1
    shots = {}
    for r in rows:
        if r["result"] not in ("failed", "known-bug"): continue
        for rid in meta.get("runs", []):
            res = read_json(os.path.join(os.environ.get("TH_RUNS", "runs"), rid, "results.json"), {})
            for x in res.get("cases", []):
                if x.get("id") == r["ID"] and x.get("status") != "passed":
                    for e in x.get("evidence", []):
                        top = os.path.realpath(os.path.join(os.environ.get("TH_RUNS", "runs"), rid, "evidence")) + os.sep
                        p = os.path.realpath(os.path.join(os.environ.get("TH_RUNS", "runs"), rid, e))
                        if p.startswith(top) and e.lower().endswith(".png") and os.path.isfile(p) and os.path.getsize(p) <= MAX_IMAGE and r["ID"] not in shots:
                            with open(p, "rb") as f: shots[r["ID"]] = (f"{rid}/{e}", base64.b64encode(f.read()).decode())
    suggestion = "No-go" if nogo else "Go with risks" if risks else "Go"
    return {"module": module, "execution": ev, "meta": meta, "design": dv[0] if dv else "", "analysis": av or "", "cases": rows, "bugs": bs, "nogo": nogo,
            "risks": risks, "suggestion": suggestion, "cover": cover, "trend": trend, "runs": runs, "cost": cost, "shots": shots,
            "decision": read_json(os.path.join(DIR, module, "decision.json")), "bugs_sha": sha_file(BUG_FILE)}


def sha_file(p):
    try:
        with open(p, "rb") as f: return hashlib.sha256(f.read()).hexdigest()
    except OSError: return ""


def report_path(module): return os.path.join("reports", f"{module}-report.html")


# The report's one script (the case filter). Only it may run: the CSP names it by its hash, here and where Studio serves the file.
SCRIPT = """const q=document.getElementById('q'),r=document.getElementById('r');function f(){const t=q.value.toLowerCase();document.querySelectorAll('#cases tbody tr').forEach(x=>{x.hidden=(r.value&&x.dataset.r!==r.value)||(t&&!x.textContent.toLowerCase().includes(t))})}q.oninput=f;r.onchange=f;"""
CSP = ("default-src 'none'; img-src data:; style-src 'unsafe-inline'; form-action 'none'; base-uri 'none'; script-src 'sha256-"
       + base64.b64encode(hashlib.sha256(SCRIPT.encode()).digest()).decode() + "'")


def built_path(module): return os.path.join(DIR, module, "built.json")  # the report's checksum, where agents cannot write


def bars(points, label):
    """A small inline bar chart (SVG) of pass rates: [(name, passed, total)]."""
    if not points: return '<p class="muted">No data yet.</p>'
    w, h = max(240, 44 * len(points)), 150
    top = 16  # room for the 100% label above a full bar
    out = [f'<svg viewBox="0 0 {w} {h + top + 34}" width="{w}" height="{h + top + 34}" role="img" aria-label="{html.escape(label)}">']
    for i, (n, p, t) in enumerate(points):
        rate = p / t if t else 0; bh = round(rate * h); x = 10 + i * 44
        out.append(f'<rect x="{x}" y="{top + h - bh}" width="30" height="{bh}" class="bar"><title>{html.escape(n)}: {p}/{t}</title></rect>'
                   f'<text x="{x + 15}" y="{top + h - bh - 4}" text-anchor="middle" class="v">{round(rate * 100)}%</text>'
                   f'<text x="{x + 15}" y="{top + h + 16}" text-anchor="middle" class="l">{html.escape(n[:7])}</text>')
    return "".join(out) + "</svg>"


def build_html(d):
    e = lambda v: html.escape(str(v if v is not None else ""))
    c, cs, m = d["meta"].get("cycle", {}), d["cases"], d["meta"]
    n = lambda r: sum(1 for x in cs if x["result"] == r)
    open_ = [b for b in d["bugs"] if b["Status"] == "Open"]
    kpi = [("Cases", len(cs)), ("Passed", f"{n('passed')} ({round(100 * n('passed') / len(cs)) if cs else 0}%)"), ("Failed", n("failed") + n("known-bug")),
           ("Blocked", n("blocked")), ("Quarantined", sum(1 for x in cs if x["quarantine"])),
           ("Open bugs", " / ".join(f"{sum(1 for b in open_ if b['Severity'] == s)} {s}" for s in SEVERITY))]
    dec = d["decision"]
    tone = {"Go": "ok", "Go with risks": "warn", "No-go": "bad"}[d["suggestion"]]
    rows = "".join(f'<tr data-r="{e(x["result"])}"><td class="id">{e(x["ID"])}</td><td>{e(x["Priority"])}</td><td>{e(x["Title"])}'
                   + (f'<details><summary>failure screenshot</summary><img alt="Screenshot of {e(x["ID"])}" src="data:image/png;base64,{d["shots"][x["ID"]][1]}"><div class="muted">{e(d["shots"][x["ID"]][0])}</div></details>' if x["ID"] in d["shots"] else "")
                   + f'</td><td>{e(x["kind"])}</td><td><span class="pill {e(x["result"])}">{e(x["result"])}</span>{" flaky" if x["flaky"] else ""}{" quarantined" if x["quarantine"] else ""}</td>'
                   f'<td>{e(x["bug"])}</td><td>{e(", ".join(x["Requirements"]))}</td></tr>' for x in cs)
    bugrows = "".join(f'<tr><td class="id">{e(b["ID"])}</td><td>{e(b["Severity"])}</td><td>{e(b["Status"])}</td><td>{e(b["Title"])}<div class="muted">'
                      f'{e(b["Steps"])}{" · expected: " + e(b["Expected"]) if b["Expected"] else ""}{" · actual: " + e(b["Actual"]) if b["Actual"] else ""}</div></td>'
                      f'<td>{e(b["Cases"])}</td><td>{e(b["Cycle"])} {e(b["Env"])} {e(b["Target"])}</td><td class="muted">{e(b["Evidence"])}</td></tr>' for b in d["bugs"])
    cover = "".join(f'<tr><td class="id">{e(q["ID"])}</td><td>{e(q["Priority"])}</td><td>{e(q["Text"])}</td><td>{e(", ".join(q["cases"]))}</td>'
                    f'<td><span class="pill {e(q["state"]).replace(" ", "-")}">{e(q["state"])}</span></td></tr>' for q in d["cover"])
    cost = "".join(f'<tr><td>{e(k)}</td><td>{v[1]}</td><td>${v[0]:.2f}</td></tr>' for k, v in sorted(d["cost"].items())) or '<tr><td colspan="3" class="muted">No agent runs with a cost recorded.</td></tr>'
    built = {"module": d["module"], "execution": d["execution"], "bugs_sha": d["bugs_sha"], "built_at": now(), "suggestion": d["suggestion"]}
    style = """:root{--bg:#fff;--fg:#1d1d1f;--muted:#5b5b66;--line:#ddd;--ok:#1e7a3c;--warn:#9a6700;--bad:#b3261e;--card:#f6f6f8}
@media (prefers-color-scheme:dark){:root{--bg:#141416;--fg:#ececf0;--muted:#a3a3ad;--line:#33333a;--ok:#5cc27e;--warn:#e0b04a;--bad:#ff7a70;--card:#1d1d21}}
body{background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif;margin:0 auto;max-width:1100px;padding:24px 16px}h1{font-size:26px;margin:0}h2{font-size:18px;margin:32px 0 8px}
.muted{color:var(--muted);font-size:13px}.kpi{display:flex;flex-wrap:wrap;gap:8px;margin:16px 0}.kpi div{background:var(--card);padding:10px 14px;border-radius:8px;min-width:120px}.kpi b{display:block;font-size:20px}
.decision{border-left:6px solid var(--muted);background:var(--card);padding:12px 16px;border-radius:6px}.decision.ok{border-color:var(--ok)}.decision.warn{border-color:var(--warn)}.decision.bad{border-color:var(--bad)}
table{border-collapse:collapse;width:100%;font-size:14px}th,td{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}.id{white-space:nowrap;font-family:ui-monospace,monospace;font-size:13px}
.wrap{overflow-x:auto}td.muted{word-break:break-all;max-width:260px}.pill{padding:1px 8px;border-radius:10px;background:var(--card);white-space:nowrap}.pill.passed{color:var(--ok)}.pill.failed,.pill.known-bug,.pill.failing,.pill.not-covered{color:var(--bad)}.pill.blocked,.pill.partly-run{color:var(--warn)}
svg .bar{fill:var(--ok)}svg text{fill:var(--fg);font-size:11px}img{max-width:100%;border:1px solid var(--line);margin-top:6px}
input,select{font:inherit;padding:4px 8px;background:var(--bg);color:var(--fg);border:1px solid var(--line);border-radius:6px}@media print{details{display:none}input,select{display:none}}"""
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="{CSP}">
<title>{e(d['module'])} test report</title><style>{style}</style></head><body>
<!-- testhive-report {json.dumps(built)} -->
<p class="muted">TestHive test report · built {e(built['built_at'])} UTC from the approved test cycle (execution baseline {e(d['execution'])}, design {e(d['design'])}, requirements {e(d['analysis'])})</p>
<h1>{e(d['module'])}: cycle {e(c.get('id'))} "{e(c.get('name'))}" on {e(c.get('env') or 'the default environment')}</h1>
<p class="muted">Cycle started {e(c.get('started_at'))} by {e(c.get('started_by'))}; results approved by {e(m.get('approved_by'))} on {e(m.get('approved_at'))}; {len(m.get('runs', []))} runs.</p>
<div class="decision {tone}"><b>TestHive suggests: {e(d['suggestion'])}</b>
{('<p>Why not:</p><ul>' + ''.join(f'<li>{e(x)}</li>' for x in d['nogo']) + '</ul>') if d['nogo'] else ''}
{('<p>Risks to accept:</p><ul>' + ''.join(f'<li>{e(x)}</li>' for x in d['risks']) + '</ul>') if d['risks'] else ''}
{f"<p><b>Decision: {e(dec['decision'])}</b> by {e(dec['by'])} on {e(dec['at'])}: {e(dec['reason'])}</p>" if dec else '<p class="muted">No decision recorded yet: a named person decides Go or No-go.</p>'}</div>
<div class="kpi">{''.join(f'<div><span class="muted">{e(k)}</span><b>{e(v)}</b></div>' for k, v in kpi)}</div>
<h2>Trend</h2><div class="wrap">{bars([(t['cycle'], t['passed'], t['cases']) for t in d['trend']], 'Pass rate per cycle')}</div>
<p class="muted">Pass rate per test cycle. Runs of this module: {len(d['runs'])}.</p><div class="wrap">{bars([(x['run'][-5:], x['passed'], x['total']) for x in d['runs'][-20:]], 'Pass rate per run')}</div>
<h2>Bugs ({len(d['bugs'])})</h2><div class="wrap"><table><thead><tr><th>ID</th><th>Severity</th><th>Status</th><th>Bug</th><th>Cases</th><th>Found in</th><th>Evidence</th></tr></thead><tbody>{bugrows or '<tr><td colspan="7" class="muted">No bugs reported.</td></tr>'}</tbody></table></div>
<h2>Requirements</h2><div class="wrap"><table><thead><tr><th>ID</th><th>P</th><th>Requirement</th><th>Cases</th><th>State</th></tr></thead><tbody>{cover or '<tr><td colspan="5" class="muted">No approved requirements.</td></tr>'}</tbody></table></div>
<h2>Cases ({len(cs)})</h2><p><input id="q" placeholder="Search" aria-label="Search the cases"> <select id="r" aria-label="Result"><option value="">every result</option>{''.join(f'<option>{x}</option>' for x in ('passed', 'failed', 'known-bug', 'blocked', 'not-run'))}</select></p>
<div class="wrap"><table id="cases"><thead><tr><th>ID</th><th>P</th><th>Case</th><th>Run</th><th>Result</th><th>Bug</th><th>Requirements</th></tr></thead><tbody>{rows}</tbody></table></div>
<h2>Cost of the agents</h2><div class="wrap"><table><thead><tr><th>Stage</th><th>Agent runs</th><th>Cost (as reported by Claude Code)</th></tr></thead><tbody>{cost}</tbody></table></div>
<p class="muted">Evidence (videos, traces, API logs) stays in runs/ on the PC that ran the tests; screenshots of failures are embedded above.</p>
<script>{SCRIPT}</script></body></html>""", built


def report_meta(p, module=None):
    """The report's header, or None when it is missing, unreadable, or not the file report.py wrote (its checksum in reporting/<M>/built.json)."""
    try:
        with open(p, encoding="utf-8") as f: head = f.read(20000)
        m = re.search(r"<!-- testhive-report (\{.*?\}) -->", head)
        meta = json.loads(m[1]) if m else None
    except (OSError, ValueError): return None
    if not isinstance(meta, dict) or not all(isinstance(meta.get(k), str) for k in ("module", "execution", "bugs_sha", "built_at", "suggestion")): return None
    b = read_json(built_path(module or meta["module"]), {})
    return meta if b.get("sha") == sha_file(p) else None


def cmd_build(a):
    if len(a) != 1: die("Usage: report.sh <MODULE>")
    module = a[0].upper()
    if not execute.MODULE.fullmatch(module): die("Module code: letters and digits only")
    if stage_status(module, "execution") != "approved": die(f"BLOCKED: the execution of {module} is not approved yet: the report is built from the approved test cycle", 2)
    d = gather(module)
    page, built = build_html(d)
    os.makedirs("reports", exist_ok=True)
    with open(report_path(module) + ".tmp", "w", encoding="utf-8", newline="\n") as f: f.write(page)
    os.replace(report_path(module) + ".tmp", report_path(module))
    os.makedirs(os.path.join(DIR, module), exist_ok=True)
    automate.write_json(built_path(module), {"sha": sha_file(report_path(module)), "built_at": built["built_at"]})
    if stage_status(module, "reporting") == "pending": subprocess.run(lib_cmd("stage.py", "start", module, "reporting"))
    print(f"REPORT {module}: {report_path(module).replace(os.sep, '/')} (TestHive suggests {d['suggestion']}; {len(d['nogo'])} reasons against, {len(d['risks'])} risks)")


def cmd_decide(a):
    pos, o = opts(a, ("--reason", "--by"))
    if len(pos) != 2 or pos[1] not in ("Go", "No-go") or not o.get("reason"): die('Usage: report.sh decide <MODULE> Go|No-go --reason "..." --by <you>')
    execute.human("the release decision")
    module, by = pos[0].upper(), execute.signed(o.get("by"))
    if not execute.MODULE.fullmatch(module): die("Module code: letters and digits only")
    if stage_status(module, "reporting") in ("approved", "awaiting_approval"): die(f"BLOCKED: the reporting of {module} is {stage_status(module, 'reporting').replace('_', ' ')}: reopen or reject it to change the decision", 2)
    rm = report_meta(report_path(module), module)
    if not rm: die(f"Build the report first: report.sh {module}")
    if (rm["execution"], rm["bugs_sha"]) != (latest(os.path.join(execute.DIR, "baseline", module))[0], sha_file(BUG_FILE)):
        die(f"BLOCKED: the report is older than the approved cycle or the bug register: build it again (report.sh {module}), then decide", 2)
    if pos[1] == "Go" and any(b["Severity"] == "Blocker" and b["Status"] == "Open" for b in bugs(module)): die("BLOCKED: Go with an open Blocker bug: fix it or decide No-go", 2)
    os.makedirs(os.path.join(DIR, module), exist_ok=True)
    automate.write_json(os.path.join(DIR, module, "decision.json"), {"decision": pos[1], "reason": text(o["reason"]), "by": by, "at": now(),
                        "execution": rm["execution"], "bugs_sha": rm["bugs_sha"], "suggestion": rm["suggestion"]})  # what it was decided on
    if subprocess.run(lib_cmd("report.py", "build", module), capture_output=True).returncode: die("The decision is recorded, but the report could not be built again: run report.sh")  # the report shows it
    print(f"DECISION {module}: {pos[1]} by {by}")


def problems(module, for_approval=False):
    err, warn = [], []
    if stage_status(module, "execution") != "approved": return [f"the execution of {module} is not approved yet"], []
    err += bug_problems(module)
    rm, ev = report_meta(report_path(module), module), latest(os.path.join(execute.DIR, "baseline", module))[0]
    if not rm: err.append(f"no report yet (or not the one report.sh built): report.sh {module}")
    elif rm["execution"] != ev or rm["bugs_sha"] != sha_file(BUG_FILE): err.append("the report is older than the approved cycle or the bug register: build it again")
    dec = read_json(os.path.join(DIR, module, "decision.json"))
    if not dec: err.append("no Go / No-go decision yet: report.sh decide (or the Reports tab)")
    elif (dec.get("execution"), dec.get("bugs_sha")) != (ev, sha_file(BUG_FILE)): err.append("the cycle or the bugs changed since the decision: decide again")
    if dec and dec["decision"] == "Go" and any(b["Severity"] == "Blocker" and b["Status"] == "Open" for b in bugs(module)): err.append("Go with an open Blocker bug")
    if rm and dec and dec["decision"] == "Go" and rm.get("suggestion") == "No-go": warn.append("Go although TestHive suggests No-go: the reason is in the decision")
    warn += [f"{b['ID']} ({b['Severity']}) is still open" for b in bugs(module) if b["Status"] == "Open"]
    return err, warn


def cmd_check(a):
    module = next((x.upper() for x in a if not x.startswith("--")), None)
    if not module: die("Usage: report.sh check <MODULE> [--for-approval]")
    err, warn = problems(module, "--for-approval" in a)
    for w in warn: print("  warning: " + w)
    if err: print(f"REPORTING NOT OK (module {module}):\n" + "\n".join("- " + x for x in err)); sys.exit(1)
    print(f"REPORTING OK (module {module})")


def cmd_baseline(a):
    if len(a) < 2: die("Usage: report.py baseline <MODULE> <approved-by>")
    module, by = a[0].upper(), a[1]
    base = os.path.join(DIR, "baseline", module); os.makedirs(base, exist_ok=True)
    v = f"v{max((int(x[1:]) for x in os.listdir(base) if re.fullmatch(r'v\d+', x)), default=0) + 1}"
    out = os.path.join(base, v); os.makedirs(out)
    shutil.copyfile(report_path(module), os.path.join(out, "report.html"))
    shutil.copyfile(BUG_FILE, os.path.join(out, "bugs.csv")) if os.path.exists(BUG_FILE) else None
    automate.write_json(os.path.join(out, "meta.json"), {"module": module, "version": v, "approved_by": by, "approved_at": now(),
        "decision": read_json(os.path.join(DIR, module, "decision.json")), "report": report_meta(report_path(module), module),
        "files": {f: sha_file(os.path.join(out, f)) for f in ("report.html", "bugs.csv") if os.path.exists(os.path.join(out, f))}})
    print(f"REPORTING BASELINE {module} {v}: the report and the bug register -> {out.replace(os.sep, '/')}")


COMMANDS = {"bug-add": cmd_bug_add, "bug-status": cmd_bug_status, "bug-list": cmd_bug_list, "build": cmd_build, "decide": cmd_decide,
            "check": cmd_check, "baseline": cmd_baseline}
if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS: die("Usage: report.py " + "|".join(COMMANDS) + " ...")
    COMMANDS[sys.argv[1]](sys.argv[2:])
