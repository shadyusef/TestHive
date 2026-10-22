# Design pre-review: SIGNUP (n=1)

Baseline: analysis/baseline/SIGNUP/v1. check-design.sh: DESIGN OK, 104 cases, 28 of 28 requirements covered, 20 warnings (closed-gap assumptions).
Reviewed against the Active requirements and the 38 gaps. I did not run the app. No cases were edited.

**Verdict: CHANGES REQUIRED before the workbook goes to the human.** Coverage is broad and the boundaries are good. There are no Blockers. Five Major findings (exactness, unexecutable cases, one unsupported expectation, a missing P0 rule) must be fixed first.

## Findings

| # | Rank | Case / REQ | What is wrong | Fix |
|---|---|---|---|---|
| 1 | Major | TC-004..012, 013..020, 021..028, 029..036, 045 and most web cases | Steps say "Fill the other fields with valid data" without exact values, and the same step often also holds the click. This is several actions in one step, and the data is not exact. The mobile is unique only in some cases. | Define one named valid data set in Test Data (Sara Test / unique mobile / Pass1234 / 1990-01-15 / en / terms ticked). Split into one action per step: fill each field, then click. Give every case its own unique mobile, including the invalid-mobile cases that do not need one. |
| 2 | Major | TC-004, 007, 008, 009, 012, 024, 025, 026, 027, 032, 052; API 074..080 | The expected result is "an error message is shown for X", "either … or …", "(or another error)" or "a 4xx". It is not exact, so the case cannot fail precisely. P0 password cases are affected. The assumption cites GAP-SIGNUP-028, which is Closed: its answer says only to use already-confirmed messages. No message exists for name, password complexity, password length 65, password = mobile, or future date. | Raise one new open gap asking for the exact Arabic and English text of those messages and for the 400 body. Cite it in Assumption. Until it is answered, write the expectation as "the field's error element is visible, the message text is not asserted (GAP-SIGNUP-0xx)". Remove the "either/or" wording in TC-007, 052, 053, 066. Pick the expected behaviour from the requirement, or log it as a gap. |
| 3 | Major | TC-059, TC-099 | "The old code is refused after a resend" cannot run on the demo. CONTEXT says the demo OTP is always 123456, so the first and new codes are the same and the old code stays valid. Expected results would be wrong. | Mark both as not executable on the demo. Say so in Assumption, set Automation=No, and keep them for a real SMS or API environment. Or add a gap on whether the demo issues distinct codes. |
| 4 | Major | TC-100 | Expected status 429 for a resend inside the 30-second cooldown is not in any requirement. REQ-017 and GAP-019 give 429 only after the hourly limit. | Log a gap on the cooldown status and body, and cite it. Do not hard-code 429 until it is answered. |
| 5 | Major | REQ-SIGNUP-014 (P0), TC-055, 056, 094, 095 | Two P0 gaps. (a) The attempt limit is "per code", but no case checks that a resend gives a fresh code with a fresh count of 3 (for example 2 wrong, resend, 2 wrong, then the correct code is accepted). (b) TC-056 step 4 and TC-094 step 4 say "does not verify" or "does not return 200": no exact message or status. | Add one web and one API case for the counter reset after resend. Replace the vague expectations with an exact message and status, or log a gap for them. |
| 6 | Major | REQ-SIGNUP-029 / 026 | The requirement says every message needs an Arabic version. Only the date message has an Arabic case (TC-045). The Arabic text for the password, mobile, full name, terms, age and resend-link messages is not in any gap answer and no gap is open. | Open a gap for the Arabic texts (and for the Arabic verify-page texts). Add Arabic cases for the messages that are confirmed. Cite the gap in the existing Arabic cases. |
| 7 | Minor | TC-003, 004, 007, 008, 009, 012, 021, 024..027, 032, 044, 052, 053, 068; TC-062, 063 | Assumption cites a Closed gap (GAP-SIGNUP-028, GAP-SIGNUP-017). Flagged by check-design (20 warnings). | For GAP-017: remove the assumption, the answer is 5 minutes. For GAP-028: replace with the new open gap from finding 2. |
| 8 | Minor | TC-027, TC-080 | The mobile number is all digits, so a password equal to it has no letter and fails the "letter and digit" rule anyway. The test cannot show that the "not equal to mobile" rule works. | Log a gap asking whether the rule is a separate check or redundant. Note it in Assumption. Consider a normalised mobile (spaces or Arabic-Indic digits) as the password. |
| 9 | Minor | REQ-SIGNUP-015 (P0), API | Boundary min-1 (5 digits) and an empty or missing code are not tested at the API. Verify with an unknown or missing signupId is not tested either. | Add TC for code 12345, empty code, and unknown signupId on /v1/otp/verify. |
| 10 | Minor | REQ-SIGNUP-001 / 003 / 007, API | The API has no cases for fullName with digits or symbols, 1 character, mobile with spaces or Arabic-Indic digits, mobile prefix 06, future birthDate, or a bad birthDate format. REQ-004: the optional API email is not tested. | Add short API equivalence cases or record why they are out of scope. |
| 11 | Minor | TC-036 | Trimming leading and trailing spaces is not in any requirement or gap, and the case expects acceptance. The type is "Negative" but the expectation is positive. | Open a gap on trimming. Set the type to Positive/Error guessing. |
| 12 | Minor | TC-029, 030 | TC-029 expects the observed message 'You must be 18 or older', which is not an approved text. TC-030 assumes that a person turning 18 today is accepted (GAP-015 is Open). | Do not assert the text. Keep GAP-015 in Assumption and say what each outcome is expected to be once it is answered. |
| 13 | Minor | TC-001 | Priority P1, but it is the core happy path of REQ-013 (P0) and is tagged smoke. | Raise to P0. |
| 14 | Minor | TC-037, 040, 097 | Expected results are not observable on the web page or API response: "no new OTP is sent", "only one pending account exists", "balance still 50" (how read, which field, which status). | State where the observation is made (for example the verify response `points`), or mark as needing a backend or log check. |
| 15 | Minor | TC-067, TC-048 | Step "Check the points balance" does not say where. "Logged in" in TC-048 has no observable. | Name the welcome-page element, and a logged-in signal (for example token or session present). |
| 16 | Minor | Coverage | Not covered: a duplicate check with a mobile in another format (spaces, Arabic-Indic digits) that normalises to a registered number; the resend limit window resetting after one hour; the welcome page language after choosing Arabic (TC-044 stops at the OTP page); a name with only Arabic letters at the boundaries of 2 and 50. | Add cases or record them as out of scope. |
| 17 | Nit | TC-046 | Duplicates TC-006 (name 50) and TC-021 (password 8). It inspects HTML attributes, not behaviour. Type "Negative" does not fit. | Delete it, or reduce to a regression check of the message text. |
| 18 | Nit | TC-045, TC-002 | TC-045 title is plural but covers one message. TC-002 cites GAP-SIGNUP-012 (welcome email), which does not relate to the field list. | Fix title and Assumption. |
| 19 | Nit | Open gaps GAP-007, 012, 015, 020, 021, 025..027, 029..031 | No case covers server error, timeout or offline (GAP-030). | Fine while the gap is open. Add cases when it is answered. |
| 20 | Nit | TC-EXAMPLE-001 | The example row is still in the workbook. | Remove it before the human review. |

## Coverage check by requirement (summary)
- REQ-001/002 name: min-1, min, max, max+1 and characters covered on the web. API gaps in finding 10.
- REQ-003 mobile: 9/10/11 digits, prefix, +966, letters, spaces and Arabic-Indic digits covered. Empty mobile only in TC-003.
- REQ-005/006 password: 7/8/64/65, letter-only, digit-only, symbols, equal-to-mobile covered. Empty password only in TC-003.
- REQ-007 age: 17y364d, 18y, 18y1d, future and empty date covered.
- REQ-009 language: defaults (fr, en, ar) and choosing Arabic covered. The API requires language (TC-081, 082).
- REQ-010 terms: web and API covered. Version values are open (GAP-007).
- REQ-011 duplicate: active (en, ar, API) and pending (web, API) covered.
- REQ-014..017: wrong, 3rd wrong, expiry (4:55 and 5:05), cooldown, hourly limit covered in en and ar. Gaps: findings 3, 4, 5, 6.
- REQ-018/019 and 022..025: covered, with the open gaps recorded in Assumption.
- Removed REQ-008, 012, 020, 021, 032 have no cases (correct).
