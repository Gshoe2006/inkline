"""Runs Qt's pyside6-android-deploy for Inkline, adding what the tool can't tell Inkline needs (build.py runs it,
in the staged app folder):

    python3 deploy.py --version X.Y.Z --numeric-version N [--icons DIR] [--release [--aab]] [--target-api N]
                      -- <pyside6-android-deploy's own options>

--release builds a release APK (not debuggable), signed with the key python-for-android reads from
P4A_RELEASE_KEYSTORE, P4A_RELEASE_KEYSTORE_PASSWD, P4A_RELEASE_KEYALIAS and P4A_RELEASE_KEYALIAS_PASSWD. --aab then
builds a signed Android App Bundle too, for Google Play (buildozer again, with android.release_artifact = aab: it
reuses the first run's compiled recipes, so only Gradle runs again). The Qt bootstrap builds one ABI per run, so
the bundle has the one ABI of the wheels given.

- numpy (a python-for-android recipe): the tool asks buildozer only for Python, shiboken6 and PySide6
- A trimmed PySide6: prune.py, appended to the PySide6 recipe the tool writes, removes the Qt modules and libraries
  Inkline doesn't use (the wheel has them all)
- Print: pyjnius, and the Java class (java/…/PdfPrint.java) that hands a PDF to Android's print service; pyjnius
  built to get its JNI environment from Qt (pyjnius_recipe.py, a local recipe: python-for-android builds it for
  the webview bootstrap's glue, which the Qt bootstrap doesn't have)
- Inkline's data files (translations and reading passages as .json, fonts, the icon, VERSION, LICENSE): buildozer
  packs only the file types it's told
- its Android identity: io.github.gshoe2006.inkline, called Inkline, at Inkline's version, with the versionCode
  build.py works out (it must rise with every release, and differs by ABI), Inkline's icon (an adaptive one), and
  the API levels Google Play asks for (target ANDROID_API; MIN_API is Qt 6.12's minimum)
"""

import argparse
import os
import runpy
import shutil
import sys

import PySide6

SCRIPTS = os.path.join(os.path.dirname(PySide6.__file__), "scripts")
HERE = os.path.dirname(os.path.abspath(__file__))
JAVA = os.path.join(HERE, "java")   # Print's Java side
ANDROID_API = "35"   # targetSdk: Google Play's floor for new apps and updates rises each August (docs/publishing.md)
MIN_API = "28"       # Qt 6.12's minimum (Android 9); python-for-android builds with the NDK at this API too
DATA_EXTS = "json,ttf,svg,md,txt"


def inkline_settings(version, numeric_version, icons=None, exts="py", api=ANDROID_API):
    """The buildozer.spec [app] values Inkline sets over the deploy tool's, in order, as (key, value) pairs. icons:
    {"icon", "foreground", "background"} PNG paths (play/make_graphics.py's app_icons)."""
    out = [
        ("requirements", "python3,shiboken6,PySide6,numpy,pyjnius"),
        ("android.add_src", JAVA),
        ("source.include_exts", f"{exts},{DATA_EXTS}"),
        ("source.include_patterns", "VERSION,LICENSE"),
        ("title", "Inkline"),
        ("package.name", "inkline"),
        ("package.domain", "io.github.gshoe2006"),
        ("version", version),
        ("android.numeric_version", str(numeric_version)),
        ("android.api", str(api)),
        ("android.minapi", MIN_API),
        ("android.ndk_api", MIN_API),   # python-for-android insists it matches minapi
        ("android.accept_sdk_license", "True"),
        # buildozer's own default for release builds is an .aab: an APK unless --aab asks for the bundle
        ("android.release_artifact", "apk"),
        ("android.debug_artifact", "apk"),
    ]
    if icons:
        out += [("icon.filename", icons["icon"]),
                ("icon.adaptive_foreground.filename", icons["foreground"]),
                ("icon.adaptive_background.filename", icons["background"])]
    return out


def trim(recipe):
    """Append prune.py to the PySide6 recipe, before the line that makes the recipe object."""
    with open(recipe, encoding="utf-8") as f:
        text = f.read()
    if "inkline_prune" in text:
        return
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "prune.py"), encoding="utf-8") as f:
        prune = f.read()
    head, sep, tail = text.rpartition("recipe = PySideRecipe()")
    if not sep:
        raise SystemExit("deploy.py: the PySide6 recipe has changed; prune.py can't be added")
    with open(recipe, "w", encoding="utf-8") as f:
        f.write(head + prune + "\n\n" + sep + tail)


def parse(argv):
    """(our options, the deploy tool's arguments), split at "--"."""
    split = argv.index("--")
    p = argparse.ArgumentParser(prog="deploy.py")
    p.add_argument("--version", required=True)
    p.add_argument("--numeric-version", type=int, required=True)
    p.add_argument("--icons", help="a folder with icon.png, icon_fg.png and icon_bg.png")
    p.add_argument("--release", action="store_true")
    p.add_argument("--aab", action="store_true")
    p.add_argument("--target-api", default=ANDROID_API)
    ours = p.parse_args(argv[:split])
    if ours.aab and not ours.release:
        p.error("--aab needs --release (python-for-android builds bundles only in release mode)")
    return ours, argv[split + 1:]


def icon_paths(folder):
    if not folder:
        return None
    return {k: os.path.join(os.path.abspath(folder), f)
            for k, f in (("icon", "icon.png"), ("foreground", "icon_fg.png"), ("background", "icon_bg.png"))}


def main(argv):
    ours, theirs = parse(argv)
    sys.path.insert(0, SCRIPTS)
    from deploy_lib.android import buildozer as bz

    original = bz.BuildozerConfig.__init__
    made = []

    def inkline_config(self, spec_file, pysidedeploy_config):
        original(self, spec_file, pysidedeploy_config)
        trim(os.path.join(str(pysidedeploy_config.recipe_dir), "PySide6", "__init__.py"))
        jnius = os.path.join(str(pysidedeploy_config.recipe_dir), "pyjnius")
        os.makedirs(jnius, exist_ok=True)
        shutil.copyfile(os.path.join(HERE, "pyjnius_recipe.py"), os.path.join(jnius, "__init__.py"))
        exts = self.get_value("app", "source.include_exts", ignore_fail=True) or "py"
        for key, value in inkline_settings(ours.version, ours.numeric_version, icon_paths(ours.icons), exts,
                                           ours.target_api):
            self.set_value("app", key, value, raise_warning=False)
        self.update_config()
        made.append(self)

    bz.BuildozerConfig.__init__ = inkline_config
    build = bz.Buildozer.create_executable

    def create(mode):
        # the tool builds in its spec file's mode (debug): a release build instead
        build("release" if ours.release else mode)
        if ours.aab:
            if not made:
                raise SystemExit("deploy.py: no buildozer.spec was written (an old one in the way?): no .aab")
            made[-1].set_value("app", "android.release_artifact", "aab", raise_warning=False)
            made[-1].update_config()
            build("release")

    bz.Buildozer.create_executable = staticmethod(create)
    sys.argv = ["pyside6-android-deploy", *theirs]
    runpy.run_path(os.path.join(SCRIPTS, "android_deploy.py"), run_name="__main__")


if __name__ == "__main__":
    main(sys.argv[1:])
