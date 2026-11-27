# Signing the Android APKs

Each release can carry signed APKs for Android phones and tablets (`inkline-<version>-android-aarch64.apk`) and for
x86-64 Android (Chromebooks, emulators: `-android-x86_64.apk`), and a signed Android App Bundle for Google Play
(`inkline-<version>-android.aab`, arm64). They're built and added by `.github/workflows/android-release.yml` after
the Release workflow publishes a release — only once the release key is in the repository's secrets. Android only installs updates signed with the same key as the copy installed, so
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
workflow**: it builds both APKs and the bundle from that release's code, checks their signatures and their 16 KB
page alignment, and adds them to it.

Without the secrets the workflow only says that no key is set; nothing else changes.

## Google Play: this key is the upload key

Google Play signs what it delivers to phones with its own **app signing key** (Play App Signing, required for app
bundles). The key above signs what you upload: for Play it is the **upload key**. When you create the app in Play
Console and upload the first bundle, choose to let Google create and keep the app signing key (the default);
Play registers the certificate of the key that signed that first bundle as your upload key, and from then on
accepts only bundles signed with it.

- Users who installed the APK from GitHub can't update it from Play, or the other way round: the two are signed
  with different keys (Play's app signing key and this one). Moving between them means uninstalling first.
- If the upload key is lost or leaked, Play can register a new one (Play Console → Test and release → App
  integrity → App signing → Request upload key reset); the app signing key, kept by Google, doesn't change. A lost
  key still means the GitHub APKs can't be updated, so keep the backup.
- Play Console → App integrity → App signing shows both certificates' SHA-256 fingerprints; `keytool -list -v
  -keystore inkline-release.keystore` shows this key's, to compare.

## F-Droid

F-Droid builds every app from source, which Qt's prebuilt PySide6 for Android doesn't allow. See
`docs/publishing.md`.
