# TestHive quickstart

## 1. Get the template
Click **Use this template** on GitHub (or clone/download), then rename the folder for your project.

## 2. Install the tools (one step)
`bash scripts/setup.sh --check` shows what is missing; `bash scripts/setup.sh --install` installs it. On Windows use `powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -Check` (or `-Install`); run every other script from Git Bash. Add `--web` (`-Web`) for Playwright. TestHive also runs this check itself the first time you call it in a project. Manual steps (phone USB debugging, Xcode on Mac) are printed at the end.

What it covers, if you prefer to install by hand:
- Maestro CLI, Java 17+, Android platform-tools (`adb`), Python 3, Node.js, and `npm i -g newman`.
- Claude Code installed, or the Claude desktop app.

## 3. Initialise the project
```
bash scripts/init-project.sh "My Project"
```
Windows PowerShell: `powershell -ExecutionPolicy Bypass -File scripts/init-project.ps1 "My Project"`

Then edit `CONTEXT.md`, `PROJECT_BRIEF.md` and `.env` (app id, URLs; never commit `.env`).

## 4. Connect a device
- Android: enable USB debugging, plug in, then `bash scripts/check-devices.sh` must show the device as `device`. Or start an emulator.
- iOS: needs a Mac or a device farm. See `mobile/ios/README.md`.

## 5. Start the team
- Claude Code: open the folder and run `claude --agent testhive-lead`
- Claude desktop app: connect the folder and ask Claude to act as the TestHive Lead using the agents in `.claude/agents/`.

Optional: install the `/testhive` skill from `skills/testhive/SKILL.md` so you can recall the team anywhere by typing `/testhive`.

Give the Lead your first module and its business rules. Example:
> Module: Signup. Platform: Android. Rules: <paste>. Explore the app, write the cases, automate the P0/P1 flows, review, and report.

## Call one agent
`/th-mobile <task>` in Claude Code, or `bash scripts/th.sh mobile "<task>"`. Agents: lead, manual, mobile, api, web, data, triage, review.

## 6. Add more later
Send the Lead a new module and rules. It creates `mobile/flows/<module>/`, new case IDs and board rows. Existing flows are not touched.

## Handy commands
```
bash scripts/check-devices.sh
bash scripts/reset-app.sh android <package>
bash scripts/run-mobile.sh <module>          # PLATFORM=ios, INCLUDE_TAGS=smoke, EXCLUDE_TAGS=known-bug
bash scripts/run-api.sh <module>
bash scripts/run-web.sh <module>
bash scripts/digest-failures.sh              # failures only -> reports/digest.md
bash scripts/stable.sh mobile <module>       # 3 runs in a row -> reports/stable-<ID>.txt
bash scripts/gate.sh                         # definition of done
```
