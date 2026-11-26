# Submitting Inkline to winget

winget (the Windows Package Manager) takes packages as pull requests to
[microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs), with the manifests in
`manifests/g/Gshoe2006/Inkline/<version>/`. After that, people install Inkline with
`winget install Gshoe2006.Inkline` and update it with `winget upgrade`.

## The manifests

`packaging/stores/make_manifests.py` writes the three files for each release (the **store-manifests** download of
the *Store manifests* workflow, folder `winget/`), with the installer's SHA-256 from the release:

- `Gshoe2006.Inkline.yaml` (version), `Gshoe2006.Inkline.installer.yaml`, `Gshoe2006.Inkline.locale.en-US.yaml`,
  schema 1.6.0.
- **Installer:** `inkline-<version>-windows-setup.exe`, an Inno Setup installer (`InstallerType: inno`, so winget
  runs it with Inno Setup's own silent switches, `/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-`). It's listed twice:
  `Scope: user` with `/CURRENTUSER` (the installer's default: no administrator needed, into
  `%LOCALAPPDATA%\Programs\Inkline`) and `Scope: machine` with `/ALLUSERS` (for everyone, into Program Files).
- `ProductCode: {6F1B7F0A-3C2E-4E9B-9C55-1D2B7A4E8C31}_is1`, the uninstall key Inno Setup makes from the installer's
  AppId (`packaging/windows/inkline.iss`), so winget recognises an Inkline installed without it.
- `.inkline` files (`FileExtensions`), the licence, a description and the release notes' link.

The installer is unsigned until code signing is set up (docs/code-signing.md). winget accepts unsigned installers;
its checks scan the installer, and SmartScreen may still warn when it's run by hand.

## Check them on Windows

```powershell
winget validate --manifest .\store-manifests\winget
winget settings --enable LocalManifestFiles     # once, in an administrator PowerShell
winget install --manifest .\store-manifests\winget
winget uninstall Gshoe2006.Inkline
```

## Submit, the quick way: wingetcreate

[wingetcreate](https://github.com/microsoft/winget-create) (`winget install Microsoft.WingetCreate`) forks
winget-pkgs, commits and opens the pull request for you. It needs a GitHub token with the `public_repo` scope
(it asks you to sign in in the browser if you don't give one):

```powershell
wingetcreate submit .\store-manifests\winget
```

For each later release, it can also write the new manifests itself from the new installer:

```powershell
wingetcreate update Gshoe2006.Inkline --version 6.2.0 --urls https://github.com/Gshoe2006/inkline/releases/download/6.2.0/inkline-6.2.0-windows-setup.exe --submit
```

(Check afterwards that both installers, user and machine, are still there with their switches.) wingetcreate may
move the manifests to a newer schema version; that's fine.

## Submit by hand

1. Fork [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs).
2. In your fork, add the three files as `manifests/g/Gshoe2006/Inkline/<version>/` (for example
   `manifests/g/Gshoe2006/Inkline/6.1.0/Gshoe2006.Inkline.installer.yaml`), on a new branch named like
   `Gshoe2006.Inkline-6.1.0`. Only this one package version in the pull request.
3. Open a pull request titled `New package: Gshoe2006.Inkline version 6.1.0` (for later ones,
   `New version: Gshoe2006.Inkline version 6.2.0`). Keep the checklist the pull request template puts in the
   description and tick what applies; the first time, the bot asks you to sign Microsoft's Contributor License
   Agreement in a comment.
4. Microsoft's bots validate the manifests and install the package in a clean Windows; when the checks pass, a
   moderator merges it. If a check fails, the bot comments with the log: fix the files in your branch.

### Pull request description

```markdown
New package: Inkline 6.1.0, a free (GPL-3.0-or-later) app that makes black and white pages to print at
true paper size: colouring pages, puzzles, worksheets and photo prints.

- Publisher / upstream: https://github.com/Gshoe2006/inkline (I'm its developer)
- Installer: the release's Inno Setup installer from GitHub Releases. It installs for the current user by
  default (no elevation); the `machine` entry passes `/ALLUSERS`.
- ProductCode is Inno Setup's `{AppId}_is1` key.
- Validated with `winget validate` and tested with `winget install --manifest`.
```
