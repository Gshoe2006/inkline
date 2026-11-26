# Inkline's Homebrew tap

Homebrew's main cask collection (homebrew/cask) only takes apps signed with an Apple Developer ID and notarized,
and well-known enough. Until then Inkline goes in a **tap** of its own: a public GitHub repository named
`homebrew-inkline` under the same account, holding `Casks/inkline.rb`. People then install it with

```sh
brew install --cask gshoe2006/inkline/inkline
```

and `brew upgrade` updates it like any other cask.

## The cask

`packaging/stores/make_manifests.py` writes `inkline.rb` for each release (the **store-manifests** download of the
*Store manifests* workflow, folder `homebrew/`):

- the **universal** disk image (`inkline-<version>-macos.dmg`, Apple silicon and Intel), with its SHA-256 from the
  release, and `livecheck` following the latest GitHub release;
- `depends_on macos: ">= :sonoma"` (PySide6 6.12 needs macOS 14);
- `uninstall launchctl:` for the update check Inkline can set up (Help → Check for updates), and a `zap` stanza for
  its settings in `~/.config/inkline`, that launch agent's file, and macOS's preferences and saved window state;
- while the app isn't notarized, a `caveats` note saying how to open it the first time.

**Unsigned apps and quarantine:** Homebrew downloads with the quarantine flag, so macOS's Gatekeeper still asks
the first time an unsigned app is opened (Control-click → Open, or System Settings → Privacy & Security → Open
Anyway). Homebrew no longer offers a way round that (`--no-quarantine` is deprecated), and that's as it should be.
Once the release is signed and notarized (docs/code-signing.md), the workflow writes the cask without the caveat,
and Inkline could then be proposed to homebrew/cask itself.

## Set up the tap (once)

1. Create a **public** repository `Gshoe2006/homebrew-inkline` on GitHub (with a README, so it has a `main`
   branch).
2. Add the cask:

   ```sh
   git clone https://github.com/Gshoe2006/homebrew-inkline.git
   cd homebrew-inkline
   mkdir -p Casks
   cp /path/to/store-manifests/homebrew/inkline.rb Casks/inkline.rb
   git add Casks/inkline.rb
   git commit -m "inkline 6.1.0"
   git push
   ```

3. Check it on a Mac:

   ```sh
   brew tap gshoe2006/inkline
   brew audit --cask --strict gshoe2006/inkline/inkline
   brew install --cask gshoe2006/inkline/inkline
   brew uninstall --zap --cask inkline
   ```

## Keep it up to date automatically (optional)

The *Store manifests* workflow (`.github/workflows/stores.yml`) has a `homebrew-tap` job that, after each release,
copies the new `inkline.rb` into the tap and pushes it. It does nothing until you give it a token:

1. Create a **fine-grained personal access token** (GitHub → Settings → Developer settings → Personal access
   tokens → Fine-grained tokens) with access to **only** `Gshoe2006/homebrew-inkline`, permission
   **Contents: Read and write**, and an expiry you'll remember to renew.
2. In the `inkline` repository, add it as the Actions secret **`TAP_TOKEN`** (Settings → Secrets and variables →
   Actions).
3. Only if the tap has another name: add the variable `HOMEBREW_TAP` (for example `someone/homebrew-inkline`).

Without `TAP_TOKEN` the job says so and skips; you can always update the tap by hand as in step 2 above.
