"""TestHive module archive: moves everything of one module out of the project into archive/<MODULE>-<time>/ and back.
Nothing is deleted. Called by scripts/stage.sh (archive, restore), which also moves the module's stage state and logs the decision.
  python modules.py archive <MODULE> <archive-dir> <by> <why>   move the module's files and register rows; writes ARCHIVE.json
  python modules.py restore <archive-dir>                       put them back (refused if any of it exists again)
  python modules.py fingerprint <archive-dir>                   SHA-256 of the folder, logged when archived, checked on restore
  python modules.py list                                         archived modules, as JSON
An archive folder holds files/<original path> and rows/<register path> (the module's rows of the shared registers)."""
import sys, os, re, json, glob, shutil, time, hashlib, fnmatch
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analysis, design
from analysis import read_csv, write_csv, die

ARCHIVE = os.environ.get("TH_ARCHIVE", "archive")
NAME = re.compile(r"[A-Z][A-Z0-9]*-\d{8}-\d{6}")  # SIGNUP-20261022-153000


def registers():
    """The shared registers: one row per item, with a Module column."""
    return [(analysis.REQ_FILE, analysis.REQ_COLS), (analysis.GAP_FILE, analysis.GAP_COLS),
            (design.CASE_FILE, design.CASE_COLS), (design.ASK_FILE, design.ASK_COLS)]


def owned(m):
    """Files and folders that belong to module m only (the ones that exist)."""
    return sorted(p for p in fixed_paths(m) + glob.glob(os.path.join("reviews", f"*-{m}-[0-9]*.md"))
                  + glob.glob(os.path.join("runs", "agents", f"[0-9]*-[0-9]*-{m}-*")) if os.path.exists(p))


def fixed_paths(m):
    return [os.path.join("requirements", "sources", m), os.path.join("requirements", "modules", f"{m}.json"),
            os.path.join("requirements", "apps", m), os.path.join(analysis.DIR, "sources-text", m),
            os.path.join(analysis.DIR, "exploration", m), os.path.join(analysis.DIR, "baseline", m),
            os.path.join(design.TC_DIR, "baseline", m), os.path.join(analysis.DIR, f"{m}-analysis.xlsx"),
            os.path.join(design.TC_DIR, f"{m}-design.xlsx")]


def belongs(p, m):
    """Is p (as written in ARCHIVE.json) a path that owned(m) could have produced? Nothing outside, nothing of another module."""
    if os.path.isabs(p) or ":" in p or ".." in p.replace("\\", "/").split("/"): return False
    p = os.path.normpath(p)
    return (p in {os.path.normpath(x) for x in fixed_paths(m)}
            or fnmatch.fnmatchcase(p, os.path.join("reviews", f"*-{m}-[0-9]*.md"))
            or fnmatch.fnmatchcase(p, os.path.join("runs", "agents", f"[0-9]*-[0-9]*-{m}-*")) and os.sep not in p[len(os.path.join("runs", "agents")) + 1:])


def mine(row, m): return row["Module"].upper() == m


def move_all(pairs):
    """Moves each (source, target); if one fails, moves the earlier ones back and raises. All or nothing."""
    done = []
    try:
        for src, dst in pairs:
            os.makedirs(os.path.dirname(dst) or ".", exist_ok=True); shutil.move(src, dst); done.append((src, dst))
    except OSError:
        for src, dst in reversed(done): shutil.move(dst, src)
        raise


def fingerprint(dest):
    """SHA-256 over every file of an archive folder (names and contents): written in the approvals log when it is archived,
    checked before it is restored, so a folder changed or planted later is refused."""
    h = hashlib.sha256()
    for p in sorted(glob.glob(os.path.join(dest, "**", "*"), recursive=True)):
        if os.path.isfile(p):
            h.update(os.path.relpath(p, dest).replace(os.sep, "/").encode() + b"\0")
            with open(p, "rb") as f:
                for chunk in iter(lambda: f.read(1 << 20), b""): h.update(chunk)
    return h.hexdigest()[:24]


def archive(m, dest, by, why):
    if os.path.exists(dest): die(f"{dest} already exists")
    files, counts, plan = owned(m), {}, []
    for path, cols in registers():
        rows = read_csv(path, cols)
        keep = [r for r in rows if mine(r, m)]
        if keep: plan.append((path, cols, rows, keep))
    os.makedirs(dest)
    try: move_all([(p, os.path.join(dest, "files", p)) for p in files])  # files first: undone if one is locked (a workbook open in Excel)
    except OSError as e:
        shutil.rmtree(dest, ignore_errors=True); die(f"Not archived: {e.filename or ''} could not be moved ({e.strerror}). Close it and try again.")
    for path, cols, rows, keep in plan:  # then the rows: copied out first, then removed from the shared register
        out = os.path.join(dest, "rows", path)
        os.makedirs(os.path.dirname(out), exist_ok=True); write_csv(out, cols, keep)
        write_csv(path, cols, [r for r in rows if not mine(r, m)])
        counts[path.replace(os.sep, "/")] = len(keep)
    meta = {"module": m, "archived_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "by": by, "why": why,
            "files": [p.replace(os.sep, "/") for p in files], "rows": counts}
    with open(os.path.join(dest, "ARCHIVE.json"), "w", encoding="utf-8", newline="\n") as f: json.dump(meta, f, indent=2, ensure_ascii=False)
    print(f"ARCHIVED {m} -> {dest.replace(os.sep, '/')}/: {len(files)} files or folders, " +
          (", ".join(f"{n} rows of {p}" for p, n in counts.items()) or "no register rows"))


def logged(m, dest):
    """True if the approvals log has an Archived line for this module and folder with this folder's fingerprint."""
    log = os.path.join(os.path.dirname(os.environ.get("TH_STATE", "workflow/state.json")) or ".", "APPROVALS.md")
    if not os.path.exists(log): return False
    fp, name = fingerprint(dest), os.path.basename(os.path.normpath(dest))
    with open(log, encoding="utf-8") as f:
        return any(f"| {m} | - | Archived |" in line and name in line and fp in line for line in f)


def restore(dest):
    name = os.path.basename(os.path.normpath(dest))
    try:
        with open(os.path.join(dest, "ARCHIVE.json"), encoding="utf-8") as f: meta = json.load(f)
        m, files, counts = meta["module"], meta["files"], meta["rows"]
    except (OSError, ValueError, KeyError, TypeError): die(f"Not restored: {dest}/ARCHIVE.json is missing or damaged.")
    if not NAME.fullmatch(name) or name.rsplit("-", 2)[0] != m: die(f"Not restored: {name} does not hold module {m}.")
    bad = [p for p in files if not isinstance(p, str) or not belongs(p, m)]
    if bad: die(f"Not restored: the archive lists files that are not {m}'s: {', '.join(map(str, bad[:3]))}")
    if not logged(m, dest): die(f"Not restored: {name} is not the folder that was archived (its fingerprint is not in the approvals log).")
    back = [p for p in files if os.path.exists(p)]
    if back: die(f"Not restored: {', '.join(back)} exists again. Move it away first.")
    plan = []
    for path, cols in registers():
        src = os.path.join(dest, "rows", path)
        if not os.path.exists(src): continue
        rows, extra = read_csv(path, cols), read_csv(src, cols)
        clash = sorted({r["ID"] for r in rows} & {r["ID"] for r in extra})
        if clash: die(f"Not restored: {path} already has {', '.join(clash[:5])}.")
        if any(not mine(r, m) for r in extra): die(f"Not restored: {src} holds rows of another module.")
        plan.append((path, cols, rows + extra))
    try: move_all([(os.path.join(dest, "files", p), p) for p in files])  # files first, undone on failure; the registers last
    except OSError as e: die(f"Not restored: {e.filename or ''} could not be moved ({e.strerror}). Nothing was changed.")
    for path, cols, rows in plan:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True); write_csv(path, cols, rows)
    done = os.path.join(ARCHIVE, "_restored", name)  # the record of the archive stays
    os.makedirs(os.path.dirname(done), exist_ok=True); shutil.move(dest, done)
    print(f"RESTORED {m} from {dest.replace(os.sep, '/')}/ ({len(files)} files or folders, {sum(counts.values())} register rows)")


def listing():
    out = []
    for p in sorted(glob.glob(os.path.join(ARCHIVE, "*", "ARCHIVE.json")), reverse=True):
        name = os.path.basename(os.path.dirname(p))
        if not NAME.fullmatch(name): continue
        try:
            with open(p, encoding="utf-8") as f: meta = json.load(f)
            out.append({"name": name, "module": meta["module"], "archived_at": meta["archived_at"], "by": meta.get("by", ""),
                        "why": meta.get("why", ""), "rows": sum(meta["rows"].values()), "files": len(meta["files"])})
        except (OSError, ValueError, KeyError, TypeError, AttributeError): continue  # a damaged entry never hides the others
    return out


def main():
    a = sys.argv[1:]
    if os.environ.get("TH_JOB") and a[:1] in (["archive"], ["restore"]): die("BLOCKED: archive and restore are human decisions", 2)
    if a[:1] == ["archive"] and len(a) == 5: archive(a[1].upper(), a[2], a[3], a[4])
    elif a[:1] == ["restore"] and len(a) == 2: restore(a[1])
    elif a[:1] == ["fingerprint"] and len(a) == 2: print(fingerprint(a[1]))
    elif a[:1] == ["list"]: print(json.dumps(listing(), indent=2, ensure_ascii=False))
    else: die(__doc__)


if __name__ == "__main__":
    main()
