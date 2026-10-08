# TestHive quickstart

## 1. Get the template
Click **Use this template** on GitHub (or clone/download), then rename the folder for your project.

## 2. Install the tools
- Maestro CLI, Android platform-tools (`adb`), Node.js, and `npm i -g newman`.
- Claude Code installed, or the Claude desktop app.

## 3. Initialise the project
```
bash scripts/init-project.sh "My Project"
```
Windows PowerShell: `powershell -File scripts/init-project.ps1 "My Project"`

Then edit `PROJECT_BRIEF.md` and `.env` (app id, URLs; never commit `.env`).

## 4. Connect a device
- Android: enable USB debugging, plug in, then `bash scripts/check-devices.sh` must show the device as `device`. Or start an emulator.
- iOS: needs a Mac or a device farm. See `mobile/ios/README.md`.

## 5. Start the team
- Claude Code: open the folder and run `claude --agent testhive-lead`
- Claude desktop app: connect the folder and ask Claude to act as the TestHive Lead using the agents in `.claude/agents/`.

Optional: install the `/testhive` skill from `skills/testhive/SKILL.md` so you can recall the team anywhere by typing `/testhive`.

Give the Lead your first module and its business rules. Example:
> Module: Signup. Platform: Android. Rules: <paste>. Explore the app, write the cases, automate the P0/P1 flows, review, and report.

## 6. Add more later
Send the Lead a new module and rules. It creates `mobile/flows/<module>/`, new case IDs and board rows. Existing flows are not touched.

## Handy commands
```
bash scripts/check-devices.sh
bash scripts/reset-app.sh android <package>
bash scripts/run-mobile.sh <module>
bash scripts/run-api.sh <module>
```
