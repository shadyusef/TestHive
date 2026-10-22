# TestHive quickstart

Step by step, from nothing to the team working on your first module. Commands are for **Windows PowerShell**; on macOS/Linux type `bash scripts/hive.sh` where you see `.\hive`.

## 1. Get your copy
- Install Git if you do not have it (Windows: `winget install --id Git.Git -e`), then open a new terminal.
- On GitHub open the TestHive repository, click **Use this template**, and create a **private** repository for your project. Clone it and `cd` into the folder (the one containing `hive.cmd`).

## 2. Install the tools
```
.\hive setup --check
```
Each line says `OK`, `MISSING` or `OPTIONAL`. Install what is missing:
```
.\hive setup --install            add --ocr for screenshot masking, --web for web tests
```
Then **open a new terminal** (so the new tools are found) and run `.\hive setup --check` again until it says `All prerequisites present.`

What it installs: Python 3 and its packages (`requirements.txt`), Node.js, Java 17+, Maestro, Android platform-tools (`adb`), Newman, Claude Code; optionally Tesseract OCR with Arabic and Playwright. Some installers need **administrator rights** on Windows; see [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) if one is cancelled.

## 3. Verify
```
.\hive selftest
```
Must end with `SELFTEST PASS`. Optional, to see the foundations at work in a temporary folder: `.\hive demo/phase0/run.sh`.

## 4. Create your project files
```
.\hive init-project "My Project"
```
This creates `PROJECT_BRIEF.md`, `CONTEXT.md`, `.env`, `workflow/BOARD.md`, `test-cases/TestCases.csv`, `analysis/requirements.csv`, `analysis/gaps.csv` and the working folders. Existing files are never overwritten.

## 5. Describe your app
- `CONTEXT.md` (max 30 lines; agents read it instead of long documents): app name, package/bundle id, platforms, environment, how test users are made, known quirks.
- `.env` (stays on your PC, never committed, agents cannot read it): `APP_ID`, `TEST_ENV`, URLs, device ids.
- Put requirement documents in `requirements/sources/`. If they contain personal data, mask them first (section 8).

## 6. Connect a device
- Android: enable Developer options and USB debugging, plug in, accept the prompt on the phone, then `.\hive check-devices` must list it as `device`. An emulator also works.
- iOS: needs a Mac or a device farm; see `mobile/ios/README.md`.

## 7. Start the team
```
claude --agent testhive-lead
```
The first start asks you to sign in to Claude and whether you **trust this folder**: answer yes (TestHive's allowed-commands list only works in a trusted folder). Put the module's documents in `requirements/sources/<MODULE>/`, then tell the Lead for example:
> Module SIGNUP, web and API. The documents are in requirements/sources/SIGNUP/.

The Lead shows a plan and waits for your approval. Follow the stages with `.\hive stage status SIGNUP`; approve with `.\hive stage approve SIGNUP <stage> --by "<your name>"`.

To call one agent only, type in Claude Code `/th-mobile <task>` (also `/th-manual`, `/th-api`, `/th-web`, `/th-data`, `/th-triage`, `/th-review`, `/th-lead`), or from a terminal `.\hive th mobile "<task>"`.

## 8. Analyse your first module
Put the module's documents in `requirements/sources/<MODULE>/`, or have a URL / APK of the built app ready. Then follow **Analyse a module** in the README: the analyst writes the requirements and its questions, you answer them in `analysis/<MODULE>-analysis.xlsx`, it re-checks, and you approve. To see the whole loop first: `.\hive demo/phase1/run.sh`.

## 8b. Design its tests
After you approve the analysis, follow **Design the tests** in the README: the manual-tester writes cases linked to the approved requirements, the reviewer checks them, you review them in `test-cases/<MODULE>-design.xlsx` (accept, change, remove, add your own, request more), it re-checks, and you approve. To see it first: `.\hive demo/phase2/run.sh`.

## 8c. Prefer a browser to a terminal?
After steps 1 to 3, `.\hive studio` opens TestHive Studio instead of steps 5 to 8: the first page asks for the project details, then **New module**, drop the documents in **Sources**, **Read the documents**, and copy the analyst command shown under **Next** into Claude Code. Answer the questions, review the cases and approve the stages in Studio too. See it first with `.\hive demo/phase2c/run.sh` (an empty project).

## 9. Mask personal data (when documents contain it)
```
.\hive mask suggest requirements/sources/prd.txt     lists likely names; put the real ones in .mask-terms
.\hive mask review  requirements/sources/prd.txt     shows every match in context; wrong ones go in .mask-allow
.\hive mask mask    requirements/sources/prd.txt requirements/sources/prd.masked.txt
```
Screenshots work the same way (`.png`, `.jpg`) once Tesseract is installed. `.mask-terms`, `.mask-allow` and `.mask-map.json` stay on your PC.

## 10. Add more modules later
Repeat steps 7 to 8b with a new module. Each module gets its own stages, case IDs and test folder; existing work is not touched.

## Handy commands
```
.\hive                                list all scripts with a one-line description
.\hive check-devices
.\hive reset-app android <package>
.\hive run-mobile <module>            env: PLATFORM=ios, INCLUDE_TAGS=smoke, EXCLUDE_TAGS=known-bug
.\hive run-api <module>
.\hive run-web <module>
.\hive digest-failures                failures only -> reports/digest.md
.\hive stable mobile <module>         3 runs in a row -> reports/stable-<ID>.txt
.\hive gate                           definition of done
```
