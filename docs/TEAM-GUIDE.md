# TestHive for your team

How to hand TestHive to colleagues: who needs what, how everyone gets the project, and how work moves between people.
The person who sets it up reads all of it; everyone else reads their own row and **Every day**.

## Who needs what

| Role | Does | Needs on their PC |
|---|---|---|
| **QA lead** (sets it up once) | Creates the project repository, describes the app, adds modules, approves stages | Everything a QA engineer needs, plus a GitHub account that can create private repositories |
| **QA engineer** | Runs the agents (Run buttons), answers, reviews, approves | Git, the Studio program, and the full TestHive setup (`.\hive setup --install`: Python, Claude Code signed in, Git Bash on Windows) |
| **Reviewer** (QA or business, with a PC) | Answers questions, reviews and approves cases in Studio | Git and the Studio program. Without Claude Code, Studio opens in **review mode**: everything works except the Run buttons, which show the command to hand to a QA engineer |
| **Business reviewer** (Excel only) | Answers questions or reviews cases in a workbook | Excel. Nothing to install |

## Set it up once (QA lead)
1. On GitHub open the TestHive repository, click **Use this template** and create a **private** repository for the project
   (requirements and test evidence stay private). One repository per product or project.
2. Clone it on your PC and follow [QUICKSTART.md](../QUICKSTART.md) steps 2 and 3 (tools, selftest).
3. Open Studio (below) on that folder: the first page asks for the project details. Add the first module.
4. Commit and push (see **Every day**). Add your colleagues to the GitHub repository (Settings > Collaborators or your organisation's team).

## Get the Studio program
- Download it from the TestHive repository's **Releases** page: `testhive-studio-windows.exe`, `testhive-studio-macos` or
  `testhive-studio-linux`. One file, no Python needed to open it. Keep it anywhere (Desktop, Downloads).
  No release yet? The QA lead builds it: `python scripts/build-studio.py` (needs `pip install pyinstaller`) makes `dist/testhive-studio.exe`.
- **Windows** shows "Windows protected your PC" the first time (the program is not code-signed): **More info > Run anyway**.
  Each download has a `.sha256` file next to it: compare it with `certutil -hashfile testhive-studio-windows.exe SHA256`.
- **macOS**: right-click the file > **Open** the first time (or `chmod +x testhive-studio-macos` and
  `xattr -d com.apple.quarantine testhive-studio-macos` in Terminal). **Linux**: `chmod +x testhive-studio-linux`.
- Starting it opens your browser on the last project you opened; the first time it asks for the project folder.
  Keep its window open while you work; closing it stops Studio (and any agent it started).
- QA engineers can also start Studio from the project folder with `.\hive studio`; both work the same.

## Get the project (everyone with a PC)
1. Install Git (Windows: `winget install --id Git.Git -e`) or GitHub Desktop.
2. Clone the project repository once, for example into `C:\Projects\<project>`
   (GitHub Desktop: **File > Clone repository**; terminal: `git clone <repository address>`).
3. Open the Studio program, paste the folder's path on the **Open a project** page (the first time, Studio asks you to confirm the folder) (File Explorer: hold Shift, right-click the
   folder, **Copy as path**). Next time it opens there by itself; **Switch project** in the sidebar changes it.

## Every day
1. **Get the latest work first:** GitHub Desktop **Fetch origin > Pull**, or `git pull` in the project folder.
   Do this before you answer, review or press Run.
2. **Work in Studio.** Sign with your real name (top of the page asks once): answers, reviews and approvals carry it.
3. **Share your work when you finish** (or before a break): GitHub Desktop **Commit to main > Push origin**, or
   ```
   git add -A
   git commit -m "SIGNUP: answered 12 questions"
   git push
   ```
   The `.gitignore` keeps out what must stay on your PC: `.env`, the masking lists, APKs, agent logs.

**Avoid stepping on each other**
- Agree who works on which module. One agent run per module at a time across the team: pull, check the module's
  **Activity** tab, then press Run.
- Answers and reviews of different modules live in the same files (`analysis/gaps.csv`, `test-cases/TestCases.csv`);
  git usually merges them. If it reports a **conflict**, do not guess: ask the QA lead. After fixing it, run
  `.\hive check-analysis <MODULE>` or `.\hive check-design <MODULE>` and push.
- Approvals are recorded in `workflow/state.json` and `workflow/APPROVALS.md`; push right after approving so nobody works on
  an old stage.

## Reviewers with Excel only
1. In Studio open the module: **Analysis** tab (questions) or **Design** tab (test cases) > **Download the workbook**.
2. Email it to the reviewer. The Cover sheet tells them what to fill (the yellow columns) and to send it back.
3. When it comes back: same tab > **upload a filled one**. Only the rows the reviewer changed are taken, so a workbook that
   comes back late, or two copies from two reviewers, never undo newer work. A row that was also changed in TestHive since the
   workbook was made is refused and listed; compare it with Studio, delete that row in the workbook (or make it match) and
   upload again.
4. Commit and push.

## Things to know
- **Secrets stay on each PC.** Passwords and tokens go into `.env` by hand when a test needs them (for example `TEST_USER` and
  `TEST_USER_PASSWORD`, the test account Explore logs in with); it is never committed, and
  agents cannot read it. Each QA engineer keeps their own.
- **Explore's findings stay on the PC that ran it** (`analysis/exploration/` is not committed: logged-in pages can show account
  details). The analyst's requirements made from them are shared as usual; run Explore again on another PC if needed.
- **Masking lists are per PC too** (`.mask-terms`, `.mask-allow`): whoever reads documents with masking keeps the list of real
  names to hide. Read documents before committing them if they contain personal data.
- **Approved stages are read-only.** To change approved answers or cases, reopen the stage in **Approvals** and say why;
  later stages then need a new approval.
- **Running agents uses the Claude plan** of whoever presses Run (minutes per run). Review mode and the demos cost nothing.
- **See it first:** `.\hive demo/phase2d/run.sh` shows the whole flow with recorded agents, free.
- Problems: [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
