# Changelog

Versions follow `MAJOR.MINOR.PATCH`. The current version is in `VERSION`.

## 0.7.1 (2026-10-22)
- Claude Code hooks in `.claude/settings.json` (`scripts/hooks/`): `check_edit` checks every file Claude edits (bash, Python, JSON, JavaScript, PowerShell syntax; no carriage returns where LF is required); `guard_records` refuses direct edits of `workflow/APPROVALS.md`, `workflow/state.json` and the baselines (also with other capitals or `..` on Windows).
- Maintainer tools: skills `/release-phase` and `/rerecord-demo`; agents `studio-security-reviewer` and `docs-consistency-reviewer` (read-only); `check-private` with a git-ignored `.private-names` list.
- `.gitattributes` keeps `.html`, `.mjs`, `.js` on LF; selftest covers the hooks and the private-name check (with a planted name: the first version passed falsely when Git Bash's grep crashed).
- Security fixes from the first studio-security-reviewer run: project fields and module titles cannot add lines to `.env`, the brief or CONTEXT.md; agents started from Studio get only `bash scripts/*` (maestro, adb, newman, npx denied), cannot approve, reject or reopen (`TH_JOB`), and cannot edit `scripts/`, `.claude/`, `templates/`, `.env` or the masking files; a job that hangs silently is stopped by a timer; signer names and comments cannot break the approvals log; safer request parsing, token comparison, temp-file cleanup, write locking, Windows device names, atomic uploads, stricter CSP.

## 0.7.0 (2026-10-22)
- Phase 2d, run the agents from Studio: every step that needs an agent has a Run button under Next (analyst first pass and re-check, manual-tester design, QA pre-review, fixing the findings, re-check of the human review, update after a requirement change), with a confirmation (time, plan usage). A live job panel shows the agent's steps; Stop ends it (the whole process tree); saving on the module pauses while it works; one job per module. Activity tab: every run with status, time, cost and log, saved in `runs/agents/` (git-ignored). Run exploration button for the web address.
- `scripts/lib/jobs.py` (background jobs, Claude Code stream-json); Studio stops running agents when it closes. Agents started from Studio can run only `bash scripts/*` and edit files.
- `demo/phase2d/run.sh`: the whole flow through Run buttons with a recorded stand-in for Claude Code (free; `--live` for real agents; `--check` for CI, with a browser click-through when web tools are installed).

## 0.6.0 (2026-10-22)
- Phase 2c, Studio setup and intake: first opening asks for the project (writes PROJECT_BRIEF, CONTEXT and the non-secret .env values: APP_ID, TEST_ENV, BASE_URL, API_BASE_URL); New module (code, title, URL of the built product and whether it is a test environment, masking choice); Sources tab: drag-and-drop upload of documents (and an APK), earlier versions kept in `_old/`, personal-data check (tick real names, untick false matches), Read the documents (`ingest`), reopen offer when documents change after approval; "Ready for automation" card per module.
- The analyst command shown under Next includes the URL / APK to explore. Upload checks: file types, size (25 MB, APK 300 MB), safe names.
- `ingest.py` importable and skips `_old/`; `mask.py` adds `suggest_names` and `add_lines`; agents may not start Studio (`.claude/settings.json`).
- Demo `demo/phase2c/run.sh` (empty project; `--check` for CI, with a browser click-through when web tools are installed).

## 0.5.0 (2026-10-22)
- Phase 2b, TestHive Studio lite: `.\hive studio` opens a local web page (127.0.0.1, access token per start) to see the stages of every module and what comes next, answer and ask questions, review cases (Accepted / Change / Remove, add cases, request cases), see coverage and open questions, and approve, reject or reopen stages; workbooks can be downloaded and uploaded from it. Python standard library and one HTML page: nothing new to install.
- Studio and the Excel imports share the same code (`analysis.apply_answers`, `design.apply_review`); approvals go through `stage.sh`. A save from an out-of-date page is refused.
- Demo `demo/phase2b/run.sh` (opens Studio on the fictional project; `--check` drives it without a browser and, with web tools, clicks through the screens with `web/studio-smoke.mjs`); selftest and CI cover Studio.

## 0.4.0 (2026-10-22)
- Phase 2, test design: the `manual-tester` designs cases from the approved analysis baseline with named techniques (equivalence, boundary, decision table, state transition, error guessing, use case, checklist), Risk, Tags (smoke, sanity, regression, e2e), requirement links and assumptions on open gaps; `qa-reviewer` adds a design pre-review (on Sonnet) before the human sees the cases.
- `check-design` (coverage of every requirement, negative cases for P0 rules, boundary cases for limits, allowed values, vague results; `--set-priority` applies the risk rule; `--for-approval`), `design-workbook` and `import-review` (Excel review: Accepted / Change / Remove, direct edits, new cases, requests), `design-impact` (cases affected by changed requirements), `score-design`.
- Case sheet: new columns Requirements, Technique, Risk, Tags, Assumption, Origin, Review, Review Comment; Type is now Positive, Negative, Localization, Accessibility, Security or Performance (Functional still read). New `test-cases/requests.csv`. Older sheets stay readable.
- Stage gate: submitting or approving the design runs `check-design --for-approval`; approval freezes `test-cases/baseline/<MODULE>/v<n>/`; a stage can be submitted only while the previous one is approved; new `stage reopen` for requirements that change after approval.
- Demo `demo/phase2/run.sh` (recorded or `--live`), continuing the fictional Nakhla Rewards SIGNUP module; CI runs it. Docs: README design section, FORMATS (case sheet, requests, design workbook, design baselines, condition key), TROUBLESHOOTING, MAINTAINING.

## 0.3.0 (2026-10-22)
- Phase 1, business analysis: `business-analyst` agent and `/th-analyst`; `ingest` (text, PDF, Word, Excel, CSV, OpenAPI/Swagger, images; optional masking); `explore-web` (Playwright with Edge, no browser download) and `explore-android` (adb + UI dumps) record a built product as Observed behaviour; `check-analysis`, `analysis-workbook`, `import-answers`, `score-analysis`.
- Stage gate: submitting or approving the analysis requires every High gap closed and no unreviewed answer; approval freezes the registers as `analysis/baseline/<MODULE>/v<n>/`.
- Benchmark: fictional Nakhla Rewards documents with 23 planted gaps; a recorded analyst run for a free, repeatable demo (`demo/phase1/run.sh`), `--live` to run the agent.
- `requirements.txt` adds pyyaml; `setup --web` uses the installed Edge on Windows instead of downloading Chromium.
- Docs: README analysis section, FORMATS (sources, exploration, workbook, baselines, answer key), TROUBLESHOOTING (folder trust for one-shot runs), MAINTAINING (benchmark, re-recording).

## 0.2.0 (2026-10-21)
- Phase 0 foundations: stage gates and approval log (`stage`), common run format and run history (`collect-run`, `runs/`), masking of personal data in text and screenshots, Arabic and English (`mask`), requirement and gap register templates, `docs/FORMATS.md`, `demo/phase0/`.
- Windows: `hive.cmd` launcher (`.\hive <script>`), `setup` runs `setup.ps1` on Windows, `-Ocr` and `-AddBashToPath`, clear message when an installer needs admin rights.
- Run scripts store every run automatically; `stable` runs are kept as history.
- Hardening: working-Python detection, LF line endings, gate accepts `TC-X-API-001` IDs and Excel's BOM, checks priority and real assertions; `stable.sh`; Lead has the setup check and stage gates; reviewer can write reviews; `.claude/settings.json` allow/deny list; CI on Linux, Windows and macOS.
- Docs: README rewritten for newcomers, `docs/TROUBLESHOOTING.md`, `docs/MAINTAINING.md`, `docs/ROADMAP.md`, `requirements.txt`.

## 0.1.0 (2026-10-08 to 2026-10-10)
- First public version: 8 agents, templates, scripts, diagram, `/testhive` skill; token-saving context, screen cache, failure digest, gate and selftest CI.
