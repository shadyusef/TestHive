"""TestHive intake: project setup, modules, requirement uploads, sources list, masking preview. Used by TestHive Studio
(scripts/lib/studio.py). Writes only the project files listed below; never shows or writes secrets.
  PROJECT_BRIEF.md, CONTEXT.md     project facts (template placeholders replaced)
  .env                             only the non-secret keys in ENV_KEYS; passwords and tokens stay for the human to add
  requirements/modules/<M>.json    module title, URL or APK to explore, test-environment flag, masking choice
  requirements/sources/<M>/        uploaded documents; an older file of the same name, or a removed one, moves to _old/<time>/
  requirements/sources/<M>/_old/history.csv   who uploaded, replaced, removed or restored which document, and when
  requirements/apps/<M>/           uploaded APKs (git-ignored)"""
import sys, os, re, json, csv, time, glob, shutil, subprocess, calendar
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pyrun

SOURCES, MODULES, APPS = "requirements/sources", "requirements/modules", "requirements/apps"
ANALYSIS = os.environ.get("TH_ANALYSIS", "analysis")
ENV_KEYS = ["APP_ID", "TEST_ENV", "BASE_URL", "API_BASE_URL"]  # the only .env keys Studio reads or writes
PLATFORMS = ["Web", "API", "Android", "iOS"]
DOC_TYPES = (".pdf", ".docx", ".xlsx", ".xlsm", ".csv", ".txt", ".md", ".json", ".yaml", ".yml", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")
MAX_DOC, MAX_APK = 25_000_000, 300_000_000
SAFE_NAME = re.compile(r"^[\w\-. ()؀-ۿ]{1,120}$")


def bash():
    return os.environ.get("TH_BASH") or "bash"


def run_py(lib, args):
    """Runs scripts/lib/<lib> with this Python, or inside the Studio program (no bash needed)."""
    r = subprocess.run(pyrun.lib_cmd(lib, *args),
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout + r.stderr).strip()


def init_project(name):
    """Creates the project files (brief, CONTEXT, board, case sheet, registers, .env) from templates; keeps the ones that exist.
    Used by scripts/init-project.sh and by Studio's first opening."""
    for d in ("workflow/intake", "test-cases", "reports", "reviews", "mobile/data", "requirements/sources", "analysis", "runs"):
        os.makedirs(d, exist_ok=True)
    first_line = lambda p: read(p).split("\n", 1)[0] + "\n"  # a register's header only: the template's example row stays in templates/
    files = {"PROJECT_BRIEF.md": lambda: read("templates/PROJECT_BRIEF.md").replace("<PROJECT_NAME>", name),
             "workflow/BOARD.md": lambda: read("templates/BOARD.md"), "test-cases/TestCases.csv": lambda: first_line("templates/TestCases.csv"),
             "test-cases/requests.csv": lambda: read("templates/requests.csv"), ".env": lambda: read("templates/env.example"),
             "CONTEXT.md": lambda: read("templates/CONTEXT.md"), "analysis/requirements.csv": lambda: first_line("templates/requirements.csv"),
             "analysis/gaps.csv": lambda: first_line("templates/gaps.csv")}
    for path, text in files.items():
        if not os.path.exists(path): write(path, text())
    h = os.environ.get("TH_CMD", "bash scripts/hive.sh")
    return f"Project '{name}' initialised. Next: fill in CONTEXT.md and .env, then run: {h} setup --check   and   {h} check-devices"


def read(path):
    with open(path, encoding="utf-8") as f: return f.read()


def write(path, text):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path + ".tmp", "w", encoding="utf-8", newline="\n") as f: f.write(text)
    os.replace(path + ".tmp", path)


# ---------- project ----------
def env_values():
    out = {k: "" for k in ENV_KEYS}
    if os.path.exists(".env"):
        for line in read(".env").splitlines():
            k, _, v = line.partition("=")
            if k.strip() in ENV_KEYS: out[k.strip()] = v.strip()
    return out


def test_login_set():
    """Is a test account in .env for Explore? Only whether both values are there: the values never leave this function."""
    if not os.path.exists(".env"): return False
    got = {}
    for line in read(".env").splitlines():
        k, _, v = line.partition("=")
        if k.strip() in ("TEST_USER", "TEST_USER_PASSWORD"): got[k.strip()] = v.strip()
    return bool(got.get("TEST_USER")) and got.get("TEST_USER_PASSWORD", "") not in ("", "change-me")


def project():
    """The project facts for the setup form. setup_needed: no brief yet (first opening)."""
    brief = read("PROJECT_BRIEF.md") if os.path.exists("PROJECT_BRIEF.md") else ""
    get = lambda label: (re.search(rf"^- {label}:\s*(.*)$", brief, re.M) or [None, ""])[1].strip()
    name = (re.match(r"#\s*Project brief:\s*(.*)", brief) or [None, ""])[1].strip()
    env = env_values()
    placeholder = lambda v: "" if (not v or "<" in v or v in ("com.example.app", "https://staging.example.com", "https://api.staging.example.com")) else v
    plats = [p for p in PLATFORMS if re.search(rf"\b{p}\b", get("Platforms"), re.I)] if "delete what" not in get("Platforms") else []
    return {"setup_needed": not brief or "<PROJECT_NAME>" in brief, "incomplete": "<APP_NAME>" in brief,
            "project": placeholder(name), "app": placeholder(get("Name")), "platforms": plats,
            "test_env": placeholder(env["TEST_ENV"]) or "staging", "base_url": placeholder(env["BASE_URL"]),
            "api_url": placeholder(env["API_BASE_URL"]), "app_id": placeholder(env["APP_ID"])}


def save_project(f):
    """Creates the project files if needed and fills in the facts. Returns (ok, message)."""
    name, app = str(f.get("project", "")).strip(), str(f.get("app", "")).strip()
    f = dict(f, test_env=str(f.get("test_env", "")).strip() or "staging")
    if not re.fullmatch(r"[\w.-]{1,30}", f["test_env"]): return False, "Environment name: letters, digits, . - _ only (for example staging)."
    for k in ("project", "app", "base_url", "api_url", "app_id"):  # nothing may add lines or keys to .env, the brief or CONTEXT.md
        if re.search(r"[\r\n|<>=`]", str(f.get(k, ""))): return False, "Fields cannot contain line breaks or the characters | < > = `"
    plats = [p for p in PLATFORMS if p in (f.get("platforms") or [])]
    if not name or not app: return False, "Enter the project name and the app name."
    if not plats: return False, "Choose at least one platform."
    for k in ("base_url", "api_url"):
        v = str(f.get(k, "")).strip()
        if v and not re.fullmatch(r"https?://[^\s|<>`]+", v): return False, f"{'Web' if k == 'base_url' else 'API'} address must start with http:// or https://"
    app_id = str(f.get("app_id", "")).strip()
    if app_id and not re.fullmatch(r"[A-Za-z][\w]*(\.[A-Za-z][\w]*)+", app_id): return False, "Android package looks like com.company.app"
    if re.search(r"[\r\n|<>]", name + app): return False, "Names cannot contain line breaks or the characters | < >"
    if not os.path.exists("PROJECT_BRIEF.md"):
        init_project(name)
    brief = read("PROJECT_BRIEF.md")
    brief = re.sub(r"^# Project brief:.*$", lambda m: f"# Project brief: {name}", brief, count=1, flags=re.M)  # lambda: user text is never a pattern
    for label, value in (("Name", app), ("Platforms", " / ".join(plats)), ("Android package", app_id or "-"),
                         ("Test environment", " ".join(x for x in (f.get("test_env", ""), f.get("base_url", ""), f.get("api_url", "")) if x).strip() or "-")):
        brief = re.sub(rf"^- {label}:.*$", lambda m, l=label, v=value: f"- {l}: {v}", brief, count=1, flags=re.M)
    write("PROJECT_BRIEF.md", brief)
    if os.path.exists("CONTEXT.md"):
        ctx = read("CONTEXT.md")
        app_line = f"App: {app} | Package/bundle: {app_id or '-'} | Platforms: {', '.join(p.lower() for p in plats)}"
        ctx = re.sub(r"^App:.*?\| Package/bundle:.*?\| Platforms:.*$", lambda m: app_line, ctx, count=1, flags=re.M)
        envtxt = " ".join(x for x in (f.get("test_env", ""), f.get("base_url", ""), f.get("api_url", "")) if x).strip() or "-"
        ctx = re.sub(r"^Env:.*?\|", lambda m: f"Env: {envtxt} |", ctx, count=1, flags=re.M)
        write("CONTEXT.md", ctx)
    values = {"APP_ID": app_id, "TEST_ENV": str(f.get("test_env", "")).strip() or "staging",
              "BASE_URL": str(f.get("base_url", "")).strip(), "API_BASE_URL": str(f.get("api_url", "")).strip()}
    lines = read(".env").splitlines() if os.path.exists(".env") else []
    seen = set()
    for i, line in enumerate(lines):
        k = line.partition("=")[0].strip()
        if k in values: lines[i] = f"{k}={values[k]}"; seen.add(k)
    lines += [f"{k}={v}" for k, v in values.items() if k not in seen]
    write(".env", "\n".join(lines) + "\n")
    return True, f"Project '{name}' saved. Passwords and tokens are not set here: add them to .env yourself when a test needs them."


# ---------- modules ----------
def meta(module):
    p = os.path.join(MODULES, f"{module}.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f: return json.load(f)
    return {"title": "", "url": "", "test_env": False, "apk": "", "mask": False}


def save_meta(module, m):
    write(os.path.join(MODULES, f"{module}.json"), json.dumps(m, indent=2, ensure_ascii=False) + "\n")


def clean_meta(module, f):
    m = meta(module)
    url = str(f.get("url", m["url"])).strip()
    if url and not re.fullmatch(r"https?://[^\s|<>`]+", url): return None, "The URL must start with http:// or https:// and contain no spaces"
    title = " ".join(str(f.get("title", m["title"])).split())[:80]  # one line: it goes into the agent's task
    m.update({"title": title, "url": url, "test_env": bool(f.get("test_env", m["test_env"])),
              "mask": bool(f.get("mask", m["mask"]))})
    return m, None


# ---------- uploads and sources ----------
def safe_name(name):
    name = os.path.basename(str(name).replace("\\", "/")).strip()
    if not name or name.startswith(".") or ".." in name or not SAFE_NAME.match(name): return None
    if re.fullmatch(r"(con|prn|aux|nul|com\d|lpt\d)(\..*)?", name, re.I): return None  # Windows device names
    return name


def stamp(): return time.strftime("%Y%m%d-%H%M%S")


def utc(): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


OLD = re.compile(r"\d{8}-\d{6}(-\d+)?")  # an _old/ folder: the time, and a counter when two changes fall in the same second


def keep_old(module, rel, folder=None):
    """Moves the current file rel (a path inside the module's folder) to _old/<time>/; returns where it went.
    Never overwrites: a second change in the same second goes to _old/<time>-2/."""
    folder = folder or os.path.join(SOURCES, module)
    base, n = stamp(), 1
    while os.path.exists(os.path.join(folder, "_old", base if n == 1 else f"{base}-{n}", rel)): n += 1
    old = os.path.join(folder, "_old", base if n == 1 else f"{base}-{n}", rel)
    os.makedirs(os.path.dirname(old), exist_ok=True); shutil.move(os.path.join(folder, rel), old)
    return old.replace(os.sep, "/")


def log_change(module, action, name, by=""):
    p = os.path.join(SOURCES, module, "_old", "history.csv")
    os.makedirs(os.path.dirname(p), exist_ok=True); new = not os.path.exists(p)
    with open(p, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        if new: w.writerow(["When", "Action", "Document", "By"])
        cell = lambda v: "'" + v if v[:1] in ("=", "+", "-", "@") else v  # never a formula when the file is opened in Excel
        w.writerow([utc(), action, cell(name), cell(" ".join(str(by).split())[:60])])


def history(module):
    p = os.path.join(SOURCES, module, "_old", "history.csv")
    if not os.path.exists(p): return []
    with open(p, encoding="utf-8", newline="") as f: rows = list(csv.DictReader(f))
    out = []
    for r in rows:  # a damaged line is skipped, never a reason the module cannot open
        try: time.strptime(r.get("When") or "", "%Y-%m-%dT%H:%M:%SZ"); out.append({k: r.get(k) or "" for k in ("When", "Action", "Document", "By")})
        except ValueError: continue
    return out


def doc_name(name):
    """A document name inside a module folder (may contain sub-folders), checked part by part; None if not allowed."""
    parts = str(name).replace("\\", "/").split("/")
    if not all(safe_name(p) == p for p in parts) or "_old" in (x.lower() for x in parts): return None  # _OLD is _old on Windows
    return "/".join(parts)


def source_file(module, name):
    """The path of one current document of the module, or None."""
    rel = doc_name(name)
    if not rel: return None
    folder = os.path.realpath(os.path.join(SOURCES, module))
    p = os.path.realpath(os.path.join(folder, rel))
    return p if p.startswith(folder + os.sep) and os.path.isfile(p) else None


def forget_text(module, rel):
    """Drops what TestHive read from one document (its line in index.csv and its text file), so the analyst never reads
    a removed or replaced document. Only TestHive's own output in analysis/sources-text/<M>/ is touched."""
    out_dir = os.path.join(ANALYSIS, "sources-text", module)
    idx, src = os.path.join(out_dir, "index.csv"), f"{SOURCES}/{module}/{rel}"
    if not os.path.exists(idx): return
    with open(idx, encoding="utf-8-sig", newline="") as f: rows = list(csv.DictReader(f))
    for r in rows:
        read_from = os.path.realpath(r.get("Read from") or "")
        if r["Source"] == src and read_from.startswith(os.path.realpath(out_dir) + os.sep) and os.path.isfile(read_from): os.remove(read_from)
    with open(idx, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, ["Source", "Type", "Read from", "Words", "Masked"], lineterminator="\n", extrasaction="ignore")
        w.writeheader(); w.writerows(r for r in rows if r["Source"] != src)


def source_text(module, name):
    """What TestHive read from one document: {"text": ...} or an explanation."""
    rel = doc_name(name)
    idx = os.path.join(ANALYSIS, "sources-text", module, "index.csv")
    if not rel or not os.path.exists(idx): return {"text": "", "note": "Not read yet: press 'Read the documents'."}
    with open(idx, encoding="utf-8-sig", newline="") as f:
        row = next((r for r in csv.DictReader(f) if r["Source"] == f"{SOURCES}/{module}/{rel}"), None)
    if not row: return {"text": "", "note": "Not read yet: press 'Read the documents'."}
    if row["Type"] == "image": return {"text": "", "note": "An image: Claude looks at the picture itself (open the original)."}
    path = os.path.realpath(row["Read from"])
    if not path.startswith(os.path.realpath(os.path.join(ANALYSIS, "sources-text", module)) + os.sep) or not os.path.isfile(path):
        return {"text": "", "note": "The text file is missing: read the documents again."}
    text = read(path)
    return {"text": re.sub(r"^<!-- source:.*?-->\n", "", text), "words": row["Words"], "masked": row["Masked"] == "yes"}


def remove_source(module, name, by):
    rel = doc_name(name)
    if not rel or not source_file(module, rel): return False, "That document is not in the module."
    kept = keep_old(module, rel); forget_text(module, rel); log_change(module, "removed", rel, by)
    return True, f"Removed {rel}. It is kept in {os.path.dirname(kept)}/ and can be restored (Earlier versions)."


def versions(module):
    """Earlier versions and removed documents, newest first."""
    old = os.path.join(SOURCES, module, "_old")
    out = []
    for d in sorted(glob.glob(os.path.join(old, "*")), reverse=True):
        v = os.path.basename(d)
        if not os.path.isdir(d) or not OLD.fullmatch(v): continue
        for p in sorted(glob.glob(os.path.join(d, "**", "*"), recursive=True)):
            if os.path.isfile(p):
                out.append({"version": v, "name": os.path.relpath(p, d).replace(os.sep, "/"), "size": os.path.getsize(p),
                            "kept": f"{v[:4]}-{v[4:6]}-{v[6:8]} {v[9:11]}:{v[11:13]}",
                            "current": bool(source_file(module, os.path.relpath(p, d)))})
    return out


def old_file(module, version, name):
    rel = doc_name(name)
    if not rel or not OLD.fullmatch(str(version)): return None
    base = os.path.realpath(os.path.join(SOURCES, module, "_old", version))
    p = os.path.realpath(os.path.join(base, rel))
    return p if p.startswith(base + os.sep) and os.path.isfile(p) else None


def restore_source(module, version, name, by):
    """Puts an earlier version back as the current document; the current one (if any) is kept in _old/ first."""
    src, rel = old_file(module, version, name), doc_name(name)
    if not src: return False, "That earlier version does not exist."
    note, folder = "", os.path.realpath(os.path.join(SOURCES, module))
    target = os.path.join(SOURCES, module, rel)
    try:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        d = os.path.realpath(os.path.dirname(target))  # a junction or link inside the folder never redirects the write
        if not (d == folder or d.startswith(folder + os.sep)) or os.path.isdir(target): return False, "That document cannot be restored here."
        shutil.copyfile(src, target + ".part")  # copy first: if it fails, the current document is untouched
        if source_file(module, rel): note = f" The version it replaced is kept in {os.path.dirname(keep_old(module, rel))}/."
        os.replace(target + ".part", target)  # a copy with today's time: the earlier version stays in _old/, and TestHive reads it again
    except OSError as e:
        if os.path.exists(target + ".part"): os.remove(target + ".part")
        return False, f"Not restored: {e.strerror}."
    forget_text(module, rel); log_change(module, f"restored {version}", rel, by)
    return True, f"Restored {rel} from {version}.{note} Read the documents again so the analyst sees it."


def save_upload(module, name, data, kind="source", by=""):
    """Saves an uploaded file in the module's folder. Returns (ok, message)."""
    name = safe_name(name)
    if not name: return False, "File name not allowed: use letters, digits, spaces, - _ . ( ) only."
    ext = os.path.splitext(name)[1].lower()
    if kind == "apk":
        if ext != ".apk": return False, "Only .apk files can be explored on Android."
        if len(data) > MAX_APK: return False, "The APK is larger than 300 MB."
        folder = os.path.join(APPS, module)
    else:
        if ext == ".doc": return False, f"{name}: old Word format. Open it in Word and save as .docx, then upload again."
        if ext not in DOC_TYPES: return False, f"{name}: this file type cannot be read. Allowed: {', '.join(DOC_TYPES)}"
        if len(data) > MAX_DOC: return False, f"{name} is larger than 25 MB."
        folder = os.path.join(SOURCES, module)
    os.makedirs(folder, exist_ok=True)
    target, note, replaced = os.path.join(folder, name), "", os.path.exists(os.path.join(folder, name))
    if replaced:  # keep the earlier version; nothing is deleted
        old = os.path.dirname(keep_old(module, name, folder))
        note = f" (the earlier version is kept in {old.replace(os.sep, '/')}/)"
    with open(target + ".part", "wb") as f: f.write(data)
    os.replace(target + ".part", target)
    if kind == "apk":
        m = meta(module); m["apk"] = target.replace(os.sep, "/"); save_meta(module, m)
    else:
        if replaced: forget_text(module, name)
        log_change(module, "replaced" if replaced else "uploaded", name, by)
    return True, f"Saved {name}{note}."


def sources(module, approved_at=""):
    """The module's documents with what TestHive has read from them."""
    folder = os.path.join(SOURCES, module)
    idx_path = os.path.join(ANALYSIS, "sources-text", module, "index.csv")
    index, read_at = {}, 0
    if os.path.exists(idx_path):
        read_at = os.path.getmtime(idx_path)
        with open(idx_path, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f): index[r["Source"]] = r
    approved = calendar.timegm(time.strptime(approved_at, "%Y-%m-%dT%H:%M:%SZ")) if approved_at else 0
    files = []
    for p in sorted(glob.glob(os.path.join(folder, "**", "*"), recursive=True)):
        rel = p.replace(os.sep, "/")
        if not os.path.isfile(p) or os.path.basename(p).startswith(".") or "/_old/" in rel or ".masked." in rel: continue
        mt = os.path.getmtime(p); row = index.get(rel)
        files.append({"name": rel[len(folder) + 1:], "path": rel, "size": os.path.getsize(p), "modified": time.strftime("%Y-%m-%d %H:%M", time.localtime(mt)),
                      "type": row["Type"] if row else os.path.splitext(p)[1].lstrip(".").lower(), "words": row["Words"] if row else "",
                      "masked": row["Masked"] if row else "", "read": bool(row) and mt <= read_at + 1,
                      "after_approval": bool(approved) and mt > approved})
    changed = {}  # document -> what happened to it after the analysis was approved
    if approved:
        for h in history(module):
            if calendar.timegm(time.strptime(h["When"], "%Y-%m-%dT%H:%M:%SZ")) > approved: changed[h["Document"]] = h["Action"].split()[0]
        for f in files:
            if f["after_approval"]: changed.setdefault(f["name"], "changed")
    return {"files": files, "read_at": time.strftime("%Y-%m-%d %H:%M", time.localtime(read_at)) if read_at else "",
            "old_versions": len(versions(module)), "apk": meta(module).get("apk", ""),
            "changed_after_approval": [{"name": n, "action": a} for n, a in sorted(changed.items())]}


def ingest(module, mask):
    return run_py("ingest.py", [module] + (["--mask"] if mask else []))


# ---------- masking (the human's own browser on this PC; agents cannot use Studio) ----------
def mask_preview(module):
    """What masking would hide in the module's documents, and names it cannot be sure about."""
    import mask as masker, ingest as reader
    names, values, skipped = {}, [], []
    for f in sources(module)["files"]:
        try: kind, text = reader.convert(f["path"])
        except (Exception, SystemExit) as e: skipped.append(f"{f['name']}: {e}"); continue
        if not text: continue  # images are masked with OCR when the sources are read
        for n, why in masker.suggest_names(text).items(): names.setdefault(n, {"name": n, "why": why, "file": f["name"]})
        for s, e, k, v in masker.find(text):
            if len(values) < 400:
                values.append({"kind": k, "value": v, "file": f["name"], "context": (text[max(0, s - 35):s] + "⟦" + v + "⟧" + text[e:e + 35]).replace("\n", " ")})
    counts = {}
    for v in values: counts[v["kind"]] = counts.get(v["kind"], 0) + 1
    return {"names": sorted(names.values(), key=lambda x: x["name"]), "values": values, "counts": counts, "skipped": skipped}


def save_mask_lists(terms, allow):
    import mask as masker
    return masker.add_lines(masker.TERMS, [str(t) for t in terms]), masker.add_lines(masker.ALLOW, [str(a) for a in allow])


if __name__ == "__main__":  # python scripts/lib/intake.py init "<PROJECT_NAME>"   (what scripts/init-project.sh runs)
    if len(sys.argv) != 3 or sys.argv[1] != "init": sys.exit('Usage: init-project.sh "<PROJECT_NAME>"')
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(init_project(sys.argv[2]))
