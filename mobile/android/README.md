# Android
- Enable Developer options and USB debugging on a real device, or start an emulator in Android Studio.
- Check: `adb devices` must list the device as `device`.
- Find the package: `adb shell pm list packages | grep <name>`.
- Reset app data: `adb shell pm clear <package>`.
- Screen inspection on failure: `maestro hierarchy`.
