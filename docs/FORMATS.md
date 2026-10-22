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
freezes the module's registers as a baseline (below). Approving `design` does the same with `check-design --for-approval`
and the design baseline. A stage can be submitted only while the stage before it is approved.
`reopen` (needs `--by` and `--comment`) sends an approved stage back to in progress, for example when requirements change;
later stages that were submitted or approved go back to in progress too and need a new approval.

## Modules and uploads (written by TestHive Studio)
`requirements/modules/<MODULE>.json`: `title`, `url` (built product to explore), `test_env` (true: the analyst may submit forms),
`apk` (path of an uploaded APK), `mask` (mask personal data when reading). Documents go to `requirements/sources/<MODULE>/`;
uploading a file with the same name, or removing a document, moves it to `requirements/sources/<MODULE>/_old/<yyyymmdd-hhmmss>/`
(`-2`, `-3` is added when two changes fall in the same second; nothing is overwritten; `ingest` skips `_old`). Restoring copies
an earlier version back (it also stays in `_old/`). `_old/history.csv` logs every change: `When` (UTC), `Action` (uploaded,
replaced, removed, restored <version>), `Document`, `By`. APKs go to `requirements/apps/<MODULE>/` (git-ignored).

## Ingested sources: `analysis/sources-text/<MODULE>/` (written by `scripts/ingest.sh`)
One `<file>.md` per source document; line 1 is `<!-- source: <path> | type: <kind> | ingested: <date> -->`.
PDF pages are marked `<!-- page N -->`; Word headings become `#` lines and tables become Markdown tables;
OpenAPI/Swagger becomes one section per endpoint with fields, required flags and limits. `index.csv` lists
Source, Type (text, pdf, word, excel, csv, openapi, data, image), Read from, Words, Masked. Images are listed, not
converted: Claude reads them directly. Reading again removes the text of documents that are gone, and removing or
replacing a document in Studio removes its text at once, so the analyst never works from a document that was taken out.

## Archived modules: `archive/<MODULE>-<yyyymmdd-hhmmss>/` (written by `stage.sh archive`)
`files/<original path>` (the module's documents, module file, APKs, read texts, explorations, baselines, workbooks, reviews and
agent logs), `rows/<register path>` (the module's rows of `analysis/requirements.csv`, `gaps.csv`, `test-cases/TestCases.csv`,
`requests.csv`), `state.json` (its stage state) and `ARCHIVE.json` (`module`, `archived_at`, `by`, `why`, `files`, `rows`).
`stage.sh restore` puts everything back, refusing if any of it exists again, and moves the folder to `archive/_restored/`.
Both are logged in `workflow/APPROVALS.md` (stage `-`). APKs and agent logs stay git-ignored inside the archive too.

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
moment) and `meta.json` (`module`, `version`, `approved_by`, `approved_at`, counts). Test design works from
the latest baseline; a later approval (after `stage reopen`) creates the next version, so changes can be compared.

## Benchmark answer key (e.g. `demo/phase1/answer-key.csv`)
Columns `Key`, `Gap`, `Where`, `Keywords`. Keywords: groups separated by `;`, alternatives by `|`; an analyst gap
matches when every group appears in its kind or question. `scripts/score-analysis.sh`
reports how many planted gaps were found (target `TH_SCORE_TARGET`, default 80 %).

## Test case sheet: `test-cases/TestCases.csv`
One row per case, all modules in one file (Excel: save as "CSV UTF-8"). Older sheets without the newer columns are still read.
| Column | Values |
|---|---|
| ID | `TC-<MODULE>-<NNN>` (an extra part is allowed: `TC-SIGNUP-API-001`) |
| Module | module code |
| Platform | Android, iOS, Both, API, Web |
| Title | what is checked, with which value |
| Priority | P0 to P3; `check-design --set-priority` fills empty cells with the risk rule below |
| Type | Positive, Negative, Localization, Accessibility, Security, Performance (older sheets: Functional = Positive) |
| Requirements | the `REQ` IDs it verifies, separated by `;` |
| Technique | Equivalence, Boundary, Decision table, State transition, Error guessing, Use case, Checklist |
| Risk | likelihood of a defect: High, Medium, Low |
| Tags | `;`-separated: `smoke`, `sanity`, `regression`, `e2e` (used later to pick suites) |
| Preconditions, Steps, Expected Result, Test Data | numbered single-action steps; an exact, observable expected result |
| Assumption | open `GAP` IDs the expected result depends on: gaps of the baseline, or questions the designer added to `analysis/gaps.csv` (Question starts with "From design:"; the analyst takes them into the next analysis round) |
| Origin | Designed (manual-tester), Human (added in Excel), Requested (added for a request) |
| Review | empty, Accepted, Change, Remove (the human's decision), Updated (the designer handled it, or the human edited the case in Excel) |
| Review Comment | what to change; TestHive appends `[edited in Excel: ...]` and `[impact: ...]` notes |
| Automation, Automation Spec | Candidate / No / Yes, and the test file once automated (`gate` checks it exists) |
| Status | Draft, Ready, Needs update (a linked requirement changed), Removed (kept for history), Automated, Done |

**Risk rule for priority:** impact = the highest priority of the linked requirements (P0 = 3, P1 = 2, P2/P3 = 1),
likelihood = Risk (High 3, Medium 2, Low 1); impact x likelihood 9 = P0, 6 = P1, 3-4 = P2, 1-2 = P3 (the usual 3x3 risk matrix: only a High-risk case of a P0 requirement is P0).

Rules checked by `scripts/check-design.sh` against the latest analysis baseline: ID format and uniqueness, allowed values,
every linked REQ exists and is not Removed, every Assumption is a gap of the baseline, every active requirement has a case,
every P0 Functional / Business rule / API requirement has a Negative case, every P0 requirement with a numeric limit has a
Boundary case (warning for other priorities). Warnings: vague expected results ("works", "correctly", ...), a priority that
differs from the risk rule, open gaps not recorded as an Assumption. With `--for-approval`: no orphan case, no Needs update,
no Review Change/Remove left, no Open request.

## Design requests: `test-cases/requests.csv`
The human's requests for more cases (from the workbook's Requests sheet). Columns: `ID` (`ASK-<MODULE>-<NNN>`), Module,
Requirement, Request, Requested By, Status (Open, Done), Response (the case IDs added, or why none).

## Design workbook: `test-cases/<MODULE>-design.xlsx` (written by `scripts/design-workbook.sh`)
Sheets: Cover (counts, coverage, how to review), Cases (yellow Review and Review Comment; edit any case text directly; a row
with an empty ID and a Title is a new case), Coverage (per requirement: its cases, whether a needed negative or boundary
case exists, its open gaps), Assumptions (open gaps and the cases relying on them), Requests (a row with an empty ID is a new
request), Requirements (the baseline). `scripts/import-review.sh` reads Cases and Requests back; if any row is invalid nothing is changed.

## Design baselines: `test-cases/baseline/<MODULE>/v<n>/`
Written when a human approves the design stage: `TestCases.csv` and `requests.csv` (the module's rows) and `meta.json`
(`module`, `version`, `approved_by`, `approved_at`, `analysis_baseline` = the analysis version the cases were designed from, counts).
`scripts/design-impact.sh` compares that analysis version with the latest one and lists the cases linked to changed or removed requirements.

## Design benchmark key (e.g. `demo/phase2/condition-key.csv`)
Columns `Key`, `Condition`, `Requirement` (`|`-separated REQ IDs; a matching case must link one of them; empty = any case),
`Keywords` (as in the analysis key; a number must match a whole number, so `7` does not match `17`). `scripts/score-design.sh`
reports how many conditions at least one active case covers (target `TH_SCORE_TARGET`, default 80 %).

## Agent runs from Studio: `runs/agents/<yyyymmdd-hhmmss>-<MODULE>-<agent>/` (git-ignored)
`meta.json` (`id`, `module`, `kind` agent or script, `agent`, `title`, `task`, `status` running / done / failed / stopped /
interrupted, `started`, `ended`, `summary`, `cost_usd` as reported by Claude Code, `exit_code`), `progress.txt` (one line per
step: `$` commands, `writes` files, `>` messages, `!` errors) and, for agents, `transcript.jsonl` (the raw Claude Code event stream).

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
