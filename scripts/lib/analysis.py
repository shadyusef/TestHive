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


def stage_status(module, stage):
    """The stage's status in workflow/state.json (TH_STATE), '' if the module or the file is unknown."""
    p = os.environ.get("TH_STATE", "workflow/state.json")
    if not os.path.exists(p): return ""
    with open(p, encoding="utf-8") as f: m = json.load(f).get("modules", {}).get(module.upper())
    return m["stages"][stage]["status"] if m else ""


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


def add_sheet(ws, cols, rows, widths, editable=()):
    """Header row, data rows, widths; wraps text, right-aligns Arabic, colours the human's columns yellow."""
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill
    head, edit = PatternFill("solid", fgColor="284A8C"), PatternFill("solid", fgColor="FFF4CC")
    ws.append(cols)
    for c in ws[1]: c.font, c.fill = Font(bold=True, color="FFFFFF"), head
    for r in rows: ws.append(r)
    for i, w in enumerate(widths, 1): ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w
    for row in ws.iter_rows(min_row=2):
        for c in row:
            rtl = isinstance(c.value, str) and bool(ARABIC.search(c.value))
            c.alignment = Alignment(wrap_text=True, vertical="top", horizontal="right" if rtl else "left", readingOrder=2 if rtl else 1)
            if cols[c.column - 1] in editable: c.fill = edit
            if isinstance(c.value, str) and c.value.startswith("="): c.data_type = "s"  # text, not an Excel formula
    ws.freeze_panes = "A2"; ws.auto_filter.ref = ws.dimensions


PACK = "_pack"  # hidden sheet: the editable values when the workbook was made


def add_pack(wb, cols, rows):
    """Keeps the editable values as they are now, so the import can tell what the reviewer changed (a review pack may come back late)."""
    ws = wb.create_sheet(PACK); ws.sheet_state = "hidden"; ws.append(cols)
    for r in rows: ws.append(r)


def reviewer_changes(wb, table, current, cols):
    """The rows of table the reviewer changed, and conflicts: rows changed in the workbook and also in TestHive since it was made.
    Rows the reviewer left as they were are dropped, so a late workbook never undoes newer work. Without a pack sheet (older
    workbooks) every row counts, as before. current: {ID: row now in the CSV}."""
    if PACK not in wb.sheetnames: return table, [], 0
    rows = list(wb[PACK].iter_rows(values_only=True))
    if not rows: return table, [], 0  # a damaged snapshot: treat it as an older workbook
    head = [str(h or "") for h in rows[0]]
    snap = {str(r[0]): {h: "" if v is None else str(v).strip() for h, v in zip(head, r)} for r in rows[1:] if r and r[0]}
    out, conflicts, same = [], [], 0
    for n, row in table:
        orig = snap.get(row.get("ID", ""))
        if orig is None: out.append((n, row)); continue  # a new row, or an ID the workbook did not have
        if all(row.get(c, "") == orig.get(c, "") for c in cols): same += 1; continue
        now = current.get(row["ID"])
        if now and any((now.get(c) or "").strip() != orig.get(c, "") for c in cols):
            conflicts.append(f"{n} ({row['ID']}): changed in this workbook and also in TestHive after the workbook was made"); continue
        out.append((n, row))
    return out, conflicts, same


def dropdown(ws, col, values, last=1000):
    from openpyxl.worksheet.datavalidation import DataValidation
    dv = DataValidation(type="list", formula1='"' + ",".join(values) + '"', allow_blank=True)
    ws.add_data_validation(dv); dv.add(f"{col}2:{col}{last}")


def cmd_workbook(a):
    import openpyxl
    from openpyxl.styles import Font
    if not a: die("Usage: analysis-workbook.sh <MODULE> [out.xlsx]")
    module = a[0].upper()
    out = a[1] if len(a) > 1 else os.path.join(DIR, f"{module}-analysis.xlsx")
    reqs = [r for r in read_csv(REQ_FILE, REQ_COLS) if r["Module"].upper() == module]
    gaps = [g for g in read_csv(GAP_FILE, GAP_COLS) if g["Module"].upper() == module]
    if not reqs and not gaps: die(f"No requirements or gaps for {module} in {DIR}/")
    req_text = {r["ID"]: r["Text"] for r in read_csv(REQ_FILE, REQ_COLS)}
    wb = openpyxl.Workbook()
    sheet = add_sheet
    ws = wb.active; ws.title = "Cover"
    open_high = sum(1 for g in gaps if g["Severity"] == "High" and g["Status"] != "Closed")
    for row in [("TestHive analysis workbook", ""), ("Module", module), ("Created", time.strftime("%Y-%m-%d %H:%M")),
                ("Requirements", len(reqs)), ("Gaps", len(gaps)), ("Open gaps", sum(1 for g in gaps if g["Status"] == "Open")),
                ("High gaps not closed", open_high), ("", ""),
                ("How to answer", "Go to the 'Gaps' sheet. Fill the yellow columns: Answer, Answered By (your name), Status (set Answered)."),
                ("", "To add a question of your own, add a row with an empty ID and fill Question, Kind and Severity."),
                ("", "Save the file and send it back to the person who sent it. They upload it in TestHive Studio (Analysis tab, 'upload a filled one')."),
                ("", "Only the rows you change are taken; answers others gave meanwhile stay. Do not change IDs or the sheet names.")]:
        ws.append(row)
    ws["A1"].font = Font(bold=True, size=14); ws.column_dimensions["A"].width = 24; ws.column_dimensions["B"].width = 100
    sheet(wb.create_sheet("Gaps"), ["ID", "Requirement", "Requirement text", "Kind", "Severity", "Question", "Answer", "Answered By", "Status"],
          [[g["ID"], g["Requirement"], " | ".join(req_text.get(x, "") for x in refs(g["Requirement"])), g["Kind"], g["Severity"],
            g["Question"], g["Answer"], g["Answered By"], g["Status"]] for g in gaps],
          [16, 18, 45, 12, 10, 55, 45, 16, 11], editable=("Answer", "Answered By", "Status"))
    for col, values in (("I", GAP_STATUS), ("D", GAP_KINDS), ("E", SEVERITY)): dropdown(wb["Gaps"], col, values)
    sheet(wb.create_sheet("Requirements"), REQ_COLS[:1] + REQ_COLS[2:], [[r[c] for c in REQ_COLS if c != "Module"] for r in reqs],
          [16, 30, 10, 60, 14, 9, 8, 11, 30])
    src_idx = os.path.join(DIR, "sources-text", module, "index.csv")
    src_rows = []
    if os.path.exists(src_idx):
        with open(src_idx, encoding="utf-8-sig", newline="") as f: src_rows = [list(r.values()) for r in csv.DictReader(f)]
    sheet(wb.create_sheet("Sources"), ["Source", "Type", "Read from", "Words", "Masked"], src_rows, [45, 10, 55, 8, 8])
    add_pack(wb, ["ID"] + PACK_GAP, [[g["ID"]] + [g[c] for c in PACK_GAP] for g in gaps])
    wb.save(out)
    print(f"WORKBOOK {out.replace(os.sep, '/')}: {len(reqs)} requirements, {len(gaps)} gaps ({open_high} High not closed)")


def apply_answers(module, rows):
    """Applies the human's answers and new questions to gaps.csv, all or nothing. rows: [(label, {column: value})] with
    ID, Answer, Answered By, Status (and Question, Kind, Severity, Requirement for a new question with an empty ID).
    Used by the Excel import and by TestHive Studio. Returns (changed, added, errors); nothing is written if errors."""
    if stage_status(module, "analysis") == "approved":  # the approved analysis is a frozen baseline: a change starts with a reopen
        return 0, 0, [f"The analysis of {module} is approved, so its questions and answers are read-only. "
                      "To change them, reopen the analysis (Approvals) and say why."]
    gaps = read_csv(GAP_FILE, GAP_COLS)
    by_id = {g["ID"]: g for g in gaps}
    nums = [int(g["ID"].rsplit("-", 1)[1]) for g in gaps if re.fullmatch(rf"GAP-{module}-\d{{3}}", g["ID"])]
    changed, added, errors = 0, 0, []
    for n, v in rows:
        val = lambda h: str(v.get(h) or "").strip()
        gid, status = val("ID"), val("Status") or "Open"
        answer, by = val("Answer"), val("Answered By")
        if status not in GAP_STATUS: errors.append(f"{n}: Status '{status}' must be Open, Answered or Closed"); continue
        if answer and status == "Open": status = "Answered"
        if status == "Answered" and not answer: errors.append(f"{n} ({gid or 'new'}): Status Answered but Answer is empty"); continue
        if status == "Answered" and not by: errors.append(f"{n} ({gid or 'new'}): Answered By is empty"); continue
        if not gid:
            q = val("Question")
            if not q: continue
            kind, sev = val("Kind") or "Missing", val("Severity") or "Medium"
            if kind not in GAP_KINDS or sev not in SEVERITY: errors.append(f"{n}: new question needs Kind ({', '.join(GAP_KINDS)}) and Severity (High/Medium/Low)"); continue
            nums.append(max(nums, default=0) + 1)
            gaps.append({"ID": f"GAP-{module}-{nums[-1]:03d}", "Module": module, "Requirement": val("Requirement"), "Kind": kind,
                         "Severity": sev, "Question": q, "Answer": answer, "Answered By": by, "Status": status}); added += 1; continue
        g = by_id.get(gid)
        if g is None or g["Module"].upper() != module: errors.append(f"{n}: {gid} is not a gap of {module}"); continue
        if (g["Answer"], g["Answered By"], g["Status"]) != (answer, by, status):
            if g["Status"] == "Closed" and status != "Closed": errors.append(f"{n}: {gid} is Closed; reopen it with the analyst"); continue
            g["Answer"], g["Answered By"], g["Status"] = answer, by, status; changed += 1
    if not errors: write_csv(GAP_FILE, GAP_COLS, gaps)
    return changed, added, errors


PACK_GAP = ["Answer", "Answered By", "Status"]  # what a reviewer edits on the Gaps sheet


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
    table = [(f"row {n}", {h: ("" if row[i] is None else str(row[i]).strip()) for i, h in enumerate(head) if h})
             for n, row in enumerate(rows[1:], 2) if any(row)]
    table, conflicts, same = reviewer_changes(wb, table, {g["ID"]: g for g in read_csv(GAP_FILE, GAP_COLS)}, PACK_GAP)
    if conflicts: die("IMPORT REFUSED, nothing changed:\n" + "\n".join("- " + e for e in conflicts) +
                      "\nCompare those rows with Studio, then delete those rows from the workbook (or make them match Studio) and upload again.")
    changed, added, errors = apply_answers(module, table)
    if errors: die("IMPORT REFUSED, nothing changed:\n" + "\n".join("- " + e for e in errors))
    print(f"IMPORTED {path.replace(os.sep, '/')}: {changed} gaps updated, {added} new questions added"
          f"{f', {same} rows you did not change left as they are' if same else ''}. Next: the analyst reviews the answers.")


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
