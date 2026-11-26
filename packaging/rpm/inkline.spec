# Inkline's RPM, filled in and built by build-rpm.sh from the tree it lays out (@TREE@)
Name:           inkline
Version:        @VERSION@
Release:        @REL@
Summary:        Black & white images for printing
License:        GPL-3.0-or-later
URL:            https://github.com/Gshoe2006/inkline
BuildArch:      x86_64

# PySide6 and Qt are inside the package (/usr/lib/inkline/vendor): don't offer their libraries to the system, or
# ask for them; ask for what they need, by file, which Fedora and openSUSE both resolve
AutoReqProv:    no
Requires:       python3 >= 3.10
Requires:       python3-numpy
Requires:       libc.so.6(GLIBC_2.34)(64bit)
Requires:       libEGL.so.1()(64bit)
Requires:       libGL.so.1()(64bit)
Requires:       libfontconfig.so.1()(64bit)
Requires:       libfreetype.so.6()(64bit)
Requires:       libxkbcommon.so.0()(64bit)
Requires:       libxkbcommon-x11.so.0()(64bit)
Requires:       libdbus-1.so.3()(64bit)
Requires:       libxcb-cursor.so.0()(64bit)
Requires:       libxcb-icccm.so.4()(64bit)
Requires:       libxcb-keysyms.so.1()(64bit)
Requires:       libxcb-shape.so.0()(64bit)
Requires:       libxcb-xkb.so.1()(64bit)
Requires:       libwayland-client.so.0()(64bit)
Requires:       libwayland-cursor.so.0()(64bit)
Requires:       libwayland-egl.so.1()(64bit)
Requires:       libX11.so.6()(64bit)
Requires:       libX11-xcb.so.1()(64bit)
Requires:       libxcb.so.1()(64bit)
Requires:       libxcb-image.so.0()(64bit)
Requires:       libxcb-randr.so.0()(64bit)
Requires:       libxcb-render.so.0()(64bit)
Requires:       libxcb-render-util.so.0()(64bit)
Requires:       libxcb-shm.so.0()(64bit)
Requires:       libxcb-sync.so.1()(64bit)
Requires:       libxcb-util.so.1()(64bit)
Requires:       libxcb-xfixes.so.0()(64bit)
Requires:       libdrm.so.2()(64bit)
Requires:       libglib-2.0.so.0()(64bit)
Requires:       libgthread-2.0.so.0()(64bit)
Requires:       libstdc++.so.6()(64bit)
Requires:       libz.so.1()(64bit)
Requires:       libzstd.so.1()(64bit)
Requires:       libcups.so.2()(64bit)
Recommends:     cups

# the files are ready-made: no stripping, debug packages or byte-compiling of PySide6's libraries
%global debug_package %{nil}
%global __os_install_post %{nil}
%global _build_id_links none

%description
Inkline makes colouring pages, puzzles and black and white photo prints, ready to print at true paper size:
mandalas, mazes, dot-to-dots, sudoku, kakuro, nonograms, spot the difference, word search and name pages;
dithered, halftone, engraved and stippled photos; booklets, photo books and posters. Print, or save as PDF, PNG
or SVG.

%install
cp -a @TREE@/. %{buildroot}/

%preun
# Python writes compiled caches beside the code the first time it runs: remove them with the package
find /usr/share/inkline /usr/lib/inkline -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || :

%files
%license /usr/share/licenses/inkline/LICENSE
/usr/bin/inkline
/usr/share/inkline
/usr/lib/inkline
/usr/share/applications/inkline.desktop
/usr/share/mime/packages/inkline.xml
/usr/share/metainfo/inkline.metainfo.xml
/usr/share/icons/hicolor/*/apps/inkline.png
/usr/share/icons/hicolor/scalable/apps/inkline.svg
/usr/share/icons/hicolor/scalable/mimetypes/application-x-inkline-project.svg
