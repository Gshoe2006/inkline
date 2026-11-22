"""Project files in the desktop: the .inkline type, its icon, and the menu entry that opens it, in every package."""

import importlib.util
import os
import xml.etree.ElementTree as ET

from inkapp import project

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TYPE = "application/x-inkline-project"
ICON = "icons/hicolor/scalable/mimetypes/application-x-inkline-project.svg"
NS = "{http://www.freedesktop.org/standards/shared-mime-info}"


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def test_the_type_matches_project_files():
    root = ET.fromstring(_read("inkline-mime.xml"))
    t = root.find(f"{NS}mime-type")
    assert t.get("type") == TYPE
    assert t.find(f"{NS}glob").get("pattern") == f"*.{project.EXT}"
    assert t.find(f"{NS}comment").text == "Inkline project"
    assert "<!-- icon -->" in _read("inkline-mime.xml")   # where the Flatpak puts its renamed icon


def test_the_menu_entry_opens_them():
    desktop = _read("inkline.desktop").splitlines()
    assert "Exec=inkline %f" in desktop
    assert f"MimeType={TYPE};" in desktop


def test_the_icon_is_a_picture():
    root = ET.fromstring(_read(ICON))
    assert root.tag.endswith("svg") and root.get("viewBox") == "0 0 256 256"


def test_every_package_installs_the_type_and_its_icon():
    stub = _read("packaging", "installer-stub.sh")
    assert 'cp "$TMP/inkline-mime.xml" "$MIME/packages/inkline.xml"' in stub and "update-mime-database" in stub
    assert 'rm -f "$MIME/packages/inkline.xml"' in stub                       # and uninstalls them
    assert 's|^Exec=inkline|Exec=$BIN/inkline|' in stub                      # keeps the %f
    assert "inkline-mime.xml" in _read("packaging", "build.sh")
    pkgbuild = _read("packaging", "arch", "PKGBUILD")
    assert "'inkline-mime.xml'" in pkgbuild and "/usr/share/mime/packages/inkline.xml" in pkgbuild
    assert "mimetypes/application-x-inkline-project.svg" in pkgbuild
    manifest = _read("packaging", "flatpak", "io.github.gshoe2006.Inkline.yml")
    assert "/app/share/mime/packages/${FLATPAK_ID}.xml" in manifest
    assert "mimetypes/${FLATPAK_ID}.application-x-inkline-project.svg" in manifest
    assert f"<mediatype>{TYPE}</mediatype>" in _read("packaging", "flatpak", "io.github.gshoe2006.Inkline.metainfo.xml")


def test_a_project_named_at_start_is_opened():
    spec = importlib.util.spec_from_file_location("inkline_main", os.path.join(ROOT, "inkline.py"))
    main = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(main)
    assert main.startup_project(["/home/me/Maya's book.inkline"]) == "/home/me/Maya's book.inkline"
    assert main.startup_project(["photo.png", "B.INKLINE"]) == "B.INKLINE"
    assert main.startup_project([]) is None and main.startup_project(["--selftest", "x"]) is None
