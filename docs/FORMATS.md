# TestHive file formats

All formats are plain files in the project folder, so the agents, the scripts, Excel and (later) the UI share them.
Every chain is linked by IDs: `REQ` -> `GAP` -> `TC` -> run `R-...` -> `BUG`.

## Stage state: `workflow/state.json` (written by `scripts/stage.sh`)
One entry per module. Stages in order: `analysis`, `design`, `tools`, `automation`, `execution`, `reporting`.
Each stage: `status` (`pending`, `in_progress`, `awaiting_approval`, `approved`) and a `history` of
`{at, status, by, comment}`. A stage cannot start until the previous one is `approved`.
Approve and reject need a named person (`--by`); a reject needs a comment.
Every decision is also appended to `workflow/APPROVALS.md` (human-readable, append-only).

## Requirements register: `analysis/requirements.csv`
| Column | Values |
|---|---|
| ID | `REQ-<MODULE>-<NNN>` |
| Module | module code, e.g. `SIGNUP` |
| Source | file, Jira key, Azure item, Figma frame or Swagger path |
| Section | section or line in the source |
| Text | the requirement, in the source language (Arabic allowed) |
| Type | Functional, Business rule, UI, API, Non-functional |
| Priority | P0 to P3 |
| Version | 1, 2, ... (raised when the requirement changes) |
| Status | Draft, Confirmed, Changed, Removed |
| Notes | free text |

## Gap register: `analysis/gaps.csv`
| Column | Values |
|---|---|
| ID | `GAP-<MODULE>-<NNN>` |
| Module | module code |
| Requirement | the `REQ` ID it is about (empty if the requirement is missing altogether) |
| Kind | Missing, Ambiguous, Conflict, Untestable |
| Severity | High, Medium, Low |
| Question | the question for the business |
| Answer | filled by the human |
| Answered By | name |
| Status | Open, Answered, Closed |

## Runs: `runs/<RUN-ID>/` (written by `scripts/collect-run.sh`)
`RUN-ID` is `R-<yyyymmdd>-<nn>` (UTC date, then a sequence number).

- `meta.json`: `run_id`, `kind` (mobile, api, web), `module`, `env`, `platform`, `collected_at`, `host_os`, `source`, `totals`.
- `results.json`: `{format, run_id, cases: [{id, name, suite, status, duration_s, message, evidence}]}`.
  `status` is `passed`, `failed`, `error` or `skipped`. `id` is the TC-ID found in the test name.
  `evidence` lists the files under `evidence/` whose name contains the TC-ID.
- `junit.xml`: the original results file.
- `evidence/`: screenshots, videos and logs (git-ignored: large files stay on the PC or in CI artifacts).
- `runs/index.csv`: one line per run, for history and trends.

## Masking: `.mask-terms`, `.mask-allow`, `.mask-map.json` (all git-ignored, never leave the PC)
`scripts/mask.sh` replaces personal data in text with tokens like `[EMAIL_001]`, `[PHONE_002]`, `[NATID_001]`,
`[CARD_001]`, `[IBAN_001]`, `[TERM_003]`, and blacks it out in images (OCR, Arabic and English).
- Card numbers must pass the Luhn check, Saudi national / iqama IDs their check digit, IBANs the mod-97 check;
  numbers that fail (order numbers, references) are left alone.
- `.mask-terms`: extra words to hide (people, company, product, project), one per line. `suggest` proposes candidates.
- `.mask-allow`: values never to mask, one per line, or `re:<regex>` (e.g. a public switchboard number).
- `.mask-map.json`: value -> token, so the same value always gets the same token; `unmask` uses it to restore.
- `suggest` and `review` print real values, so only the human runs them; agents use `check` (counts only).
