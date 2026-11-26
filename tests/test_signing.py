"""Optional code signing in the release (docs/code-signing.md): the commands packaging/windows/build.py and
packaging/macos/sign.py build, and what they sign in which order. Nothing here needs Windows, a Mac or a certificate."""
import importlib.util
import io
import os
import plistlib
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name, *path):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, *path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


win = _load("windows_build", "packaging", "windows", "build.py")
sign = _load("macos_sign", "packaging", "macos", "sign.py")
sys.modules.setdefault("sign", sign)
mac = _load("macos_build", "packaging", "macos", "build.py")

THUMB = "0123456789abcdef0123456789ABCDEF01234567"
SIGNTOOL = r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\signtool.exe"


def _read(*p):
    with open(os.path.join(ROOT, *p), encoding="utf-8") as f:
        return f.read()


# --- Windows ----------------------------------------------------------------------------------------------------
def test_nothing_is_signed_without_a_signing_command():
    assert win.sign_template({}) is None and win.sign_template({"INKLINE_SIGN_CMD": "  "}) is None
    with pytest.raises(SystemExit):
        win.sign_template({"INKLINE_SIGN_CMD": "signtool sign /a"})   # where would the file go?
    assert win.sign_template({"INKLINE_SIGN_CMD": "signtool sign {file}"}) == "signtool sign {file}"


def test_the_signtool_command_picks_the_certificate_by_thumbprint():
    t = win.signtool_template(THUMB, signtool=SIGNTOOL)
    assert t.startswith(f'"{SIGNTOOL}" sign /fd sha256 /tr http://timestamp.digicert.com /td sha256 ')
    assert f"/sha1 {THUMB.upper()}" in t and t.endswith(" {file}")
    assert "/p " not in t and "/f " not in t                 # no password, no certificate file
    for bad in ("", "xyz", THUMB[:-1]):
        with pytest.raises(SystemExit):
            win.signtool_template(bad, signtool=SIGNTOOL)


def test_each_file_is_signed_with_its_path_quoted():
    t = win.signtool_template(THUMB, signtool=SIGNTOOL)
    cmd = win.sign_command(t, r"D:\a\inkline\dist\Inkline\Inkline.exe")
    assert cmd.endswith(r' "D:\a\inkline\dist\Inkline\Inkline.exe"') and "{file}" not in cmd
    seen = []
    win.sign(r"D:\x\Inkline.exe", t, run=lambda c, **k: seen.append((c, k)))
    assert seen == [(win.sign_command(t, r"D:\x\Inkline.exe"), {"shell": True, "check": True})]
    assert win.app_files_to_sign(os.path.join("dist", "Inkline")) == [os.path.join("dist", "Inkline", "Inkline.exe")]


def test_inno_setup_signs_the_installer_and_uninstaller_with_the_same_command():
    t = 'C:\\pay$\\signtool.exe sign /sha1 AB "{file}x" {file}'
    assert win.inno_sign_tool(t) == "C:\\pay$$\\signtool.exe sign /sha1 AB $q$fx$q $f"
    args = win.iscc_args("iscc", "6.1.0", "dist/Inkline", win.signtool_template(THUMB, signtool=SIGNTOOL))
    assert "/DSIGNTOOL" in args and args[-1].endswith("inkline.iss")
    s = next(a for a in args if a.startswith("/Sinkline="))
    assert '"' not in s and s.startswith("/Sinkline=$qC:\\Program Files (x86)") and s.endswith(" $f")
    plain = win.iscc_args("iscc", "6.1.0", "dist/Inkline")
    assert "/DSIGNTOOL" not in plain and not any(a.startswith("/S") for a in plain)
    iss = _read("packaging", "windows", "inkline.iss")
    assert "#ifdef SIGNTOOL\n" in iss and "SignTool=inkline\n" in iss and "SignedUninstaller=yes" in iss


def test_signtool_comes_from_the_newest_windows_sdk():
    base = os.path.join(r"C:\PF86", "Windows Kits", "10", "bin")
    have = {os.path.join(base, v, "x64", "signtool.exe") for v in ("10.0.19041.0", "10.0.22621.0")}
    found = win.find_signtool({"ProgramFiles(x86)": r"C:\PF86"}, which=lambda n: None, exists=have.__contains__,
                              listdir=lambda p: ["10.0.19041.0", "10.0.22621.0", "10.0.26100.0", "x64"])
    assert found == os.path.join(base, "10.0.22621.0", "x64", "signtool.exe")   # 26100 has no signtool here
    assert win.find_signtool({}, which=lambda n: "C:\\on\\path\\signtool.exe") == "C:\\on\\path\\signtool.exe"
    with pytest.raises(SystemExit):
        win.find_signtool({}, which=lambda n: None, listdir=lambda p: [])


def test_the_release_signs_windows_only_when_set_up():
    flow = _read(".github", "workflows", "release.yml")
    for name in ("secrets.AZURE_CLIENT_ID", "vars.TRUSTED_SIGNING_ACCOUNT", "secrets.WINDOWS_CERT_PFX",
                 "vars.SIGNPATH_ORGANIZATION_ID", "'none'"):
        assert name in flow, name
    assert flow.count("uses: azure/trusted-signing-action@") == 2 and flow.count("if: env.SIGN_WITH == 'azure'") >= 2
    # Inkline.exe is signed between building the app and packing it into the installer and the zip
    app, package = flow.index("build.py --stage app"), flow.index("build.py --stage package")
    assert app < flow.index("Sign Inkline.exe (Azure Trusted Signing)") < package
    assert package < flow.index("Sign the installer (Azure Trusted Signing)")
    assert "INKLINE_SIGN_CMD=$(python packaging/windows/build.py --signtool-template" in flow
    assert "No Windows code signing is set up" in flow and 'Get-AuthenticodeSignature $f' in flow
    assert "if: env.SIGN_WITH == 'signpath'" in flow


# --- macOS ------------------------------------------------------------------------------------------------------
MACHO = bytes.fromhex("cffaedfe0c000001") + b"\0" * 24
FAT = bytes.fromhex("cafebabe00000002") + b"\0" * 24


def _bundle(tmp_path):
    app = tmp_path / "Inkline.app"
    files = {
        "Contents/Info.plist": b"<plist/>",
        "Contents/MacOS/Inkline": FAT,
        "Contents/Frameworks/libpython3.12.dylib": MACHO,
        "Contents/Frameworks/numpy/_core/_multiarray_umath.cpython-312-darwin.so": MACHO,
        "Contents/Frameworks/PySide6/QtCore.abi3.so": MACHO,
        "Contents/Frameworks/PySide6/Qt/lib/QtCore.framework/Versions/A/QtCore": MACHO,
        "Contents/Frameworks/PySide6/Qt/lib/QtCore.framework/Versions/A/Resources/Info.plist": b"<plist/>",
        "Contents/Frameworks/PySide6/Qt/plugins/platforms/libqcocoa.dylib": MACHO,
        "Contents/Frameworks/NoPlist.framework/Versions/A/NoPlist": MACHO,      # not a signable bundle
        "Contents/Resources/inkline.icns": b"icns",
        "Contents/Resources/base_library.zip": b"PK\3\4",
        "Contents/Resources/Example.class": bytes.fromhex("cafebabe00000041"),   # Java, not a fat Mach-O
    }
    for rel, data in files.items():
        p = app / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    fw = app / "Contents/Frameworks/PySide6/Qt/lib/QtCore.framework"
    os.symlink("A", fw / "Versions" / "Current")
    os.symlink("Versions/Current/QtCore", fw / "QtCore")
    os.symlink("Versions/Current/Resources", fw / "Resources")
    os.symlink("../Frameworks/libpython3.12.dylib", app / "Contents/Resources/libpython3.12.dylib")
    return app


def test_mach_o_files_are_told_apart(tmp_path):
    for name, data, want in (("thin", MACHO, True), ("fat", FAT, True), ("java", bytes.fromhex("cafebabe00000041"), False),
                             ("text", b"#!/bin/sh\n", False), ("short", b"\xcf\xfa", False)):
        (tmp_path / name).write_bytes(data)
        assert sign.is_macho(str(tmp_path / name)) is want, name
    assert sign.is_macho(str(tmp_path / "missing")) is False


def test_the_app_is_signed_inside_out(tmp_path):
    app = _bundle(tmp_path)
    rel = [os.path.relpath(p, tmp_path) for p in sign.signing_order(str(app))]
    fw = "Inkline.app/Contents/Frameworks/PySide6/Qt/lib/QtCore.framework"
    assert rel[-1] == "Inkline.app"                                         # the app last
    assert "Inkline.app/Contents/MacOS/Inkline" not in rel                  # signed with the app
    assert f"{fw}/Versions/A/QtCore" not in rel and fw in rel               # signed with its framework
    assert "Inkline.app/Contents/Frameworks/NoPlist.framework/Versions/A/NoPlist" in rel   # no Info.plist: a file
    assert not any(r.endswith((".icns", ".zip", ".class", ".plist")) for r in rel)
    assert "Inkline.app/Contents/Resources/libpython3.12.dylib" not in rel  # a link: its file is signed once
    assert len(rel) == len(set(rel)) == 7
    depth = [r.count(os.sep) for r in rel[:-1]]
    assert depth == sorted(depth, reverse=True)                             # deepest first
    assert rel.index(f"{fw}") > rel.index("Inkline.app/Contents/Frameworks/PySide6/Qt/plugins/platforms/libqcocoa.dylib")
    assert sign.signing_order(str(app)) == sign.signing_order(str(app) + os.sep)


def test_the_codesign_commands(tmp_path):
    app = _bundle(tmp_path)
    ident = "Developer ID Application: Example (ABCDE12345)"
    cmds = sign.app_commands(str(app), ident, keychain="/tmp/k.keychain-db")
    assert len(cmds) == len(sign.signing_order(str(app)))
    for c in cmds:
        assert c[:5] == ["codesign", "--force", "--timestamp", "--sign", ident] and "--deep" not in c
        assert c[c.index("--options") + 1] == "runtime" and c[c.index("--keychain") + 1] == "/tmp/k.keychain-db"
    assert all("--entitlements" not in c for c in cmds[:-1])
    assert cmds[-1][-3:] == ["--entitlements", sign.ENTITLEMENTS, str(app)]
    dmg = sign.dmg_command("x.dmg", ident)
    assert dmg == ["codesign", "--force", "--timestamp", "--sign", ident, "x.dmg"]
    assert ["codesign", "--verify", "--deep", "--strict", "--verbose=2", "a.app"] in sign.verify_app_commands("a.app")


def test_the_entitlements_are_what_python_needs_and_no_more():
    with open(sign.ENTITLEMENTS, "rb") as f:
        ent = plistlib.load(f)
    assert ent == {"com.apple.security.cs.allow-unsigned-executable-memory": True,
                   "com.apple.security.cs.disable-library-validation": True}


def test_notarization_credentials(tmp_path):
    assert sign.notary_credentials({}) is None
    assert sign.notary_credentials({"APPLE_ID": "a@b.c", "APPLE_TEAM_ID": "T"}) is None     # no password
    ids = sign.notary_credentials({"APPLE_ID": "a@b.c", "APPLE_TEAM_ID": "T", "APPLE_APP_PASSWORD": "pw"})
    assert ids == ["--apple-id", "a@b.c", "--team-id", "T", "--password", "pw"]
    pem = "-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----"
    import base64
    for text in (pem, base64.b64encode(pem.encode()).decode()):
        env = {"APPLE_API_KEY_P8": text, "APPLE_API_KEY_ID": "K1", "APPLE_API_ISSUER": "iss", "APPLE_ID": "a@b.c",
               "APPLE_TEAM_ID": "T", "APPLE_APP_PASSWORD": "pw"}
        key = sign.notary_credentials(env, str(tmp_path))                    # the API key wins
        path = str(tmp_path / "AuthKey_K1.p8")
        assert key == ["--key", path, "--key-id", "K1", "--issuer", "iss"]
        assert open(path).read().strip() == pem and (os.stat(path).st_mode & 0o777) == 0o600
    cmd = sign.notarize_command("x.dmg", ids)
    assert cmd[:6] == ["xcrun", "notarytool", "submit", "x.dmg", "--wait", "--output-format"] and cmd[-6:] == ids
    assert sign.redact(cmd)[-1] == "***" and "pw" not in sign.redact(cmd)
    assert sign.staple_commands("x.dmg")[0] == ["xcrun", "stapler", "staple", "x.dmg"]
    assert sign.gatekeeper_commands("x.dmg")[0][:3] == ["spctl", "--assess", "-vv"]


def test_the_notary_verdict_is_read():
    assert sign.notary_result('{"id": "abc", "status": "Accepted", "message": "ok"}') == (True, "abc", "Accepted")
    assert sign.notary_result('Conducting pre-submission checks\n{"id": "d", "status": "Invalid"}') == (False, "d", "Invalid")
    assert sign.notary_result("")[0] is False and sign.notary_result("not json")[2] == "unreadable"


def test_the_keychain_commands_hide_their_passwords():
    cmds = sign.keychain_commands("/t/k.keychain-db", "kcpw", "/t/c.p12", "certpw", ["/Users/r/login.keychain-db"])
    assert cmds[0] == ["security", "create-keychain", "-p", "kcpw", "/t/k.keychain-db"]
    assert cmds[-1] == ["security", "list-keychains", "-d", "user", "-s", "/t/k.keychain-db", "/Users/r/login.keychain-db"]
    assert any(c[:2] == ["security", "set-key-partition-list"] for c in cmds)
    for c in cmds:
        shown = " ".join(sign.redact(c))
        assert "kcpw" not in shown and "certpw" not in shown
    out = '  1) ABCDEF "Apple Development: x"\n  2) 0123 "Developer ID Application: Example (ABCDE12345)"\n'
    assert sign.parse_identity(out) == "Developer ID Application: Example (ABCDE12345)"
    assert sign.parse_identity("0 valid identities found") is None


def test_import_cert_needs_a_certificate():
    with pytest.raises(SystemExit):
        sign.import_cert({}, out=io.StringIO())


def test_without_an_identity_the_app_is_signed_ad_hoc():
    assert mac.signing({}) == (None, None) and mac.signing({"MACOS_SIGN_IDENTITY": " "}) == (None, None)
    assert mac.signing({"MACOS_SIGN_IDENTITY": "Developer ID Application: X", "MACOS_KEYCHAIN": "/k"}) == \
        ("Developer ID Application: X", "/k")
    assert mac.ad_hoc_command("a.app") == ["codesign", "--force", "--deep", "--sign", "-", "a.app"]


def test_the_release_signs_macos_only_when_set_up():
    flow = _read(".github", "workflows", "release.yml")
    assert "HAVE_MAC_CERT: ${{ secrets.MACOS_CERT_P12 != '' }}" in flow
    assert 'python3 packaging/macos/sign.py import-cert >> "$GITHUB_ENV"' in flow
    assert "No MACOS_CERT_P12 secret, so Inkline.app is signed ad hoc" in flow
    for name in ("APPLE_ID", "APPLE_TEAM_ID", "APPLE_APP_PASSWORD", "APPLE_API_KEY_P8", "APPLE_API_KEY_ID",
                 "APPLE_API_ISSUER", "MACOS_CERT_PASSWORD", "MACOS_SIGN_IDENTITY"):
        assert f"${{{{ secrets.{name} }}}}" in flow, name
    assert "python3 packaging/macos/sign.py delete-keychain" in flow


def test_the_docs_list_every_secret():
    doc = _read("docs", "code-signing.md")
    for name in ("AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET", "TRUSTED_SIGNING_ENDPOINT",
                 "TRUSTED_SIGNING_ACCOUNT", "TRUSTED_SIGNING_PROFILE", "WINDOWS_CERT_PFX", "WINDOWS_CERT_PASSWORD",
                 "SIGNPATH_API_TOKEN", "SIGNPATH_ORGANIZATION_ID", "MACOS_CERT_P12", "MACOS_CERT_PASSWORD",
                 "MACOS_SIGN_IDENTITY", "APPLE_ID", "APPLE_TEAM_ID", "APPLE_APP_PASSWORD", "APPLE_API_KEY_P8",
                 "APPLE_API_KEY_ID", "APPLE_API_ISSUER"):
        assert f"`{name}`" in doc, name
    assert "docs/code-signing.md" in _read("README.md")
