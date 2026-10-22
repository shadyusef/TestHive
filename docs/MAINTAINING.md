# Maintaining TestHive

For the person who takes over TestHive: how it is built, how to change it without breaking it, and how to release.
You do not need the original author or any chat history; everything is in this repository.

## Design principles
1. **Files are the source of truth.** Agents, scripts, Excel and (later) the UI all read and write plain files in the project folder. No hidden state, no database. Anything important can be reviewed in git.
2. **Scripts for anything repeatable, agents for judgement.** Scripts are free, fast and give the same result every time; agents cost tokens. Formatting, checking, running, collecting and reporting are scripts. Analysis, test design and triage are agents.
3. **A human approves every stage.** `scripts/stage.sh` enforces it; agents may not approve on their own.
4. **Never weaken a test.** A real bug is reported and the test keeps its assertion.
5. **Nothing personal or secret in the repo.** `.env`, masking files and evidence are git-ignored; agents are blocked from reading them.
6. **Short context for agents.** Agents read `CONTEXT.md` (30 lines) and the board, then only the files of the module in hand.

## Repository map
| Path | What it is | Change it when |
|---|---|---|
| `.claude/agents/*.md` | Agent definitions: frontmatter (`name` = file name, `model`, `tools`) and rules | An agent's role or rules change |
| `.claude/commands/th-*.md` | `/th-*` slash commands, one per agent | An agent is added or renamed |
| `.claude/settings.json` | Commands agents may run (`allow`) and must never run (`deny`) | A new script or tool is needed by agents |
| `CLAUDE.md` | Rules for every Claude session opened in the folder | Project-wide rules change |
| `hive.cmd`, `scripts/hive.sh` | Launcher: `.\hive <name>` runs `scripts/<name>.sh` | Rarely |
| `scripts/*.sh` | One script per job. Line 2 is its one-line description (shown by `.\hive`); then `# Usage:` lines | Behaviour changes |
| `scripts/_py.sh` | Finds a Python 3 that really runs (Windows `python3` is often a Store stub) | Never, unless Python lookup breaks |
| `scripts/lib/*.py` | Python code too big for a heredoc: `mask.py` (masking), `ingest.py` (documents to text), `analysis.py` (register check, workbook, import, score, baseline), `uiscreen.py` (Android UI dumps), `design.py` (case check, risk priority, design workbook, import, impact, score, design baseline) | Behaviour changes |
| `web/explore.mjs` | Web exploration with Playwright (Edge on Windows) | Exploration behaviour changes |
| `scripts/lib/studio.py`, `studio/index.html` | TestHive Studio lite: a local server (Python standard library, 127.0.0.1 only, token per start) and one page with no libraries or build step. Writes only through `analysis.apply_answers`, `design.apply_review` and `stage.sh` | A screen or an action changes; keep every rule in the shared functions, never in the page |
| `web/studio-smoke.mjs`, `demo/phase2b/` | Studio click-through (Playwright) and the Studio demo; `run.sh --check` drives the API (`walkthrough.py`) and, with web tools, the screens | When Studio changes |
| `.claude/agents/business-analyst.md` | The analyst's procedure and checklist; the quality of the gaps depends on it | After a benchmark shows misses; re-run `demo/phase1/run.sh --live` and `score-analysis` |
| `.claude/agents/manual-tester.md` | The designer's procedure (techniques, risk, tags, review loop); the coverage of the cases depends on it | After a design benchmark shows misses; re-run `demo/phase2/run.sh --live` and `score-design` |
| `demo/phase2/` | Design demo from the phase 1 result: condition key, `CONTEXT.md` of the fictional app, recorded agent runs (`recorded/`), the script that plays the reviewer (`make/review-workbook.py`) | When the designer or the case format changes: re-record (see below) |
| `demo/phase1/` | Fictional sources with planted gaps (`sources/`, generators in `make/`), the answer key, a local demo site, a recorded agent run (`recorded/`) | When the analyst or formats change: re-record (see below) |
| `scripts/setup.sh`, `setup.ps1` | Prerequisite check/installer for macOS/Linux and Windows | A tool is added or its install changes; keep both in step |
| `scripts/selftest.sh` | Tests TestHive itself; also run by CI | Every change: add a test for it |
| `templates/` | Files `init-project` copies into a new project | Formats change; update `docs/FORMATS.md` too |
| `docs/` | FORMATS, TROUBLESHOOTING, MAINTAINING, ROADMAP | With every change that affects users |
| `demo/phase<N>/run.sh` | Runnable demo per phase, in a temporary copy | When the phase's behaviour changes |
| `requirements.txt` | Python packages | A script needs a new package; add an import check in `setup.sh`/`setup.ps1` |
| `web/package.json` | Playwright for web tests | Playwright version changes |
| `.github/workflows/selftest.yml` | CI: selftest on Linux, Windows, macOS; PowerShell parse; Windows launcher | New platform checks |
| `VERSION`, `CHANGELOG.md` | Release number and notes | Every release |

## Conventions for scripts
- Bash with `#!/usr/bin/env bash`; Python through `. "$(dirname "$0")/_py.sh"` then `$PY`. No other languages without a reason.
- Run from the project root (the launcher does `cd` there). Relative paths only; never a personal path.
- Print short, plain results; print the next command to run when useful (`$TH_CMD` holds how the user types commands: `.\hive` on Windows).
- Exit 0 on success, 1 on error, 2 when blocked by a rule (stage gate).
- UTF-8 everywhere (`sys.stdout.reconfigure(encoding="utf-8")`), `newline="\n"` when writing files; Arabic must survive.
- Files the user may open in Excel are CSV UTF-8; read them with `utf-8-sig` (Excel adds a BOM).
- Tests and demos use `TH_*` variables to work in a temporary folder instead of the real project (see below).
- Windows-only fallbacks (e.g. `C:\Program Files\Tesseract-OCR`) are allowed only as fallbacks after `PATH` and an override variable.

## Environment variables
| Variable | Used by | Meaning |
|---|---|---|
| `TH_CMD` | all, set by the launcher | How the user types a command (`.\hive` or `bash scripts/hive.sh`), for hints |
| `TH_STATE` | `stage` | State file (default `workflow/state.json`) |
| `TH_RUNS` | `collect-run` | Runs folder (default `runs`) |
| `TH_MASK_MAP`, `TH_MASK_TERMS`, `TH_MASK_ALLOW` | `mask` | Masking files (defaults `.mask-map.json`, `.mask-terms`, `.mask-allow`) |
| `TH_OCR_LANGS` | `mask` | OCR languages (default `ara+eng`) |
| `TESSERACT_CMD`, `TESSDATA_PREFIX` | `mask` | Tesseract program and language data |
| `TH_PERMISSION_MODE`, `TH_CLAUDE_ARGS` | `th` | Claude Code options for one-shot agent runs |
| `NO_COLLECT` | `run-*` | `1` = do not store the run in `runs/` |
| `TH_ANALYSIS` | `ingest`, analysis scripts, `stage` | Analysis folder (default `analysis`) |
| `TH_CASES` | design scripts, `stage` | Test case folder (default `test-cases`) |
| `TH_SCORE_TARGET` | `score-analysis`, `score-design` | Pass mark in percent (default 80) |
| `TH_BROWSER_CHANNEL` | `explore-web`, web tests | `msedge` (Windows default), `chrome` or `chromium` |
| `TH_BASH` | `studio` (set by `studio.sh`) | The bash that runs `stage.sh` for approvals from Studio |
| `TH_SCRIPTS` | `stage` (set by itself) | Where the scripts are, to call `lib/analysis.py` |
| `PLATFORM`, `INCLUDE_TAGS`, `EXCLUDE_TAGS` | `run-mobile` | iOS instead of Android; tag filters |
| `TEST_ENV` and every other `.env` key | `run-*` | Environment name recorded with each run; all keys are passed to Maestro flows |

## Common changes
**Add a script:** create `scripts/<name>.sh` (line 2 = description, then `# Usage:`), add a test to `scripts/selftest.sh`, add it to the README table if users run it, and to `.claude/settings.json` only if agents need it beyond `bash scripts/*`. `.\hive` lists it automatically.

**Add or change an agent:** edit `.claude/agents/<name>.md` (frontmatter `name` must equal the file name; give only the tools it needs), add `.claude/commands/th-<short>.md` and the short name in `scripts/th.sh` and `th.ps1`. The selftest checks names and commands. Update the team table in README and `skills/testhive/SKILL.md`.

**Change a file format:** update the template, `docs/FORMATS.md`, every script that reads it, and the selftest. Keep old files readable or explain the migration in `CHANGELOG.md`.

**Add a prerequisite:** add the check and install in both `setup.sh` and `setup.ps1`; if it needs admin rights on Windows, say so in the README "What you need" table and `docs/TROUBLESHOOTING.md`.

## The analyst benchmark
`demo/phase1/answer-key.csv` lists 23 gaps planted in the fictional Nakhla Rewards documents. `score-analysis` matches the analyst's questions against keywords (word-start matching, one gap per key) and prints every pairing so a human can verify it. Keyword matching is an approximation: always read the pairings, and add keywords or keys when a real finding is not recognised. After changing the analyst's instructions, run `.\hive demo/phase1/run.sh --live` and compare the score.

**Re-recording the demo:** run the analyst live on a copy of the demo project (see `demo/phase1/run.sh --live`), check the pairings, then copy `analysis/requirements.csv` and `gaps.csv` after the first pass to `demo/phase1/recorded/first-pass/`, after the first re-check to `recorded/recheck-1/` and after the second to `recorded/recheck-2/`. The human's answers are `recorded/sample-answers.csv` (round 1) and `sample-answers-2.csv` (round 2): if the new run asks different questions, rewrite them so their IDs match.

## The design benchmark
`demo/phase2/condition-key.csv` lists 46 test conditions a QA expert expects for the SIGNUP baseline (boundaries, invalid classes, states and timers, messages in both languages, API codes). `score-design` checks that at least one active case linked to the right requirement mentions each condition. As with the analysis key, read the pairings: keywords are an approximation.

**Re-recording the phase 2 demo:** run `demo/phase2/run.sh --live`, or run its agent steps by hand on a copy, and copy `test-cases/TestCases.csv` after the first pass to `demo/phase2/recorded/first-pass/`, the review file to `recorded/DESIGN-SIGNUP-1.md`, the cases and `analysis/gaps.csv` (it holds the designer's new questions) after the fixes to `recorded/after-review/`, and the cases, `requests.csv` and `gaps.csv` after the re-check to `recorded/recheck-1/`. Remove the template's `TC-EXAMPLE-001` row if an older project copy still has it. `recorded/sample-review.csv` is the human's review: if the case IDs changed, rewrite it so the IDs match.

## Testing
- `.\hive selftest` (or `bash scripts/selftest.sh`): must end with `SELFTEST PASS`. Image masking is tested only where Tesseract is installed; otherwise the test says it was skipped.
- `.\hive demo/phase0/run.sh`, `demo/phase1/run.sh`, `demo/phase2/run.sh`: the demos; read the output top to bottom. CI runs the phase 1 and phase 2 demos and `demo/phase2b/run.sh --check` (Studio API; the browser click-through runs where the web tools are installed).
- CI runs the selftest on Linux, Windows and macOS for every push and pull request (GitHub, Actions tab).
- Not covered by automated tests: real installs (`setup --install`), real Maestro/Newman/Playwright runs against an app, the agents' own work. Check those by hand when they change.

## Releasing
1. All tests pass locally; the demo runs.
2. Update `VERSION` and add a `CHANGELOG.md` entry.
3. Commit, push, and check the Actions tab is green on all three systems.
4. Tag: `git tag v<version> && git push --tags`.
5. The repository is a GitHub **template**: users click "Use this template". Existing projects update by copying changed files from the new version (scripts, agents, templates); their own data folders are not touched.

## Known limitations
- Masking finds people's names only when they follow a title or are listed in `.mask-terms`; `suggest` helps, a human must confirm. Long numbers that pass a checksum by chance are masked.
- Screenshot masking needs Tesseract, which needs admin rights to install on Windows.
- iOS needs a Mac or a device farm.
- `scripts/th.sh` one-shot runs cannot answer permission prompts; they accept file edits and run only allowed commands, and only after the folder was trusted once in an interactive `claude` session.
- Exploration records what it can reach: the web explorer does not know real passwords or OTP codes, and `adb` cannot type Arabic. The analyst must treat explored behaviour as Observed and ask.
- The analyst and the designer are AI: their registers and cases are a draft for a human, not a final answer. The approval gates, the pre-review and the benchmarks exist for that reason.
- `check-design` judges coverage by links and labels (Type, Technique), not by reading the steps: a case labelled Boundary that tests no boundary passes the check. The reviewer and the human catch that.
- macOS and Linux are verified by CI only.
