"""TestHive analysis registers: check, Excel workbook, import answers, score against a key, baseline.
Called by scripts/check-analysis.sh, analysis-workbook.sh, import-answers.sh, score-analysis.sh and stage.sh.
Formats: docs/FORMATS.md (requirements and gap registers)."""
import sys, os, re, csv, json, time, shutil

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
DIR = os.environ.get("TH_ANALYSIS", "analysis")
REQ_FILE, GAP_FILE = os.path.join(DIR, "requirements.csv"), os.path.join(DIR, "gaps.csv")
REQ_COLS = ["ID", "Module", "Source", "Section", "Text", "Type", "Priority", "Version", "Status", "Notes"]
GAP_COLS = ["ID", "Module", "Requirement", "Kind", "Severity", "Question", "Answer", "Answered By", "Status"]
REQ_TYPES = ["Functional", "Business rule", "UI", "API", "Non-functional"]
REQ_STATUS = ["Draft", "Observed", "Confirmed", "Changed", "Removed"]
GAP_KINDS = ["Missing", "Ambiguous", "Conflict", "Untestable", "To confirm"]
SEVERITY = ["High", "Medium", "Low"]
GAP_STATUS = ["Open", "Answered", "Closed"]
ARABIC = re.compile(r"[؀-ۿ]")


def die(m, code=1): print(m); sys.exit(code)


def read_csv(path, cols):
    if not os.path.exists(path): return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return [{c: (r.get(c) or "").strip() for c in cols} for r in rows]


def write_csv(path, cols, rows):
    with open(path + ".tmp", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, cols, lineterminator="\n"); w.writeheader(); w.writerows(rows)
    os.replace(path + ".tmp", path)


def refs(cell): return [x.strip() for x in re.split(r"[;,]", cell or "") if x.strip()]


def problems(module=None, for_approval=False):
    """Returns (errors, warnings) for the registers, limited to one module if given."""
    reqs, gaps = read_csv(REQ_FILE, REQ_COLS), read_csv(GAP_FILE, GAP_COLS)
    err, warn = [], []
    if module:
        reqs = [r for r in reqs if r["Module"].upper() == module]
        gaps = [g for g in gaps if g["Module"].upper() == module]
    all_req_ids = {r["ID"] for r in read_csv(REQ_FILE, REQ_COLS)}
    seen = set()
    for r in reqs:
        i = r["ID"] or "?"
        m = re.fullmatch(r"REQ-([A-Z0-9]+)-\d{3}", i)
        if not m: err.append(f"{i}: ID must look like REQ-<MODULE>-001")
        elif m.group(1) != r["Module"].upper(): err.append(f"{i}: ID module does not match Module column ({r['Module']})")
        if i in seen: err.append(f"{i}: duplicate ID")
        seen.add(i)
        for c in ("Module", "Source", "Text", "Type", "Priority", "Version", "Status"):
            if not r[c]: err.append(f"{i}: empty {c}")
        if r["Type"] and r["Type"] not in REQ_TYPES: err.append(f"{i}: Type must be one of {', '.join(REQ_TYPES)}")
        if r["Status"] and r["Status"] not in REQ_STATUS: err.append(f"{i}: Status must be one of {', '.join(REQ_STATUS)}")
        if r["Priority"] and not re.fullmatch(r"P[0-3]", r["Priority"]): err.append(f"{i}: Priority must be P0-P3")
        if r["Version"] and not r["Version"].isdigit(): err.append(f"{i}: Version must be a number")
    gseen = set()
    for g in gaps:
        i = g["ID"] or "?"
        m = re.fullmatch(r"GAP-([A-Z0-9]+)-\d{3}", i)
        if not m: err.append(f"{i}: ID must look like GAP-<MODULE>-001")
        elif m.group(1) != g["Module"].upper(): err.append(f"{i}: ID module does not match Module column ({g['Module']})")
        if i in gseen: err.append(f"{i}: duplicate ID")
        gseen.add(i)
        for c in ("Module", "Kind", "Severity", "Question", "Status"):
            if not g[c]: err.append(f"{i}: empty {c}")
        if g["Kind"] and g["Kind"] not in GAP_KINDS: err.append(f"{i}: Kind must be one of {', '.join(GAP_KINDS)}")
        if g["Severity"] and g["Severity"] not in SEVERITY: err.append(f"{i}: Severity must be High, Medium or Low")
        if g["Status"] and g["Status"] not in GAP_STATUS: err.append(f"{i}: Status must be Open, Answered or Closed")
        for ref in refs(g["Requirement"]):
            if ref not in all_req_ids: err.append(f"{i}: points to {ref}, which is not in requirements.csv")
        if g["Kind"] == "Conflict" and len(refs(g["Requirement"])) < 1: warn.append(f"{i}: a conflict should name the requirements involved")
        if g["Status"] in ("Answered", "Closed") and not g["Answer"]: err.append(f"{i}: {g['Status']} but no Answer")
        if g["Status"] == "Answered" and not g["Answered By"]: err.append(f"{i}: Answered but no Answered By")
    for r in reqs:
        if r["Status"] == "Observed" and not any(r["ID"] in refs(g["Requirement"]) and g["Kind"] == "To confirm" for g in gaps):
            err.append(f"{r['ID']}: Observed requirement needs a 'To confirm' gap so a human confirms it")
    if for_approval:
        carried = []
        for g in gaps:
            if g["Severity"] == "High" and g["Status"] != "Closed": err.append(f"{g['ID']}: High gap is {g['Status']}; it must be Closed before approval")
            elif g["Status"] == "Answered": err.append(f"{g['ID']}: answered but not reviewed; the analyst must close it or ask again")
            elif g["Status"] == "Open": carried.append(g["ID"])
        for r in reqs:
            if r["Status"] == "Observed": err.append(f"{r['ID']}: still Observed; confirm or remove it before approval")
        if carried: warn.append(f"{len(carried)} Medium/Low gaps still open (allowed, carried into test design): {', '.join(carried)}")
        if not reqs: err.append(f"no requirements for module {module}")
    return err, warn, reqs, gaps


def cmd_check(a):
    module = next((x.upper() for x in a if not x.startswith("--")), None)
    err, warn, reqs, gaps = problems(module, "--for-approval" in a)
    scope = f"module {module}" if module else "all modules"
    for w in warn: print("  warning: " + w)
    if err:
        print(f"ANALYSIS NOT OK ({scope})\n" + "\n".join("- " + e for e in err)); sys.exit(1)
    open_g = sum(1 for g in gaps if g["Status"] == "Open")
    count = lambda rows, col, values: ", ".join(f"{v} {n}" for v in values if (n := sum(1 for r in rows if r[col] == v)))
    print(f"ANALYSIS OK ({scope}): {len(reqs)} requirements, {len(gaps)} gaps ({open_g} open)")
    if reqs: print(f"  requirements by status: {count(reqs, 'Status', REQ_STATUS)}")
    if gaps:
        print(f"  gaps by kind: {count(gaps, 'Kind', GAP_KINDS)}")
        print(f"  gaps by severity: {count(gaps, 'Severity', SEVERITY)}; by status: {count(gaps, 'Status', GAP_STATUS)}")


def cmd_workbook(a):
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.worksheet.datavalidation import DataValidation
    if not a: die("Usage: analysis-workbook.sh <MODULE> [out.xlsx]")
    module = a[0].upper()
    out = a[1] if len(a) > 1 else os.path.join(DIR, f"{module}-analysis.xlsx")
    reqs = [r for r in read_csv(REQ_FILE, REQ_COLS) if r["Module"].upper() == module]
    gaps = [g for g in read_csv(GAP_FILE, GAP_COLS) if g["Module"].upper() == module]
    if not reqs and not gaps: die(f"No requirements or gaps for {module} in {DIR}/")
    req_text = {r["ID"]: r["Text"] for r in read_csv(REQ_FILE, REQ_COLS)}
    head, edit = PatternFill("solid", fgColor="284A8C"), PatternFill("solid", fgColor="FFF4CC")
    wb = openpyxl.Workbook()

    def sheet(ws, cols, rows, widths, editable=()):
        ws.append(cols)
        for c in ws[1]: c.font, c.fill = Font(bold=True, color="FFFFFF"), head
        for r in rows: ws.append(r)
        for i, w in enumerate(widths, 1): ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w
        for row in ws.iter_rows(min_row=2):
            for c in row:
                rtl = isinstance(c.value, str) and bool(ARABIC.search(c.value))
                c.alignment = Alignment(wrap_text=True, vertical="top", horizontal="right" if rtl else "left", readingOrder=2 if rtl else 1)
                if cols[c.column - 1] in editable: c.fill = edit
        ws.freeze_panes = "A2"; ws.auto_filter.ref = ws.dimensions

    ws = wb.active; ws.title = "Cover"
    open_high = sum(1 for g in gaps if g["Severity"] == "High" and g["Status"] != "Closed")
    for row in [("TestHive analysis workbook", ""), ("Module", module), ("Created", time.strftime("%Y-%m-%d %H:%M")),
                ("Requirements", len(reqs)), ("Gaps", len(gaps)), ("Open gaps", sum(1 for g in gaps if g["Status"] == "Open")),
                ("High gaps not closed", open_high), ("", ""),
                ("How to answer", "Go to the 'Gaps' sheet. Fill the yellow columns: Answer, Answered By, Status (set Answered)."),
                ("", "To add a question of your own, add a row with an empty ID and fill Question, Kind and Severity."),
                ("", "Save the file, then run: import-answers " + module + " (TestHive reads your answers back)."),
                ("", "Do not change IDs or the sheet names.")]:
        ws.append(row)
    ws["A1"].font = Font(bold=True, size=14); ws.column_dimensions["A"].width = 24; ws.column_dimensions["B"].width = 100
    sheet(wb.create_sheet("Gaps"), ["ID", "Requirement", "Requirement text", "Kind", "Severity", "Question", "Answer", "Answered By", "Status"],
          [[g["ID"], g["Requirement"], " | ".join(req_text.get(x, "") for x in refs(g["Requirement"])), g["Kind"], g["Severity"],
            g["Question"], g["Answer"], g["Answered By"], g["Status"]] for g in gaps],
          [16, 18, 45, 12, 10, 55, 45, 16, 11], editable=("Answer", "Answered By", "Status"))
    gs = wb["Gaps"]
    for col, values in (("I", GAP_STATUS), ("D", GAP_KINDS), ("E", SEVERITY)):
        dv = DataValidation(type="list", formula1='"' + ",".join(values) + '"', allow_blank=True)
        gs.add_data_validation(dv); dv.add(f"{col}2:{col}1000")
    sheet(wb.create_sheet("Requirements"), REQ_COLS[:1] + REQ_COLS[2:], [[r[c] for c in REQ_COLS if c != "Module"] for r in reqs],
          [16, 30, 10, 60, 14, 9, 8, 11, 30])
    src_idx = os.path.join(DIR, "sources-text", module, "index.csv")
    src_rows = []
    if os.path.exists(src_idx):
        with open(src_idx, encoding="utf-8-sig", newline="") as f: src_rows = [list(r.values()) for r in csv.DictReader(f)]
    sheet(wb.create_sheet("Sources"), ["Source", "Type", "Read from", "Words", "Masked"], src_rows, [45, 10, 55, 8, 8])
    wb.save(out)
    print(f"WORKBOOK {out.replace(os.sep, '/')}: {len(reqs)} requirements, {len(gaps)} gaps ({open_high} High not closed)")


def cmd_import(a):
    import openpyxl
    if not a: die("Usage: import-answers.sh <MODULE> [workbook.xlsx]")
    module = a[0].upper()
    path = a[1] if len(a) > 1 else os.path.join(DIR, f"{module}-analysis.xlsx")
    if not os.path.exists(path): die(f"Workbook not found: {path}. Create it with analysis-workbook {module}.")
    wb = openpyxl.load_workbook(path, data_only=True)
    if "Gaps" not in wb.sheetnames: die("The workbook has no 'Gaps' sheet. Do not rename sheets.")
    rows = list(wb["Gaps"].iter_rows(values_only=True))
    head = [str(h or "").strip() for h in rows[0]]
    need = ["ID", "Question", "Answer", "Answered By", "Status"]
    if any(h not in head for h in need): die("The 'Gaps' sheet is missing a column: " + ", ".join(h for h in need if h not in head))
    col = {h: head.index(h) for h in head}
    val = lambda row, h: ("" if h not in col or row[col[h]] is None else str(row[col[h]]).strip())
    gaps = read_csv(GAP_FILE, GAP_COLS)
    by_id = {g["ID"]: g for g in gaps}
    nums = [int(g["ID"].rsplit("-", 1)[1]) for g in gaps if re.fullmatch(rf"GAP-{module}-\d{{3}}", g["ID"])]
    changed, added, errors = 0, 0, []
    for n, row in enumerate(rows[1:], 2):
        if not any(row): continue
        gid, status = val(row, "ID"), val(row, "Status") or "Open"
        answer, by = val(row, "Answer"), val(row, "Answered By")
        if status not in GAP_STATUS: errors.append(f"row {n}: Status '{status}' must be Open, Answered or Closed"); continue
        if answer and status == "Open": status = "Answered"
        if status == "Answered" and not answer: errors.append(f"row {n} ({gid or 'new'}): Status Answered but Answer is empty"); continue
        if status == "Answered" and not by: errors.append(f"row {n} ({gid or 'new'}): Answered By is empty"); continue
        if not gid:
            q = val(row, "Question")
            if not q: continue
            kind, sev = val(row, "Kind") or "Missing", val(row, "Severity") or "Medium"
            if kind not in GAP_KINDS or sev not in SEVERITY: errors.append(f"row {n}: new question needs Kind ({', '.join(GAP_KINDS)}) and Severity (High/Medium/Low)"); continue
            nums.append(max(nums, default=0) + 1)
            g = {"ID": f"GAP-{module}-{nums[-1]:03d}", "Module": module, "Requirement": val(row, "Requirement"), "Kind": kind,
                 "Severity": sev, "Question": q, "Answer": answer, "Answered By": by, "Status": status}
            gaps.append(g); added += 1; continue
        g = by_id.get(gid)
        if g is None or g["Module"].upper() != module: errors.append(f"row {n}: {gid} is not a gap of {module}"); continue
        if (g["Answer"], g["Answered By"], g["Status"]) != (answer, by, status):
            if g["Status"] == "Closed" and status != "Closed": errors.append(f"row {n}: {gid} is Closed; reopen it with the analyst, not in Excel"); continue
            g["Answer"], g["Answered By"], g["Status"] = answer, by, status; changed += 1
    if errors: die("IMPORT REFUSED, nothing changed:\n" + "\n".join("- " + e for e in errors))
    write_csv(GAP_FILE, GAP_COLS, gaps)
    print(f"IMPORTED {path.replace(os.sep, '/')}: {changed} gaps updated, {added} new questions added. Next: the analyst reviews the answers.")


def cmd_score(a):
    if len(a) < 2: die("Usage: score-analysis.sh <MODULE> <answer-key.csv>")
    module, key_path = a[0].upper(), a[1]
    reqs = {r["ID"]: r for r in read_csv(REQ_FILE, REQ_COLS)}
    gaps = [g for g in read_csv(GAP_FILE, GAP_COLS) if g["Module"].upper() == module]
    with open(key_path, encoding="utf-8-sig", newline="") as f: keys = list(csv.DictReader(f))
    def text(g): return (g["Kind"] + " " + g["Question"]).lower()  # the question itself; linked requirement text adds noise
    def has(t, alt):  # alternative must start a word: "lock" matches "locked", not "blocked"
        return re.search(r"(?<![a-z0-9])" + re.escape(alt.strip().lower()), t) is not None
    def hits(k, g):  # every ';' group must match at least one '|' alternative
        t = text(g)
        return all(any(has(t, alt) for alt in grp.split("|")) for grp in k["Keywords"].split(";"))
    def strength(k, g): return sum(has(text(g), alt) for grp in k["Keywords"].split(";") for alt in grp.split("|"))
    cand = {k["Key"]: sorted((i for i, g in enumerate(gaps) if hits(k, g)), key=lambda i: -strength(k, gaps[i])) for k in keys}
    match = {}  # gap index -> key: one gap counts for one planted gap at most (bipartite matching)
    def assign(key, seen):
        for gi in cand[key]:
            if gi in seen: continue
            seen.add(gi)
            if gi not in match or assign(match[gi], seen): match[gi] = key; return True
        return False
    for k in keys: assign(k["Key"], set())
    found = set(match.values())
    n = len(keys)
    print(f"SCORE {module}: found {len(found)} of {n} planted gaps ({100 * len(found) // max(n, 1)}%); analyst raised {len(gaps)} gaps in total")
    for k in keys:
        gi = next((gi for gi, kk in match.items() if kk == k["Key"]), None)
        print(f"  {'FOUND ' if k['Key'] in found else 'MISSED'} {k['Key']} {k['Gap']}")
        if gi is not None: print(f"         <- {gaps[gi]['ID']}: {gaps[gi]['Question'][:140]}")
    extra = len(gaps) - len(match)
    if extra: print(f"  {extra} other gaps raised (not in the key; may still be valid: read them)")
    target = int(os.environ.get("TH_SCORE_TARGET", "80"))
    sys.exit(0 if 100 * len(found) >= target * n else 1)


def cmd_baseline(a):
    if len(a) < 2: die("Usage: analysis.py baseline <MODULE> <approved-by>")
    module, by = a[0].upper(), a[1]
    reqs = [r for r in read_csv(REQ_FILE, REQ_COLS) if r["Module"].upper() == module]
    gaps = [g for g in read_csv(GAP_FILE, GAP_COLS) if g["Module"].upper() == module]
    base = os.path.join(DIR, "baseline", module)
    os.makedirs(base, exist_ok=True)
    nums = [int(d[1:]) for d in os.listdir(base) if re.fullmatch(r"v\d+", d)]
    v = f"v{max(nums, default=0) + 1}"
    out = os.path.join(base, v); os.makedirs(out)
    write_csv(os.path.join(out, "requirements.csv"), REQ_COLS, reqs)
    write_csv(os.path.join(out, "gaps.csv"), GAP_COLS, gaps)
    with open(os.path.join(out, "meta.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump({"module": module, "version": v, "approved_by": by, "approved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "requirements": len(reqs), "gaps": len(gaps)}, f, indent=2, ensure_ascii=False)
    print(f"BASELINE {module} {v}: {len(reqs)} requirements, {len(gaps)} gaps -> {out.replace(os.sep, '/')}")


COMMANDS = {"check": cmd_check, "workbook": cmd_workbook, "import": cmd_import, "score": cmd_score, "baseline": cmd_baseline}
if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS: die("Usage: analysis.py " + "|".join(COMMANDS) + " ...")
    COMMANDS[sys.argv[1]](sys.argv[2:])
