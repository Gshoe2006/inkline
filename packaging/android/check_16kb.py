"""Checks every native library in APKs, app bundles (.aab) or folders is ready for 16 KB memory pages, as Google Play
requires of apps targeting Android 15 (API 35) and later: each ELF LOAD segment must be aligned to at least 16 KB.

    python3 packaging/android/check_16kb.py FILE.apk|FILE.aab|DIR ...

Prints each library's smallest LOAD alignment and exits 1 if any is under 16 KB. Files named .so that aren't ELF
are skipped (python-for-android's libpybundle.so is a tar of the Python standard library). Only the 64-bit ABIs
are checked (arm64-v8a, x86_64), as on Play; NDK r28 and later build 16 KB-aligned by default.
"""

import os
import struct
import sys
import zipfile

PAGE = 16384
ABIS = ("arm64-v8a", "x86_64")
PT_LOAD = 1


def load_alignments(data):
    """The p_align of each PT_LOAD program header in an ELF file's bytes; None if it isn't ELF."""
    if data[:4] != b"\x7fELF" or len(data) < 52:
        return None
    is64 = data[4] == 2
    end = "<" if data[5] == 1 else ">"
    if is64:
        phoff, = struct.unpack_from(end + "Q", data, 0x20)
        phentsize, phnum = struct.unpack_from(end + "HH", data, 0x36)
    else:
        phoff, = struct.unpack_from(end + "I", data, 0x1C)
        phentsize, phnum = struct.unpack_from(end + "HH", data, 0x2A)
    out = []
    for i in range(phnum):
        off = phoff + i * phentsize
        if off + phentsize > len(data):
            raise ValueError("truncated ELF program headers")
        p_type, = struct.unpack_from(end + "I", data, off)
        if p_type != PT_LOAD:
            continue
        if is64:
            p_align, = struct.unpack_from(end + "Q", data, off + 48)
        else:
            p_align, = struct.unpack_from(end + "I", data, off + 28)
        out.append(p_align)
    return out


def _abi(path):
    parts = path.replace("\\", "/").split("/")
    for i, part in enumerate(parts[:-1]):
        if part == "lib" and i + 1 < len(parts) - 1:
            return parts[i + 1]
    return None


def libraries(path):
    """(name, bytes) for each .so in an APK, an .aab (base/lib/<abi>/) or a folder, in the 64-bit ABIs (or any,
    for a folder without lib/<abi>/)."""
    if os.path.isdir(path):
        for d, _dirs, files in os.walk(path):
            for f in sorted(files):
                if f.endswith(".so"):
                    full = os.path.join(d, f)
                    if _abi(full) in (None, *ABIS):
                        with open(full, "rb") as fh:
                            yield os.path.relpath(full, path), fh.read()
        return
    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            if name.endswith(".so") and _abi(name) in ABIS:
                yield name, z.read(name)


def check(paths, out=print):
    """The libraries under 16 KB alignment, as "file: name (alignment)" lines; out() is told about every one."""
    bad = []
    seen = 0
    for path in paths:
        for name, data in libraries(path):
            aligns = load_alignments(data)
            if aligns is None:
                out(f"{name}: not ELF, skipped")
                continue
            seen += 1
            low = min(aligns) if aligns else 0
            ok = low >= PAGE
            out(f"{name}: {low // 1024 if low >= 1024 else low}{' KB' if low >= 1024 else ' bytes'}"
                f"{'' if ok else '  <-- under 16 KB'}")
            if not ok:
                bad.append(f"{os.path.basename(path)}: {name} ({low})")
    if not seen:
        bad.append("no native libraries found in " + ", ".join(paths))
    return bad


def main(argv):
    if not argv:
        raise SystemExit(__doc__)
    bad = check(argv)
    if bad:
        print("\nNot ready for 16 KB pages:\n  " + "\n  ".join(bad))
        raise SystemExit(1)
    print("\nEvery native library is aligned for 16 KB pages.")


if __name__ == "__main__":
    main(sys.argv[1:])
