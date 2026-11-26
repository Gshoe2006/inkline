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
