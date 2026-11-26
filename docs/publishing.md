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
| Google Play | Android | a Play developer account ($25 once) and the signing key | an afternoon, then review |

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

Play wants an Android App Bundle signed through Play App Signing. Once the release key is set up
(docs/android-signing.md):

1. Make a Play developer account (<https://play.google.com/console>), and an app named Inkline with the package name
   `io.github.gshoe2006.inkline`.
2. Fill in the store listing, content rating and data safety form (Inkline collects nothing; it only asks GitHub for
   the latest version when updates are on).
3. Upload a bundle: buildozer builds one with `android.release_artifact = aab` (a change to
   packaging/android/deploy.py, not made yet), then Play reviews it.

F-Droid builds every app from source, including its libraries; Inkline's Android build uses Qt's prebuilt PySide6
for Android, so F-Droid's main repository won't take it as it is.
