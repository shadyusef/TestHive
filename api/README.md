# API (Postman + Newman)
- Collections: `api/collections/<module>.postman_collection.json`
- Environments: `api/environments/*.json` (placeholders only, no secrets)
- `scaffold <MODULE>` (stage 4) writes the collection with one placeholder request per case (marked `TESTHIVE:STUB`) and its environment.
- Name requests `[TC-ID] title @tag ...`; `{{API_BASE_URL}}` comes from `.env`.
- Run: `bash scripts/run-api.sh <module> [--tag smoke]`
- The framework can change later; case definitions stay in `test-cases/TestCases.csv`.
