# Demos and tests

Each phase of TestHive has a runnable demo on a fictional app (Nakhla Rewards, module SIGNUP). A demo works in a temporary copy of
TestHive, needs no Claude plan (recorded agents stand in for Claude Code), and never touches your project. CI and `scripts/selftest.sh`
run them to prove TestHive works. Your projects never use these files.

Run one: `.\hive demo/<phase>/run.sh` (Windows) or `bash demo/<phase>/run.sh`. Most take `--check`, which also drives Studio through
its API and exits 1 when a step is wrong. `TH_KEEP_DEMO=1` keeps the temporary folder to look around.

| Demo | What it shows | Needs |
|---|---|---|
| `phase0` | Stage gates, approval log, the common run format, masking | — |
| `phase1` | Business analysis from documents and a built web app | — |
| `phase2` | Test design from the approved analysis | — |
| `phase2b` | Studio on a project waiting for the design approval | Web tools for the browser click-through |
| `phase2c` | Studio from an empty project: set up, add a module, upload documents | Web tools for the browser click-through |
| `phase2d` | Running the agents from Studio's Run buttons | — |
| `phase3` | Tool advice from the approved test cases | — |
| `phase4` | Automation: placeholders, real tests against a local stand-in app, contract tests | Web tools, Newman |
| `phase5` | A test cycle: a planted bug, its fix and retest, a flaky test quarantined | Web tools, Newman |
| `phase5b` | Run targets: a local browser, BrowserStack browsers and devices (played by local stand-ins) | Web tools |
| `phase6` | The test report and the sign-off (runs the phase 5 demo first) | Web tools, Newman |
| `phase7` | Studio answers the agents' questions; Android exploration on a stand-in device | — |

The web tools: `.\hive setup --install --web`. Newman: `npm install -g newman`. What a demo writes for you to look at goes to
`demo/<phase>/output/` (git-ignored). Shared helpers: `_lib.sh` (the temporary copy) and `phase2d/fake-claude.py` (the recorded agents).
