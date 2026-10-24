# Mobile (Maestro)

```
mobile/
  flows/<module>/      one folder per module, files named <TC-ID>_<title>.yaml
  subflows/            reusable steps (launch clean, login, ...)
  data/                test data (no secrets)
  android/             Android notes and config
  ios/                 iOS notes and config
```

Platform differences use tags (`android`, `ios`) and env variables, not copied flows.

`scaffold <MODULE>` (stage 4) writes one placeholder flow per case (marked `TESTHIVE:STUB`, failing until written), with the case's tags.

Run: `bash scripts/run-mobile.sh <module> [device-id] [--tag smoke] [--target android|bs-pixel7|bs-iphone15|...]` (targets: `bash scripts/targets.sh`; BrowserStack uploads `APP_FILE` / `IOS_APP_FILE` from `.env`, or `--app <file>`: an .apk, .aab or .ipa only), or `maestro test -e APP_ID=$APP_ID mobile/flows/<module>`
Single device: add `--device <id>`. Report: add `--format junit --output reports/junit.xml`.
