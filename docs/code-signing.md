# Signing the Windows installer with SignPath

Windows SmartScreen warns about an unsigned installer ("unknown publisher"). SignPath Foundation gives
open-source projects a free code signing certificate. The certificate is issued to SignPath Foundation, which
appears as the publisher. The private key never leaves SignPath's hardware: the release workflow sends the
installer to SignPath, someone approves the release there, and the signed installer comes back.

Until the steps below are done, nothing changes: the release workflow skips signing and publishes the
installer unsigned.

## 1. What SignPath Foundation asks of the project

From [signpath.org/terms](https://signpath.org/terms):

- **OSI-approved licence, no proprietary parts.** Inkline is GPL-3.0. It bundles Qt (LGPL), PySide6 (LGPL)
  and numpy (BSD) unsigned, which is allowed ("you may include unsigned binaries of upstream OSS projects").
- **Released, maintained and documented.** The installer is already published on GitHub Releases, and the
  README says what Inkline does.
- **Multi-factor authentication** on both GitHub and SignPath for everyone on the team.
- **Roles:** authors (committers), reviewers and approvers, named in the README's
  [Code signing policy](../README.md#code-signing-policy).
- **A "Code signing policy" on the home page and the release pages,** with the line "Free code signing provided
  by SignPath.io, certificate by SignPath Foundation", the roles and a privacy statement. The README has it,
  and the release workflow adds a link to it to every release's notes.
- **An uninstaller,** and no changes to the system without warning. The installer has an uninstaller (Settings →
  Apps).
- **Built from source in a verifiable way,** on GitHub-hosted runners, with each release approved by hand.
- **Product name and version set on every signed file,** enforced in the artifact configuration. The installer
  carries "Inkline" and the version, and the release workflow checks them.

SignPath Foundation also says it wants executables it signs to have "a certain verifiable reputation", and
it decides which projects to accept. A young project may be asked to wait.

## 2. Apply

Fill in the form at [signpath.org/apply](https://signpath.org/apply) with the repository
(`https://github.com/Gshoe2006/inkline`), the licence (GPL-3.0), what's signed (the Windows installer, built
by GitHub Actions) and where releases are published (GitHub Releases).

## 3. Once accepted: set up SignPath

In SignPath ([app.signpath.io](https://app.signpath.io)):

1. **Trusted build system:** add the predefined *GitHub.com* trusted build system to the organization, and link
   it to the project.
2. **GitHub App:** install the SignPath GitHub App on the repository. SignPath uses it to check where each build
   came from.
3. **Project:** call it `inkline`, the slug the workflow expects.
4. **Artifact configuration:** paste in
   [`packaging/windows/signpath-artifact-configuration.xml`](../packaging/windows/signpath-artifact-configuration.xml)
   and make it the default.
5. **Signing policy:** call it `release-signing`, with the SignPath Foundation certificate. Make yourself an
   approver, so each release waits for your approval.
6. **API token:** create a CI user (or a token for yourself) that may submit signing requests to that policy.

## 4. Tell the repository

In GitHub, open the repository's Settings → Secrets and variables → Actions:

- **Secret** `SIGNPATH_API_TOKEN`: the API token.
- **Variable** `SIGNPATH_ORGANIZATION_ID`: the organization ID (SignPath shows it under the organization's
  settings).
- Only if you chose other names in SignPath: variables `SIGNPATH_PROJECT_SLUG` (default `inkline`) and
  `SIGNPATH_SIGNING_POLICY_SLUG` (default `release-signing`).

## 5. Each release

When a release merges, the Windows job builds the installer and sends it to SignPath. It then waits, for up
to 75 minutes, for you to approve the signing request in SignPath, where it waits under the project's signing requests. After approval,
the job checks that the installer's signature is valid and publishes it with the other packages. If nobody
approves in time, the job fails and nothing is published; re-run the workflow to try again.

Test builds ("Test build only") and builds of other branches are never sent for signing.

## If the first signing request is refused

Inno Setup pads the installer's product name and version with spaces ("Inkline" and "4.7.1" followed by
blanks). The SignPath documentation doesn't say whether its product-name and product-version checks ignore
trailing spaces. If the first request is refused over them, remove the `product-name` and `product-version`
attributes from the artifact configuration in SignPath for now, and ask SignPath support how they want an
Inno Setup installer restricted (SignPath Foundation requires the restriction).
