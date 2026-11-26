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
    assert '"python3,shiboken6,PySide6,numpy"' in deploy and "json,ttf,svg" in deploy
    assert '"io.github.gshoe2006"' in deploy and '"inkline"' in deploy


def test_ci_builds_both_and_runs_the_self_test_on_an_emulator():
    flow = open(os.path.join(ROOT, ".github", "workflows", "android.yml"), encoding="utf-8").read()
    assert "arch: [x86_64, aarch64]" in flow and "packaging/android/build.py --arch ${{ matrix.arch }}" in flow
    assert "reactivecircus/android-emulator-runner@v2" in flow and "check_selftest.py android-test/selftest" in flow
    test = open(os.path.join(ROOT, "packaging", "android", "emulator-test.sh"), encoding="utf-8").read()
    assert "io.github.gshoe2006.inkline" in test and "inkline-selftest" in test and "screencap" in test
