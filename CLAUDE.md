# TestHive
A team of 9 QA agents in `.claude/agents/` (plus 2 maintainer reviewers: studio-security-reviewer, docs-consistency-reviewer). Start the Lead with `claude --agent testhive-lead`, or call one agent with `/th-<name>`.

- Read `CONTEXT.md` and `workflow/BOARD.md` first; open other files only for the module in hand.
- Explain the plan and get approval before implementing. Never push, delete or install without a clear yes.
- Verify on the real app; never assume behaviour. Never weaken an assertion: report the bug and keep the test.
- Use the scripts in `scripts/` for runs, digests, stability and the gate instead of doing that work by hand.
- Never read or print `.env`. No secrets or project data in files that get committed.
- On Windows the user runs scripts with `.\hive <name> ...` (PowerShell); in the Bash tool use `bash scripts/<name>.sh`.
- Keep answers short.
