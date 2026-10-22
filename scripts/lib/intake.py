"""TestHive intake: project setup, modules, requirement uploads, sources list, masking preview. Used by TestHive Studio
(scripts/lib/studio.py). Writes only the project files listed below; never shows or writes secrets.
  PROJECT_BRIEF.md, CONTEXT.md     project facts (template placeholders replaced)
  .env                             only the non-secret keys in ENV_KEYS; passwords and tokens stay for the human to add
  requirements/modules/<M>.json    module title, URL or APK to explore, test-environment flag, masking choice
  requirements/sources/<M>/        uploaded documents; an older file of the same name moves to _old/<time>/
  requirements/apps/<M>/           uploaded APKs (git-ignored)"""
import sys, os, re, json, csv, time, glob, shutil, subprocess, calendar
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SOURCES, MODULES, APPS = "requirements/sources", "requirements/modules", "requirements/apps"
ANALYSIS = os.environ.get("TH_ANALYSIS", "analysis")
ENV_KEYS = ["APP_ID", "TEST_ENV", "BASE_URL", "API_BASE_URL"]  # the only .env keys Studio reads or writes
PLATFORMS = ["Web", "API", "Android", "iOS"]
DOC_TYPES = (".pdf", ".docx", ".xlsx", ".xlsm", ".csv", ".txt", ".md", ".json", ".yaml", ".yml", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")
MAX_DOC, MAX_APK = 25_000_000, 300_000_000
SAFE_NAME = re.compile(r"^[\w\-. ()؀-ۿ]{1,120}$")


def bash():
    return os.environ.get("TH_BASH") or "bash"


def run(args):
    r = subprocess.run([bash()] + args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout + r.stderr).strip()


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
    plats = [p for p in PLATFORMS if p in (f.get("platforms") or [])]
    if not name or not app: return False, "Enter the project name and the app name."
    if not plats: return False, "Choose at least one platform."
    for k in ("base_url", "api_url"):
        v = str(f.get(k, "")).strip()
        if v and not re.match(r"^https?://\S+$", v): return False, f"{'Web' if k == 'base_url' else 'API'} address must start with http:// or https://"
    app_id = str(f.get("app_id", "")).strip()
    if app_id and not re.fullmatch(r"[A-Za-z][\w]*(\.[A-Za-z][\w]*)+", app_id): return False, "Android package looks like com.company.app"
    if re.search(r"[\r\n|<>]", name + app): return False, "Names cannot contain line breaks or the characters | < >"
    if not os.path.exists("PROJECT_BRIEF.md"):
        code, out = run(["scripts/init-project.sh", name])
        if code: return False, out
    brief = read("PROJECT_BRIEF.md")
    brief = re.sub(r"^# Project brief:.*$", f"# Project brief: {name}", brief, count=1, flags=re.M)
    for label, value in (("Name", app), ("Platforms", " / ".join(plats)), ("Android package", app_id or "-"),
                         ("Test environment", " ".join(x for x in (f.get("test_env", ""), f.get("base_url", ""), f.get("api_url", "")) if x).strip() or "-")):
        brief = re.sub(rf"^- {label}:.*$", f"- {label}: {value}", brief, count=1, flags=re.M)
    write("PROJECT_BRIEF.md", brief)
    if os.path.exists("CONTEXT.md"):
        ctx = read("CONTEXT.md")
        ctx = re.sub(r"^App:.*?\| Package/bundle:.*?\| Platforms:.*$", f"App: {app} | Package/bundle: {app_id or '-'} | Platforms: {', '.join(p.lower() for p in plats)}",
                     ctx, count=1, flags=re.M)
        envtxt = " ".join(x for x in (f.get("test_env", ""), f.get("base_url", ""), f.get("api_url", "")) if x).strip() or "-"
        ctx = re.sub(r"^Env:.*?\|", f"Env: {envtxt} |", ctx, count=1, flags=re.M)
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
    if url and not re.match(r"^https?://\S+$", url): return None, "The URL must start with http:// or https://"
    m.update({"title": str(f.get("title", m["title"])).strip()[:80], "url": url, "test_env": bool(f.get("test_env", m["test_env"])),
              "mask": bool(f.get("mask", m["mask"]))})
    return m, None


# ---------- uploads and sources ----------
def safe_name(name):
    name = os.path.basename(str(name).replace("\\", "/")).strip()
    if not name or name.startswith(".") or ".." in name or not SAFE_NAME.match(name): return None
    return name


def save_upload(module, name, data, kind="source"):
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
    target, note = os.path.join(folder, name), ""
    if os.path.exists(target):  # keep the earlier version; nothing is deleted
        old = os.path.join(folder, "_old", time.strftime("%Y%m%d-%H%M%S"))
        os.makedirs(old, exist_ok=True); shutil.move(target, os.path.join(old, name))
        note = f" (the earlier version is kept in {old.replace(os.sep, '/')}/)"
    with open(target, "wb") as f: f.write(data)
    if kind == "apk":
        m = meta(module); m["apk"] = target.replace(os.sep, "/"); save_meta(module, m)
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
    old = sorted({os.path.basename(os.path.dirname(p)) for p in glob.glob(os.path.join(folder, "_old", "*", "*"))})
    return {"files": files, "read_at": time.strftime("%Y-%m-%d %H:%M", time.localtime(read_at)) if read_at else "",
            "old_versions": len(old), "apk": meta(module).get("apk", "")}


def ingest(module, mask):
    return run(["scripts/ingest.sh", module] + (["--mask"] if mask else []))


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
