# Changelog

Versions follow `MAJOR.MINOR.PATCH`. The current version is in `VERSION`.

## 0.2.0 (2026-10-21)
- Phase 0 foundations: stage gates and approval log (`stage`), common run format and run history (`collect-run`, `runs/`), masking of personal data in text and screenshots, Arabic and English (`mask`), requirement and gap register templates, `docs/FORMATS.md`, `demo/phase0/`.
- Windows: `hive.cmd` launcher (`.\hive <script>`), `setup` runs `setup.ps1` on Windows, `-Ocr` and `-AddBashToPath`, clear message when an installer needs admin rights.
- Run scripts store every run automatically; `stable` runs are kept as history.
- Hardening: working-Python detection, LF line endings, gate accepts `TC-X-API-001` IDs and Excel's BOM, checks priority and real assertions; `stable.sh`; Lead has the setup check and stage gates; reviewer can write reviews; `.claude/settings.json` allow/deny list; CI on Linux, Windows and macOS.
- Docs: README rewritten for newcomers, `docs/TROUBLESHOOTING.md`, `docs/MAINTAINING.md`, `docs/ROADMAP.md`, `requirements.txt`.

## 0.1.0 (2026-10-08 to 2026-10-10)
- First public version: 8 agents, templates, scripts, diagram, `/testhive` skill; token-saving context, screen cache, failure digest, gate and selftest CI.
