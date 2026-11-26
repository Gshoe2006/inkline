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

Steps, the checks to run first and the pull request text: [packaging/stores/flathub/README.md](../packaging/stores/flathub/README.md).

In short: fork <https://github.com/flathub/flathub> and open a pull request against its `new-pr` branch with
`io.github.gshoe2006.Inkline.yml` from **store-manifests/flathub/**. Once merged, Flathub makes a repository
`flathub/io.github.gshoe2006.Inkline`, and each later release is a pull request there with the new manifest. The
manifest is the repository's own Flatpak manifest with the source pinned to the release's tag and commit, for
x86-64 and ARM64. The app ID `io.github.gshoe2006.Inkline` proves ownership through this GitHub account, so
submit it from it.

## winget

Steps (wingetcreate, or a pull request by hand) and the pull request text:
[packaging/stores/winget/README.md](../packaging/stores/winget/README.md).

In short: the three files from **store-manifests/winget/** go in `manifests/g/Gshoe2006/Inkline/<version>/` of a
fork of <https://github.com/microsoft/winget-pkgs>, in a pull request; Microsoft's bots install and check the
installer, then it's merged. `wingetcreate submit store-manifests/winget` does it from a command line. The installer
is unsigned until code signing is set up (docs/code-signing.md): winget accepts that, but SmartScreen may still warn.

## Homebrew

Setting up the tap, checking the cask, and updating it automatically:
[packaging/stores/homebrew/README.md](../packaging/stores/homebrew/README.md).

Homebrew's main cask collection only takes apps signed with an Apple Developer ID, so Inkline goes in a tap of its
own: a public repository `Gshoe2006/homebrew-inkline` with **store-manifests/homebrew/inkline.rb** as
`Casks/inkline.rb`. People install it with `brew install --cask gshoe2006/inkline/inkline`. With a `TAP_TOKEN`
secret, the Store manifests workflow pushes each new cask to the tap itself. Until the app is notarized, macOS
still asks on first open (Control-click → Open), and the cask says so.

## AUR

SSH key, first push and updates: [packaging/stores/aur/README.md](../packaging/stores/aur/README.md).

In short: make an account at <https://aur.archlinux.org> with your SSH public key,
`git clone ssh://aur@aur.archlinux.org/inkline.git`, copy in **store-manifests/aur/PKGBUILD** and **.SRCINFO**,
check it builds (`makepkg -si`), then commit and push. It builds from the release's source and uses Arch's own
PySide6, like the Arch package attached to each release.

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
