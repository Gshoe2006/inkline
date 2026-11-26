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
    assert "\"python3,shiboken6,PySide6,numpy,pyjnius\"" in deploy and "json,ttf,svg" in deploy
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
