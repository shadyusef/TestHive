# Web (Playwright + TypeScript)
Idle until the project has a web flow. When needed:

1. Install once: `bash scripts/setup.sh --install --web` (Windows: `scripts\setup.ps1 -Install -Web`). It runs `npm install` here and downloads Chromium.
2. Specs in `web/tests/<module>/<TC-ID>_<title>.spec.ts`, Page Objects in `web/pages/`, fixtures in `web/fixtures/`.
3. Titles start with the case ID: `test('[TC-LOGIN-001] valid login', ...)`. The ID is how `stable.sh` and the gate find the case.
4. Run: `bash scripts/run-web.sh <module>` (reads `BASE_URL` from `.env`, writes `reports/web-<module>.xml`).
5. Stability: `bash scripts/stable.sh web <module>`.
