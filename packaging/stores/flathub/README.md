# Submitting Inkline to Flathub

Flathub takes a new app as a pull request to [flathub/flathub](https://github.com/flathub/flathub), against its
**`new-pr`** branch, adding the manifest. Once it's merged, Flathub makes a repository of the app's own,
`flathub/io.github.gshoe2006.Inkline`, and each later release is a pull request there.

## The manifest

`io.github.gshoe2006.Inkline.yml` is written for each release by `packaging/stores/make_manifests.py` (the
**store-manifests** download of the *Store manifests* workflow, folder `flathub/`). It's the repository's own
Flatpak manifest (`packaging/flatpak/io.github.gshoe2006.Inkline.yml`, which the release builds and tests) with one
change: Inkline's source is its git repository at the release's tag, pinned to the tag's commit. To write it
yourself, without downloading anything:

```sh
python3 packaging/stores/make_manifests.py 6.1.0 --commit "$(git rev-list -n 1 6.1.0)" --flathub-only --out store-manifests
```

What it already does for Flathub's rules:

- **No network while building.** Every source is pinned: Inkline by tag and commit, and PySide6 (Essentials only),
  shiboken6 and numpy as PyPI's wheels by URL and sha256, installed with `pip install --no-index`.
- **Both processors Flathub builds for:** the wheels come for x86-64 and ARM64 (`only-arches`).
- **AppStream** (`packaging/flatpak/io.github.gshoe2006.Inkline.metainfo.xml`): ID, `<developer id>`, launchable,
  OARS content rating, screenshots by URL with captions, branding colours, the media type it opens, and a
  `<release>` for each version (the release workflow warns when the new version's is missing).
- **Desktop file and icons** renamed to the app ID, the `.inkline` file type and its icon too, and the licence
  installed.

## Before submitting

1. **Check the manifest and the AppStream file with Flathub's linter** (the manifest file must be named exactly
   `io.github.gshoe2006.Inkline.yml`):

   ```sh
   flatpak install --user flathub org.flatpak.Builder
   flatpak run --command=flatpak-builder-lint org.flatpak.Builder manifest store-manifests/flathub/io.github.gshoe2006.Inkline.yml
   flatpak run --command=flatpak-builder-lint org.flatpak.Builder appstream packaging/flatpak/io.github.gshoe2006.Inkline.metainfo.xml
   ```

   Both should pass (an AppStream "pedantic" note that the ID has capital letters is fine: Flathub allows it for
   `io.github.*` IDs).
2. **Build and run it from the manifest**, as Flathub's bot will:

   ```sh
   flatpak-builder --user --install --force-clean build-flathub store-manifests/flathub/io.github.gshoe2006.Inkline.yml
   flatpak run io.github.gshoe2006.Inkline
   ```

   `flatpak run --command=flatpak-builder-lint org.flatpak.Builder builddir build-flathub` then checks the build.
   Locally it reports `appstream-external-screenshot-url` ("Screenshots are not mirrored to dl.flathub.org"): that
   one is expected, since Flathub's own build copies the screenshots to its server (add
   `--mirror-screenshots-url=https://dl.flathub.org/media` to the flatpak-builder command to see it go away).

3. Make sure two-factor authentication is on for the GitHub account you submit from. The ID
   `io.github.gshoe2006.Inkline` is verified against `github.com/Gshoe2006`, so submit from that account.

## Submitting

1. Fork [flathub/flathub](https://github.com/flathub/flathub) **with all its branches** (untick "Copy the master
   branch only"), then:

   ```sh
   git clone --branch=new-pr git@github.com:Gshoe2006/flathub.git
   cd flathub
   git checkout -b io.github.gshoe2006.Inkline new-pr
   cp /path/to/store-manifests/flathub/io.github.gshoe2006.Inkline.yml .
   git add io.github.gshoe2006.Inkline.yml
   git commit -m "Add io.github.gshoe2006.Inkline"
   git push -u origin io.github.gshoe2006.Inkline
   ```

   (Flathub's [submission guide](https://docs.flathub.org/docs/for-app-authors/submission) says whether the
   manifest goes at the top of the repository or in a folder named after the app ID; follow what it says now.)
2. Open a pull request **against `new-pr`** (not `master`), titled `Add io.github.gshoe2006.Inkline`. Keep the
   checklist Flathub's pull request template puts in the description, tick what applies, and add the text below.
3. Flathub's bot builds it when a reviewer (or you) comments `bot, build`. Answer the reviewers' comments in the
   pull request; when they approve and merge it, you're invited to `flathub/io.github.gshoe2006.Inkline`.
4. **Later releases:** open a pull request in `flathub/io.github.gshoe2006.Inkline` replacing the manifest with the
   new release's one from **store-manifests**; the bot builds it, and merging publishes it.

### Pull request description

```markdown
Inkline makes black and white pages to print at true paper size: colouring pages (mandalas, mazes,
dot-to-dots, name pages), puzzles (sudoku, kakuro, nonograms, word searches, spot the difference) and
photos turned into dithering, halftone, engraving or stippling; booklets, photo books and posters.
It prints, or saves PDF, PNG or SVG.

- Upstream: https://github.com/Gshoe2006/inkline (GPL-3.0-or-later). I'm its developer, and submit from
  the account the app ID is based on.
- Built from the release's git tag, pinned to its commit. PySide6 (only its Essentials: QtCore, QtGui,
  QtWidgets, QtPrintSupport), shiboken6 and numpy come as PyPI's wheels pinned by sha256, for x86_64 and
  aarch64, installed with `pip install --no-index`: there's no PySide6 in the freedesktop runtime, and the
  same wheels are what the project's other packages ship and test.
- `--socket=cups`: Inkline is a printing app, and Qt prints through CUPS (File → Print…).
- `--env=QT_QPA_PLATFORMTHEME=xdgdesktopportal`: file dialogs go through the desktop's portal, so no
  filesystem access is requested.
- No network permission. The app's update check is opt-in and, in a Flatpak, only points to the release
  page; without network access it simply finds nothing, and Flathub keeps the app up to date.
- `flatpak-builder-lint` passes for the manifest and the AppStream file.
```

## If the reviewers ask for changes

- **Prebuilt wheels:** if they'd rather not have PySide6 and numpy as binary wheels, the alternative is Flathub's
  PySide6 base app (`base: io.qt.PySide.BaseApp` on the KDE runtime), which provides PySide6, with numpy built from
  source or from its wheel. That changes the runtime, so make the same change in `packaging/flatpak/` (the release
  builds and tests that manifest) and make_manifests.py follows it.
- **Screenshots:** they're the PNGs in `docs/screenshots/` on GitHub, referenced from `main`. Flathub keeps its own
  copies when it builds, but if a reviewer asks for stable URLs, point them at a tag instead.
- **Release notes:** Flathub shows a `<description>` for each `<release>` if there is one; the metainfo file has
  dates only so far.
