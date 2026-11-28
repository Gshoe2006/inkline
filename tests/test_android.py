"""packaging/android: the first Android build (the app folder it packs, and its CI)."""
import importlib.util
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _build():
    spec = importlib.util.spec_from_file_location("android_build", os.path.join(ROOT, "packaging", "android", "build.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_the_app_folder_has_inkline_and_a_main_py(tmp_path, monkeypatch):
    build = _build()
    monkeypatch.setattr(build, "ROOT", ROOT)
    app = build.stage("x86_64")
    try:
        for name in ("main.py", "inkline.py", "VERSION", "inkline.svg", "inkengine/locale/de.json",
                     "inkengine/reading/en.json", "inkapp/window.py"):
            assert os.path.exists(os.path.join(app, name)), name
        assert not any("__pycache__" in d for d, _s, _f in os.walk(app))
        main = open(os.path.join(app, "main.py"), encoding="utf-8").read()
        assert '"inkline-selftest"' in main and '"--selftest"' in main and "inkline.main()" in main
    finally:
        import shutil
        shutil.rmtree(os.path.join(ROOT, "build", "android"), ignore_errors=True)


def test_deploy_adds_numpy_and_the_data_files():
    deploy = open(os.path.join(ROOT, "packaging", "android", "deploy.py"), encoding="utf-8").read()
    assert "\"python3,shiboken6,PySide6,numpy,pyjnius,inkline_fast\"" in deploy and "json,ttf,svg" in deploy
    assert '"io.github.gshoe2006"' in deploy and '"inkline"' in deploy


def test_ci_builds_both_and_runs_the_self_test_on_an_emulator():
    flow = open(os.path.join(ROOT, ".github", "workflows", "android.yml"), encoding="utf-8").read()
    assert "arch: [x86_64, aarch64]" in flow and "packaging/android/build.py --arch ${{ matrix.arch }}" in flow
    assert "reactivecircus/android-emulator-runner@v2" in flow and "check_selftest.py android-test/selftest" in flow
    test = open(os.path.join(ROOT, "packaging", "android", "emulator-test.sh"), encoding="utf-8").read()
    assert "io.github.gshoe2006.inkline" in test and "inkline-selftest" in test and "screencap" in test


def test_print_hands_the_pdf_to_androids_print_service(tmp_path):
    from inkapp import android_print
    calls = []

    class Activity:
        mActivity = "the activity"

    class PdfPrint:
        @staticmethod
        def start(activity, path, name, duplex):
            calls.append((activity, path, name, duplex))

    classes = {android_print.ACTIVITY: Activity, android_print.JAVA_CLASS: PdfPrint}
    android_print.print_pdf("/x/a.pdf", "Mazes", duplex=True, autoclass=classes.__getitem__)
    assert calls == [("the activity", "/x/a.pdf", "Mazes", True)]
    assert android_print.available("android") and not android_print.available("linux")
    p = android_print.job_path("Maze: 3/4")
    assert p.endswith("Maze_ 3_4.pdf") and os.path.isdir(os.path.dirname(p))

    def broken(_name):
        raise RuntimeError("java.lang.ClassNotFoundException")
    import pytest
    with pytest.raises(OSError):
        android_print.print_pdf("/x/a.pdf", "Mazes", autoclass=broken)


def test_print_on_android_writes_a_pdf_then_opens_androids_dialog(tmp_path, monkeypatch):
    import time
    from PySide6.QtWidgets import QApplication
    from inkapp import android_print
    from inkapp.window import Window
    monkeypatch.setenv("INKLINE_CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(android_print, "available", lambda platform=None: True)
    monkeypatch.setattr(android_print, "job_path", lambda name: str(tmp_path / "job.pdf"))
    opened = []
    monkeypatch.setattr(android_print, "print_pdf", lambda path, name, duplex=False: opened.append((path, duplex)))
    w = Window("6.0.0", remember=False)
    w.show()
    w.print_()
    end = time.time() + 30
    while not opened and time.time() < end:
        QApplication.processEvents()
        time.sleep(0.02)
    assert opened == [(str(tmp_path / "job.pdf"), False)]
    assert (tmp_path / "job.pdf").read_bytes()[:5] == b"%PDF-"
    assert "print dialog" in w.sidebar.status.text()


def test_the_apk_carries_print_and_ci_checks_the_dialog_opens():
    deploy = open(os.path.join(ROOT, "packaging", "android", "deploy.py"), encoding="utf-8").read()
    assert "numpy,pyjnius" in deploy and '"android.add_src", JAVA' in deploy
    java = os.path.join(ROOT, "packaging", "android", "java", "io", "github", "gshoe2006", "inkline", "PdfPrint.java")
    src = open(java, encoding="utf-8").read()
    assert "class PdfPrint extends PrintDocumentAdapter" in src and "public static void start(" in src
    assert "DUPLEX_MODE_SHORT_EDGE" in src and "COLOR_MODE_MONOCHROME" in src
    test = open(os.path.join(ROOT, "packaging", "android", "emulator-test.sh"), encoding="utf-8").read()
    assert "inkline-printtest" in test and "printspooler" in test


def test_release_apks_are_signed_and_added_after_a_release():
    flow = open(os.path.join(ROOT, ".github", "workflows", "android-release.yml"), encoding="utf-8").read()
    assert "workflows: [Release]" in flow and "--release" in flow and "apksigner\" verify" in flow
    for s in ("ANDROID_KEYSTORE", "ANDROID_KEYSTORE_PASSWORD", "ANDROID_KEY_ALIAS", "ANDROID_KEY_PASSWORD"):
        assert f"secrets.{s}" in flow and s in open(os.path.join(ROOT, "docs", "android-signing.md"), encoding="utf-8").read()
    assert "gh release upload" in flow and "fetch-wheels.sh" in flow
    deploy = open(os.path.join(ROOT, "packaging", "android", "deploy.py"), encoding="utf-8").read()
    assert 'build("release")' in deploy and "trim(" in deploy


def test_the_trim_follows_what_the_kept_modules_load(tmp_path):
    ns = {"PySideRecipe": type("R", (), {"build_arch": lambda s, a: None}), "info": print}
    exec(open(os.path.join(ROOT, "packaging", "android", "prune.py"), encoding="utf-8").read(), ns)
    assert ns["INKLINE_MODULES"] == {"QtCore", "QtGui", "QtWidgets", "QtPrintSupport"}
    import sys
    core = os.path.join(os.path.dirname(sys.modules["PySide6"].__file__), "QtCore.abi3.so")
    if os.path.exists(core):   # a Linux PySide6: its ELF files are read the same way
        assert any(n.startswith("libQt6Core") for n in ns["_inkline_needed"](core))
    pyside, libs = tmp_path / "PySide6", tmp_path / "libs"
    (pyside / "Qt" / "qml").mkdir(parents=True)
    (pyside / "Qt" / "plugins" / "platforms").mkdir(parents=True)
    (pyside / "Qt" / "plugins" / "multimedia").mkdir(parents=True)
    libs.mkdir()
    for f in ("QtCore.abi3.so", "QtQuick.abi3.so", "QtQuick.pyi"):
        (pyside / f).write_bytes(b"x")
    (libs / "libQt6Quick_x86_64.so").write_bytes(b"x" * 10)
    ns["inkline_prune"](str(pyside), str(libs))
    assert (pyside / "QtCore.abi3.so").exists() and not (pyside / "QtQuick.abi3.so").exists()
    assert not (pyside / "Qt" / "qml").exists() and not (pyside / "Qt" / "plugins" / "multimedia").exists()
    assert (pyside / "Qt" / "plugins" / "platforms").exists() and not (libs / "libQt6Quick_x86_64.so").exists()


def test_the_trim_drops_plugins_of_unused_kinds_and_what_only_they_load(tmp_path):
    ns = {"PySideRecipe": type("R", (), {"build_arch": lambda s, a: None}), "info": print}
    exec(open(os.path.join(ROOT, "packaging", "android", "prune.py"), encoding="utf-8").read(), ns)
    pyside, libs = tmp_path / "PySide6", tmp_path / "libs"
    (pyside / "Qt" / "lib").mkdir(parents=True)
    libs.mkdir()
    for f in ("libplugins_multimedia_ffmpegmediaplugin_x86_64.so", "libplugins_platforms_qtforandroid_x86_64.so",
              "libavcodec.so", "libQt6Multimedia_x86_64.so"):
        (libs / f).write_bytes(b"x")
    ns["inkline_prune"](str(pyside), str(libs))
    left = sorted(p.name for p in libs.iterdir())
    assert left == ["libplugins_platforms_qtforandroid_x86_64.so"]   # (stand-in files load nothing)


def test_pyjnius_gets_its_jni_environment_from_qt():
    recipe = open(os.path.join(ROOT, "packaging", "android", "pyjnius_recipe.py"), encoding="utf-8").read()
    assert "_ZN17QtAndroidPrivate6javaVMEv" in recipe and "AttachCurrentThread" in recipe   # Qt's Java VM
    assert '"_ZN15QJniEnvironment6javaVMEv", "_ZN17QtAndroidPrivate6javaVMEv"' in recipe and "libQt6Core_x86_64.so" in recipe
    deploy = open(os.path.join(ROOT, "packaging", "android", "deploy.py"), encoding="utf-8").read()
    assert '"pyjnius_recipe.py"' in deploy
    src = open(os.path.join(ROOT, "inkapp", "android_print.py"), encoding="utf-8").read()
    assert "org.qtproject.qt.android.QtNative" in src   # Qt's activity, if python-for-android's isn't set


# --- Google Play: the bundle, versionCode, API levels, 16 KB pages, icons, listing graphics, screenshots ---------
def _load(name, *path):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, *path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_the_version_code_rises_with_every_release_and_tells_the_abis_apart():
    import pytest
    build = _build()
    assert build.version_code("6.1.0", "aarch64") == 1000601001
    assert build.version_code("6.1.0", "x86_64") == 1000601002
    assert build.version_code("6.1.0", "aarch64") > 102860100   # what python-for-android gave 6.1.0's APKs
    order = ["6.1.0", "6.1.1", "6.1.10", "6.2.0", "6.10.0", "6.99.99", "7.0.0", "10.0.0", "100.0.0"]
    codes = [build.version_code(v, "aarch64") for v in order]
    assert codes == sorted(codes) and len(set(codes)) == len(codes)
    assert build.version_code("6.1.1", "aarch64") > build.version_code("6.1.0", "x86_64")
    assert build.version_code("10999.99.99", "x86_64") <= 2_100_000_000   # Play's largest versionCode
    for bad in ("6.1", "6.1.0.1", "6.100.0", "6.1.100", "v6.1.0", "6.1.0-rc1"):
        with pytest.raises(ValueError):
            build.version_code(bad, "aarch64")


def test_the_outputs_are_named_for_the_release():
    import pytest
    build = _build()
    assert build.outputs("6.1.0", "x86_64") == ("inkline-6.1.0-android-x86_64-debug.apk", None)
    assert build.outputs("6.1.0", "aarch64", release=True) == ("inkline-6.1.0-android-aarch64.apk", None)
    assert build.outputs("6.1.0", "aarch64", True, True) == ("inkline-6.1.0-android-aarch64.apk",
                                                            "inkline-6.1.0-android.aab")
    assert build.outputs("6.1.0", "x86_64", True, True)[1] == "inkline-6.1.0-android-x86_64.aab"
    with pytest.raises(SystemExit):   # a bundle only from a release build
        build.main(["--arch", "aarch64", "--wheel-pyside", "a", "--wheel-shiboken", "b", "--aab"])


def test_deploy_sets_play_api_levels_the_version_code_icons_and_apk_or_aab():
    import pytest
    deploy = _load("android_deploy", "packaging", "android", "deploy.py")
    icons = deploy.icon_paths("/i")
    assert icons == {"icon": "/i/icon.png", "foreground": "/i/icon_fg.png", "background": "/i/icon_bg.png"}
    s = dict(deploy.inkline_settings("6.1.0", 1000601001, icons, "py,png,qml"))
    assert s["android.api"] == "36" and s["android.minapi"] == "28" and s["android.ndk_api"] == "28"
    assert s["android.numeric_version"] == "1000601001" and s["version"] == "6.1.0"
    assert s["android.release_artifact"] == "apk" and s["android.debug_artifact"] == "apk"   # buildozer's default: aab
    assert s["source.include_exts"] == "py,png,qml,json,ttf,svg,md,txt"
    assert s["icon.filename"] == "/i/icon.png"
    assert not any(k.startswith("icon.adaptive") for k in s)   # the Qt bootstrap can't take an adaptive icon
    assert s["package.domain"] + "." + s["package.name"] == "io.github.gshoe2006.inkline" and s["title"] == "Inkline"
    assert "icon.filename" not in dict(deploy.inkline_settings("6.1.0", 1, None))
    assert dict(deploy.inkline_settings("6.1.0", 1, api="36"))["android.api"] == "36"
    ours, theirs = deploy.parse(["--version", "6.1.0", "--numeric-version", "7", "--release", "--aab", "--",
                                 "--name", "Inkline"])
    assert ours.aab and ours.release and ours.numeric_version == 7 and theirs == ["--name", "Inkline"]
    with pytest.raises(SystemExit):
        deploy.parse(["--version", "6.1.0", "--numeric-version", "7", "--aab", "--"])


def _elf(aligns, is64=True, types=None, big=False):
    """A minimal ELF file: a header and one program header per alignment (PT_LOAD unless types says)."""
    import struct
    e = ">" if big else "<"
    types = types or [1] * len(aligns)
    ident = b"\x7fELF" + bytes([2 if is64 else 1, 2 if big else 1, 1]) + bytes(9)
    if is64:
        head = ident + struct.pack(e + "HHIQQQIHHHHHH", 3, 183, 1, 0, 64, 0, 0, 64, 56, len(aligns), 64, 0, 0)
        ph = b"".join(struct.pack(e + "IIQQQQQQ", t, 5, 0, 0, 0, 0, 0, a) for t, a in zip(types, aligns))
    else:
        head = ident + struct.pack(e + "HHIIIIIHHHHHH", 3, 40, 1, 0, 52, 0, 0, 52, 32, len(aligns), 40, 0, 0)
        ph = b"".join(struct.pack(e + "IIIIIIII", t, 0, 0, 0, 0, 0, 5, a) for t, a in zip(types, aligns))
    return head + ph


def test_16kb_check_reads_each_load_segments_alignment(tmp_path):
    import zipfile
    import pytest
    check = _load("check_16kb", "packaging", "android", "check_16kb.py")
    assert check.load_alignments(_elf([0x4000, 0x4000])) == [0x4000, 0x4000]
    assert check.load_alignments(_elf([0x4000, 8, 0x1000], types=[1, 2, 1])) == [0x4000, 0x1000]   # PT_DYNAMIC skipped
    assert check.load_alignments(_elf([0x10000], is64=False)) == [0x10000]
    assert check.load_alignments(_elf([0x4000], big=True)) == [0x4000]
    assert check.load_alignments(b"not an elf file at all, a tar of the stdlib" * 2) is None
    apk = tmp_path / "a.apk"
    with zipfile.ZipFile(apk, "w") as z:
        z.writestr("lib/arm64-v8a/libgood.so", _elf([0x4000, 0x4000]))
        z.writestr("lib/arm64-v8a/libpybundle.so", b"a tar, not ELF" * 10)
        z.writestr("lib/armeabi-v7a/libold.so", _elf([0x1000]))   # 32-bit: not Play's concern
        z.writestr("assets/private.tar", b"x")
    said = []
    assert check.check([str(apk)], out=said.append) == []
    assert any("libpybundle.so: not ELF" in s for s in said) and not any("armeabi" in s for s in said)
    aab = tmp_path / "inkline.aab"
    with zipfile.ZipFile(aab, "w") as z:
        z.writestr("base/lib/x86_64/libgood.so", _elf([0x4000]))
        z.writestr("base/lib/arm64-v8a/libbad.so", _elf([0x4000, 0x1000]))
    assert check.check([str(aab)], out=said.append) == ["inkline.aab: base/lib/arm64-v8a/libbad.so (4096)"]
    empty = tmp_path / "empty.apk"
    with zipfile.ZipFile(empty, "w") as z:
        z.writestr("classes.dex", b"x")
    assert check.check([str(empty)], out=said.append)   # no libraries at all is a failure too
    folder = tmp_path / "libs" / "lib" / "x86_64"
    folder.mkdir(parents=True)
    (folder / "libok.so").write_bytes(_elf([0x4000]))
    assert check.check([str(tmp_path / "libs")], out=said.append) == []
    with pytest.raises(SystemExit):
        check.main([str(aab)])


def test_the_icons_and_listing_graphics_are_play_sized(tmp_path):
    import pytest
    from PySide6.QtGui import QImage
    graphics = _load("make_graphics", "packaging", "android", "play", "make_graphics.py")
    shots = _load("check_screenshots", "packaging", "android", "play", "check_screenshots.py")
    made = graphics.listing_graphics(str(tmp_path / "play"))
    assert shots.png_info(made["icon"]) == (512, 512, True)
    assert shots.png_info(made["feature"]) == (1024, 500, False)   # Play refuses a feature graphic with alpha
    feature = QImage(made["feature"])
    assert feature.pixelColor(20, 20).lightness() < 80 and feature.pixelColor(960, 60).lightness() > 240
    icons = graphics.app_icons(str(tmp_path / "icons"))
    assert shots.png_info(icons["icon"])[:2] == (512, 512)
    fg, bg = QImage(icons["foreground"]), QImage(icons["background"])
    assert fg.width() == fg.height() == bg.width() == 432
    assert fg.pixelColor(0, 0).alpha() == 0 and bg.pixelColor(0, 0).alpha() == 255   # the shape, then its backdrop
    assert fg.pixelColor(216, 216).alpha() == 255
    safe = 432 * 33 / 108   # the foreground stays inside the middle 66 of 108 dp, which every launcher's mask shows
    for x in range(0, 432, 4):
        for y in range(0, 432, 4):
            if (x - 216) ** 2 + (y - 216) ** 2 > safe ** 2:
                assert fg.pixelColor(x, y).alpha() < 100, (x, y)   # at most the page's faint shadow
    with pytest.raises(SystemExit):
        graphics.main([])


def test_screenshots_are_checked_against_plays_size_rules(tmp_path):
    from PySide6.QtGui import QImage
    shots = _load("check_screenshots", "packaging", "android", "play", "check_screenshots.py")
    assert shots.problem(1080, 1920) == "" and shots.problem(2560, 1600) == ""   # a 16:9 phone, a tablet
    assert "twice" in shots.problem(1080, 2400) and "320" in shots.problem(300, 500) and shots.problem(4000, 3000)
    assert shots.check(str(tmp_path)) == ["(none)"]
    QImage(1080, 1920, QImage.Format.Format_RGB32).save(str(tmp_path / "1-create.png"))
    assert shots.check(str(tmp_path), out=lambda _s: None) == []
    QImage(1080, 2400, QImage.Format.Format_RGB32).save(str(tmp_path / "2-preview.png"))
    assert shots.check(str(tmp_path), out=lambda _s: None) == ["2-preview.png"]


def test_the_screenshot_pass_shows_each_page_and_waits_for_each_picture(tmp_path, monkeypatch):
    import json
    import time
    from PySide6.QtWidgets import QApplication
    screens = _load("inkline_screens", "packaging", "android", "screens.py")
    monkeypatch.setenv("INKLINE_CONFIG_DIR", str(tmp_path))   # (for monkeypatch to put back)
    folder = str(tmp_path / "s")
    cfg = screens.fresh_settings(folder)
    assert os.environ["INKLINE_CONFIG_DIR"] == cfg
    prefs = json.load(open(os.path.join(cfg, "preferences.json"), encoding="utf-8"))
    assert prefs == {"tour_seen": True, "update_check": False}   # no tour, no "Check for updates?" box
    assert [n for n, _a in screens.STEPS] == ["1-create", "2-preview", "3-booklet", "4-print-options",
                                               "5-print-dialog"]
    done = []
    steps = [("a", lambda w: done.append("a")), ("b", lambda w: done.append("b")),
             ("c", lambda w: 1 / 0)]   # a step that fails still gets its turn
    d = screens.Driver(object(), folder, steps, settle=5, wait=20000, poll=5)
    d.start()
    now, ack = os.path.join(folder, "now"), os.path.join(folder, "ack")
    end = time.time() + 20
    while time.time() < end:
        QApplication.processEvents()
        current = open(now, encoding="utf-8").read().strip() if os.path.exists(now) else ""
        if current == "done":
            break
        if current == "b":
            d.deadline = 0   # the script never answers b: its wait runs out
        elif current:
            with open(ack, "w", encoding="utf-8") as f:
                f.write(current)
        time.sleep(0.005)
    assert done == ["a", "b"] and d.shown == [("a", True), ("b", False), ("c", True)]
    assert open(now, encoding="utf-8").read().strip() == "done"


def test_the_print_dialog_step_is_announced_before_it_opens(tmp_path):
    """Android's print dialog pauses Inkline behind it, timers too: the last step is named before it runs."""
    screens = _load("inkline_screens", "packaging", "android", "screens.py")
    folder = str(tmp_path / "screens")
    seen = []
    steps = [("a", lambda w: None),
             ("z-print", lambda w: seen.append(open(os.path.join(folder, "now"), encoding="utf-8").read().strip()))]
    d = screens.Driver(object(), folder, steps, settle=5, wait=20000, poll=5)
    d.i = 1
    d._next()
    assert seen == ["z-print"]
    sh = open(os.path.join(ROOT, "packaging", "android", "screenshots.sh"), encoding="utf-8").read()
    assert '[ "$taken" -ge 5 ] && break' in sh


def test_the_screenshot_pass_drives_the_real_window(tmp_path, monkeypatch):
    from inkapp import window
    screens = _load("inkline_screens", "packaging", "android", "screens.py")
    monkeypatch.setenv("INKLINE_CONFIG_DIR", str(tmp_path))
    w = window.Window("6.1.0", remember=False)
    w.show()
    for _name, act in screens.STEPS[:-1]:   # each page the steps show (not Print: it opens a dialog)
        act(w)
    assert w.sidebar.rail.buttons["print"].isChecked()
    show = window.Window.show
    try:
        drivers = screens.install(str(tmp_path / "screens"))
        assert os.environ["INKLINE_CONFIG_DIR"] == str(tmp_path / "screens" / "config")
        w2 = window.Window("6.1.0", remember=False)
        w2.show()
        w2.show()
        assert len(drivers) == 1 and drivers[0].w is w2   # one pass, for the first window shown
    finally:
        window.Window.show = show


def test_the_apk_can_run_the_screenshot_pass_and_ci_takes_the_play_screenshots():
    build = _build()
    assert '"inkline-screens"' in build.MAIN and "inkline_screens.install" in build.MAIN
    shot = open(os.path.join(ROOT, "packaging", "android", "screenshots.sh"), encoding="utf-8").read()
    assert "inkline-screens" in shot and "screens/ack" in shot and "printspooler" in shot
    assert "check_screenshots.py" in shot and "screencap" in shot
    flow = open(os.path.join(ROOT, ".github", "workflows", "android.yml"), encoding="utf-8").read()
    assert "screenshots.sh" in flow and "play-screenshots" in flow and "profile: pixel_tablet" in flow
    assert "check_16kb.py" in flow and 'zipalign" -c -P 16' in flow and "targetSdkVersion:'36'" in flow
    assert "build.version_code(" in flow and "make_graphics.py play-graphics" in flow


def test_release_adds_the_signed_play_bundle():
    flow = open(os.path.join(ROOT, ".github", "workflows", "android-release.yml"), encoding="utf-8").read()
    assert "matrix.arch == 'aarch64' && '--aab'" in flow and "inkline-$V-android.aab" in flow
    assert "jarsigner -verify" in flow and 'check_16kb.py --bundled inkline_fast.abi3.so "$AAB"' in flow
    signing = open(os.path.join(ROOT, "docs", "android-signing.md"), encoding="utf-8").read()
    assert "upload key" in signing and "Play App Signing" in signing
    publishing = open(os.path.join(ROOT, "docs", "publishing.md"), encoding="utf-8").read()
    for words in ("$25", "12 testers", "14 days", "data safety", "content rating", "listing.md", "play-screenshots",
                  "arm64"):
        assert words.lower() in publishing.lower(), words


def test_the_play_listing_fits_plays_limits():
    import re
    text = open(os.path.join(ROOT, "packaging", "android", "play", "listing.md"), encoding="utf-8").read()

    def section(name):
        m = re.search(r"^## " + name + r"[^\n]*\n(.*?)(?=^## |\Z)", text, re.S | re.M)
        assert m, name
        return m.group(1).strip()
    assert 0 < len(section("Title")) <= 30
    assert 0 < len(section("Short description")) <= 80
    assert 500 < len(section("Full description")) <= 4000
    privacy = open(os.path.join(ROOT, "packaging", "android", "play", "privacy.md"), encoding="utf-8").read()
    assert "api.github.com" in privacy and "collect" in privacy


# --- inkline_fast, the optional Rust module, cross-compiled into the APK ------------------------------------------
def _workflow(name):
    return open(os.path.join(ROOT, ".github", "workflows", name), encoding="utf-8").read()


def test_the_fast_recipe_cross_compiles_with_the_ndks_clang_against_the_apks_libpython():
    import pytest
    r = _load("inkline_fast_recipe", "packaging", "android", "inkline_fast_recipe.py")
    assert r.Recipe is None or r.recipe   # (python-for-android isn't here: only the parts it builds with)
    assert r.rust_target("arm64-v8a") == "aarch64-linux-android" and r.rust_target("x86_64") == "x86_64-linux-android"
    with pytest.raises(SystemExit):
        r.rust_target("armeabi-v7a")   # CPython has no 32-bit Android build
    clang = r.linker("/ndk/bin", "aarch64-linux-android", 28)
    assert clang == os.path.join("/ndk/bin", "aarch64-linux-android28-clang")
    base = {"PATH": "/usr/bin", "HOME": "/h", "RUSTFLAGS": "-C target-cpu=native", "CC": "clang", "CFLAGS": "-O0",
            "CARGO_BUILD_TARGET": "x86_64-unknown-linux-gnu"}
    env = r.cargo_env(base, "aarch64-linux-android", clang, "/p4a/python3/android-build", "3.14", "/b/target")
    assert env["PATH"] == "/usr/bin" and env["HOME"] == "/h"
    assert not {"RUSTFLAGS", "CC", "CFLAGS", "CARGO_BUILD_TARGET"} & set(env)   # nothing meant for something else
    assert env["CARGO_TARGET_AARCH64_LINUX_ANDROID_LINKER"] == clang
    assert "-Wl,-z,max-page-size=16384" in env["CARGO_TARGET_AARCH64_LINUX_ANDROID_RUSTFLAGS"]   # 16 KB pages
    assert env["PYO3_CROSS_LIB_DIR"] == "/p4a/python3/android-build"   # where libpython3.14.so is
    assert env["PYO3_CROSS_PYTHON_VERSION"] == "3.14" and env["PYO3_NO_PYTHON"] == "1"
    assert env["CARGO_TARGET_DIR"] == "/b/target" and env["CARGO_PROFILE_RELEASE_STRIP"] == "symbols"
    assert base["RUSTFLAGS"] == "-C target-cpu=native"   # the caller's environment is left as it was
    x86 = r.cargo_env({}, "x86_64-linux-android", "/c", "/l", "3.14", "/t")
    assert x86["CARGO_TARGET_X86_64_LINUX_ANDROID_LINKER"] == "/c"
    crate = os.path.join(ROOT, "rust", "inkline_fast")
    cmd = r.cargo_command(crate, "x86_64-linux-android")
    assert cmd[:4] == ["cargo", "build", "--release", "--locked"]   # the crates Cargo.lock pins, as on desktop
    assert cmd[cmd.index("--target") + 1] == "x86_64-linux-android"
    assert os.path.exists(cmd[cmd.index("--manifest-path") + 1])
    assert r.built_library("/t", "x86_64-linux-android") == os.path.join("/t", "x86_64-linux-android", "release",
                                                                         "libinkline_fast.so")
    src = open(os.path.join(ROOT, "packaging", "android", "inkline_fast_recipe.py"), encoding="utf-8").read()
    assert '"inkline_fast.abi3.so"' in src and "get_python_install_dir(arch.arch)" in src   # site-packages, as PySide6's
    assert 'depends = ["python3"]' in src and "python.link_root(arch.arch)" in src


def test_the_fast_recipe_refuses_a_library_not_ready_for_16kb_pages(tmp_path):
    import pytest
    r = _load("inkline_fast_recipe2", "packaging", "android", "inkline_fast_recipe.py")
    r.INKLINE_ANDROID = os.path.join(ROOT, "packaging", "android")
    good, bad = tmp_path / "good.so", tmp_path / "bad.so"
    good.write_bytes(_elf([0x4000, 0x4000]))
    bad.write_bytes(_elf([0x4000, 0x1000]))
    assert r.check_alignment(str(good)) == 0x4000
    with pytest.raises(SystemExit, match="16 KB"):
        r.check_alignment(str(bad))


def test_deploy_writes_the_fast_recipe_with_where_inkline_is(tmp_path):
    import pytest
    deploy = _load("android_deploy2", "packaging", "android", "deploy.py")
    assert deploy.REQUIREMENTS.split(",")[-2:] == ["pyjnius", "inkline_fast"]
    assert dict(deploy.inkline_settings("6.1.0", 1))["requirements"] == deploy.REQUIREMENTS
    deploy.local_recipes(str(tmp_path))
    assert (tmp_path / "pyjnius" / "__init__.py").read_text(encoding="utf-8") == \
        open(os.path.join(ROOT, "packaging", "android", "pyjnius_recipe.py"), encoding="utf-8").read()
    text = (tmp_path / "inkline_fast" / "__init__.py").read_text(encoding="utf-8")
    assert "INKLINE_ANDROID = None" not in text
    ns = {}
    exec(compile(text, "inkline_fast/__init__.py", "exec"), ns)
    assert os.path.samefile(ns["INKLINE_ANDROID"], os.path.join(ROOT, "packaging", "android"))
    assert os.path.exists(os.path.join(ns["INKLINE_ANDROID"], "check_16kb.py"))
    assert os.path.exists(os.path.join(ns["INKLINE_ANDROID"], "..", "..", "rust", "inkline_fast", "Cargo.toml"))
    assert "INKLINE_ANDROID = '/x/y'" in deploy.fast_recipe("a\nINKLINE_ANDROID = None\nb", "/x/y")
    with pytest.raises(SystemExit):
        deploy.fast_recipe("nothing to fill in")
    src = open(os.path.join(ROOT, "packaging", "android", "deploy.py"), encoding="utf-8").read()
    assert "local_recipes(str(pysidedeploy_config.recipe_dir))" in src


def test_the_trim_leaves_inkline_fast_alone(tmp_path):
    ns = {"PySideRecipe": type("R", (), {"build_arch": lambda s, a: None}), "info": print}
    exec(open(os.path.join(ROOT, "packaging", "android", "prune.py"), encoding="utf-8").read(), ns)
    site = tmp_path / "site-packages"
    pyside, libs = site / "PySide6", tmp_path / "libs"
    (pyside / "Qt" / "lib").mkdir(parents=True)
    libs.mkdir()
    (site / "inkline_fast.abi3.so").write_bytes(_elf([0x4000]))
    (pyside / "QtCore.abi3.so").write_bytes(b"x")
    (libs / "libpython3.14.so").write_bytes(b"x")
    ns["inkline_prune"](str(pyside), str(libs))
    assert (site / "inkline_fast.abi3.so").exists() and (libs / "libpython3.14.so").exists()


def _pybundle(files):
    import io
    import tarfile
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def test_16kb_check_finds_inkline_fast_inside_the_python_bundle(tmp_path):
    import zipfile
    import pytest
    check = _load("check_16kb2", "packaging", "android", "check_16kb.py")
    mod = "_python_bundle/site-packages/inkline_fast.abi3.so"
    name = ["inkline_fast.abi3.so"]

    def apk(filename, bundle_files, where="lib/x86_64/"):
        p = tmp_path / filename
        with zipfile.ZipFile(p, "w") as z:
            z.writestr(where + "libpython3.14.so", _elf([0x4000]))
            if bundle_files is not None:
                z.writestr(where + "libpybundle.so", _pybundle(bundle_files))
        return str(p)
    said = []
    good = apk("good.apk", {mod: _elf([0x4000, 0x4000]), "_python_bundle/stdlib.zip": b"zip"})
    assert check.check([good], out=said.append, bundled_names=name) == []
    assert any(f"libpybundle.so!{mod}: 16 KB" in s for s in said)
    assert check.check([good], out=said.append) == []   # without --bundled, the bundle isn't opened
    missing = apk("missing.apk", {"_python_bundle/stdlib.zip": b"zip"})
    assert check.check([missing], out=said.append, bundled_names=name) == \
        ["missing.apk: inkline_fast.abi3.so (not in lib/x86_64/libpybundle.so)"]
    nobundle = apk("nobundle.apk", None)
    assert "no libpybundle.so" in check.check([nobundle], out=said.append, bundled_names=name)[0]
    loose = apk("loose.apk", {mod: _elf([0x4000, 0x1000])})
    assert check.check([loose], out=said.append, bundled_names=name) == \
        [f"loose.apk: lib/x86_64/libpybundle.so!{mod} (4096)"]
    notelf = apk("notelf.apk", {mod: b"not a library" * 8})
    assert "isn't an ELF library" in check.check([notelf], out=said.append, bundled_names=name)[0]
    aab = apk("inkline.aab", {mod: _elf([0x4000])}, where="base/lib/arm64-v8a/")
    assert check.check([aab], out=said.append, bundled_names=name) == []
    check.main(["--bundled", "inkline_fast.abi3.so", good])
    with pytest.raises(SystemExit):
        check.main(["--bundled", "inkline_fast.abi3.so", missing])
    with pytest.raises(SystemExit):
        check.main([good, "--bundled"])   # a name is needed


def test_the_apk_self_test_requires_inkline_fast_in_ci():
    build = _build()
    assert '"inkline-expect-fast"' in build.MAIN and 'os.environ["INKLINE_EXPECT_FAST"] = "1"' in build.MAIN
    assert build.MAIN.index("inkline-expect-fast") < build.MAIN.index("import inkline ")
    test = open(os.path.join(ROOT, "packaging", "android", "emulator-test.sh"), encoding="utf-8").read()
    assert "EXPECT_FAST=${INKLINE_EXPECT_FAST:-}" in test and "touch $d/inkline-expect-fast" in test
    assert 'grep -q "^yes" "$OUT/selftest/inkline-fast.txt"' in test
    flow = _workflow("android.yml")
    assert "rust/inkline_fast/**" in flow   # a change to the crate runs the Android build
    apk = flow.split("\n  emulator:\n")[0]
    assert "uses: dtolnay/rust-toolchain@stable" in apk and "targets: ${{ matrix.arch }}-linux-android" in apk
    assert apk.index("dtolnay/rust-toolchain") < apk.index("name: Build the APK")
    assert 'check_16kb.py --bundled inkline_fast.abi3.so "$APK"' in apk
    assert "INKLINE_EXPECT_FAST=1 sh packaging/android/emulator-test.sh" in flow
    assert 'grep -q "^yes" android-test/selftest/inkline-fast.txt' in flow


def test_release_apks_and_the_bundle_carry_inkline_fast():
    flow = _workflow("android-release.yml")
    assert "uses: dtolnay/rust-toolchain@stable" in flow and "targets: ${{ matrix.arch }}-linux-android" in flow
    assert flow.index("dtolnay/rust-toolchain") < flow.index("packaging/android/build.py --release")
    assert 'check_16kb.py --bundled inkline_fast.abi3.so "$APK"' in flow
    assert 'check_16kb.py --bundled inkline_fast.abi3.so "$AAB"' in flow
