"""Runs Qt's pyside6-android-deploy for Inkline, adding what the tool can't tell Inkline needs (build.py runs it,
in the staged app folder):

    python3 deploy.py --version X.Y.Z [--release] -- <pyside6-android-deploy's own options>

--release builds a release APK (not debuggable), signed with the key python-for-android reads from
P4A_RELEASE_KEYSTORE, P4A_RELEASE_KEYSTORE_PASSWD, P4A_RELEASE_KEYALIAS and P4A_RELEASE_KEYALIAS_PASSWD.

- numpy (a python-for-android recipe): the tool asks buildozer only for Python, shiboken6 and PySide6
- A trimmed PySide6: prune.py, appended to the PySide6 recipe the tool writes, removes the Qt modules and libraries
  Inkline doesn't use (the wheel has them all)
- Print: pyjnius, and the Java class (java/…/PdfPrint.java) that hands a PDF to Android's print service; pyjnius
  built to get its JNI environment from Qt (pyjnius_recipe.py, a local recipe: python-for-android builds it for
  the webview bootstrap's glue, which the Qt bootstrap doesn't have)
- Inkline's data files (translations and reading passages as .json, fonts, the icon, VERSION, LICENSE): buildozer
  packs only the file types it's told
- its Android identity: io.github.gshoe2006.inkline, called Inkline, at Inkline's version
"""

import os
import runpy
import shutil
import sys

import PySide6

SCRIPTS = os.path.join(os.path.dirname(PySide6.__file__), "scripts")
HERE = os.path.dirname(os.path.abspath(__file__))
JAVA = os.path.join(HERE, "java")   # Print's Java side


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


def main(argv):
    split = argv.index("--")
    ours, theirs = argv[:split], argv[split + 1:]
    ver = ours[ours.index("--version") + 1]
    sys.path.insert(0, SCRIPTS)
    from deploy_lib.android import buildozer as bz

    original = bz.BuildozerConfig.__init__

    def inkline_config(self, spec_file, pysidedeploy_config):
        original(self, spec_file, pysidedeploy_config)
        trim(os.path.join(str(pysidedeploy_config.recipe_dir), "PySide6", "__init__.py"))
        jnius = os.path.join(str(pysidedeploy_config.recipe_dir), "pyjnius")
        os.makedirs(jnius, exist_ok=True)
        shutil.copyfile(os.path.join(HERE, "pyjnius_recipe.py"), os.path.join(jnius, "__init__.py"))
        self.set_value("app", "requirements", "python3,shiboken6,PySide6,numpy,pyjnius")
        self.set_value("app", "android.add_src", JAVA, raise_warning=False)
        exts = self.get_value("app", "source.include_exts", ignore_fail=True) or "py"
        self.set_value("app", "source.include_exts", f"{exts},json,ttf,svg,md,txt", raise_warning=False)
        self.set_value("app", "source.include_patterns", "VERSION,LICENSE", raise_warning=False)
        self.set_value("app", "title", "Inkline")
        self.set_value("app", "package.name", "inkline")
        self.set_value("app", "package.domain", "io.github.gshoe2006")
        self.set_value("app", "version", ver, raise_warning=False)
        self.set_value("app", "android.accept_sdk_license", "True", raise_warning=False)
        self.update_config()

    bz.BuildozerConfig.__init__ = inkline_config
    if "--release" in ours:   # the tool builds in its spec file's mode (debug): a release build instead
        build = bz.Buildozer.create_executable
        bz.Buildozer.create_executable = staticmethod(lambda _mode: build("release"))
    sys.argv = ["pyside6-android-deploy", *theirs]
    runpy.run_path(os.path.join(SCRIPTS, "android_deploy.py"), run_name="__main__")


if __name__ == "__main__":
    main(sys.argv[1:])
