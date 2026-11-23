# Answers for the SignPath Foundation application

Ready-made answers for the form at [signpath.org/apply](https://signpath.org/apply). The form's exact questions
couldn't be seen when this was written, so match these to what it asks. Your own name and email go in by hand.

Before you send it:

- **Turn on two-factor authentication on GitHub** (https://github.com/settings/security). SignPath Foundation
  requires it for everyone on the team. `bash packaging/windows/signpath-setup.sh --check` shows whether it's
  on.
- **Check the README's [Code signing policy](../README.md#code-signing-policy).** It's what SignPath reads to
  see the team's roles and privacy statement.

---

**Project name**
Inkline

**Repository**
https://github.com/Gshoe2006/inkline

**Home page / download page**
https://github.com/Gshoe2006/inkline (download page: https://github.com/Gshoe2006/inkline/releases)

**Licence**
GPL-3.0 (GNU General Public License v3.0). Every component is open source: Inkline's own code is GPL-3.0, and
the libraries it bundles are Qt and PySide6 (LGPL-3.0) and numpy (BSD-3-Clause). There is no commercial
dual licence and no proprietary code.

**What the project does**
Inkline is a desktop app for Linux and Windows that makes black & white pages to print: colouring pages,
mazes, sudoku, nonograms, kakuro, word searches, dot-to-dots, spot the difference and name pages, and photos
turned into line art, halftone, engraving or colour-by-number pages. It builds multi-page booklets with answer
pages, prints class sets with a different design on each copy, and makes posters across several sheets. It's
aimed at parents and teachers. It works offline and makes no network connections.

**What should be signed**
The Windows installer, `inkline-<version>-windows-setup.exe`, published with each release on GitHub
Releases (since 4.7.0). It's an Inno Setup installer around the app, which PyInstaller builds. Only the
installer is signed: it's what users download. The program files inside it come from the same build.

**How it's built**
GitHub Actions, on GitHub-hosted runners (windows-2022), from the repository's own source:
`.github/workflows/release.yml`. A release is built and published when the version number changes on the
main branch. The workflow already has the SignPath step (`signpath/github-action-submit-signing-request@v3`).
The build artifact is uploaded with `actions/upload-artifact@v4`, and the artifact configuration is in
`packaging/windows/signpath-artifact-configuration.xml`. It signs only the installer for the release's
version, whose product name and version must match.

**Releases so far**
Inkline is published on GitHub Releases with packages for Linux (.deb, AppImage, Flatpak, Arch package,
`.run` installer) and Windows (since 4.7.0). Each release runs the app's self-test with every package
before anything is published.

**Team and roles**
- Committers and reviewers: Gshoe2006 (https://github.com/Gshoe2006), the sole maintainer
- Approvers: Gshoe2006

**Privacy**
This program will not transfer any information to other networked systems unless specifically requested by
the user or the person installing or operating it.

**Installation and uninstallation**
The installer installs for the current user without administrator rights, or for every user, and says so
on its pages. It adds a Start menu entry and the `.inkline` file association, and it uninstalls
from Settings → Apps.

**Why signing is wanted**
Windows SmartScreen warns about the unsigned installer ("unknown publisher"), so people have to choose "More
info → Run anyway". A signature that ties the installer to this repository's builds would remove that warning
and let users check where the installer came from.

---

Be aware that SignPath Foundation says it signs executables only for projects with "a certain verifiable
reputation". Inkline is young, and SignPath may ask to see more history first. If they say no, the release
workflow keeps publishing the installer unsigned, exactly as now. Nothing else needs undoing.
