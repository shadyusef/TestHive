---
name: rerecord-demo
description: For TestHive maintainers. Re-records the agent runs that the phase 1 or phase 2 demo replays, after the business-analyst, manual-tester or qa-reviewer instructions changed, then re-checks the benchmark and the demos. Use when the owner asks to re-record a demo or after an agent's rules changed.
disable-model-invocation: true
argument-hint: "phase1 | phase2"
---

# Re-record a demo's agent runs

Argument: `$ARGUMENTS` = `phase1` (business-analyst) or `phase2` (manual-tester and qa-reviewer). This runs real agents with Claude Code: tell the owner it takes 30 to 60 minutes of their Claude plan and wait for a yes.

Background: `docs/MAINTAINING.md` (sections "The analyst benchmark" and "The design benchmark"). Recordings live in `demo/<phase>/recorded/`; `demo/phase2d/fake-claude.py` replays the same files.

## 1. Prepare a working copy (never the real project)
Make a temporary folder in the session scratchpad and copy the repository into it with tar, leaving out `.git`, `analysis`, `test-cases`, `reviews`, `requirements`, `workflow/state.json`, `workflow/APPROVALS.md`, `runs/agents`, `demo/*/output`, `HANDOVER.md`. Never use `rm` with a relative path after `cd`. Then build the starting state exactly as `demo/<phase>/run.sh` does before its first agent step.

## 2. Run each agent step live and copy its output
Run every agent with: `claude --agent <name> --permission-mode acceptEdits --allowedTools "Bash(bash scripts/*)" --output-format text -p "<the task text from demo/<phase>/run.sh>"` (qa-reviewer: add `--model sonnet`). Run them in the background and wait for the notification.

- **phase1:** first pass -> copy `analysis/requirements.csv` and `gaps.csv` to `recorded/first-pass/`; play the human with `recorded/sample-answers.csv` (`make/answer-workbook.py`), re-check -> `recorded/recheck-1/`; second answers `sample-answers-2.csv`, re-check -> `recorded/recheck-2/`.
- **phase2:** first pass -> `recorded/first-pass/TestCases.csv` (remove any `TC-EXAMPLE-001` row); pre-review -> `recorded/DESIGN-SIGNUP-1.md`; fix -> `recorded/after-review/TestCases.csv` and `gaps.csv`; play the human with `recorded/sample-review.csv` (`make/review-workbook.py`), re-check -> `recorded/recheck-1/TestCases.csv`, `requests.csv`, `gaps.csv`.

## 3. Keep the human's files in step
If the new run produced different IDs, rewrite `sample-answers*.csv` / `sample-review.csv` so every ID they mention exists and still makes sense (a Remove must not take away the only case of a requirement; requests must be unambiguous). Check every ID before replaying.

## 4. Verify
- Benchmark: `bash scripts/score-analysis.sh SIGNUP demo/phase1/answer-key.csv` or `bash scripts/score-design.sh SIGNUP demo/phase2/condition-key.csv` in the working copy. Read every pairing; a match that is wrong is a key problem: fix the key, do not count it.
- In the repository: `bash demo/<phase>/run.sh` (replay), `bash demo/phase2d/run.sh --check`, `bash scripts/selftest.sh`.

## 5. Report
The score before and after, what changed in the agents' output, files re-recorded, and anything in the human's files you rewrote. Do not commit: use the release-phase skill or let the owner decide.
