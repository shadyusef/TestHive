# TestHive

TestHive is a team of AI QA agents that runs inside [Claude Code](https://claude.com/claude-code). You give it a product module and its business rules; it helps you analyse the requirements, design test cases, automate them for **mobile (Maestro)**, **API (Postman/Newman)** and **web (Playwright)**, run them, and report bugs, with a human approval between every stage.

Everything lives as plain files in your project folder, so the work is visible, reviewable in git, and does not depend on any one chat or person.

![The TestHive team](docs/testhive-diagram.png)

> **Status (v0.17.0).** Working today: the agent team and scripts, the phase 0 foundations (stage gates, approval log, run storage, masking), phase 1, business analysis (documents, API specs, designs, or exploring a built web/Android app; requirement and gap registers; Excel questions and answers; approval and baselines); phase 2, test design (cases traced to the approved requirements, design techniques, risk-based priority, tags, AI pre-review, Excel review, change impact) and TestHive Studio, a local web page that takes a person who does not use a terminal from an empty project to approved test cases, running the agents with a button, also as a single Windows program for colleagues with review mode, Excel review packs and a team guide, phase 3, tool advice (a decision matrix per test type for the functional cases, the human's choice with a reason, approval), phase 4, automation (the test project set up for the approved tools, one placeholder per case, the engineers' tests run by tag and environment, proven stable, approved; contract tests built from the OpenAPI spec; end-to-end journeys across web and API) and phase 5a, execution (test cycles per environment, results by hand and from the runs, bugs, retest after a fix, flaky tests quarantined, evidence per failure) phase 5b, run targets (local browsers and devices, BrowserStack browsers and real devices) and phase 6a, reporting (bug register, one HTML test report with a Go / No-go suggestion, trends and cost, a signed decision). Phase 7 adds the agents' questions answered in Studio and Android exploration from Studio. The roadmap is complete; what was left out is listed in [docs/ROADMAP.md](docs/ROADMAP.md). TestHive targets Windows (tested on Windows 11; CI runs on Windows); the bash scripts run in Git Bash.

## What you need
| Need | Why | Who provides it |
|---|---|---|
| A Claude account with Claude Code | The agents run in Claude Code | You / your team's Claude plan |
| Git (on Windows it also gives Git Bash) | To get TestHive, and to run its bash scripts; `hive.cmd` finds Git Bash for you | Install it first. Windows: `winget install --id Git.Git -e` |
| Python 3, Node.js, Java 17+, Maestro, adb, Newman | Scripts, mobile and API runs | `setup --install` installs them |
| An Android phone with USB debugging, or an emulator | Mobile tests | You |
| A Mac, or a BrowserStack account (`run-mobile --target bs-iphone15`) | iOS tests; Windows cannot run the iOS Simulator | You |
| Optional: Tesseract OCR | Blacking out personal data in screenshots | `setup --install --ocr` |
| Administrator rights on Windows, or IT help | Several installers (Git, Node.js, Python, Java, Tesseract) install for all users and ask for admin rights. Maestro, adb, Newman and Claude Code do not. | You / IT |

## Start in 10 minutes
Commands are shown for **Windows PowerShell** (`.\hive ...`). In Git Bash type `bash scripts/hive.sh ...` instead of `.\hive ...`.

1. **Get your copy.** On GitHub click **Use this template** to make a **private** repo for your project (your requirements and test evidence should not be public), then clone it and open a terminal in the folder.
2. **Check the tools:** `.\hive setup --check`. Install what is missing with `.\hive setup --install` (add `--ocr` for screenshot masking, `--web` for web tests). Open a **new** terminal afterwards.
3. **Verify TestHive works on your machine:** `.\hive selftest` must end with `SELFTEST PASS`.
4. **See it in action (optional, 1 minute):** `.\hive demo/phase0/run.sh`.
5. **Create your project files:** `.\hive init-project "My Project"`.
6. **Describe your app:** fill in `CONTEXT.md` (app name, platforms, environment, quirks) and `.env` (app id, URLs; never committed). Connect the phone and check it: `.\hive check-devices`.
7. **Give it a module:** put the module's documents in `requirements/sources/<MODULE>/` (PDF, Word, Excel, text, OpenAPI, designs), or have a URL or APK of the built product ready.
8. **Start the team:** `claude --agent testhive-lead`, then tell it e.g. *"Module SIGNUP, web and API. The documents are in requirements/sources/SIGNUP/."* It shows a plan and waits for your approval at every stage (below).

Stuck? See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).

## How work flows
Each module goes through six stages. A stage cannot start until a named person approves the one before it; every decision is logged in `workflow/APPROVALS.md`.

| Stage | TestHive does | You get | You decide |
|---|---|---|---|
| 1. Analysis | Reads the requirements, lists gaps and questions | Gap register | Answer and approve |
| 2. Design | Writes test cases, reviews them | Excel test cases | Add, edit, approve |
| 3. Tools | Compares tools for your product | Decision matrix | Choose |
| 4. Automation | Writes the test project | Scripts, tagged smoke/sanity/regression/E2E | Review |
| 5. Execution | Runs a test cycle on one environment, keeps evidence | Results per case, bugs, retests, videos, API logs | Record results by hand, quarantine, approve |
| 6. Reporting | Keeps the bug register, builds the test report | One HTML report with a Go / No-go suggestion, trends and cost | Decide Go or No-go, sign off |

```
.\hive stage status SIGNUP
.\hive stage approve SIGNUP analysis --by "<your name>" --comment "All High gaps answered"
```

## The team
| Agent | Model | Role |
|---|---|---|
| `testhive-lead` | Sonnet | Runs the pipeline, briefs the others, keeps the board, stops at every approval. Never writes tests. |
| `business-analyst` | Sonnet | Reads documents, API specs and designs, or explores a built web/Android app; writes the requirement and gap registers; re-checks your answers. |
| `manual-tester` | Sonnet | Designs test cases from the approved requirements (techniques, risk, tags, exact expected results); handles your review. |
| `mobile-automation-engineer` | Sonnet | Maestro flows for Android and iOS. |
| `api-backend-test-engineer` | Sonnet | Postman collections run with Newman. |
| `web-automation-engineer` | Sonnet | Playwright + TypeScript. Writes the web tests from the scaffold placeholders. |
| `test-data-env-manager` | Haiku | Test users, resets, environment files. Scripts first. |
| `defect-triage` | Sonnet | Runs on failures only: test defect, environment or real bug; writes real bugs to the register (reports/bugs.csv). |
| `qa-reviewer` | Opus | Independent audit and module sign-off; design pre-review (on Sonnet) before you see the cases. |

Call one agent directly inside Claude Code with `/th-lead`, `/th-analyst`, `/th-manual`, `/th-mobile`, `/th-api`, `/th-web`, `/th-data`, `/th-triage`, `/th-review` followed by the task, or from a terminal with `.\hive th mobile "automate TC-SIGNUP-001"`. `/th-lead` makes the current session act as the Lead (a subagent cannot start other agents); for a full module `claude --agent testhive-lead` is the better start.

Maintainer tools (not part of the QA team): the `studio-security-reviewer` and `docs-consistency-reviewer` agents, and the `/release-phase` and `/rerecord-demo` skills. See [docs/MAINTAINING.md](docs/MAINTAINING.md).

## Analyse a module (stage 1)
1. Put the module's documents in `requirements/sources/<MODULE>/` (PDF, Word, Excel, text, OpenAPI/Swagger, design images). No documents? Give the analyst a URL or an APK instead: it explores the built product and drafts the requirements as **observed** behaviour for you to confirm. Behind a login? Put a test account in `.env` (`TEST_USER`, `TEST_USER_PASSWORD`): Explore records the login page, logs in, and explores from there without writing the password down.
2. In Claude Code: `/th-analyst SIGNUP` (add e.g. `url=https://staging.example.com, test environment`), or ask the Lead.
3. Open `analysis/SIGNUP-analysis.xlsx`, sheet **Gaps**: answer the questions in the yellow columns (you may add your own questions in a new row). Save.
4. Ask the analyst to re-check (`/th-analyst re-check SIGNUP`). Repeat 3-4 until no High question is open.
5. Approve: `.\hive stage approve SIGNUP analysis --by "<your name>"`. The requirements are frozen as `analysis/baseline/SIGNUP/v1/`.

See it end to end with a fictional app: `.\hive demo/phase1/run.sh` (recorded agent, free) or `--live` (real agent, uses your Claude plan).

## Design the tests (stage 2)
1. After the analysis is approved: `/th-manual SIGNUP` (or ask the Lead). The manual-tester designs cases from `analysis/baseline/SIGNUP/v<latest>/`: every case names the requirements it tests, its technique (equivalence, boundary, decision table, state transition, error guessing, use case, checklist), its risk and its tags (`smoke`, `sanity`, `regression`, `e2e`). Priority comes from a fixed rule: the requirement's priority times the case's risk.
2. `.\hive check-design SIGNUP` shows the counts and anything missing: a requirement without a case, a P0 rule without a negative case, a limit without a boundary case.
3. The Lead asks the qa-reviewer for a pre-review (`reviews/DESIGN-SIGNUP-1.md`) and has the findings fixed before you see anything.
4. Open `test-cases/SIGNUP-design.xlsx`. Sheet **Cases**: set **Review** to Accepted, Change (say what in Review Comment) or Remove, or edit a case directly; add your own case in an empty row. Sheet **Requests**: ask for more cases ("add cases for pasted mobile numbers"). Sheets **Coverage** and **Assumptions** show what each requirement is tested by and which open questions the cases rely on. Save.
5. Ask the manual-tester to re-check (`/th-manual re-check SIGNUP`); it imports your review and handles every row. Repeat 4-5 as needed.
6. Approve: `.\hive stage approve SIGNUP design --by "<your name>"`. The cases are frozen as `test-cases/baseline/SIGNUP/v1/`.
7. Requirements changed later? `.\hive stage reopen SIGNUP analysis --by "<name>" --comment "<what>"`, let the analyst update them, approve again, then `.\hive design-impact SIGNUP --apply` marks the affected cases **Needs update** until they are fixed.

See it with the fictional app: `.\hive demo/phase2/run.sh` (recorded agents, free) or `--live`.

## Choose the tools (stage 3)
After the design is approved, TestHive groups the module's functional cases marked for automation (Positive, Negative, Localization; Automation Yes or Candidate) into test types (Web UI, API, Android, iOS; a case on Both counts for Android and iOS) and scores the tools for each on fit, ready-made TestHive support, upkeep, running on Windows, your team's skills, evidence and cost. The best total is recommended; you choose, with a reason when it is not the recommended one. No agent is involved, so it is free and the same every time. Accessibility, security and performance cases are counted; tool advice for them comes later.
```
.\hive tool-advice SIGNUP                                   the decision matrix
.\hive tool-advice settings --skills Java,TypeScript         your team's languages (and --weights fit=3,testhive=3,...)
.\hive stage start SIGNUP tools
.\hive tool-advice choose SIGNUP "Web UI" Playwright --by "<your name>"
.\hive tool-advice choose SIGNUP API "REST Assured" --by "<your name>" --reason "<why>"
.\hive stage submit SIGNUP tools
.\hive stage approve SIGNUP tools --by "<name>"            frozen as tools/baseline/SIGNUP/v1/
```
If the design is approved again later, the choice must be checked and saved again before the tools can be approved. In Studio this is the **Tools** tab: choose per test type, change the weights and skills, **Save the choices** (which submits the stage when every type has a tool), then approve in **Approvals**. See it: `.\hive demo/phase3/run.sh`.

## Automate (stage 4)
After the tools are approved, `scaffold` sets up the test project for Playwright (`web/`), Postman + Newman (`api/`) and Maestro (`mobile/`): one placeholder test per approved functional case marked Automation Yes (Candidate cases are not scaffolded: set them to Yes in the design first), with the case's steps, expected result and tags (`@smoke`, `@sanity`, `@regression`, `@e2e`). Placeholders are skipped or fail until written. With the API tool and an OpenAPI spec among the module's sources, scaffold also builds the **contract tests**: one request per endpoint that checks the status is one the spec lists and the body matches its schema (no AI, no test data; rebuilt when the spec changes). Cases tagged `@e2e` are **journeys**: Playwright tests that reuse the module's steps and set up or check data through the API with the `api` fixture. The engineers replace the placeholders (smoke first), run them by tag and prove them with 3 runs in a row; the stage can be submitted only when every case has a written test with a real check that is stable. Other approved tools are automated by hand.
```
.\hive scaffold SIGNUP                         placeholders (starts the stage; never overwrites)
.\hive run-web SIGNUP --tag smoke              also run-api, run-mobile; TEST_ENV=uat loads .env.uat over .env
.\hive stable web SIGNUP                       3 runs in a row (TH_TAG=smoke for a subset)
.\hive run-api SIGNUP --contract              the contract tests (contract SIGNUP rebuilds them)
.\hive check-automation SIGNUP --for-approval  what is still missing
.\hive stage submit SIGNUP automation; .\hive stage approve SIGNUP automation --by "<name>"   recorded in automation/baseline/
```
An endpoint that answers differently from the spec blocks the approval until it is reported and listed in `api/collections/<MODULE>.contract-bugs.txt` (`<METHOD> <path> <BUG-ID>` per line), or the spec is fixed.
In Studio: the **Automation** tab (the state of each test, the contract tests, **Run** by type, tag, environment and target (and the Android device), the last run with its evidence); the Run button starts the engineers. See it: `.\hive demo/phase4/run.sh` (a small local stand-in of the demo app, recorded engineers, real tests; the contract tests find two responses the spec does not list, and a second environment shows a wrong field type caught).

## Execute (stage 5)
After the automation is approved, a **test cycle** runs every functional case of the approved design once on one environment (for example "1.4 UAT" on `.env.uat`). Every run of the module on that environment after the cycle starts counts in it: the automated cases take their result from the runs, the others are run by hand and recorded with the tester's name. A failure needs a bug ID; a test that both passed and failed with no fix in between is **flaky** and blocks the cycle until it is fixed or **quarantined** with a reason (it still runs). When a bug is marked Fixed (`bug status`, or the Reports tab: the register and the cycle agree) its cases must be retested: `retest` reruns only those. The stage is approved on the cycle's results, recorded in `execution/baseline/`.
```
.\hive cycle start SIGNUP "1.4 UAT" --env uat --by "<name>"    starts the stage; runs on .env.uat count from now on
.\hive run-web SIGNUP; .\hive run-api SIGNUP; .\hive run-api SIGNUP --contract    (TEST_ENV=uat, or set it in .env)
.\hive cycle result SIGNUP TC-SIGNUP-044 Failed --bug BUG-SIGNUP-002 --by "<name>"           cases run by hand: Passed, Failed (with its bug), Blocked (with a note)
.\hive cycle bug SIGNUP TC-SIGNUP-051 BUG-SIGNUP-001 --by "<name>"                          the bug of a failed automated test
.\hive cycle quarantine SIGNUP TC-SIGNUP-098 --reason "<why>" --by "<name>"         a flaky test stops blocking
.\hive bug status SIGNUP BUG-SIGNUP-001 Fixed --by "<name>"; .\hive retest web SIGNUP   the register says Fixed and the cases are retested
.\hive cycle check SIGNUP --for-approval; .\hive stage submit SIGNUP execution; .\hive stage approve SIGNUP execution --by "<name>"
```
Each run keeps its evidence: a failed web test its video, screenshot and Playwright trace (every step), an API test each request and response with Authorization, cookies and secret-looking fields masked. In Studio: the **Execution** tab (start a cycle, run its tests and retests, record the cases run by hand, link bugs, mark them fixed, quarantine flaky tests); the Automation tab's **Run** also picks the environment. See it: `.\hive demo/phase5/run.sh` (build 1.0 of the stand-in app has a planted bug and a flaky resend; build 1.0.1 fixes the bug).

**Where the tests run (targets).** `targets.json` (copy `templates/targets.json` to change it; no secrets in it) names each target: a local browser (`edge`, `chrome`), an Android device on this PC (`android`), a BrowserStack browser (`bs-win11-chrome`, `bs-mac-safari`) or a BrowserStack device (`bs-pixel7`, `bs-galaxy-s23`, `bs-iphone15`; iOS needs no Mac). `.\hive targets` lists them, the devices adb sees and whether the keys are set. For BrowserStack, put `BROWSERSTACK_USERNAME` and `BROWSERSTACK_ACCESS_KEY` in `.env` yourself (and `APP_FILE` / `IOS_APP_FILE`, the app it installs): the keys go only to BrowserStack, never on a command line, into a run, to an agent or to the page. Web tests connect to BrowserStack's browsers as they are (Playwright), and its session link is kept with each test; Maestro flows are uploaded with the app, run on the device and read back as a normal run with each flow's video link. Every run records its target, and Studio's **Run** picks it (and the Android device).
```
.\hive targets
.\hive run-web SIGNUP --tag smoke --target bs-win11-chrome
.\hive run-mobile SIGNUP --target bs-pixel7          (or a local device: --target android <device-id>)
```
Your test environment must be reachable from the internet for BrowserStack (BrowserStack Local, the tunnel, is not set up by TestHive yet). See it: `.\hive demo/phase5b/run.sh` (local stand-ins play BrowserStack; nothing is sent to it).

## Report and sign off (stage 6)
Bugs live in one register, `reports/bugs.csv` (`BUG-<MODULE>-<NNN>`, severity Blocker, Major or Minor, status Open, Fixed, Verified or Won't fix, the cases, where it was found, steps, expected, actual, evidence). A person's report links the bug to the failed tests in the open cycle; marking it Fixed asks for their retest. After the test cycle is approved, `report` builds one HTML file from it: TestHive's Go / No-go suggestion with its reasons (open Blocker bugs, open Major bugs or failures on P0/P1 cases, cases not run) and the risks to accept (quarantined or blocked tests, other open bugs), the results, the bugs, which requirements passed or fail, the pass rate per cycle and per run, and what the agents cost per stage. It opens offline, prints to PDF and embeds small failure screenshots. A named person then decides Go or No-go with the reason (Go is refused while a Blocker is open); the decision goes stale if the bugs or the cycle change. Approval freezes the report, the register and the decision in `reporting/baseline/`.
```
.\hive bug add SIGNUP --title "..." --severity Major --cases TC-SIGNUP-051 --steps "..." --expected "..." --actual "..." --by "<name>"
.\hive bug status SIGNUP BUG-SIGNUP-001 Fixed --note "build 1.0.1" --by "<name>"
.\hive report SIGNUP                                     reports/SIGNUP-report.html
.\hive report decide SIGNUP Go --reason "<why>" --by "<name>"; .\hive stage submit SIGNUP reporting; .\hive stage approve SIGNUP reporting --by "<name>"
```
In Studio: the **Reports** tab (the register, report a bug (also from a failed case in the Execution tab), change its status, build and open the report, record the decision). See it: `.\hive demo/phase6/run.sh` (the phase 5 cycle, then the report: TestHive suggests No-go, the product owner decides Go with the reason).

## TestHive Studio (no terminal needed)
Working as a team, or handing it to colleagues? See [docs/TEAM-GUIDE.md](docs/TEAM-GUIDE.md).

- **As a program (no Python, no terminal):** `testhive-studio-windows.exe` from the Releases page (or build it: `python scripts/build-studio.py`). It opens the last project, or asks for the project folder (**Open a project**, recent projects; **Switch project** in the sidebar); `--project <folder>` opens one directly.
- **Review mode:** on a PC without Claude Code or Git Bash the Run buttons are off and the command to hand over is shown; documents, answers, reviews, approvals and Excel work.
- **Explore the built product** (Sources): records each screen of the address in a hidden browser (free, no AI), logs in first with `TEST_USER` / `TEST_USER_PASSWORD` from `.env` when set, and shows what it found (**Open the report**). A module with only an address runs **Analyse the built product**. Module details save as you type.
- **Explore the app** (Sources, after uploading the APK): the analyst installs it on the Android device you pick (a phone with USB debugging, or an emulator; adb lists them) and walks its screens; Studio shows each recorded screen and the report.

`.\hive studio` opens a page in your browser, on this PC only. On it you can:
- **first opening:** describe the project (name, app, platforms, test environment addresses). Studio writes `PROJECT_BRIEF.md`, `CONTEXT.md` and the non-secret `.env` values; passwords and tokens are never typed into Studio;
- **New module:** give its code and title, and optionally the address of the built product (say whether it is a test environment);
- **Sources:** drop the requirement documents (PDF, Word, Excel, text, OpenAPI, design images; an APK for Android), check what masking would hide and tick the real names, then **Read the documents** (free, no AI). Open any document, or see the text TestHive read from it (what the analyst works from); **Remove** one, or bring back an earlier version or a removed document (**Earlier versions**, with who changed what). Nothing is deleted: a replaced or removed document is kept in `_old/`. If a document changes after the analysis was approved, **Next** says so and the module is no longer ready for automation until the analysis is reopened;
- **Every module** is in the sidebar with what it waits for. A module opens on one sentence saying what to do next, with its button, and a **stage track**: who approved each stage, what comes in later phases, and **Ready for automation** (the three approvals: requirements, test cases, tools; click it for what is still assumed);
- what to do next. Where an agent is needed, **Run** starts it in the background (Claude Code, on your plan, after you confirm): a panel shows its steps live, **Stop** ends it, and saving on that module pauses while it works. When the agent wants something its rules do not allow (a command outside `scripts/`, a file it may not write), the panel asks you: **Allow once** or **Deny**, with a note to the agent, signed with your name; no answer in 10 minutes is a No, and the hard rules (`.env`, the protected records, the blocked commands) are never asked. **Activity** lists every run with its result, time, cost and log (`runs/agents/`). The same command is still shown, to run it in Claude Code yourself if you prefer;
- **Analysis:** answer the analyst's questions, or ask your own; the **Requirements** tab lists what the analyst wrote. Once the analysis is approved its questions and answers are read-only until it is reopened;
- **Design:** review the test cases (**Accept**, **Change** with a comment, **Remove**), see each case's steps and expected result, see coverage and the open questions the cases rely on, add a case, or ask for more cases. Once the design is approved its cases are read-only until it is reopened. A requirement ID anywhere opens the requirement with its questions and cases;
- **Tools:** the decision matrix per test type, with the recommended tool; choose one per type (a reason when it is not the recommended one), set the criteria weights and your team's languages, and save to submit the stage. Read-only once approved;
- **Automation:** set up the test project, start the engineers, see each case's test (placeholder, written, stable), see the contract tests (up to date, stale or missing, and the endpoints that answer differently from the spec), run the tests by type and tag (**Contract tests** is one of the types), and open the last run's screenshots, videos and logs;
- **Reports:** the bug register (report a bug, change its status), build and open the test report with TestHive's Go / No-go suggestion, and record the decision, signed;
- **Execution:** start a test cycle on an environment, run its tests and retest the failures, record the cases run by hand, link bugs and mark them fixed, quarantine flaky tests with a reason; failed tests open their video, screenshots, trace or API log;
- **Approvals:** see whether a stage passes its rules, then approve, reject or reopen it, signed with your name; the decision log is there too;
- **Archive a module** added by mistake or no longer tested (bottom of Sources; you type its code and a reason): the module, its documents, questions, cases, baselines and logs move to `archive/<MODULE>-<time>/`, and **Restore** on the start page puts everything back. The same from a terminal: `.\hive stage archive <MODULE> --by "<name>" --comment "<why>"` and `.\hive stage restore <MODULE>-<time> --by "<name>"`.

Every module and tab has its own address (for example `#/SIGNUP/design`), so a refresh or a bookmark opens the same place. Studio works on a phone or tablet too, in light or dark.

Studio writes the same files with the same rules as the Excel workbooks (which still work: download and upload them from the page) and as the `stage` script. A workbook works as a review pack for people with Excel only: send it, they fill the yellow columns and send it back, you upload it. Only the rows they changed are taken, so a pack that comes back late, or two copies from two reviewers, never undo newer answers or reviews; a row changed in the pack and also in TestHive since is refused and listed. If an agent or Excel saved in the meantime, Studio refuses to overwrite and reloads. Agents started by Studio can run only the TestHive scripts and edit files: anything that would need your permission fails and is reported (allowing it from the page comes later). Approvals always stay with you. Keep its window open while you use it; Ctrl+C stops it. Try it: `.\hive demo/phase2d/run.sh` presses Run through the whole flow with recorded agents (free; `--live` for real ones); `.\hive demo/phase2c/run.sh` starts from an empty project (upload the files in `demo/phase1/sources/`); `.\hive demo/phase2b/run.sh` opens a project whose cases wait for approval.

## Scripts
Run `.\hive` with no arguments for the full list with one-line descriptions. The main ones:

| Script | What it does |
|---|---|
| `setup` | Checks and installs the tools. `--check` (default), `--install`, `--web`, `--ocr` |
| `selftest` | Proves TestHive works on this machine |
| `init-project` | Creates the project files from `templates/` |
| `stage` | Stage gates and approvals; `archive` / `restore` move a module out of the project and back (nothing is deleted) |
| `ingest` | Turns a module's documents (text, PDF, Word, Excel, OpenAPI, images) into text for the analyst; `--mask` hides personal data first |
| `explore-web` / `explore-android` | Record what a built web app (URL) or Android app (APK) actually does, as observed behaviour; the web one logs in with `TEST_USER` / `TEST_USER_PASSWORD` from `.env` when set; `explore-android ... packages` lists the apps installed on the device, to find the one just installed |
| `check-analysis` | Checks the requirement and gap registers; `--for-approval` checks they are ready to approve |
| `analysis-workbook` / `import-answers` | Excel workbook of questions for the business, and reading the answers back |
| `score-analysis` | Benchmark: how many planted gaps the analyst found |
| `check-design` | Checks a module's test cases against the approved requirements (coverage, negatives, boundaries); `--set-priority`, `--for-approval` |
| `design-workbook` / `import-review` | Excel workbook for reviewing the cases, and reading your decisions, edits, new cases and requests back |
| `design-impact` | Lists (and with `--apply` flags) the cases affected when approved requirements change |
| `score-design` | Benchmark: how many expert test conditions the cases cover |
| `scaffold` / `check-automation` | Stage 4: placeholders for the approved tools, and the automation gate (`--for-approval` needs every test stable) |
| `contract` | Stage 4: builds the contract tests of a module from its OpenAPI spec (`run-api <MODULE> --contract` runs them) |
| `tool-advice` | Stage 3: the decision matrix per test type, the choice (`choose`), its check (`check`) and the project's weights and team skills (`settings`) |
| `studio` | Opens TestHive Studio in the browser (local only); `--project <folder>`, `--port N`, `--no-browser` |
| `check-private` | Fails if a private name from your git-ignored `.private-names` list is in a file that would be published |
| `run-mobile` / `run-api` / `run-web` | Run a module's tests (`--tag smoke`; `--ids` for web and API; `--target <name>` for web and mobile, see `targets`; `run-mobile --app <apk|ipa>` for BrowserStack; `run-api --contract`; `TEST_ENV=<name>` loads `.env.<name>`); each run is stored in `runs/` with its evidence and target |
| `bug` / `report` | Stage 6: the bug register (add, status, list); the HTML test report, the Go / No-go decision (`decide`) and its check |
| `targets` | Where the tests can run (targets.json), the Android devices adb sees, and whether the BrowserStack keys are set |
| `cycle` / `retest` | Stage 5: the test cycle (start, status, results by hand, bugs, fixed, quarantine, check), and rerunning its failures (`retest` takes `--target`) |
| `stable` | Runs a module 3 times; only cases that pass every time count as done |
| `gate` | Definition-of-done check on the case sheet |
| `mask` | Hides personal data in documents and screenshots before Claude sees them (Arabic + English) |
| `collect-run`, `digest-failures`, `check-intake`, `check-devices`, `reset-app`, `gen-user` | Helpers used by the agents and by you |

## Privacy and safety
- `.env` holds your app ids and URLs; it is git-ignored and the agents are blocked from reading it (`.claude/settings.json`).
- Agents cannot `git push`; you publish.
- Two Claude Code hooks (`.claude/settings.json`): every file Claude edits is checked at once (shell, Python, JSON, JavaScript, PowerShell syntax; no Windows line endings where they break things), and Claude cannot edit the approval records (`workflow/APPROVALS.md`, `workflow/state.json`, the baselines, the test cycles in `execution/`, the decisions and baselines in `reporting/`, the bug register): only `stage`, `cycle`, `bug` and `report` write them.
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
docs/                TEAM-GUIDE, FORMATS, TROUBLESHOOTING, MAINTAINING, ROADMAP
demo/                one runnable demo per phase       studio/  the Studio page: index.html, style.css, fonts/, app.js and js/ (one file per screen), served by scripts/lib/studio.py
mobile/ api/ web/    test code per platform
requirements/sources/  your input documents          analysis/  requirements and gap registers
workflow/            state.json, APPROVALS.md, BOARD.md, intake/     test-cases/  TestCases.csv, requests.csv, baseline/
tools/               choices.csv, settings.json, baseline/ (the approved tool choice per module)
automation/          baseline/ (the approved tests per module: files and their checksums)
reporting/           <MODULE>/decision.json (Go / No-go), baseline/ (the signed-off report and bug register)
execution/           <MODULE>/C<n>/ (a test cycle: cycle.json, log.csv), baseline/ (the approved cycle's results)
runs/                one folder per test run           reports/ reviews/  reports and reviews
skills/testhive/     optional /testhive skill for the Claude app
```

## More documentation
- [QUICKSTART.md](QUICKSTART.md): the same start, with more detail per step.
- [docs/TEAM-GUIDE.md](docs/TEAM-GUIDE.md): handing TestHive to colleagues: who needs what, the Studio program, sharing the project with git, Excel-only reviewers.
- [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md): common errors and fixes.
- [docs/FORMATS.md](docs/FORMATS.md): every file format (state, registers, runs, masking).
- [docs/MAINTAINING.md](docs/MAINTAINING.md): how TestHive is built, how to change it safely, how to release.
- [docs/ROADMAP.md](docs/ROADMAP.md): what is built and what comes next.
- [CHANGELOG.md](CHANGELOG.md): what changed in each version.

## License
MIT. See [LICENSE](LICENSE).
