"""TestHive module archive: moves everything of one module out of the project into archive/<MODULE>-<time>/ and back.
Nothing is deleted. Called by scripts/stage.sh (archive, restore), which also moves the module's stage state and logs the decision.
  python modules.py archive <MODULE> <archive-dir> <by> <why>   move the module's files and register rows; writes ARCHIVE.json
  python modules.py restore <archive-dir>                       put them back (refused if any of it exists again)
  python modules.py list                                         archived modules, as JSON
An archive folder holds files/<original path> and rows/<register path> (the module's rows of the shared registers)."""
import sys, os, re, json, glob, shutil, time
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
    paths = [os.path.join("requirements", "sources", m), os.path.join("requirements", "modules", f"{m}.json"),
             os.path.join("requirements", "apps", m), os.path.join(analysis.DIR, "sources-text", m),
             os.path.join(analysis.DIR, "exploration", m), os.path.join(analysis.DIR, "baseline", m),
             os.path.join(design.TC_DIR, "baseline", m), os.path.join(analysis.DIR, f"{m}-analysis.xlsx"),
             os.path.join(design.TC_DIR, f"{m}-design.xlsx")]
    paths += glob.glob(os.path.join("reviews", f"*-{m}-*")) + glob.glob(os.path.join("runs", "agents", f"*-{m}-*"))
    return sorted(p for p in paths if os.path.exists(p))


def mine(row, m): return row["Module"].upper() == m


def archive(m, dest, by, why):
    if os.path.exists(dest): die(f"{dest} already exists")
    files, counts = owned(m), {}
    os.makedirs(dest)
    for path, cols in registers():  # rows first: they are copied out before anything is moved
        rows = read_csv(path, cols)
        keep = [r for r in rows if mine(r, m)]
        if not keep: continue
        out = os.path.join(dest, "rows", path)
        os.makedirs(os.path.dirname(out), exist_ok=True); write_csv(out, cols, keep)
        write_csv(path, cols, [r for r in rows if not mine(r, m)])
        counts[path.replace(os.sep, "/")] = len(keep)
    for p in files:
        target = os.path.join(dest, "files", p)
        os.makedirs(os.path.dirname(target), exist_ok=True); shutil.move(p, target)
    meta = {"module": m, "archived_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "by": by, "why": why,
            "files": [p.replace(os.sep, "/") for p in files], "rows": counts}
    with open(os.path.join(dest, "ARCHIVE.json"), "w", encoding="utf-8", newline="\n") as f: json.dump(meta, f, indent=2, ensure_ascii=False)
    print(f"ARCHIVED {m} -> {dest.replace(os.sep, '/')}/: {len(files)} files or folders, " +
          (", ".join(f"{n} rows of {p}" for p, n in counts.items()) or "no register rows"))


def restore(dest):
    with open(os.path.join(dest, "ARCHIVE.json"), encoding="utf-8") as f: meta = json.load(f)
    m = meta["module"]
    back = [p for p in meta["files"] if os.path.exists(p)]
    if back: die(f"Not restored: {', '.join(back)} exists again. Move it away first.")
    plan = []
    for path, cols in registers():
        src = os.path.join(dest, "rows", path)
        if not os.path.exists(src): continue
        rows, extra = read_csv(path, cols), read_csv(src, cols)
        clash = sorted({r["ID"] for r in rows} & {r["ID"] for r in extra})
        if clash: die(f"Not restored: {path} already has {', '.join(clash[:5])}.")
        plan.append((path, cols, rows + extra))
    for path, cols, rows in plan:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True); write_csv(path, cols, rows)
    for p in meta["files"]:
        os.makedirs(os.path.dirname(p) or ".", exist_ok=True); shutil.move(os.path.join(dest, "files", p), p)
    done = os.path.join(ARCHIVE, "_restored", os.path.basename(os.path.normpath(dest)))  # the record of the archive stays
    os.makedirs(os.path.dirname(done), exist_ok=True); shutil.move(dest, done)
    print(f"RESTORED {m} from {dest.replace(os.sep, '/')}/ ({len(meta['files'])} files or folders, {sum(meta['rows'].values())} register rows)")


def listing():
    out = []
    for p in sorted(glob.glob(os.path.join(ARCHIVE, "*", "ARCHIVE.json")), reverse=True):
        name = os.path.basename(os.path.dirname(p))
        if not NAME.fullmatch(name): continue
        with open(p, encoding="utf-8") as f: meta = json.load(f)
        out.append({"name": name, "module": meta["module"], "archived_at": meta["archived_at"], "by": meta.get("by", ""),
                    "why": meta.get("why", ""), "rows": sum(meta["rows"].values()), "files": len(meta["files"])})
    return out


def main():
    a = sys.argv[1:]
    if a[:1] == ["archive"] and len(a) == 5: archive(a[1].upper(), a[2], a[3], a[4])
    elif a[:1] == ["restore"] and len(a) == 2: restore(a[1])
    elif a[:1] == ["list"]: print(json.dumps(listing(), indent=2, ensure_ascii=False))
    else: die(__doc__)


if __name__ == "__main__":
    main()
