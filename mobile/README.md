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

Run: `maestro test -e APP_ID=$APP_ID mobile/flows/<module>`
Single device: add `--device <id>`. Report: add `--format junit --output reports/junit.xml`.
