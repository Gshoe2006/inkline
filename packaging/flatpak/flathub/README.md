# Submitting Inkline to Flathub

`io.github.gshoe2006.Inkline.yml` here is the manifest for Flathub. It's the same build as
`../io.github.gshoe2006.Inkline.yml`, but it takes Inkline's source from GitHub at a release tag,
pinned to the tag's commit, as Flathub requires.

## Before submitting

1. **Make the repository public.** Flathub builds from public source. It checks the app ID
   `io.github.gshoe2006.Inkline` against https://github.com/Gshoe2006/inkline, and it downloads the
   screenshots listed in the AppStream file from there. While the repository is private, its
   checker reports `appid-url-not-reachable` and `appstream-missing-screenshots`.
2. **Publish a release** that includes `LICENSE`, `docs/screenshots/` and this folder. Inkline's
   release tags are the plain version, such as `3.4.2`.
3. **Fill in the manifest:** set `tag` to the release's tag and `commit` to that tag's full commit
   hash (`git rev-list -n 1 3.4.2`). It's filled in for 3.4.2.
4. **Run Flathub's checker,** with the manifest named exactly `io.github.gshoe2006.Inkline.yml`:
   ```sh
   flatpak install --user flathub org.flatpak.Builder
   flatpak run --command=flatpak-builder-lint org.flatpak.Builder manifest io.github.gshoe2006.Inkline.yml
   flatpak run --command=flatpak-builder-lint org.flatpak.Builder appstream ../io.github.gshoe2006.Inkline.metainfo.xml
   ```
   Both should report no errors.

## Submitting

1. Fork https://github.com/flathub/flathub, and create a branch from its **`new-pr`** branch, not
   from `master`.
2. Add `io.github.gshoe2006.Inkline.yml` (the filled-in manifest) at the top of the fork.
3. Open a pull request against `flathub/flathub`'s `new-pr` branch, titled
   `Add io.github.gshoe2006.Inkline`.
4. Flathub's bot builds it and its reviewers comment on the pull request. Once it's accepted,
   Flathub creates `flathub/io.github.gshoe2006.Inkline`, and later releases are pull requests
   there that update the tag and commit.

## Notes for the review

- `--socket=cups` is there for **File → Print…**: Qt prints through CUPS, and Inkline is a printing
  app.
- PySide6 and numpy come as their official wheels (PySide6's Essentials only), pinned by sha256.
