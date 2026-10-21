# TestHive

A reusable team of AI QA agents for Claude. It plans, writes, automates and reviews tests for **mobile (Android + iOS, Maestro)**, **API/backend (Postman + Newman)** and **web (Playwright)**, and it scales one module at a time.

![How TestHive works](docs/testhive-diagram.png)

## The team (8 agents)

| Agent | Model | Role |
|---|---|---|
| `testhive-lead` | Sonnet | Plans, briefs, owns the board, signs off. Never writes tests. |
| `manual-tester` | Sonnet | Explores the app, writes test cases with exact expected results. |
| `mobile-automation-engineer` | Sonnet | Maestro flows for Android and iOS. |
| `api-backend-test-engineer` | Sonnet | Postman collections run with Newman. |
| `web-automation-engineer` | Sonnet | Playwright + TypeScript. Idle until a web flow exists. |
| `test-data-env-manager` | Haiku | Test users, resets, environment files. Scripts first. |
| `defect-triage` | Sonnet | Runs on failures only: test defect or real bug, writes bug reports. |
| `qa-reviewer` | Opus | Independent audit and module sign-off. |

## How it works
Plan -> cases -> automate P0/P1 first -> run -> triage failures -> review -> fix -> stability run (3 passes in a row) -> reports.

## Token-saving design
- Idle agents (web) are not started until needed.
- Repetitive setup is done by scripts in `scripts/`, not by agents.
- Defect Triage runs only on failures.
- Interim reviews use Sonnet; Opus is used for module sign-off.
- Each agent has only the tools it needs; runs print failures only; screen hierarchy is read only when a step fails.
- `CONTEXT.md` (30 lines) is read by agents instead of the full brief.
- Mobile screen ids are cached once in `mobile/screens/` and reused.
- `scripts/digest-failures.sh` trims run output to failures only before triage.
- `templates/MODULE_INTAKE.md` + `scripts/check-intake.sh`: structured business input, with a check for gaps and uncovered rules.
- `scripts/stable.sh` runs a module 3 times and writes the proof (`reports/stable-<ID>.txt`) for every case that passed all 3.
- `scripts/gate.sh` is a hard definition-of-done check; `scripts/selftest.sh` (run in CI on Linux, Windows and macOS) proves the template works.
- Short briefs by case ID, one CSV for all cases, shared subflows and data.

## One-step setup
`bash scripts/setup.sh --check` lists missing tools; `--install` installs them after you agree. TestHive runs the check automatically on first use in a project.

Windows: `powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -Check` (or `-Install`). Windows blocks `.ps1` files by default, so the `-ExecutionPolicy Bypass` part is needed. All other scripts are bash.

**Windows (PowerShell or cmd):** every `bash scripts/<name>.sh ...` command in these docs can be typed as `.\hive <name> ...`, for example `.\hive stage status SIGNUP` or `.\hive demo/phase0/run.sh`. `hive.cmd` finds Git Bash by itself. To type `bash` directly instead, run `setup.ps1 -AddBashToPath` once.

## Use it for your own project
1. On GitHub click **Use this template** (or clone), and open the folder.
2. Run the setup check above and install what is missing.
3. `bash scripts/init-project.sh "My Project"` creates the board, the case sheet, `CONTEXT.md` and `.env`.
4. Fill `CONTEXT.md` and `.env` (app id, URLs), and connect a device: `bash scripts/check-devices.sh`.
5. Copy `templates/MODULE_INTAKE.md` to `workflow/intake/<module>.md` and fill in the business rules.
6. Start the Lead: `claude --agent testhive-lead`, and give it the module name.

Handing it to a colleague: send them the repo link and these 6 steps. Nothing else is needed; `.env` stays on each machine.

## Stages and approvals
Each module moves through six stages: analysis, design, tools, automation, execution, reporting. A stage cannot start until a named person approves the one before it, and every decision is logged in `workflow/APPROVALS.md`.
```
bash scripts/stage.sh init SIGNUP
bash scripts/stage.sh status SIGNUP
bash scripts/stage.sh approve SIGNUP analysis --by "<your name>" --comment "..."
```
- `scripts/collect-run.sh` stores each test run in `runs/<RUN-ID>/` in one format for every tool, with its evidence.
- `scripts/mask.sh` hides names, emails, phones, national IDs, IBANs and card numbers (Arabic and English) before documents are sent to Claude, and restores them afterwards. Numbers are checked (Luhn, mod-97, ID check digit) so order numbers are not hidden by mistake. `suggest` proposes names to hide, `review` shows every match in context, `.mask-allow` lists values never to hide, and images (screenshots, Figma exports) are blacked out with OCR once Tesseract is installed (`setup -Ocr`).
- Every `run-mobile.sh`, `run-api.sh` and `run-web.sh` run is stored automatically in `runs/`.
- Formats: [docs/FORMATS.md](docs/FORMATS.md). Demo: `bash demo/phase0/run.sh` (Windows: `.\hive demo/phase0/run.sh`).

## Requirements
- [Claude Code](https://claude.com/claude-code) (or Claude desktop app with the project folder connected)
- [Maestro CLI](https://maestro.mobile.dev), Android platform-tools (`adb`)
- Node.js and `npm i -g newman` for API runs; Python 3 and Java 17+ (used by the scripts and by Maestro)
- iOS: a Mac (or cloud Mac / device farm). Windows cannot run the iOS Simulator.

## Quick start
See [QUICKSTART.md](QUICKSTART.md).

## Layout
```
skills/testhive/  the /testhive recall skill (copy to your Claude skills to use it)
.claude/agents/   the 8 agent definitions
.claude/commands/ /th-* slash commands, one per agent
.claude/settings.json  allowed commands (scripts, maestro, adb, newman); blocks reading .env and git push
templates/        project brief, CONTEXT, module intake, board, test case sheet, bug and test report, env example
mobile/           Maestro flows, subflows, data, android/ios notes
api/              Postman collections and environments
web/              Playwright config (installed only when needed)
scripts/          th (call one agent), init, setup, device check, reset, run-mobile/api/web, digest-failures, stable, gate, selftest
workflow/         BOARD.md (created by init)
test-cases/       TestCases.csv and exploration notes (created by init)
reviews/ reports/ review files and run output
```

## Call an agent on its own
| Agent | Slash command | Launcher |
|---|---|---|
| testhive-lead | `/th-lead` | `bash scripts/th.sh lead` |
| manual-tester | `/th-manual` | `bash scripts/th.sh manual` |
| mobile-automation-engineer | `/th-mobile` | `bash scripts/th.sh mobile` |
| api-backend-test-engineer | `/th-api` | `bash scripts/th.sh api` |
| web-automation-engineer | `/th-web` | `bash scripts/th.sh web` |
| test-data-env-manager | `/th-data` | `bash scripts/th.sh data` |
| defect-triage | `/th-triage` | `bash scripts/th.sh triage` |
| qa-reviewer | `/th-review` | `bash scripts/th.sh review` |

- In a Claude Code session: `/th-mobile automate TC-SIGNUP-001..005`, or mention `@agent-manual-tester`.
- `/th-lead` makes the current session act as the Lead (a subagent cannot start other agents). For a full module, `claude --agent testhive-lead` is the better start.
- One-shot from a terminal or CI: `bash scripts/th.sh mobile "automate TC-SIGNUP-001"` (Windows: `.\scripts\th.ps1 mobile "..."`). With no task text it opens an interactive session with that agent. One-shot runs cannot ask for permission, so they accept file edits and run only the commands allowed in `.claude/settings.json`.
- A standalone agent reads CONTEXT.md and workflow/BOARD.md itself and sees only its own files and your brief. Record results on the board so the others can pick them up.

## Rules the team follows
- Verify against the real app; never assume behaviour.
- Cases: `TC-<MODULE>-<NNN>` (an extra part is allowed, e.g. `TC-SIGNUP-API-001`), atomic steps, exact expected results, independent. Priority is P0 to P3.
- Mobile selectors: id, then accessibility label, then text. No fixed sleeps.
- Real bugs are reported and the test keeps its assertion (tagged `known-bug` with the bug ID). Assertions are never weakened.
- A test is done only when it passes 3 times in a row: `bash scripts/stable.sh mobile|api|web <module>`.
- The case sheet can be edited in Excel: save it as "CSV UTF-8".

## License
MIT. See [LICENSE](LICENSE).
