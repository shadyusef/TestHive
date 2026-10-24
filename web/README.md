# Web (Playwright + TypeScript)
Set up per module by `scaffold <MODULE>` once the tools are approved (stage 4).

1. Install once: `bash scripts/setup.sh --install --web` (Windows: `scripts\setup.ps1 -Install -Web`). It runs `npm install` here and downloads Chromium.
2. Specs in `web/tests/<module>/<TC-ID>_<title>.spec.ts` (scaffold writes a placeholder per case, marked `TESTHIVE:STUB`), Page Objects and reusable steps in `web/pages/<module>/`, the shared fixture in `web/fixtures/testhive.ts` (unique test data, and `api` for requests to `API_BASE_URL`). Journeys (`@e2e`) reuse the steps in `web/pages/<module>/steps.ts` and set up or check data through the API. `getByTestId()` reads `data-qa`.
3. Titles start with the case ID and end with its tags: `test('[TC-LOGIN-001] valid login @smoke @regression', ...)`. The ID is how `stable.sh` and the gate find the case; the tags are how runs pick tests.
4. Run: `bash scripts/run-web.sh <module> [--tag smoke]` (reads `BASE_URL` from `.env`, and `.env.<TEST_ENV>` over it; writes `reports/web-<module>.xml` and stores the run in `runs/`).
5. Stability: `bash scripts/stable.sh web <module>`.
