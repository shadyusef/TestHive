# TestHive file formats

All formats are plain files in the project folder, so the agents, the scripts, Excel and (later) the UI share them.
Every chain is linked by IDs: `REQ` -> `GAP` -> `TC` -> run `R-...` -> `BUG`.

## Stage state: `workflow/state.json` (written by `scripts/stage.sh`)
One entry per module. Stages in order: `analysis`, `design`, `tools`, `automation`, `execution`, `reporting`.
Each stage: `status` (`pending`, `in_progress`, `awaiting_approval`, `approved`) and a `history` of
`{at, status, by, comment}`. A stage cannot start until the previous one is `approved`.
Approve and reject need a named person (`--by`); a reject needs a comment.
Every decision is also appended to `workflow/APPROVALS.md` (human-readable, append-only).
Approving `analysis` first runs `check-analysis --for-approval` (when `analysis/requirements.csv` exists) and then
freezes the module's registers as a baseline (below).

## Ingested sources: `analysis/sources-text/<MODULE>/` (written by `scripts/ingest.sh`)
One `<file>.md` per source document; line 1 is `<!-- source: <path> | type: <kind> | ingested: <date> -->`.
PDF pages are marked `<!-- page N -->`; Word headings become `#` lines and tables become Markdown tables;
OpenAPI/Swagger becomes one section per endpoint with fields, required flags and limits. `index.csv` lists
Source, Type (text, pdf, word, excel, csv, openapi, data, image), Read from, Words, Masked. Images are listed, not
converted: Claude reads them directly.

## Exploration: `analysis/exploration/<MODULE>/web|android/`
`exploration.md` (for the analyst), screenshots, and for web `exploration.json` (pages, form fields with their HTML
rules, messages after empty / invalid / valid submissions); for Android one `NN-name.png` + `NN-name.xml` (UI dump)
per recorded screen. Everything there is observed behaviour, not confirmed requirements.

## Requirements register: `analysis/requirements.csv`
| Column | Values |
|---|---|
| ID | `REQ-<MODULE>-<NNN>` |
| Module | module code, e.g. `SIGNUP` |
| Source | file plus its own ID or section (`prd.pdf R4`, `openapi.yaml POST /v1/signup`), Jira key, Azure item, Figma frame, or `observed: web page 01` / `observed: android 03-otp` |
| Section | section or line in the source |
| Text | the requirement, in the source language (Arabic allowed) |
| Type | Functional, Business rule, UI, API, Non-functional |
| Priority | P0 to P3 |
| Version | 1, 2, ... (raised when the requirement changes) |
| Status | Draft (documented), Observed (seen only in the built product; needs a `To confirm` gap), Confirmed, Changed, Removed |
| Notes | free text |

## Gap register: `analysis/gaps.csv`
| Column | Values |
|---|---|
| ID | `GAP-<MODULE>-<NNN>` |
| Module | module code |
| Requirement | the `REQ` ID(s) it is about, separated by `;` (a conflict names both); empty if the requirement is missing altogether |
| Kind | Missing, Ambiguous, Conflict, Untestable, To confirm (observed behaviour a human must confirm) |
| Severity | High, Medium, Low |
| Question | the question for the business |
| Answer | filled by the human |
| Answered By | name |
| Status | Open, Answered (human answered; the analyst still has to review), Closed (settled) |

Rules checked by `scripts/check-analysis.sh`: ID formats and uniqueness, ID module = Module column, required
columns, allowed values, every referenced REQ exists, Answered/Closed have an answer, every Observed requirement has a
To confirm gap. With `--for-approval`: every High gap Closed, no Answered gap left unreviewed, no Observed requirement.

## Analysis workbook: `analysis/<MODULE>-analysis.xlsx` (written by `scripts/analysis-workbook.sh`)
Sheets: Cover (counts and how to answer), Gaps (yellow columns Answer, Answered By, Status are for the human; a row
with an empty ID is a new question), Requirements, Sources. `scripts/import-answers.sh` reads the Gaps sheet back;
if any row is invalid nothing is changed. Arabic cells are right-aligned.

## Baselines: `analysis/baseline/<MODULE>/v<n>/`
Written when a human approves the analysis stage: `requirements.csv` and `gaps.csv` (the module's rows at that
moment) and `meta.json` (`module`, `version`, `approved_by`, `approved_at`, counts). Test design (phase 2) works from
the latest baseline; a later approval creates the next version, so changes can be compared.

## Benchmark answer key (e.g. `demo/phase1/answer-key.csv`)
Columns `Key`, `Gap`, `Where`, `Keywords`. Keywords: groups separated by `;`, alternatives by `|`; an analyst gap
matches when every group appears in its kind or question. `scripts/score-analysis.sh`
reports how many planted gaps were found (target `TH_SCORE_TARGET`, default 80 %).

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
