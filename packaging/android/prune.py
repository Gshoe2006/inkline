# Inkline's trim of the PySide6 recipe (packaging/android/deploy.py appends this file to the recipe Qt's deploy tool
# writes): the wheel holds every Qt module, ~150 MB, and Inkline uses four. After the recipe has installed PySide6
# and copied its libraries, everything no kept part needs goes: other PySide6 modules, Qt libraries no kept library
# loads (followed through each ELF file's DT_NEEDED list), QML, and Qt translations other than qtbase's.
import os as _ink_os
import struct as _ink_struct

INKLINE_MODULES = {"QtCore", "QtGui", "QtWidgets", "QtPrintSupport"}
INKLINE_PLUGINS = {"platforms", "imageformats", "iconengines", "styles", "platformthemes"}


def _inkline_needed(path):
    """The DT_NEEDED names of a 64-bit little-endian ELF file (Android's), or () for anything else."""
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError:
        return ()
    if data[:4] != b"\x7fELF" or data[4] != 2 or data[5] != 1:
        return ()
    shoff, = _ink_struct.unpack_from("<Q", data, 0x28)
    shentsize, shnum = _ink_struct.unpack_from("<HH", data, 0x3A)
    sections = [_ink_struct.unpack_from("<IIQQQQIIQQ", data, shoff + i * shentsize) for i in range(shnum)]
    out = []
    for _name, kind, _f, _a, offset, size, link, _i, _al, entsize in sections:
        if kind != 6 or not entsize:   # SHT_DYNAMIC
            continue
        strtab = sections[link][4]
        for k in range(size // entsize):
            tag, val = _ink_struct.unpack_from("<qQ", data, offset + k * entsize)
            if tag == 1:   # DT_NEEDED
                end = data.index(b"\0", strtab + val)
                out.append(data[strtab + val:end].decode())
            elif tag == 0:
                break
    return out


def inkline_prune(pyside_dir, libs_dir):
    """Keep what Inkline's four modules need, in site-packages/PySide6 and in the APK's libs folder; returns the bytes
    removed."""
    removed = 0

    def rm(path):
        nonlocal removed
        if _ink_os.path.isdir(path) and not _ink_os.path.islink(path):
            for root, _d, files in _ink_os.walk(path):
                removed += sum(_ink_os.path.getsize(_ink_os.path.join(root, f)) for f in files)
            import shutil
            shutil.rmtree(path, ignore_errors=True)
        elif _ink_os.path.exists(path):
            removed += _ink_os.path.getsize(path)
            _ink_os.remove(path)

    for name in _ink_os.listdir(pyside_dir):
        if name.startswith("Qt") and name.endswith((".abi3.so", ".pyi")) and name.split(".")[0] not in INKLINE_MODULES:
            rm(_ink_os.path.join(pyside_dir, name))
    qt = _ink_os.path.join(pyside_dir, "Qt")
    rm(_ink_os.path.join(qt, "qml"))
    plugins = _ink_os.path.join(qt, "plugins")
    if _ink_os.path.isdir(plugins):
        for cat in _ink_os.listdir(plugins):
            if cat not in INKLINE_PLUGINS:
                rm(_ink_os.path.join(plugins, cat))
    tr = _ink_os.path.join(qt, "translations")
    if _ink_os.path.isdir(tr):
        for f in _ink_os.listdir(tr):
            if not f.startswith("qtbase_"):
                rm(_ink_os.path.join(tr, f))
    # the libraries: what the kept modules, PySide's own libraries and the kept plugins load, and what those load
    starts = [_ink_os.path.join(pyside_dir, m + ".abi3.so") for m in INKLINE_MODULES]
    # Qt for Android keeps its plugins beside its libraries (libplugins_<kind>_<name>_<arch>.so): those of kinds
    # Inkline doesn't use go first, or they'd keep what they load (the multimedia plugins keep all of FFmpeg)
    for d in (libs_dir, _ink_os.path.join(qt, "lib")):
        if _ink_os.path.isdir(d):
            for f in _ink_os.listdir(d):
                if f.startswith("libplugins_") and f.split("_")[1] not in INKLINE_PLUGINS:
                    rm(_ink_os.path.join(d, f))
    starts += [_ink_os.path.join(libs_dir, f) for f in _ink_os.listdir(libs_dir)
               if f.endswith(".so") and not f.startswith(("libQt6", "libav", "libsw"))]
    if _ink_os.path.isdir(plugins):
        for root, _d, files in _ink_os.walk(plugins):
            starts += [_ink_os.path.join(root, f) for f in files if f.endswith(".so")]
    keep, todo = set(), list(starts)
    lib_dirs = [libs_dir, _ink_os.path.join(qt, "lib")]
    while todo:
        for name in _inkline_needed(todo.pop()):
            if name.startswith(("libQt6", "libav", "libsw")) and name not in keep:
                keep.add(name)
                todo += [_ink_os.path.join(d, name) for d in lib_dirs if _ink_os.path.exists(_ink_os.path.join(d, name))]
    for d in lib_dirs:
        if _ink_os.path.isdir(d):
            for f in _ink_os.listdir(d):
                if f.startswith(("libQt6", "libav", "libsw")) and f.endswith(".so") and f not in keep:
                    rm(_ink_os.path.join(d, f))   # Qt libraries, and FFmpeg's, that nothing kept loads
    return removed


_inkline_build_arch = PySideRecipe.build_arch   # noqa: F821 (the recipe this file is appended to defines it)


def _inkline_build(self, arch):
    _inkline_build_arch(self, arch)
    gone = inkline_prune(_ink_os.path.join(self.ctx.get_python_install_dir(arch.arch), "PySide6"),
                         self.ctx.get_libs_dir(arch.arch))
    info(f"Inkline: removed {gone // (1024 * 1024)} MB of PySide6 it doesn't use")   # noqa: F821


PySideRecipe.build_arch = _inkline_build   # noqa: F821
