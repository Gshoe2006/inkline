# Publishing Inkline in app stores

After each release, the **Store manifests** workflow writes what each store needs, with that release's checksums,
and keeps it as the run's **store-manifests** download (Actions → Store manifests → the run → Artifacts). Each
store is a one-time submission under your own account; after that, a new version is a small update with the new
files. Nothing here is submitted automatically.

| Store | Who it reaches | What you need | Effort |
| --- | --- | --- | --- |
| Flathub | GNOME Software, KDE Discover, any Linux with Flatpak | a GitHub account | an hour, then a reviewed pull request |
| winget | Windows 10 and 11 (`winget install Gshoe2006.Inkline`) | a GitHub account | minutes, then automated checks |
| Homebrew (a tap of your own) | Mac users of Homebrew | a GitHub repository | minutes |
| AUR | Arch, Manjaro, CachyOS (`yay -S inkline`) | an AUR account and an SSH key | minutes |
| Google Play | Android | a Play developer account ($25 once), the signing key, 12 testers for 14 days | an afternoon, two weeks of testing, then review |

## Flathub

1. Fork <https://github.com/flathub/flathub> and open a pull request against its `new-pr` branch, adding
   `io.github.gshoe2006.Inkline.yml` from **store-manifests/flathub/** (Flathub's
   [submission guide](https://docs.flathub.org/docs/for-app-authors/submission) has the details).
2. Flathub's reviewers build it and may ask for changes; once merged, Flathub makes a repository
   `flathub/io.github.gshoe2006.Inkline`, and each later release is a pull request there with the new
   manifest (its tag and commit), which Flathub's bot builds before you merge it.

The app ID `io.github.gshoe2006.Inkline` proves ownership through this GitHub account, so submit it from it.

## winget

1. Fork <https://github.com/microsoft/winget-pkgs>.
2. Put the three files from **store-manifests/winget/** in `manifests/g/Gshoe2006/Inkline/<version>/`.
3. Open a pull request; Microsoft's bots install and check the installer, then it's merged.

For later versions, `wingetcreate update Gshoe2006.Inkline --version <v> --urls <setup.exe url> --submit` does the
same from a command line.

The installer isn't signed (docs/code-signing.md): winget accepts that, but SmartScreen may still warn on first run.

## Homebrew

Homebrew's main cask collection only takes apps signed with an Apple Developer ID, so Inkline goes in a tap of its
own:

1. Make a public repository named `homebrew-inkline` under the same account.
2. Add **store-manifests/homebrew/inkline.rb** as `Casks/inkline.rb`.
3. People install it with `brew install --cask gshoe2006/inkline/inkline`; for a new version, replace the file.

Homebrew lets an unsigned app install, but macOS still asks on first open (Control-click → Open), as the README says.

## AUR

1. Make an account at <https://aur.archlinux.org> and add your SSH public key to it.
2. `git clone ssh://aur@aur.archlinux.org/inkline.git` (an empty repository the first time).
3. Copy **store-manifests/aur/PKGBUILD** and **.SRCINFO** into it, check it builds (`makepkg -si`), then commit
   and push. For a new version, the same with the new files.

It builds from the release's source and uses Arch's own PySide6, like the Arch package attached to each release.

## Google Play

Play takes an Android App Bundle (`.aab`), not an APK. Once the release key is set up (docs/android-signing.md),
**Android release** (`.github/workflows/android-release.yml`) adds a signed `inkline-<version>-android.aab` to every
release, next to the APKs. Everything for the listing is in the repository or the Android workflow's downloads:

| What | Where |
| --- | --- |
| The bundle | the release's `inkline-<version>-android.aab` |
| Title, short and full description, category, contact | `packaging/android/play/listing.md` |
| Privacy policy | `packaging/android/play/privacy.md` (link to it on GitHub) |
| Icon (512×512) and feature graphic (1024×500) | the **play-graphics** download of the Android workflow, or `python3 packaging/android/play/make_graphics.py OUTDIR` |
| Phone screenshots | the **play-screenshots** download (Actions → Android → the run → Artifacts) |
| Tablet screenshots | **play-screenshots-tablet**, when the tablet emulator managed (it's allowed to fail) |

### What the bundle is

- **arm64 only.** python-for-android's Qt bootstrap builds one ABI per run (each ABI has its own PySide6 wheel),
  and bundles of different ABIs can't simply be merged: each lists the Qt libraries to load for its own ABI in its
  compiled resources. Play accepts an arm64-only bundle: it reaches every 64-bit ARM phone and tablet, which is
  nearly all of them. x86-64 Chromebooks see it if they translate ARM code (many do); otherwise their owners can use
  the `-android-x86_64.apk` from GitHub. (`build.py --release --aab --arch x86_64` makes an x86-64 bundle,
  `inkline-<version>-android-x86_64.aab`, with its own versionCode; whether Play Console takes it beside the arm64
  one in the same release is worth trying before relying on it. Merging the two into one bundle would mean merging
  their compiled resources, which isn't done.)
- **Target API 35** (`ANDROID_API` in `packaging/android/deploy.py`), minimum API 28 (Android 9, Qt 6.12's
  minimum). Play raises the target it requires every August (API 35 from 31 August 2025; expect API 36 from
  31 August 2026): check <https://developer.android.com/google/play/requirements/target-sdk> before uploading, and
  if it has gone up, change `ANDROID_API`, the `platforms;android-NN` the workflows install, and the
  `targetSdkVersion` the Android workflow checks for. Building for a newer target: `build.py --target-api 36`.
- **16 KB pages.** Play requires every native library of an app targeting API 35 or later to be aligned for 16 KB
  memory pages. NDK r28c builds that way by default; the workflows check every library in the APKs and the bundle
  with `packaging/android/check_16kb.py` (and `zipalign -c -P 16`), and fail if one isn't.
- **versionCode** `1 000 000 000 + XYYZZ × 10 + ABI` from VERSION X.Y.Z (6.1.0 on arm64: 1000601001; x86_64 ends
  in 2), from `version_code()` in `packaging/android/build.py`. It rises with every release as long as the minor
  and patch numbers stay under 100, and it's above what earlier APKs had, so they update in place.
- **Icon:** an adaptive launcher icon drawn from `inkline.svg` at build time (the page on the dark background).

### Before the first submission

- **Updates on Android.** Play's policy doesn't let an app installed from Play point people to installing a newer
  version from elsewhere. Inkline's Android update check offers the APK on the GitHub release page (`updater.py`,
  install kind `android`); the copy built for Play should only say a new version exists (Play updates it), or not
  check at all. That's a change in `inkapp/`, not made yet: make it before the first upload.
- Read `aapt2 dump badging` in the Android workflow's log ("Check it as Google Play would"): it lists the
  permissions the APK asks for, which the Data safety form and the review look at.

### One-time setup

1. **A developer account:** <https://play.google.com/console/signup>, with a Google account. It costs **$25 once**.
   Personal accounts are checked with a government ID and need a real Android phone for verification; an
   organisation account needs a D-U-N-S number instead.
2. **Create the app:** Play Console → Create app: name **Inkline**, default language English (United Kingdom),
   *App*, *Free*; accept the declarations. The package name is set by the first upload:
   `io.github.gshoe2006.inkline`, and it can never change.
3. **App content** (Policy → App content), each a short form:
   - Privacy policy: the GitHub link to `packaging/android/play/privacy.md`.
   - Ads: no ads. App access: all functionality is available without special access (no login).
   - **Content rating** questionnaire (IARC): category *Reference, news or educational* (or *All other app
     types*); no violence, fear, sexuality, language, controlled substances or gambling; no user interaction or
     shared content between users; no location sharing; no purchases. That gives Everyone / PEGI 3 / USK 0.
   - **Target audience:** Inkline's users are the parents and teachers who make the pages, so choose the 18+ age
     group (adding under-13 groups brings in Play's Families policy and its extra review; Inkline has no ads or
     data collection, so it could meet it, but it's more to declare). Say the listing may appeal to children if
     asked: it shows colouring pages.
   - **Data safety:** *Does your app collect or share any of the required user data types?* **No.** Inkline sends
     nothing about the person or their work anywhere; photos and pages stay on the device. The optional update
     check is a plain request to GitHub's public releases API carrying no user data. Data encrypted in transit and
     deletion requests then don't apply. Inkline is open source, and this matches `privacy.md`.
   - Government app, financial features, health, news, COVID-19: no.
4. **Store listing** (Grow users → Store presence → Main store listing): paste the fields from `listing.md`; upload
   the icon, the feature graphic, 2 to 8 phone screenshots from **play-screenshots**, and tablet ones from
   **play-screenshots-tablet** if there are some. Store settings: category Education (or Art & Design), contact
   email, website `https://github.com/Gshoe2006/inkline`.

### Closed testing first: 12 testers for 14 days

New **personal** developer accounts can't publish to production straight away: an app must first run a **closed
test with at least 12 testers who stay opted in for at least 14 days in a row**, then you apply for production
access. (Organisation accounts skip this.)

1. Test and release → Testing → **Closed testing** → Create track (or use *Alpha*) → Testers: an email list or a
   Google Group with at least 12 people (friends, family, teachers who'll try it), and copy the opt-in link for them.
2. Create a release: let Google create and manage the app signing key (Play App Signing; docs/android-signing.md
   explains why the release key becomes the upload key), upload `inkline-<version>-android.aab` from the GitHub
   release, and paste that version's notes from CHANGELOG.md. Review and roll out; Google reviews it (hours to a few
   days).
3. Testers open the link, join, and install Inkline from Play. Keep at least 12 of them opted in for 14 days; new
   versions uploaded to the same track during the test are fine, and Play asks for real use and feedback.
4. Dashboard → **Apply for production**: a few questions about the test (how testers were found, what feedback
   changed, why it's ready). Once approved, promote the release (or upload the latest bundle) to **Production**,
   at a staged rollout percentage if you like.

### Each new version

The release's new `inkline-<version>-android.aab` goes into a new release on the production track (or a test track
first), with its CHANGELOG notes. Its versionCode is already higher than the last. Uploading could be automated
later (a Play service account and an upload step in android-release.yml); it isn't set up.

## F-Droid

F-Droid builds every app from source, including its libraries; Inkline's Android build uses Qt's prebuilt PySide6
for Android, so F-Droid's main repository won't take it as it is.
