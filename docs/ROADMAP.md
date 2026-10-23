# Roadmap

Goal: hand TestHive a product's business requirements early, and get back, with a human approval at every step:
analysis and gaps -> approved requirements -> reviewed test cases (Excel) -> tool advice -> a maintainable automation
project (API, web, mobile) -> executed runs with evidence -> bug and test reports in interactive HTML, readable by managers.

Each phase ends with a runnable demo in `demo/phase<N>/` and selftest coverage.

| Phase | Content | Status |
|---|---|---|
| 0 | Stage gates and approval log, common run format, masking (text + screenshots, Arabic + English), Windows launcher | Done (v0.2.0) |
| 1 | Business analysis: read text, PDF, Word, Excel, images, Swagger; explore a built web app (URL) or Android app (APK); `business-analyst` agent; requirements and gap registers; Excel Q&A loop; approval gate and baselines; benchmark with planted gaps | Done (v0.3.0) |
| 1b | Jira / Azure DevOps / Figma connectors (read, then write-back) | When access is provided; samples only until then |
| 2 | Test design: cases traced to the approved requirements, design techniques, risk-based priority, tags, AI pre-review, Excel review and re-import, cases added by hand or on request, stage reopen and change impact; benchmark with 46 expert conditions | Done (v0.4.0) |
| 2b | TestHive Studio lite: local web page to see stage status, answer gaps, approve stages, open the workbooks (for people who do not use a terminal) | Done (v0.5.0) |
| 2c | Studio setup and intake: first-opening project setup, new module, document and APK upload, masking review, read the documents, sources with versions, readiness for automation | Done (v0.6.0) |
| 2d | Run the agents from Studio: Run buttons, live job panel, Stop, Activity log, one job per module, web exploration button; recorded stand-in for free demos and CI | Done (v0.7.0) |
| 2e | Hardening before phase 3: view, remove and restore documents with a change history; archive and restore modules; approved design read-only; changes after approval shown in Next; page addresses and requirement links; demos clean up; unit tests; browser click-throughs in CI | Done (v0.8.0) |
| 2f | Studio design for the two stages: sidebar with every module, module header with the next step and a stage track, requirements and test-case screens with summary rows, review switch, phone layout, dark theme, fonts kept offline; answers read-only after the analysis approval | Done (v0.9.0) |
| 2g | Studio on its own for colleagues: a single Studio program (Windows) built by CI, review mode without Claude Code, a hand-off guide; projects shared through a git repository, Excel review packs for reviewers who install nothing | Done (v0.10.0) |
| 3 | Tool advice for functional tests: decision matrix per test type (Web UI, API, Android, iOS) from the approved design, weights and team skills, the human's choice with a reason, approval and baseline; Tools tab in Studio; Windows only from here on | Done (v0.11.0) |
| 3b | Tool advice for non-functional tests: accessibility, security, performance | Planned |
| 4 | Automation: framework scaffolds, reusable steps, E2E journeys, tags (smoke, sanity, regression, e2e), environments, test data, contract tests | Planned |
| 5 | Execution: run picker (type, suite, environment, device, BrowserStack), video and step screenshots, API request/response logs, retest after fix, flaky quarantine | Planned |
| 6 | Reporting: interactive HTML bug and test reports, management summary, trends, cost per stage, write-back to Jira / Azure | Planned |
| 7 | More Studio: answer agent permission prompts from the browser (Claude Agent SDK), Android exploration from Studio | Planned |
| 8 | Scale: scheduled CI runs, team roles, notifications, device farms, iOS on a Mac | Planned |

Owner decisions that shape the design: all input types plus a "no tools, one folder" mode; Excel export with human
edits before approval; one user now, team later; Arabic in scope, masking optional; template stays public (projects
made from it should be private); real devices and BrowserStack.
