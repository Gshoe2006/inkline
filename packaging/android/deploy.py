"""Runs Qt's pyside6-android-deploy for Inkline, adding what the tool can't tell Inkline needs (build.py runs it,
in the staged app folder):

    python3 deploy.py --version X.Y.Z -- <pyside6-android-deploy's own options>

- numpy (a python-for-android recipe): the tool asks buildozer only for Python, shiboken6 and PySide6
- Print: pyjnius, and the Java class (java/…/PdfPrint.java) that hands a PDF to Android's print service
- Inkline's data files (translations and reading passages as .json, fonts, the icon, VERSION, LICENSE): buildozer
  packs only the file types it's told
- its Android identity: io.github.gshoe2006.inkline, called Inkline, at Inkline's version
"""

import os
import runpy
import sys

import PySide6

SCRIPTS = os.path.join(os.path.dirname(PySide6.__file__), "scripts")
JAVA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "java")   # Print's Java side


def main(argv):
    split = argv.index("--")
    ours, theirs = argv[:split], argv[split + 1:]
    ver = ours[ours.index("--version") + 1]
    sys.path.insert(0, SCRIPTS)
    from deploy_lib.android import buildozer as bz

    original = bz.BuildozerConfig.__init__

    def inkline_config(self, spec_file, pysidedeploy_config):
        original(self, spec_file, pysidedeploy_config)
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
    sys.argv = ["pyside6-android-deploy", *theirs]
    runpy.run_path(os.path.join(SCRIPTS, "android_deploy.py"), run_name="__main__")


if __name__ == "__main__":
    main(sys.argv[1:])
