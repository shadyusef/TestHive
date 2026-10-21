# Roadmap

Goal: hand TestHive a product's business requirements early, and get back, with a human approval at every step:
analysis and gaps -> approved requirements -> reviewed test cases (Excel) -> tool advice -> a maintainable automation
project (API, web, mobile) -> executed runs with evidence -> bug and test reports in interactive HTML, readable by managers.

Each phase ends with a runnable demo in `demo/phase<N>/` and selftest coverage.

| Phase | Content | Status |
|---|---|---|
| 0 | Stage gates and approval log, common run format, masking (text + screenshots, Arabic + English), Windows launcher | Done (v0.2.0) |
| 1 | Business analysis: read text, PDF, Word, Excel, images, Swagger; optional Jira / Azure DevOps / Figma connectors (read); `business-analyst` agent; requirements and gap registers; Q&A loop; analysis workbook; benchmark with planted gaps | Next |
| 2 | Test design: design techniques, risk-based priority, review rounds, Excel export and re-import, cases added by hand or on request, change impact | Planned |
| 3 | Tool advice: decision matrix per test type, human choice | Planned |
| 4 | Automation: framework scaffolds, reusable steps, E2E journeys, tags (smoke, sanity, regression, e2e), environments, test data, contract tests | Planned |
| 5 | Execution: run picker (type, suite, environment, device, BrowserStack), video and step screenshots, API request/response logs, retest after fix, flaky quarantine | Planned |
| 6 | Reporting: interactive HTML bug and test reports, management summary, trends, cost per stage, write-back to Jira / Azure | Planned |
| 7 | TestHive Studio: local web UI over the same files (one user first, team later) | Planned |
| 8 | Scale: scheduled CI runs, team roles, notifications, device farms, iOS on a Mac | Planned |

Owner decisions that shape the design: all input types plus a "no tools, one folder" mode; Excel export with human
edits before approval; one user now, team later; Arabic in scope, masking optional; template stays public (projects
made from it should be private); real devices and BrowserStack.
