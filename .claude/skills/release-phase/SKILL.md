---
name: release-phase
description: For TestHive maintainers. Finishes a TestHive phase or fix as a release on its own branch - version and changelog, every check (selftest, all demo checks, private names, fresh clone), commit with attribution, then the push command for the owner. Use when the owner says a phase is done or asks to release, commit or wrap up the work.
disable-model-invocation: true
argument-hint: "<version> <branch> \"<one-line summary>\""
---

# Release a TestHive phase

Arguments: `$ARGUMENTS` = new version (e.g. `0.8.0`), branch name (e.g. `phase3-tools`), one-line summary. Ask for any that are missing.

Never push, merge or tag: the owner does that. Stop at the first failing step, show its output, and fix the cause (never weaken a check).

1. **Branch.** `git branch --show-current`. If it is `main` or not the given branch, create the branch from the current one (`git checkout -b <branch>`) after saying so.
2. **Version.** Write the version to `VERSION` (one line, LF).
3. **Changelog.** Add `## <version> (<today, YYYY-MM-DD>)` at the top of `CHANGELOG.md` (below the intro): 3 to 6 bullets in plain words — what a user can do now, new scripts or formats, behaviour changes, docs touched. Match the existing entries.
4. **Docs in step.** Update the status line in `README.md` (`> **Status (v<version>).**`) and the phase row in `docs/ROADMAP.md` (`Done (v<version>)`, next phase `Next`). Ask the docs-consistency-reviewer agent for a check and fix what it reports.
5. **Checks** (all must pass; on Windows run them through the Bash tool):
   - `bash scripts/selftest.sh` ends with `SELFTEST PASS`;
   - `bash demo/phase1/run.sh` and `bash demo/phase2/run.sh` end with "Demo finished"; every `demo/phase*/run.sh --check` that exists ends with `PASS`;
   - `bash scripts/check-private.sh` says `PASS` (or `SKIPPED` when there is no `.private-names`: then ask the owner whether that is expected);
   - `git status --short` shows nothing unexpected: no `HANDOVER.md`, `.env`, `.mask-*`, `.private-names`, `skills/*.zip`, `runs/agents/`, `demo/*/output/`.
6. **Commit.** Stage only the files of this work (never `git add -A` blindly). Commit as the owner's configured author with a message: first line `<Phase name> (v<version>): <summary>`, a blank line, 3 to 6 bullets, a blank line, and the attribution trailer required by the current session.
7. **Fresh clone.** Clone the branch into a temporary folder (`git clone -q -b <branch> <repo path> <tmp>`) and run `bash scripts/selftest.sh` there: it must pass without anything that exists only on this PC.
8. **Report** in a few lines: version, branch, commit id, the checks that passed (with counts), anything skipped and why, and the push command for the owner in its own bash block:
   `git -C <repo path> push -u origin <branch>`
