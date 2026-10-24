# Troubleshooting

First run these two; most problems show up in them:
```
.\hive setup --check      (Git Bash: bash scripts/hive.sh setup --check)
.\hive selftest
```

| Symptom | Cause | Fix |
|---|---|---|
| `bash : The term 'bash' is not recognized` | PowerShell does not know Git Bash (Git only adds `git` to PATH) | Use the launcher: `.\hive <script> ...`. Or run `setup.ps1 -AddBashToPath` once and open a new terminal. |
| `.\hive : The term '.\hive' is not recognized` | The terminal is not in the TestHive folder | `cd` to the project folder (the one with `hive.cmd`). |
| `Git Bash was not found` | Git is not installed | `winget install --id Git.Git -e`, then open a new terminal. |
| `running scripts is disabled on this system` | Windows blocks `.ps1` files by default | Use `.\hive setup ...`, or `powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -Check`. |
| `Python was not found; run without arguments to install from the Microsoft Store` | `python3` on Windows is a Store shortcut, not Python | Nothing to do if `setup --check` shows python OK: scripts pick a Python that really works. Otherwise install Python with `setup --install`. |
| `setup --check` still shows a tool missing right after installing | The terminal has the old PATH | Close and open a new terminal, then check again. |
| `The operation was canceled by the user` / `0x800704c7` while installing | The installer needs administrator rights and the Windows admin prompt was declined or is blocked | Accept the admin prompt, or ask IT to install the named winget package (e.g. `UB-Mannheim.TesseractOCR`). Everything except screenshot masking works without it. |
| `No applicable installer found` (winget) | That package has no per-user installer | Same as above: needs admin rights. |
| Image masking says `Tesseract is not installed`, or the demo skips step 11 | Tesseract (optional) is missing | `.\hive setup --install --ocr` (needs admin on Windows). |
| Arabic text in screenshots is not masked | Arabic OCR data missing, or the terminal was opened before setup set `TESSDATA_PREFIX` | Run `.\hive setup --install --ocr` again and open a new terminal; `tesseract --list-langs` must show `ara`. |
| `BLOCKED: analysis is not approved yet` | A stage gate: the previous stage needs a human approval | `.\hive stage status <MODULE>` shows what is waiting; approve with `.\hive stage approve <MODULE> <stage> --by "<name>"`. |
| `approve needs --by <name>` / `reject needs --comment` | Decisions must be signed, rejections explained | Add `--by "<your name>"` (and `--comment "..."` for a reject). |
| Claude says "Edit check failed for <file>" | The `check_edit` hook found a syntax error or a Windows line ending in a file Claude just wrote | Nothing to do: Claude reads the message and fixes the file. If it repeats, fix the line it names by hand |
| BLOCKED: "the execution of <MODULE> is approved" (or awaiting approval), or "No test cycle for <MODULE> yet" | A cycle is frozen while it waits for approval and after it, and starts only after the automation is approved | Reject or reopen the execution stage (`.\hive stage reject\|reopen <MODULE> execution ...`), or start a cycle: `.\hive cycle start <MODULE> "<name>" --env <name> --by "<you>"` |
| Claude says "Refused: workflow/... is not edited directly" | The `guard_records` hook: approval records and baselines are written only by `stage`, test cycles only by `cycle` | Use `.\hive stage ...` (or Studio's Approvals tab); approvals are made by a named person |
| `PRIVATE CHECK FAIL` | A name from your `.private-names` list is in a file that would be published | Remove or replace it in the files listed, then run `.\hive check-private` again |
| `DESIGN NOT OK` | The cases break a design rule (a requirement without a case, a P0 rule without a negative case, a bad value) | Each line names the case or requirement. Ask the manual-tester to fix it, or fix the CSV and run `.\hive check-design <MODULE>` again |
| `IMPORT REFUSED, nothing changed` (import-review / import-answers) | A row in the workbook is invalid, e.g. Review = Change without a comment, a value not in the list | Each line names the row. Fix it in Excel, save, import again: nothing was half-imported |
| `BLOCKED: analysis is not approved (it was reopened)` | Requirements were reopened after the design started | Finish and approve the analysis again, then run `.\hive design-impact <MODULE> --apply` and update the flagged cases |
| Studio opens on another port than 8765, or the page says the access key is missing | 8765 was in use, or the page was opened without the address Studio printed | Use the full address printed in the Studio window (it contains `?t=...`); restart `.\hive studio` for a new one |
| Studio: "the questions/cases changed since you opened the page" | An agent, Excel or another tab saved the same file | Nothing was lost: the page reloads; make your change again |
| Studio: "Explore needs the web tools on this PC" | The web tools (Playwright library) are not installed in this project folder | At a terminal in the project: `.\hive setup --install --web`, then reload Studio |
| Explore: "NOT EXPLORED: ... could not be opened" | The hidden browser could not load the address (wrong address, VPN or company network, or a site that blocks automated browsers) | Open the address in Edge on the same PC; if it opens there but not in Explore, give the analyst documents instead, or ask IT about the network |
| Studio: the Run buttons are off and the top bar says "Review mode" | Claude Code or Git Bash is not on this PC (documents, answers, reviews, approvals and Excel still work) | Hand the command shown under the module title to someone with Claude Code, or run `.\hive setup --install`, type `claude` once to sign in, then restart Studio |
| Studio: "That folder is not a TestHive project" | The folder has no `scripts/` and `templates/` of TestHive | Clone your team's project repository and open that folder (see docs/TEAM-GUIDE.md) |
| Studio: "An agent is working: wait until it finishes ... before opening another project" | Switch project waits for a running agent | Wait, or stop it in the module's job panel |
| "Another stage command is still running (workflow/state.json.lock)" | Two stage commands at the same moment | Try again; a lock left by a crashed command is removed after 2 minutes |
| "Windows protected your PC" when starting the Studio program | The program is not code-signed | More info > Run anyway |
| Explore: "Login: failed: the login form was still shown" | `TEST_USER` / `TEST_USER_PASSWORD` in `.env` are wrong, or the login needs more than a user name and password | Fix them in `.env` (Studio never asks for them), or give the analyst documents |
| Studio refuses an upload ("file type cannot be read", "old Word format", "larger than 25 MB", "file name not allowed") | Only documents TestHive can read are accepted, up to 25 MB (APK 300 MB) | Save .doc as .docx, split very large files, rename files with unusual characters |
| Restore says "Not restored: <path> exists again" or "already has ..." | A file or register row of that module was created again after it was archived | Move or rename the new one, then restore |
| Restore says "its fingerprint is not in the approvals log" | The archive folder was changed after it was archived, or was not made by `stage archive` | Restore only folders TestHive archived; put back the original folder if you have it |
| Archive says "could not be moved ... Close it and try again" | A file of the module is open (often its workbook in Excel); nothing was changed | Close the file, then archive again |
| Studio: "The design of <MODULE> is approved, so its cases are read-only" | An approved design cannot be changed or imported | Reopen the design in **Approvals** (or `.\hive stage reopen <MODULE> design --by "<name>" --comment "<why>"`), then change it |
| Studio: "The analysis of <MODULE> is approved, so its questions and answers are read-only" (also from import-answers) | An approved analysis is a frozen baseline | Reopen the analysis in **Approvals** (or `.\hive stage reopen <MODULE> analysis --by "<name>" --comment "<why>"`), answer, and let the analyst re-check |
| Next says "N requirement document(s) changed after the analysis was approved" | A document was uploaded, replaced, removed or restored after approval | Reopen the analysis, or restore the earlier version under **Earlier versions** |
| A document shows "not read yet" in Studio | It was added or replaced after the last read | Click **Read the documents** |
| Studio: "Claude Code is not installed here" | The `claude` command is not found | `.\hive setup --install`, then type `claude` once in a terminal to sign in; restart Studio |
| A run from Studio fails at once, or its log says it needs approval / is not signed in | Claude Code is not signed in, or the agent tried something outside `bash scripts/*` and file edits | Open a terminal, type `claude`, sign in; read the run's log in Activity; run that step in Claude Code yourself if it needs a permission |
| Studio: "saving is paused" | An agent is working on that module | Wait for the job panel to finish, or press Stop |
| A run shows "interrupted" in Activity | Studio was closed while it ran (the agent was stopped) | Run it again |
| `no approved analysis baseline` | Design needs the approved requirements | Approve the analysis stage first (`.\hive stage status <MODULE>`) |
| `No results file: reports/...xml` | The test run did not produce results (tool crashed, wrong module name) | Run `.\hive run-mobile <module>` and read its output; module name = folder under `mobile/flows/`. |
| `GATE FAIL` | The case sheet breaks a definition-of-done rule | Each line says which case and why. Fix the sheet or finish the work (e.g. run `stable` for "Done" cases). |
| Device not listed by `check-devices` | USB debugging off, prompt not accepted, cable is charge-only | Enable Developer options + USB debugging, accept the "Allow USB debugging" prompt, try another cable; `adb devices` must show `device`. |
| Shell scripts fail with `$'\r': command not found` | The files were checked out with Windows line endings | `.gitattributes` prevents this for fresh clones; for an old clone run `git rm --cached -r . && git reset --hard`. |
| An agent asks for permission for every command | Normal for commands outside `.claude/settings.json` | Approve once, or add the command to `allow` in `.claude/settings.json` (keep the `deny` list). |
| A one-shot agent run (`.\hive th <agent> "..."`) says every `bash scripts/...` command "requires approval", or `Ignoring ... permissions.allow entries ... workspace has not been trusted` | Claude Code only uses the project's allowed-commands list after you trust the folder once | Open the folder once interactively: run `claude` in it, accept the trust question, type `/exit`. Then one-shot runs work. |
| `claude: command not found` | Claude Code CLI not installed | `.\hive setup --install`, or `npm install -g @anthropic-ai/claude-code`; first start asks you to sign in. |

Still stuck: run `.\hive selftest`, copy the last 20 lines and the command you ran into an issue on the repo.
