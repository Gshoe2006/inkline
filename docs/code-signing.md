# Code signing

Inkline's Windows installer and macOS app are **unsigned until the secrets below are added**. Signing is optional
in the release workflow (`.github/workflows/release.yml`), the same way Android signing is
(`android-release.yml`): each job looks for its secrets, signs when they're there, and otherwise builds unsigned and
says so in the run ("No Windows code signing is set up…", "No MACOS_CERT_P12 secret…").

Without signing:

- **Windows:** SmartScreen may say the installer is from an unknown publisher (**More info → Run anyway**).
- **macOS:** the app is signed ad hoc only, so the first time it's opened macOS says it can't check it (Control-click
  → **Open**, or System Settings → Privacy & Security → **Open Anyway**).

## The options and what they cost

Prices and eligibility change; check each provider's current terms before paying for anything.

| Option | For | Cost | What it takes |
| --- | --- | --- | --- |
| [SignPath Foundation](https://signpath.org) | Windows installer | free for open-source projects | an application, which SignPath Foundation may accept or turn down; MFA; each release approved by hand in SignPath; the publisher shown is "SignPath Foundation" |
| [Azure Trusted Signing](https://learn.microsoft.com/azure/trusted-signing/) | Windows (Inkline.exe, installer) | about US$10 a month (Basic tier) | an Azure subscription and Microsoft's identity validation. It has been limited to organizations in some countries and to individual developers in a few (the US and Canada when this was written). Check the current eligibility, and whether Microsoft has renamed it (it's being rebranded as *Artifact Signing*) |
| A code signing certificate (.pfx) | Windows (Inkline.exe, installer, uninstaller) | a few hundred US$ a year from a certificate authority | identity validation. Since 2023 new certificates must keep their key on hardware (a token or a cloud HSM), so a plain exportable .pfx is mostly an option for a certificate you already have |
| [Apple Developer Program](https://developer.apple.com/programs/) | macOS (Developer ID signing and notarization) | US$99 a year | an Apple Account with two-factor authentication; an organization also needs a D-U-N-S number |

On Windows one of them is used, in this order when several are set up: Azure Trusted Signing, then the .pfx, then
SignPath. Azure Trusted Signing and the .pfx sign every build (including "Test build only" runs, which checks that
signing works); SignPath signs only a release, because each one waits for your approval.

## Windows: Azure Trusted Signing

1. In the [Azure portal](https://portal.azure.com), create a **Trusted Signing account** (Basic), then an
   **identity validation** (Public Trust) and, once it's approved, a **certificate profile** (Public Trust).
2. Create an app registration (Microsoft Entra ID → App registrations), give it a client secret, and give it the
   **Trusted Signing Certificate Profile Signer** role on the Trusted Signing account.
3. In GitHub, under the repository's Settings → Secrets and variables → Actions, add:
   - **Secrets** `AZURE_TENANT_ID` (the directory/tenant ID), `AZURE_CLIENT_ID` (the app registration's
     application ID) and `AZURE_CLIENT_SECRET` (its client secret's value).
   - **Variables** `TRUSTED_SIGNING_ENDPOINT` (the account's region endpoint, such as
     `https://eus.codesigning.azure.net/`), `TRUSTED_SIGNING_ACCOUNT` (the account's name) and
     `TRUSTED_SIGNING_PROFILE` (the certificate profile's name).

The release builds the app (`packaging/windows/build.py --stage app`), signs `dist/Inkline/Inkline.exe` with
[`azure/trusted-signing-action`](https://github.com/Azure/trusted-signing-action), builds the installer and the
portable zip from it (`--stage package`), and signs the installer. The uninstaller that the installer writes isn't
signed this way (Inno Setup can only sign it through a command line; the .pfx route does).

## Windows: a .pfx certificate

Add two **secrets**:

- `WINDOWS_CERT_PFX`: the .pfx file, base64 encoded. On Windows:
  `[Convert]::ToBase64String([IO.File]::ReadAllBytes("cert.pfx")) | Set-Clipboard`; on Linux or a Mac:
  `base64 -w0 cert.pfx` (on a Mac, `base64 -i cert.pfx`).
- `WINDOWS_CERT_PASSWORD`: its password.

The release imports the certificate into the runner's own certificate store, sets `INKLINE_SIGN_CMD` to a
`signtool sign /fd sha256 /tr http://timestamp.digicert.com /td sha256 /sha1 <thumbprint>` command (signtool from
the Windows SDK; `build.py --signtool-template <thumbprint>` writes it), and `build.py` then signs Inkline.exe
before it's packed into the installer and the zip. Inno Setup signs the installer and its uninstaller with the same
command. No password is ever on a command line.

`INKLINE_SIGN_CMD` works on your own computer too: set it to any command holding `{file}` and run
`python packaging/windows/build.py`.

## Windows: SignPath Foundation (free for open source)

SignPath Foundation gives open-source projects a free certificate. It's issued to SignPath Foundation, which
appears as the publisher, and the private key never leaves SignPath's hardware: the release workflow sends the
installer to SignPath, someone approves the release there, and the signed installer comes back. Only the installer
is signed this way, not the Inkline.exe inside it.

### What SignPath Foundation asks of the project

From [signpath.org/terms](https://signpath.org/terms):

- **OSI-approved licence, no proprietary parts.** Inkline is GPL-3.0. It bundles Qt (LGPL), PySide6 (LGPL)
  and numpy (BSD) unsigned, which is allowed ("you may include unsigned binaries of upstream OSS projects").
- **Released, maintained and documented.** The installer is already published on GitHub Releases, and the
  README says what Inkline does.
- **Multi-factor authentication** on both GitHub and SignPath for everyone on the team.
- **Roles:** authors (committers), reviewers and approvers, named in the README's
  [Code signing policy](../README.md#code-signing-policy).
- **A "Code signing policy" on the home page and the release pages,** with the line "Free code signing provided
  by SignPath.io, certificate by SignPath Foundation", the roles and a privacy statement. The README has it
  (saying the installer stays unsigned until SignPath Foundation accepts Inkline), and the release workflow adds
  a link to it to every release's notes.
- **An uninstaller,** and no changes to the system without warning. The installer has an uninstaller (Settings →
  Apps).
- **Built from source in a verifiable way,** on GitHub-hosted runners, with each release approved by hand.
- **Product name and version set on every signed file,** enforced in the artifact configuration. The installer
  carries "Inkline" and the version, and the release workflow checks them.

SignPath Foundation also says it wants executables it signs to have "a certain verifiable reputation", and
it decides which projects to accept. A young project may be asked to wait.

### Apply

Answers ready to copy into the form are in [signpath-application.md](signpath-application.md). Fill in the form at
[signpath.org/apply](https://signpath.org/apply) with the repository (`https://github.com/Gshoe2006/inkline`), the
licence (GPL-3.0), what's signed (the Windows installer, built by GitHub Actions) and where releases are published
(GitHub Releases).

### Once accepted: set up SignPath

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

### Tell the repository

The quickest way is the setup script. Run it on your own computer with the [GitHub CLI](https://cli.github.com)
signed in (`gh auth login`):

```sh
bash packaging/windows/signpath-setup.sh            # asks for the organization ID and the API token
bash packaging/windows/signpath-setup.sh --check    # shows what's set up
bash packaging/windows/signpath-setup.sh --remove   # stops signing again
```

It checks that two-factor authentication is on for your GitHub account. It then saves the token as the secret
`SIGNPATH_API_TOKEN`, without showing it, and the organization ID as the variable `SIGNPATH_ORGANIZATION_ID`.

Or do it by hand in GitHub, under the repository's Settings → Secrets and variables → Actions:

- **Secret** `SIGNPATH_API_TOKEN`: the API token.
- **Variable** `SIGNPATH_ORGANIZATION_ID`: the organization ID (SignPath shows it under the organization's
  settings).
- Only if you chose other names in SignPath: variables `SIGNPATH_PROJECT_SLUG` (default `inkline`) and
  `SIGNPATH_SIGNING_POLICY_SLUG` (default `release-signing`).

### Each release

When a release merges, the Windows job builds the installer and sends it to SignPath. It then waits, for up
to 75 minutes, for you to approve the signing request in SignPath, where it waits under the project's signing
requests. After approval, the job checks that the installer's signature is valid and publishes it with the other
packages. If nobody approves in time, the job fails and nothing is published; re-run the workflow to try again.

Test builds ("Test build only") and builds of other branches are never sent to SignPath.

### If the first signing request is refused

Inno Setup pads the installer's product name and version with spaces ("Inkline" and "4.7.1" followed by
blanks). The SignPath documentation doesn't say whether its product-name and product-version checks ignore
trailing spaces. If the first request is refused over them, remove the `product-name` and `product-version`
attributes from the artifact configuration in SignPath for now, and ask SignPath support how they want an
Inno Setup installer restricted (SignPath Foundation requires the restriction).

## macOS: Developer ID and notarization

1. Join the [Apple Developer Program](https://developer.apple.com/programs/) (US$99 a year).
2. **Certificate:** as the account holder, create a **Developer ID Application** certificate (Xcode → Settings →
   Accounts → Manage Certificates, or [developer.apple.com/account/resources](https://developer.apple.com/account/resources/certificates/list)).
   In Keychain Access, export it with its private key as a .p12 file, with a password.
3. **Notarization credentials**, one of:
   - an **app-specific password** for your Apple Account ([account.apple.com](https://account.apple.com) → Sign-In
     and Security → App-Specific Passwords), with your Apple ID and your team ID (Membership details on
     developer.apple.com); or
   - an **App Store Connect API key** (App Store Connect → Users and Access → Integrations → Team Keys, role
     Developer): download the .p8 file once, and note its key ID and the issuer ID shown above the keys.
4. Add the **secrets**:
   - `MACOS_CERT_P12`: the .p12, base64 encoded (`base64 -i cert.p12 | pbcopy`).
   - `MACOS_CERT_PASSWORD`: the .p12's password.
   - `MACOS_SIGN_IDENTITY` (optional): the identity's full name, such as
     `Developer ID Application: Your Name (ABCDE12345)`; without it the first Developer ID Application identity in
     the .p12 is used.
   - For an app-specific password: `APPLE_ID` (your Apple Account's email), `APPLE_TEAM_ID` and `APPLE_APP_PASSWORD`.
   - Or for an API key: `APPLE_API_KEY_P8` (the .p8 file's text, or base64 of it), `APPLE_API_KEY_ID` and
     `APPLE_API_ISSUER`. When both are there, the API key is used.

Each of the three macOS builds then:

1. puts the certificate in a keychain of its own (`packaging/macos/sign.py import-cert`), removed again at the end;
2. builds Inkline.app and signs everything in it inside out with `codesign --options runtime --timestamp`: each
   `.so` and `.dylib`, then each framework, the app last with
   [`packaging/macos/entitlements.plist`](../packaging/macos/entitlements.plist) (Python's
   `allow-unsigned-executable-memory` and `disable-library-validation`), and no `--deep`;
3. builds the disk image and signs it, sends it to Apple with `xcrun notarytool submit --wait`, staples the ticket
   to it (`xcrun stapler staple`) and checks it with `spctl`;
4. runs the self-test with the signed app (so the hardened runtime is tested too).

With the certificate but no notarization credentials, the app and disk image are signed but not notarized, and the
run warns. macOS still asks on first open then.

## Checking a signed build

**Windows** (PowerShell):

```powershell
Get-AuthenticodeSignature .\inkline-6.1.0-windows-setup.exe | Format-List Status, SignerCertificate, TimeStamperCertificate
& "C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64\signtool.exe" verify /pa /v .\inkline-6.1.0-windows-setup.exe
```

Or right-click the file → Properties → **Digital Signatures**. Check Inkline.exe in the portable zip and in the
installed folder the same way. Status should be `Valid`, with a timestamp.

**macOS:**

```sh
xcrun stapler validate inkline-6.1.0-macos.dmg
spctl --assess -vv --type open --context context:primary-signature inkline-6.1.0-macos.dmg
codesign --verify --deep --strict --verbose=2 /Applications/Inkline.app
spctl --assess -vv /Applications/Inkline.app        # "accepted, source=Notarized Developer ID"
codesign --display --verbose=2 /Applications/Inkline.app   # Authority=Developer ID Application: …, Runtime Version
```

## Updates and signatures

Help → Check for updates (`inkapp/updater.py`) downloads the new package and checks its SHA-256 against the digest
GitHub publishes for the release asset; it doesn't check a code signature. On Windows it runs the new installer
(`/SILENT`); on macOS it copies the app out of the disk image in place of the old one. Files downloaded this way
carry no "downloaded from the internet" mark, so SmartScreen and Gatekeeper don't check them either. Signing
therefore mainly helps people downloading Inkline in a browser; the updater behaves the same either way. Checking
the signature (the publisher, as well as the SHA-256) before installing would be a later change.
