"""Which TestHive project Studio works on: a folder given at start (--project), the folder Studio was started in, or the
last one opened (remembered per user, never inside a project). Used by studio.py; one Studio program serves any project."""
import os, sys, json

RECENT_MAX = 8


def is_project(path):
    """A TestHive project folder: the template's scripts and templates are there (a clone of the template or of a project)."""
    return bool(path) and os.path.isfile(os.path.join(path, "scripts", "hive.sh")) and os.path.isdir(os.path.join(path, "templates"))


def config_file():
    """The per-user settings file: %APPDATA%\\TestHive\\studio.json on Windows, ~/.config/testhive/studio.json elsewhere
    (TH_STUDIO_CONFIG overrides it, for tests)."""
    if os.environ.get("TH_STUDIO_CONFIG"): return os.environ["TH_STUDIO_CONFIG"]
    base = os.environ.get("APPDATA") if os.name == "nt" else os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base or os.path.expanduser("~"), "TestHive" if os.name == "nt" else "testhive", "studio.json")


def load():
    try:
        with open(config_file(), encoding="utf-8") as f: c = json.load(f)
        return c if isinstance(c, dict) else {}
    except (OSError, ValueError): return {}


def recent():
    """Recently opened projects that still exist, newest first."""
    return [p for p in load().get("recent", []) if isinstance(p, str) and is_project(p)][:RECENT_MAX]


def remember(path):
    path = os.path.realpath(path)
    c = load(); c["recent"] = [path] + [p for p in c.get("recent", []) if isinstance(p, str) and os.path.realpath(p) != path][:RECENT_MAX - 1]
    try:
        os.makedirs(os.path.dirname(config_file()), exist_ok=True)
        tmp = config_file() + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f: json.dump(c, f, indent=2)
        os.replace(tmp, config_file())
    except OSError: pass  # remembering is a convenience: Studio works without it


def choose(argv, cwd):
    """The project to open at start: --project <folder>, else the current folder, else the last one opened; None when there is none."""
    if "--project" in argv:
        i = argv.index("--project")
        p = argv[i + 1] if i + 1 < len(argv) else ""
        if not is_project(p): sys.exit(f"Not a TestHive project folder: {p or '(none given)'} (it has no scripts/hive.sh and templates/).")
        return os.path.realpath(p)
    if is_project(cwd): return os.path.realpath(cwd)
    r = recent()
    return r[0] if r else None
