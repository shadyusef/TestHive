# iOS
iOS needs macOS. Windows cannot run the iOS Simulator or Maestro's iOS driver.
Options: a Mac (local or cloud Mac), or a cloud device farm.
- Check simulators: `xcrun simctl list devices booted`.
- Install a simulator build: `xcrun simctl install booted <App.app>`.
- Run the same flows with `--device <udid>` and the iOS bundle id in `APP_ID`.
- Android-only or iOS-only steps: use tags and `runFlow: when: platform:`.
