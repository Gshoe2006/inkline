"""Signs and notarizes Inkline.app and its disk image with an Apple Developer ID (docs/code-signing.md).

packaging/macos/build.py uses this when MACOS_SIGN_IDENTITY is set (or a certificate was imported with
import-cert); otherwise the app is signed ad hoc, as before, and macOS asks the first time it's opened.

    python3 packaging/macos/sign.py import-cert >> "$GITHUB_ENV"
        puts the Developer ID Application certificate from MACOS_CERT_P12 (base64) and MACOS_CERT_PASSWORD in a new
        keychain of its own, and prints MACOS_KEYCHAIN=… and MACOS_SIGN_IDENTITY=… for the steps after it
    python3 packaging/macos/sign.py delete-keychain
        removes that keychain again (MACOS_KEYCHAIN)

Notarization takes either an Apple ID: APPLE_ID, APPLE_TEAM_ID and APPLE_APP_PASSWORD (an app-specific password),
or an App Store Connect API key: APPLE_API_KEY_P8 (the .p8 file's text, or base64 of it), APPLE_API_KEY_ID and
APPLE_API_ISSUER. With neither, the app is signed but not notarized, and the build says so.

Everything that builds a command is a plain function, so the tests can check them on any computer.
"""

import base64
import json
import os
import secrets
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ENTITLEMENTS = os.path.join(HERE, "entitlements.plist")
# the first four bytes of a Mach-O file (thin 32/64-bit either way round, and universal "fat" files)
MACHO_MAGIC = {bytes.fromhex(h) for h in ("feedface", "feedfacf", "cefaedfe", "cffaedfe", "cafebabe", "bebafeca")}
SECRET_FLAGS = ("--password", "-p", "-P", "-k")   # -k: set-key-partition-list's keychain password


# --- what to sign, in which order -----------------------------------------------------------------------------
def is_macho(path):
    try:
        with open(path, "rb") as f:
            head = f.read(8)
    except OSError:
        return False
    if len(head) < 8 or head[:4] not in MACHO_MAGIC:
        return False
    if head[:4] == bytes.fromhex("cafebabe"):   # a Java class file starts the same way: fat files hold few archs
        return int.from_bytes(head[4:8], "big") < 20
    return True


def _is_signable_bundle(path):
    """A nested .framework or .app that codesign can sign as a bundle (it has an Info.plist)."""
    if path.endswith(".app"):
        return os.path.exists(os.path.join(path, "Contents", "Info.plist"))
    if path.endswith(".framework"):
        return any(os.path.exists(os.path.join(path, *p, "Info.plist"))
                   for p in (("Resources",), ("Versions", "Current", "Resources")))
    return False


def _bundle_main_binary(path, bundles):
    """Whether path is the main program of one of the bundles (signed with its bundle, not on its own)."""
    parts = path.split(os.sep)
    for b in bundles:
        name = os.path.basename(b).rsplit(".", 1)[0]
        if b.endswith(".framework") and path.startswith(b + os.sep) and parts[-1] == name and "Versions" in parts:
            return True
        if b.endswith(".app") and path == os.path.join(b, "Contents", "MacOS", name):
            return True
    return False


def signing_order(bundle):
    """Everything inside the app that needs its own signature, inside out: the deepest first, so each bundle is
    signed after what it holds. The app itself comes last. Symbolic links are left alone (what they point to is
    signed once); codesign's --deep isn't used, as Apple advises."""
    bundle = os.path.normpath(bundle)
    nested, files = [], []
    for dirpath, dirnames, filenames in os.walk(bundle):
        for d in dirnames:
            p = os.path.join(dirpath, d)
            if not os.path.islink(p) and _is_signable_bundle(p):
                nested.append(p)
        for f in filenames:
            p = os.path.join(dirpath, f)
            if not os.path.islink(p) and is_macho(p):
                files.append(p)
    main = os.path.join(bundle, "Contents", "MacOS", os.path.basename(bundle).rsplit(".", 1)[0])
    files = [f for f in files if f != main and not _bundle_main_binary(f, nested)]
    items = files + nested
    # deeper first; at the same depth, files before bundles; then by name, so the order is always the same
    items.sort(key=lambda p: (-p.count(os.sep), p in nested, p))
    return items + [bundle]


# --- the commands --------------------------------------------------------------------------------------------
def codesign_cmd(path, identity, keychain=None, entitlements=None, runtime=True):
    cmd = ["codesign", "--force", "--timestamp", "--sign", identity]
    if runtime:
        cmd += ["--options", "runtime"]
    if keychain:
        cmd += ["--keychain", keychain]
    if entitlements:
        cmd += ["--entitlements", entitlements]
    return cmd + [path]


def app_commands(bundle, identity, keychain=None, entitlements=ENTITLEMENTS):
    """codesign for each nested piece, then the app with the hardened runtime and Inkline's entitlements."""
    order = signing_order(bundle)
    return ([codesign_cmd(p, identity, keychain) for p in order[:-1]] +
            [codesign_cmd(order[-1], identity, keychain, entitlements=entitlements)])


def verify_app_commands(bundle):
    # --deep is fine for checking (only signing with it is discouraged)
    return [["codesign", "--verify", "--deep", "--strict", "--verbose=2", bundle],
            ["codesign", "--display", "--verbose=2", bundle]]


def dmg_command(dmg, identity, keychain=None):
    return codesign_cmd(dmg, identity, keychain, runtime=False)


def notary_credentials(env, key_dir=None):
    """notarytool's credential options from the environment, or None when there are none. An API key's text is
    written to a file in key_dir (notarytool reads it from a file)."""
    if env.get("APPLE_API_KEY_P8") and env.get("APPLE_API_KEY_ID") and env.get("APPLE_API_ISSUER"):
        text = env["APPLE_API_KEY_P8"].strip()
        if "BEGIN PRIVATE KEY" not in text:
            text = base64.b64decode(text).decode("utf-8")
        key_dir = key_dir or tempfile.mkdtemp(prefix="inkline-notary-")
        path = os.path.join(key_dir, f"AuthKey_{env['APPLE_API_KEY_ID']}.p8")
        with open(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w", encoding="utf-8") as f:
            f.write(text + "\n")
        return ["--key", path, "--key-id", env["APPLE_API_KEY_ID"], "--issuer", env["APPLE_API_ISSUER"]]
    if env.get("APPLE_ID") and env.get("APPLE_TEAM_ID") and env.get("APPLE_APP_PASSWORD"):
        return ["--apple-id", env["APPLE_ID"], "--team-id", env["APPLE_TEAM_ID"], "--password", env["APPLE_APP_PASSWORD"]]
    return None


def notarize_command(dmg, credentials):
    return ["xcrun", "notarytool", "submit", dmg, "--wait", "--output-format", "json"] + credentials


def notary_log_command(submission_id, credentials):
    return ["xcrun", "notarytool", "log", submission_id] + credentials


def notary_result(output):
    """(accepted, submission id, status) from `notarytool submit --wait --output-format json`."""
    try:
        data = json.loads(output.strip().splitlines()[-1] if output.strip() else "{}")
    except (ValueError, IndexError):
        return False, None, "unreadable"
    status = str(data.get("status", ""))
    return status == "Accepted", data.get("id"), status or "unknown"


def staple_commands(dmg):
    return [["xcrun", "stapler", "staple", dmg], ["xcrun", "stapler", "validate", dmg]]


def gatekeeper_commands(dmg):
    """spctl's own verdict on the disk image, as a downloaded one is checked."""
    return [["spctl", "--assess", "-vv", "--type", "open", "--context", "context:primary-signature", dmg]]


def redact(cmd):
    """The command for the log, with passwords hidden."""
    out = list(cmd)
    for i, a in enumerate(out[:-1]):
        if a in SECRET_FLAGS:
            out[i + 1] = "***"
    return out


# --- the keychain (on the release's Mac) ------------------------------------------------------------------------
def keychain_commands(keychain, keychain_password, p12, cert_password, existing=()):
    return [
        ["security", "create-keychain", "-p", keychain_password, keychain],
        ["security", "set-keychain-settings", "-lut", "21600", keychain],
        ["security", "unlock-keychain", "-p", keychain_password, keychain],
        ["security", "import", p12, "-k", keychain, "-P", cert_password, "-f", "pkcs12",
         "-T", "/usr/bin/codesign", "-T", "/usr/bin/security"],
        ["security", "set-key-partition-list", "-S", "apple-tool:,apple:,codesign:", "-s", "-k", keychain_password,
         keychain],
        ["security", "list-keychains", "-d", "user", "-s", keychain, *existing],
    ]


def parse_identity(find_identity_output):
    """The first "Developer ID Application" identity `security find-identity -v -p codesigning` lists."""
    for line in find_identity_output.splitlines():
        if '"Developer ID Application:' in line:
            return line.split('"')[1]
    return None


# --- running them ---------------------------------------------------------------------------------------------
def run(cmd, capture=False):
    print("+", " ".join(redact(cmd)), file=sys.stderr, flush=True)   # stdout may be $GITHUB_ENV
    return subprocess.run(cmd, check=True, capture_output=capture, text=True)


def sign_app(bundle, identity, keychain=None):
    for cmd in app_commands(bundle, identity, keychain):
        run(cmd)
    for cmd in verify_app_commands(bundle):
        run(cmd)


def sign_and_notarize_dmg(dmg, identity, keychain=None, env=None):
    """Signs the disk image; notarizes and staples it when there are notarization credentials. False if it
    couldn't be notarized for want of them."""
    env = os.environ if env is None else env
    run(dmg_command(dmg, identity, keychain))
    with tempfile.TemporaryDirectory(prefix="inkline-notary-") as key_dir:
        creds = notary_credentials(env, key_dir)
        if not creds:
            print("::warning::Signed with a Developer ID but not notarized: no APPLE_ID/APPLE_TEAM_ID/APPLE_APP_PASSWORD "
                  "or APPLE_API_KEY_P8/APPLE_API_KEY_ID/APPLE_API_ISSUER (docs/code-signing.md).", flush=True)
            return False
        p = subprocess.run(notarize_command(dmg, creds), capture_output=True, text=True)
        print(p.stderr, end="", file=sys.stderr)
        accepted, sub_id, status = notary_result(p.stdout)
        print(f"notarization: {status} ({sub_id})", flush=True)
        if not accepted:
            if sub_id:
                subprocess.run(notary_log_command(sub_id, creds))
            raise SystemExit(f"sign.py: Apple didn't notarize {os.path.basename(dmg)} ({status})")
    for cmd in staple_commands(dmg) + gatekeeper_commands(dmg):
        run(cmd)
    return True


def import_cert(env=None, out=sys.stdout):
    env = os.environ if env is None else env
    if not env.get("MACOS_CERT_P12"):
        raise SystemExit("sign.py: no MACOS_CERT_P12")
    tmp = env.get("RUNNER_TEMP") or tempfile.gettempdir()
    keychain = os.path.join(tmp, "inkline-signing.keychain-db")
    p12 = os.path.join(tmp, "inkline-cert.p12")
    with open(os.open(p12, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "wb") as f:
        f.write(base64.b64decode(env["MACOS_CERT_P12"]))
    try:
        existing = [k.strip().strip('"') for k in
                    subprocess.run(["security", "list-keychains", "-d", "user"], check=True, capture_output=True,
                                   text=True).stdout.splitlines() if k.strip()]
        for cmd in keychain_commands(keychain, secrets.token_hex(16), p12, env.get("MACOS_CERT_PASSWORD", ""), existing):
            run(cmd, capture=True)
    finally:
        os.remove(p12)
    identity = env.get("MACOS_SIGN_IDENTITY") or parse_identity(
        run(["security", "find-identity", "-v", "-p", "codesigning", keychain], capture=True).stdout)
    if not identity:
        raise SystemExit("sign.py: the certificate in MACOS_CERT_P12 holds no Developer ID Application identity")
    print(f"MACOS_KEYCHAIN={keychain}", file=out)
    print(f"MACOS_SIGN_IDENTITY={identity}", file=out)


def delete_keychain(env=None):
    keychain = (os.environ if env is None else env).get("MACOS_KEYCHAIN")
    if keychain and os.path.exists(keychain):
        subprocess.run(["security", "delete-keychain", keychain])


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else ""
    if what == "import-cert":
        import_cert()
    elif what == "delete-keychain":
        delete_keychain()
    else:
        raise SystemExit("sign.py: import-cert | delete-keychain")
