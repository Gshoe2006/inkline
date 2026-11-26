# Publishing Inkline in the AUR

The Arch User Repository takes a package as a git repository of its own on aur.archlinux.org, holding a `PKGBUILD`
and its `.SRCINFO`. People then install it with an AUR helper (`yay -S inkline`, `paru -S inkline`).

## The files

`packaging/stores/make_manifests.py` writes them for each release (the **store-manifests** download of the
*Store manifests* workflow, folder `aur/`). The PKGBUILD builds from the release's source tarball on GitHub (with its
SHA-256) and uses Arch's own `pyside6` and `python-numpy`, like the Arch package attached to each release. Before
the first push, put your own name and email in its `# Maintainer:` line (AUR guidelines ask for a way to reach the
maintainer); keep that line when you copy in later versions.

Note on updates: the AUR package says it was installed as `arch`, so Inkline's own Help → Check for updates offers
to install the release's Arch package (`inkline-<version>-1-any.pkg.tar.zst`, the same files) with pacman. Either
way the package is called `inkline`, so `yay -Syu` and the in-app update replace each other cleanly.

## First time

1. Make an account at <https://aur.archlinux.org/register> and add your **SSH public key** under My Account
   (make one with `ssh-keygen -t ed25519 -f ~/.ssh/aur` if you don't have one).
2. Tell SSH to use it for the AUR, in `~/.ssh/config`:

   ```
   Host aur.archlinux.org
     IdentityFile ~/.ssh/aur
     User aur
   ```

3. Clone the (still empty) package repository. The name is free if this gives an empty repository rather than an
   error:

   ```sh
   git clone ssh://aur@aur.archlinux.org/inkline.git aur-inkline
   cd aur-inkline
   ```

4. Copy in the files, check they build and install on Arch, and push:

   ```sh
   cp /path/to/store-manifests/aur/PKGBUILD /path/to/store-manifests/aur/.SRCINFO .
   makepkg -si                       # builds from the release tarball and installs it
   namcap PKGBUILD                   # optional: Arch's package checker (pacman -S namcap)
   git add PKGBUILD .SRCINFO
   git commit -m "Inkline 6.1.0"
   git push origin master            # the AUR's branch is master
   ```

   The package appears at <https://aur.archlinux.org/packages/inkline>.

## Each later release

```sh
cd aur-inkline
cp /path/to/store-manifests/aur/PKGBUILD /path/to/store-manifests/aur/.SRCINFO .
makepkg -si
git commit -am "Inkline 6.2.0"
git push
```

If you edit the PKGBUILD by hand, regenerate `.SRCINFO` with `makepkg --printsrcinfo > .SRCINFO` before committing:
the AUR refuses a push whose `.SRCINFO` doesn't match.
