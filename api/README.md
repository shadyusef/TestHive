# API (Postman + Newman)
- Collections: `api/collections/<module>.postman_collection.json`
- Environments: `api/environments/*.json` (placeholders only, no secrets)
- `scaffold <MODULE>` (stage 4) writes the collection with one placeholder request per case (marked `TESTHIVE:STUB`) and its environment.
- Name requests `[TC-ID] title @tag ...`; `{{API_BASE_URL}}` comes from `.env`.
- Contract tests: `contract <MODULE>` (scaffold runs it too) builds `api/collections/<MODULE>.contract.postman_collection.json` from the OpenAPI spec in `requirements/sources/<MODULE>/`: each endpoint must answer with a status and body the spec lists. Do not edit it; list known bugs in `<MODULE>.contract-bugs.txt` (`<METHOD> <path> <BUG-ID>`).
- Run: `bash scripts/run-api.sh <module> [--tag smoke | --contract]` (`TEST_API_TOKEN` in `.env` for endpoints that need a bearer token)
- The framework can change later; case definitions stay in `test-cases/TestCases.csv`.
