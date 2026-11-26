# Signing the Android APKs

Each release can carry signed APKs for Android phones and tablets (`inkline-<version>-android-aarch64.apk`) and for
x86-64 Android (Chromebooks, emulators: `-android-x86_64.apk`). They're built and added by
`.github/workflows/android-release.yml` after the Release workflow publishes a release — only once the release key
is in the repository's secrets. Android only installs updates signed with the same key as the copy installed, so
make the key once, keep a backup, and never replace it.

## 1. Make the key (once)

With a JDK installed (`keytool` comes with it):

```sh
keytool -genkeypair -v -keystore inkline-release.keystore -alias inkline \
  -keyalg RSA -keysize 4096 -validity 10000
```

It asks for a keystore password, your name (or Inkline's) and a key password. Keep `inkline-release.keystore` and
both passwords somewhere safe and private (a password manager): **a lost key means users must uninstall to update**.

## 2. Add it to GitHub

Repository → Settings → Secrets and variables → Actions → New repository secret, four times:

| Secret | Value |
| --- | --- |
| `ANDROID_KEYSTORE` | the keystore, base64: `base64 -w0 inkline-release.keystore` (macOS: `base64 -i inkline-release.keystore`) |
| `ANDROID_KEYSTORE_PASSWORD` | the keystore password |
| `ANDROID_KEY_ALIAS` | `inkline` (the `-alias` above) |
| `ANDROID_KEY_PASSWORD` | the key password |

## 3. Add APKs to a release

New releases get them automatically. For the release already out, open Actions → **Android release** → **Run
workflow**: it builds both APKs from that release's code, checks their signatures, and adds them to it.

Without the secrets the workflow only says that no key is set; nothing else changes.

## Google Play and F-Droid

Google Play wants an Android App Bundle (`.aab`) uploaded under your Play developer account, with Play App Signing;
F-Droid builds every app from source, which Qt's prebuilt PySide6 for Android doesn't allow. See
`docs/publishing.md`.
