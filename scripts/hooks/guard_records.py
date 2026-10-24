"""Claude Code hook (PreToolUse on Edit|Write|MultiEdit|NotebookEdit): blocks direct edits of the approval records.
Only scripts/stage.sh writes them, so a decision always has a named human, a log line and a frozen baseline.
Registered in .claude/settings.json; tested by scripts/selftest.sh. Exit 2 = the edit is refused and Claude reads why."""
import sys, os, json

PROTECTED = {"workflow/APPROVALS.md": "the approvals log is append-only and written by stage.sh",
             "workflow/state.json": "stage status changes only through stage.sh (start, submit; approve and reject by a named human)"}
PROTECTED_DIRS = {"analysis/baseline/": "an approved analysis baseline is frozen",
                  "test-cases/baseline/": "an approved design baseline is frozen", "tools/baseline/": "an approved tool choice is frozen", "automation/baseline/": "an approved automation is recorded",
                  "execution/": "test cycles and their results are recorded with cycle.sh (results, bugs, quarantine) or in Studio",
                  "tools/choices.csv": "tool choices are a person's decision, saved with tool-advice.sh choose or in Studio",
                  "tools/settings.json": "the weights and team skills are a person's decision (tool-advice.sh settings or Studio)"}

try: data = json.load(sys.stdin)
except ValueError: sys.exit(0)
inp = data.get("tool_input") or {}
path = inp.get("file_path") or inp.get("notebook_path") or ""
if not path: sys.exit(0)
root = os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd()
full = path if os.path.isabs(path) else os.path.join(root, path)
rel = os.path.relpath(os.path.realpath(full), os.path.realpath(root)).replace(os.sep, "/")  # realpath: links, junctions, short names
if os.environ.get("TH_JOB"):  # an agent started by TestHive Studio: the tool itself and the secrets are off limits too
    PROTECTED.update({".env": "secrets are added by a person", ".mask-terms": "masking lists are kept by a person",
                      ".mask-allow": "masking lists are kept by a person", ".mask-map.json": "the masking map is written by mask.sh"})
    PROTECTED_DIRS.update({"scripts/": "agents started from Studio may run the scripts, not change them",
                           ".claude/": "agents started from Studio may not change their own rules or settings",
                           "templates/": "agents started from Studio may not change the templates",
                           "archive/": "archived modules are moved there by stage.sh archive, never written by hand"})
if os.environ.get("TH_JOB") and os.path.basename(rel).lower().startswith(".env."): PROTECTED[rel] = "secrets are added by a person"  # .env.<name>
fold = (lambda x: x.lower()) if os.name == "nt" else (lambda x: x)  # Windows paths ignore case
why = next((w for f, w in PROTECTED.items() if fold(rel) == fold(f)), None) or \
      next((w for d, w in PROTECTED_DIRS.items() if fold(rel).startswith(fold(d))), None)
if why:
    record = rel.startswith(("workflow/", "analysis/baseline/", "test-cases/baseline/", "tools/", "automation/", "execution/"))
    print(f"Refused: {rel} is not edited directly ({why})." + (" Use bash scripts/stage.sh (status, start, submit, reopen); "
          "approvals and rejections are made by a named human." if record else ""), file=sys.stderr)
    sys.exit(2)
