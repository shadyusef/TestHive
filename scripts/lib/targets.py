"""TestHive run targets (phase 5b): where the tests run. targets.json in the project (else templates/targets.json) names each
target: a local browser or Android device, or a BrowserStack browser or device. Called by run-web.sh and run-mobile.sh
(`shell <name> <kind>` prints the settings to eval), browserstack.py, and Studio (the Run picker). The BrowserStack keys stay in
.env: this file never reads or prints them; it only says whether they are set.
Usage: python targets.py shell <target> web|mobile   |   python targets.py list"""
import sys, os, re, json, shlex, shutil, subprocess

NAME = re.compile(r"[a-z0-9][a-z0-9._-]{0,40}")
TEXT = re.compile(r"[A-Za-z0-9 ._()+-]{1,60}")  # BrowserStack browser, OS and device names
CHANNELS = ("msedge", "chrome", "chromium")
BS_KEYS = ("BROWSERSTACK_USERNAME", "BROWSERSTACK_ACCESS_KEY")
BS_WS = "wss://cdp.browserstack.com/playwright"  # Playwright on BrowserStack
BS_API = "https://api-cloud.browserstack.com"     # App Automate (Maestro)
LOCAL = re.compile(r"(?:ws|http)://127\.0\.0\.1:\d+/?[A-Za-z0-9/_-]*")  # the only other addresses allowed (a local stand-in): the keys never go elsewhere


def die(m): print(m, file=sys.stderr); sys.exit(2)


def load():
    """{name: target} with only valid targets; a broken entry is left out with a note on stderr."""
    p = "targets.json" if os.path.exists("targets.json") else os.path.join("templates", "targets.json")
    try:
        with open(p, encoding="utf-8") as f: raw = json.load(f).get("targets") or {}
    except (OSError, ValueError) as e: print(f"targets: cannot read {p}: {e}", file=sys.stderr); return {}
    out = {}
    for n, t in raw.items():
        ok = isinstance(t, dict) and NAME.fullmatch(n) and t.get("kind") in ("web", "mobile") and t.get("where") in ("local", "browserstack")
        if ok and t["where"] == "local": ok = t.get("channel") in CHANNELS if t["kind"] == "web" else t.get("platform") == "android"
        if ok and t["where"] == "browserstack":
            ok = all(TEXT.fullmatch(str(t.get(k, ""))) for k in (("browser", "os", "os_version") if t["kind"] == "web" else ("device",))) and \
                 (t["kind"] == "web" or t.get("platform") in ("android", "ios"))
        if ok: out[n] = {k: str(v) for k, v in t.items() if k in ("kind", "where", "channel", "browser", "os", "os_version", "platform", "device", "label")}
        else: print(f"targets: {n} is not a valid target in {p}: left out", file=sys.stderr)
    return out


def keys_set(env=""):
    """Are both BrowserStack keys in .env or .env.<env> (or the environment)? Only whether they are there, never their values."""
    have = {k for k in BS_KEYS if os.environ.get(k)}
    for p in [".env"] + ([f".env.{env}"] if env and re.fullmatch(r"[A-Za-z0-9._-]+", env) and not env.startswith(".") else []):
        try:
            with open(p, encoding="utf-8-sig") as f:
                have |= {m[1] for m in (re.match(r"\s*(BROWSERSTACK_\w+)\s*=\s*\S", ln) for ln in f) if m}
        except OSError: pass
    return all(k in have for k in BS_KEYS)


def endpoint(kind):
    """BrowserStack's address, or a local stand-in given by TH_BS_WS / TH_BS_API (only 127.0.0.1)."""
    v = os.environ.get("TH_BS_WS" if kind == "web" else "TH_BS_API", "")
    if not v: return BS_WS if kind == "web" else BS_API
    if not LOCAL.fullmatch(v): die(f"{'TH_BS_WS' if kind == 'web' else 'TH_BS_API'} may only point to a local stand-in (127.0.0.1): the BrowserStack keys never go to another address")
    return v.rstrip("/")


def adb_devices():
    """IDs of the Android devices adb sees now ([] without adb)."""
    if not shutil.which("adb"): return []
    try: out = subprocess.run([shutil.which("adb"), "devices"], capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.TimeoutExpired): return []
    return [m[1] for m in (re.match(r"([A-Za-z0-9][A-Za-z0-9._:-]*)\s+device$", ln.strip()) for ln in out.splitlines()[1:]) if m]


def shell(name, kind):
    """The shell lines run-web.sh / run-mobile.sh eval for a target (values quoted)."""
    t = load().get(name)
    if not t: die(f"Unknown target {name}: see targets.json (or templates/targets.json): " + ", ".join(n for n, x in load().items() if x["kind"] == kind))
    if t["kind"] != kind: die(f"{name} is a {t['kind']} target, not {kind}")
    out = {"TH_TARGET": name, "TH_TARGET_WHERE": t["where"]}
    if t["where"] == "local": out.update({"TH_BROWSER_CHANNEL": t["channel"]} if kind == "web" else {"PLATFORM": t["platform"]})
    else:
        if kind == "web":
            caps = {"browser": t["browser"], "os": t["os"], "os_version": t["os_version"], "name": f"TestHive {name}", "build": os.environ.get("TH_BS_BUILD", "TestHive")}
            out.update(TH_BS_CAPS=json.dumps(caps), TH_BS_WS=endpoint("web"))
        else: out.update(PLATFORM=t["platform"], TH_BS_DEVICE=t["device"], TH_BS_API=endpoint("mobile"))
    return "\n".join(f"export {k}={shlex.quote(v)}" for k, v in out.items())


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["shell"] and len(a) == 3 and a[2] in ("web", "mobile"): print(shell(a[1], a[2]))
    elif a == ["list"]:
        for n, t in load().items(): print(f"{n:<18} {t['kind']:<7} {t['where']:<13} {t.get('label', '')}")
    else: die(__doc__.splitlines()[-1].strip())
