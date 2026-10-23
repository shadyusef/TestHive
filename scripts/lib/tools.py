"""TestHive tool advice (stage 3; functional tests only for now): which automation tool for each test type of a module.
Groups the approved design's functional cases that can be automated into test types (Web UI, API, Android, iOS), scores the
tools in CATALOG on fixed criteria with the project's weights and team skills, and records the human's choice with a reason.
Called by scripts/tool-advice.sh, stage.sh (check --for-approval, baseline) and Studio. Formats: docs/FORMATS.md (tool advice)."""
import sys, os, re, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analysis import read_csv, write_csv, die, stage_status
import design

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
DIR = os.environ.get("TH_TOOLS", "tools")
CHOICE_FILE, SETTINGS_FILE = os.path.join(DIR, "choices.csv"), os.path.join(DIR, "settings.json")
CHOICE_COLS = ["Module", "Test Type", "Cases", "Recommended", "Chosen", "Reason", "Chosen By", "Chosen At", "Design Baseline"]
TEST_TYPES = ["Web UI", "API", "Android", "iOS"]
FUNCTIONAL = ["Positive", "Negative", "Localization", "Functional"]  # Accessibility, Security and Performance get tool advice later
BY_PLATFORM = {"Web": ["Web UI"], "API": ["API"], "Android": ["Android"], "iOS": ["iOS"], "Both": ["Android", "iOS"]}
CRITERIA = [("fit", "Fits the test type"), ("testhive", "Ready-made in TestHive"), ("upkeep", "Low upkeep"), ("windows", "Runs on Windows"),
            ("skills", "Team skills"), ("evidence", "Evidence (video, screenshots, logs)"), ("cost", "Cost and licence")]
WEIGHTS = {"fit": 3, "testhive": 3, "upkeep": 2, "windows": 2, "skills": 2, "evidence": 1, "cost": 1}
NO_CODE = "No code"
# Scores 1-5 per criterion: TestHive's starting judgement, not a measurement; change them here when the team knows better.
# "skills" is not scored here: it comes from the team's skills (settings) and the tool's languages.
CATALOG = {
    "Web UI": [
        {"tool": "Playwright", "langs": ["TypeScript", "JavaScript", "Python", "Java", "C#"], "fit": 5, "testhive": 5, "upkeep": 5, "windows": 5, "evidence": 5, "cost": 5,
         "note": "Waits for the page by itself; trace, video and screenshots per test. TestHive's web engineer writes Playwright + TypeScript."},
        {"tool": "Selenium WebDriver", "langs": ["Java", "Python", "C#", "JavaScript"], "fit": 4, "testhive": 1, "upkeep": 3, "windows": 5, "evidence": 2, "cost": 5,
         "note": "The long-standing standard, every language; waits, screenshots and reports are yours to add."},
        {"tool": "Cypress", "langs": ["JavaScript", "TypeScript"], "fit": 4, "testhive": 1, "upkeep": 4, "windows": 5, "evidence": 4, "cost": 4,
         "note": "Friendly runner with time travel; one browser tab per test, parallel runs and its dashboard are paid."}],
    "API": [
        {"tool": "Postman + Newman", "langs": [NO_CODE, "JavaScript"], "fit": 5, "testhive": 5, "upkeep": 4, "windows": 5, "evidence": 4, "cost": 4,
         "note": "Requests are built without code, checks are short JavaScript; Newman runs them in CI. TestHive's API engineer uses it."},
        {"tool": "REST Assured", "langs": ["Java"], "fit": 5, "testhive": 1, "upkeep": 4, "windows": 5, "evidence": 3, "cost": 5,
         "note": "API tests as Java code (JUnit or TestNG); strong for teams that already write Java."}],
    "Android": [
        {"tool": "Maestro", "langs": [NO_CODE], "fit": 5, "testhive": 5, "upkeep": 5, "windows": 4, "evidence": 4, "cost": 5,
         "note": "Flows in plain YAML, waits by itself; runs on an emulator or a USB phone. TestHive's mobile engineer uses it."},
        {"tool": "Appium", "langs": ["Java", "Python", "JavaScript", "C#"], "fit": 4, "testhive": 1, "upkeep": 2, "windows": 5, "evidence": 3, "cost": 5,
         "note": "WebDriver for apps, every language, works with device clouds; slower and more setup to keep stable."},
        {"tool": "Espresso", "langs": ["Kotlin", "Java"], "fit": 3, "testhive": 1, "upkeep": 4, "windows": 5, "evidence": 2, "cost": 5,
         "note": "Google's in-app framework, fastest and steadiest, but lives in the app's source code (the developers' project)."}],
    "iOS": [
        {"tool": "Maestro", "langs": [NO_CODE], "fit": 5, "testhive": 5, "upkeep": 5, "windows": 1, "evidence": 4, "cost": 5,
         "note": "The same YAML flows as Android; iOS simulators need a Mac (or Maestro's paid cloud)."},
        {"tool": "Appium", "langs": ["Java", "Python", "JavaScript", "C#"], "fit": 4, "testhive": 1, "upkeep": 2, "windows": 3, "evidence": 3, "cost": 5,
         "note": "From a Windows PC only with a device cloud (for example BrowserStack); a local iPhone needs a Mac."},
        {"tool": "XCUITest", "langs": ["Swift"], "fit": 3, "testhive": 1, "upkeep": 4, "windows": 1, "evidence": 2, "cost": 5,
         "note": "Apple's framework in the app's Xcode project; needs a Mac and the app's source code."}]}
MAX_TEXT = 300  # a name or a reason
LANGS = sorted({l for ts in CATALOG.values() for t in ts for l in t["langs"] if l != NO_CODE})


def settings():
    """The project's criteria weights (0-5) and team skills (languages from LANGS)."""
    s = {}
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, encoding="utf-8") as f: s = json.load(f)
        except ValueError: s = {}
    w = s.get("weights") if isinstance(s.get("weights"), dict) else {}
    return {"weights": {k: w[k] if type(w.get(k)) is int and 0 <= w[k] <= 5 else v for k, v in WEIGHTS.items()},
            "skills": [x for x in s.get("skills", []) if x in LANGS] if isinstance(s.get("skills"), list) else []}


def save_settings(weights, skills):
    """Checks and saves the weights and skills. Returns a list of errors (nothing saved when there are any)."""
    err = [f"unknown criterion {k}" for k in weights if k not in WEIGHTS]
    err += [f"weight of {k} must be a whole number from 0 to 5" for k, v in weights.items() if k in WEIGHTS and not (type(v) is int and 0 <= v <= 5)]
    err += [f"unknown skill {x} (known: {', '.join(LANGS)})" for x in skills if x not in LANGS]
    if not err and not any({**settings()["weights"], **weights}.values()): err.append("at least one weight must be above 0")
    if err: return err
    s = settings(); s["weights"].update(weights); s["skills"] = sorted(set(skills))
    os.makedirs(DIR, exist_ok=True)
    with open(SETTINGS_FILE + ".tmp", "w", encoding="utf-8", newline="\n") as f: json.dump(s, f, indent=2)
    os.replace(SETTINGS_FILE + ".tmp", SETTINGS_FILE)
    return []


def design_baseline(module):
    """(version, cases) of the latest approved design baseline, or None."""
    base = os.path.join(design.TC_DIR, "baseline", module)
    vs = sorted(int(d[1:]) for d in os.listdir(base) if re.fullmatch(r"v\d+", d)) if os.path.isdir(base) else []
    if not vs: return None
    return f"v{vs[-1]}", read_csv(os.path.join(base, f"v{vs[-1]}", "TestCases.csv"), design.CASE_COLS)


def score(t, cfg):
    """The tool's per-criterion scores (1-5) with the team's skills, and its weighted total in percent."""
    sk = {x.lower() for x in cfg["skills"]}
    s = {k: t[k] for k in WEIGHTS if k != "skills"}
    s["skills"] = 5 if NO_CODE in t["langs"] or sk & {l.lower() for l in t["langs"]} else 1 if sk else 3  # no skills given: neutral
    w = cfg["weights"]
    return s, round(100 * sum(w[k] * s[k] for k in w) / (5 * sum(w.values()) or 1))


def advice(module):
    """The decision matrix of the module from its latest design baseline; None when the design has no baseline yet."""
    b = design_baseline(module)
    if not b: return None
    ver, cases = b
    act = [c for c in cases if design.active(c)]
    auto = [c for c in act if c["Automation"] in ("Yes", "Candidate")]
    cfg, types = settings(), []
    for tt in TEST_TYPES:
        cs = [c for c in auto if c["Type"] in FUNCTIONAL and tt in BY_PLATFORM.get(c["Platform"], [])]
        if not cs: continue
        opts = []
        for t in CATALOG[tt]:
            s, total = score(t, cfg)
            opts.append({"tool": t["tool"], "score": total, "scores": s, "langs": t["langs"], "note": t["note"], "ready": t["testhive"] == 5})
        opts.sort(key=lambda o: (-o["score"], -o["ready"]))
        types.append({"type": tt, "cases": len(cs), "smoke": sum(1 for c in cs if "smoke" in design.refs(c["Tags"])),
                      "high": sum(1 for c in cs if c["Priority"] in ("P0", "P1")), "options": opts, "recommended": opts[0]["tool"]})
    return {"design_baseline": ver, "types": types, "settings": cfg,
            "other": sum(1 for c in act if c["Type"] not in FUNCTIONAL),
            "manual": sum(1 for c in act if c["Type"] in FUNCTIONAL and c not in auto)}


def choices(module): return [r for r in read_csv(CHOICE_FILE, CHOICE_COLS) if r["Module"].upper() == module]


def tool_of(tt, name):
    """The catalogue name of a tool for a test type (any case), or None."""
    return next((t["tool"] for t in CATALOG.get(tt, []) if t["tool"].lower() == name.strip().lower()), None)


def choose(module, picks, by):
    """picks: [(test type, tool, reason)]. Saves them for the module (an empty tool clears the choice). Returns errors."""
    if stage_status(module, "tools") == "approved": return ["the tool choice is approved (a frozen baseline): reopen the tools stage to change it"]
    if not by.strip() or re.search(r"[\r\n|]", by) or len(by) > MAX_TEXT: return [f"your name is needed (no line breaks or |, at most {MAX_TEXT} characters): choices are signed"]
    adv = advice(module)
    if not adv: return [f"no approved design baseline for {module}: approve the design stage first"]
    types = {x["type"]: x for x in adv["types"]}
    err, rows = [], read_csv(CHOICE_FILE, CHOICE_COLS)
    mine = {r["Test Type"]: r for r in rows if r["Module"].upper() == module}
    for tt, tool, reason in picks:
        reason = re.sub(r"\s+", " ", reason or "").strip()
        if len(reason) > MAX_TEXT: err.append(f"{tt}: the reason is longer than {MAX_TEXT} characters"); continue
        if reason and reason[0] in "=+-@": reason = "'" + reason  # text, never a formula when the CSV is opened in Excel
        if tt not in types: err.append(f"{tt}: not a test type of {module} (types with functional cases to automate: {', '.join(types) or 'none'})"); continue
        if not tool.strip(): mine.pop(tt, None); continue
        name = tool_of(tt, tool)
        if not name: err.append(f"{tt}: {tool} is not in the list ({', '.join(t['tool'] for t in CATALOG[tt])})"); continue
        if name != types[tt]["recommended"] and not reason: err.append(f"{tt}: say why {name} instead of the recommended {types[tt]['recommended']}")
        mine[tt] = {"Module": module, "Test Type": tt, "Cases": str(types[tt]["cases"]), "Recommended": types[tt]["recommended"], "Chosen": name,
                    "Reason": reason, "Chosen By": by.strip(), "Chosen At": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "Design Baseline": adv["design_baseline"]}
    if err: return err
    os.makedirs(DIR, exist_ok=True)
    write_csv(CHOICE_FILE, CHOICE_COLS, [r for r in rows if r["Module"].upper() != module] + [mine[t] for t in TEST_TYPES if t in mine])
    return []


def problems(module, for_approval=False):
    """(errors, warnings) of the module's tool choice."""
    adv = advice(module)
    if not adv: return [f"no approved design baseline for {module}: approve the design stage first"], []
    err, warn, mine = [], [], {r["Test Type"]: r for r in choices(module)}
    for x in adv["types"]:
        r = mine.get(x["type"])
        if not r: err.append(f"{x['type']}: no tool chosen yet ({x['cases']} cases; recommended {x['recommended']})"); continue
        if r["Design Baseline"] != adv["design_baseline"]:
            err.append(f"{x['type']}: the test cases changed since {r['Chosen']} was chosen (design {r['Design Baseline']} -> {adv['design_baseline']}): check it and save it again")
        if r["Chosen"] != x["recommended"] and not r["Reason"]:
            err.append(f"{x['type']}: {r['Chosen']} is chosen instead of the recommended {x['recommended']}: say why")
        t = next((t for t in CATALOG[x["type"]] if t["tool"] == r["Chosen"]), None)
        if not t: err.append(f"{x['type']}: {r['Chosen']} is not in the list"); continue
        if t["testhive"] < 5: warn.append(f"{x['type']}: {r['Chosen']} has no ready-made TestHive setup yet; phase 4 automation starts it by hand")
        if t["windows"] <= 2: warn.append(f"{x['type']}: {r['Chosen']} needs a Mac (or a paid cloud) to run")
    for tt in mine:
        if tt not in {x["type"] for x in adv["types"]}: warn.append(f"{tt}: chosen, but design {adv['design_baseline']} has no functional cases to automate for it (ignored)")
    if not adv["types"]: warn.append(f"design {adv['design_baseline']} has no functional cases marked for automation: there is nothing to choose")
    if adv["other"]: warn.append(f"{adv['other']} non-functional cases (accessibility, security, performance): tool advice comes later")
    return err, warn


def matrix_text(adv):
    out = [f"TOOL ADVICE from design baseline {adv['design_baseline']} (functional cases to automate; weights "
           + ", ".join(f"{k} {v}" for k, v in adv["settings"]["weights"].items()) + f"; team skills: {', '.join(adv['settings']['skills']) or 'not given'})"]
    for x in adv["types"]:
        out.append(f"\n{x['type']}: {x['cases']} cases ({x['smoke']} smoke, {x['high']} P0/P1). Recommended: {x['recommended']}")
        out.append("  " + f"{'Tool':<20}{'Score':>6}  " + " ".join(f"{k[:7]:>7}" for k in WEIGHTS))
        for o in x["options"]:
            out.append("  " + f"{o['tool']:<20}{o['score']:>5}%  " + " ".join(f"{o['scores'][k]:>7}" for k in WEIGHTS) + ("" if o["ready"] else "   (no TestHive setup yet)"))
    if not adv["types"]: out.append("No functional cases are marked for automation (Automation Yes or Candidate): nothing to choose.")
    if adv["other"]: out.append(f"\n{adv['other']} non-functional cases (accessibility, security, performance): tool advice for them comes later.")
    return "\n".join(out)


USAGE = ("Usage: tool-advice.sh <MODULE>                                 the decision matrix\n"
         "       tool-advice.sh choose <MODULE> \"<test type>\" <tool> --by <name> [--reason \"why\"]\n"
         "       tool-advice.sh check <MODULE> [--for-approval]\n"
         "       tool-advice.sh settings [--weights fit=3,testhive=3,...] [--skills Java,Python]")


def opts(a, names):
    pos, o, i = [], {}, 0
    while i < len(a):
        if a[i] in names:
            if i + 1 >= len(a): die(f"{a[i]} needs a value")
            o[a[i][2:]] = a[i + 1]; i += 2
        else: pos.append(a[i]); i += 1
    return pos, o


def cmd_advise(a):
    if len(a) != 1: die(USAGE)
    adv = advice(a[0].upper())
    if not adv: die(f"No approved design baseline for {a[0].upper()}: approve the design stage first.")
    print(matrix_text(adv))
    mine = choices(a[0].upper())
    if mine: print("\nChosen: " + "; ".join(f"{r['Test Type']}: {r['Chosen']} by {r['Chosen By']}" for r in mine))


def human_only():
    if os.environ.get("TH_JOB"): die("BLOCKED: choosing tools is a human decision; an agent started from TestHive Studio cannot make it", 2)


def cmd_choose(a):
    human_only()
    pos, o = opts(a, ("--by", "--reason"))
    if len(pos) != 3 or "by" not in o: die(USAGE)
    err = choose(pos[0].upper(), [(pos[1], pos[2], o.get("reason", ""))], o["by"])
    if err: die("NOT SAVED:\n" + "\n".join("- " + e for e in err))
    print(f"SAVED {pos[0].upper()} {pos[1]}: {tool_of(pos[1], pos[2]) or '(cleared)'}")


def cmd_check(a):
    module = next((x.upper() for x in a if not x.startswith("--")), None)
    if not module: die(USAGE)
    err, warn = problems(module, "--for-approval" in a)
    for w in warn: print("  warning: " + w)
    if err: print(f"TOOLS NOT OK (module {module})\n" + "\n".join("- " + e for e in err)); sys.exit(1)
    print(f"TOOLS OK (module {module}): " + ("; ".join(f"{r['Test Type']}: {r['Chosen']}" for r in choices(module)) or "nothing to choose"))


def cmd_settings(a):
    pos, o = opts(a, ("--weights", "--skills"))
    if pos: die(USAGE)
    if o: human_only()
    if o:
        try: w = {k.strip(): int(v) for k, v in (x.split("=") for x in o.get("weights", "").split(",") if x.strip())}
        except ValueError: die("--weights looks like fit=3,testhive=3 (whole numbers 0-5)")
        sk = [x.strip() for x in o["skills"].split(",") if x.strip()] if "skills" in o else settings()["skills"]
        err = save_settings(w, sk)
        if err: die("NOT SAVED:\n" + "\n".join("- " + e for e in err))
    s = settings()
    print("weights: " + ", ".join(f"{k} {v}" for k, v in s["weights"].items()) + f"\nteam skills: {', '.join(s['skills']) or 'not given'}\nknown skills: {', '.join(LANGS)}")


def cmd_baseline(a):
    if len(a) < 2: die("Usage: tools.py baseline <MODULE> <approved-by>")
    module, by = a[0].upper(), a[1]
    base = os.path.join(DIR, "baseline", module); os.makedirs(base, exist_ok=True)
    v = f"v{max((int(d[1:]) for d in os.listdir(base) if re.fullmatch(r'v\d+', d)), default=0) + 1}"
    out = os.path.join(base, v); os.makedirs(out)
    rows, adv = choices(module), advice(module)
    write_csv(os.path.join(out, "choices.csv"), CHOICE_COLS, rows)
    with open(os.path.join(out, "meta.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump({"module": module, "version": v, "approved_by": by, "approved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "design_baseline": adv["design_baseline"] if adv else None, "settings": settings(),
                   "tools": {r["Test Type"]: r["Chosen"] for r in rows}}, f, indent=2, ensure_ascii=False)
    print(f"TOOLS BASELINE {module} {v}: " + "; ".join(f"{r['Test Type']}: {r['Chosen']}" for r in rows) + f" -> {out.replace(os.sep, '/')}")


COMMANDS = {"advise": cmd_advise, "choose": cmd_choose, "check": cmd_check, "settings": cmd_settings, "baseline": cmd_baseline}
if __name__ == "__main__":
    a = sys.argv[1:]
    if not a: die(USAGE)
    if a[0] not in COMMANDS: a = ["advise"] + a  # tool-advice.sh <MODULE>
    COMMANDS[a[0]](a[1:])
