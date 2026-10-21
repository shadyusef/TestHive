# TestHive

TestHive is a team of AI QA agents that runs inside [Claude Code](https://claude.com/claude-code). You give it a product module and its business rules; it helps you analyse the requirements, design test cases, automate them for **mobile (Maestro)**, **API (Postman/Newman)** and **web (Playwright)**, run them, and report bugs, with a human approval between every stage.

Everything lives as plain files in your project folder, so the work is visible, reviewable in git, and does not depend on any one chat or person.

![The TestHive team](docs/testhive-diagram.png)

> **Status (v0.3.0).** Working today: the agent team and scripts, the phase 0 foundations (stage gates, approval log, run storage, masking) and phase 1, business analysis (documents, API specs, designs, or exploring a built web/Android app; requirement and gap registers; Excel questions and answers; approval and baselines). Still being built phase by phase: Excel test cases, tool advice, HTML reports and a UI: see [docs/ROADMAP.md](docs/ROADMAP.md). Tested on Windows 11. The selftest also runs on Linux and macOS in GitHub Actions; there is no hands-on macOS/Linux test yet.

## What you need
| Need | Why | Who provides it |
|---|---|---|
| A Claude account with Claude Code | The agents run in Claude Code | You / your team's Claude plan |
| Git (on Windows it also gives Git Bash) | To get TestHive, and to run its bash scripts; `hive.cmd` finds Git Bash for you | Install it first. Windows: `winget install --id Git.Git -e` |
| Python 3, Node.js, Java 17+, Maestro, adb, Newman | Scripts, mobile and API runs | `setup --install` installs them |
| An Android phone with USB debugging, or an emulator | Mobile tests | You |
| A Mac (or BrowserStack, later phase) | iOS tests; Windows cannot run the iOS Simulator | You |
| Optional: Tesseract OCR | Blacking out personal data in screenshots | `setup --install --ocr` |
| Administrator rights on Windows, or IT help | Several installers (Git, Node.js, Python, Java, Tesseract) install for all users and ask for admin rights. Maestro, adb, Newman and Claude Code do not. | You / IT |

## Start in 10 minutes
Commands are shown for **Windows PowerShell** (`.\hive ...`). On macOS/Linux type `bash scripts/hive.sh ...` instead of `.\hive ...`.

1. **Get your copy.** On GitHub click **Use this template** to make a **private** repo for your project (your requirements and test evidence should not be public), then clone it and open a terminal in the folder.
2. **Check the tools:** `.\hive setup --check`. Install what is missing with `.\hive setup --install` (add `--ocr` for screenshot masking, `--web` for web tests). Open a **new** terminal afterwards.
3. **Verify TestHive works on your machine:** `.\hive selftest` must end with `SELFTEST PASS`.
4. **See it in action (optional, 1 minute):** `.\hive demo/phase0/run.sh`.
5. **Create your project files:** `.\hive init-project "My Project"`.
6. **Describe your app:** fill in `CONTEXT.md` (app name, platforms, environment, quirks) and `.env` (app id, URLs; never committed). Connect the phone and check it: `.\hive check-devices`.
7. **Describe a module:** copy `templates/MODULE_INTAKE.md` to `workflow/intake/<module>.md` and fill in the business rules.
8. **Start the team:** `claude --agent testhive-lead`, then tell it e.g. *"Module: Signup, Android. The intake is in workflow/intake/signup.md."* It shows a plan and waits for your approval.

Stuck? See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).

## How work flows
Each module goes through six stages. A stage cannot start until a named person approves the one before it; every decision is logged in `workflow/APPROVALS.md`.

| Stage | TestHive does | You get | You decide |
|---|---|---|---|
| 1. Analysis | Reads the requirements, lists gaps and questions | Gap register | Answer and approve |
| 2. Design | Writes test cases, reviews them | Excel test cases | Add, edit, approve |
| 3. Tools | Compares tools for your product | Decision matrix | Choose |
| 4. Automation | Writes the test project | Scripts, tagged smoke/sanity/regression/E2E | Review |
| 5. Execution | Runs what you pick, keeps evidence | Runs with screenshots, video, API logs | What to run |
| 6. Reporting | Writes bug and test reports | HTML reports for testers and managers | Sign off |

```
.\hive stage status SIGNUP
.\hive stage approve SIGNUP analysis --by "<your name>" --comment "All High gaps answered"
```

## The team
| Agent | Model | Role |
|---|---|---|
| `testhive-lead` | Sonnet | Runs the pipeline, briefs the others, keeps the board, stops at every approval. Never writes tests. |
| `business-analyst` | Sonnet | Reads documents, API specs and designs, or explores a built web/Android app; writes the requirement and gap registers; re-checks your answers. |
| `manual-tester` | Sonnet | Explores the app, writes test cases with exact expected results. |
| `mobile-automation-engineer` | Sonnet | Maestro flows for Android and iOS. |
| `api-backend-test-engineer` | Sonnet | Postman collections run with Newman. |
| `web-automation-engineer` | Sonnet | Playwright + TypeScript. Idle until a web flow exists. |
| `test-data-env-manager` | Haiku | Test users, resets, environment files. Scripts first. |
| `defect-triage` | Sonnet | Runs on failures only: test defect, environment or real bug; writes bug reports. |
| `qa-reviewer` | Opus | Independent audit and module sign-off. |

Call one agent directly inside Claude Code with `/th-lead`, `/th-analyst`, `/th-manual`, `/th-mobile`, `/th-api`, `/th-web`, `/th-data`, `/th-triage`, `/th-review` followed by the task, or from a terminal with `.\hive th mobile "automate TC-SIGNUP-001"`. `/th-lead` makes the current session act as the Lead (a subagent cannot start other agents); for a full module `claude --agent testhive-lead` is the better start.

## Analyse a module (stage 1)
1. Put the module's documents in `requirements/sources/<MODULE>/` (PDF, Word, Excel, text, OpenAPI/Swagger, design images). No documents? Give the analyst a URL or an APK instead: it explores the built product and drafts the requirements as **observed** behaviour for you to confirm.
2. In Claude Code: `/th-analyst SIGNUP` (add e.g. `url=https://staging.example.com, test environment`), or ask the Lead.
3. Open `analysis/SIGNUP-analysis.xlsx`, sheet **Gaps**: answer the questions in the yellow columns (you may add your own questions in a new row). Save.
4. Ask the analyst to re-check (`/th-analyst re-check SIGNUP`). Repeat 3-4 until no High question is open.
5. Approve: `.\hive stage approve SIGNUP analysis --by "<your name>"`. The requirements are frozen as `analysis/baseline/SIGNUP/v1/`.

See it end to end with a fictional app: `.\hive demo/phase1/run.sh` (recorded agent, free) or `--live` (real agent, uses your Claude plan).

## Scripts
Run `.\hive` with no arguments for the full list with one-line descriptions. The main ones:

| Script | What it does |
|---|---|
| `setup` | Checks and installs the tools. `--check` (default), `--install`, `--web`, `--ocr` |
| `selftest` | Proves TestHive works on this machine |
| `init-project` | Creates the project files from `templates/` |
| `stage` | Stage gates and approvals |
| `ingest` | Turns a module's documents (text, PDF, Word, Excel, OpenAPI, images) into text for the analyst; `--mask` hides personal data first |
| `explore-web` / `explore-android` | Record what a built web app (URL) or Android app (APK) actually does, as observed behaviour |
| `check-analysis` | Checks the requirement and gap registers; `--for-approval` checks they are ready to approve |
| `analysis-workbook` / `import-answers` | Excel workbook of questions for the business, and reading the answers back |
| `score-analysis` | Benchmark: how many planted gaps the analyst found |
| `run-mobile` / `run-api` / `run-web` | Run a module's tests; each run is stored in `runs/` |
| `stable` | Runs a module 3 times; only cases that pass every time count as done |
| `gate` | Definition-of-done check on the case sheet |
| `mask` | Hides personal data in documents and screenshots before Claude sees them (Arabic + English) |
| `collect-run`, `digest-failures`, `check-intake`, `check-devices`, `reset-app`, `gen-user` | Helpers used by the agents and by you |

## Privacy and safety
- `.env` holds your app ids and URLs; it is git-ignored and the agents are blocked from reading it (`.claude/settings.json`).
- Agents cannot `git push`; you publish.
- Before sending business documents to Claude, mask them: `.\hive mask suggest <file>` (find names), `.\hive mask review <file>` (check every match), `.\hive mask mask <file> <out>`. The token map stays on your PC (`.mask-map.json`, git-ignored). `suggest` and `review` show real data, so only you run them.
- Use made-up test data in test environments, so screenshots never show real people.

## Rules the team follows
- Verify on the real app; never assume behaviour.
- Cases: `TC-<MODULE>-<NNN>` (an extra part is allowed, e.g. `TC-SIGNUP-API-001`), atomic steps, exact expected results, independent; priority P0 to P3.
- Real bugs are reported and the test keeps its assertion (tagged `known-bug` with the bug ID). Assertions are never weakened.
- A test is done only when it passes 3 times in a row.
- The case sheet can be edited in Excel: save it as "CSV UTF-8".

## Folder layout
```
hive.cmd             Windows launcher: .\hive <script> ...
CLAUDE.md            rules every Claude session in this folder follows
.claude/agents/      the 9 agent definitions        .claude/commands/  /th-* slash commands
.claude/settings.json  allowed and blocked commands for agents
scripts/             all scripts (lib/ holds their Python code)
templates/           files init-project copies: brief, CONTEXT, intake, board, case sheet, registers, reports, env
docs/                FORMATS, TROUBLESHOOTING, MAINTAINING, ROADMAP
demo/                one runnable demo per phase
mobile/ api/ web/    test code per platform
requirements/sources/  your input documents          analysis/  requirements and gap registers
workflow/            state.json, APPROVALS.md, BOARD.md, intake/     test-cases/  TestCases.csv
runs/                one folder per test run           reports/ reviews/  reports and reviews
skills/testhive/     optional /testhive skill for the Claude app
```

## More documentation
- [QUICKSTART.md](QUICKSTART.md): the same start, with more detail per step.
- [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md): common errors and fixes.
- [docs/FORMATS.md](docs/FORMATS.md): every file format (state, registers, runs, masking).
- [docs/MAINTAINING.md](docs/MAINTAINING.md): how TestHive is built, how to change it safely, how to release.
- [docs/ROADMAP.md](docs/ROADMAP.md): what is built and what comes next.
- [CHANGELOG.md](CHANGELOG.md): what changed in each version.

## License
MIT. See [LICENSE](LICENSE).
