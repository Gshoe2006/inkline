#!/usr/bin/env python3
"""Writes the Rust crates the optional module (rust/inkline_fast) needs into the Flatpak manifest, as sources.

    python3 packaging/flatpak/cargo_sources.py           rewrite them in io.github.gshoe2006.Inkline.yml
    python3 packaging/flatpak/cargo_sources.py --check   only say whether they match Cargo.lock (exit 1 if not)

A Flatpak builds without the network, so cargo can't fetch crates: each crate in rust/inkline_fast/Cargo.lock is
listed as an archive from crates.io, pinned by the sha256 Cargo.lock already holds, unpacked into a vendor folder
that cargo is told to use instead of crates.io (as flatpak-cargo-generator does). Run it after Cargo.lock changes;
tests/test_fast_packaging.py fails while the two disagree.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
LOCK = os.path.join(ROOT, "rust", "inkline_fast", "Cargo.lock")
MANIFEST = os.path.join(HERE, "io.github.gshoe2006.Inkline.yml")
BEGIN = "      # --- Rust crates for inkline_fast: written by packaging/flatpak/cargo_sources.py from Cargo.lock ---\n"
END = "      # --- end of the Rust crates ---\n"
REGISTRY = "registry+https://github.com/rust-lang/crates.io-index"
VENDOR = "cargo/vendor"   # under the module's build folder; CARGO_HOME is its cargo/ folder
# cargo's configuration, as a YAML double-quoted string (\\n a new line, \\" a quote)
CONFIG = (f'[source.vendored-sources]\\ndirectory = \\"{VENDOR}\\"\\n\\n'
          '[source.crates-io]\\nreplace-with = \\"vendored-sources\\"\\n')


def crates(lock_text):
    """(name, version, sha256) of every crates.io package in a Cargo.lock, in its order."""
    out = []
    for block in lock_text.split("[[package]]")[1:]:
        f = dict(re.findall(r'^(name|version|source|checksum) = "([^"]*)"', block, re.M))
        if f.get("source") is None:
            continue   # inkline_fast itself
        if f["source"] != REGISTRY or "checksum" not in f:
            raise SystemExit(f"cargo_sources.py: {f.get('name')} doesn't come from crates.io with a checksum")
        out.append((f["name"], f["version"], f["checksum"]))
    return out


def sources(lock_text):
    """The manifest lines (inside a module's sources:) for the crates and cargo's configuration."""
    lines = [BEGIN]
    for name, version, sha in crates(lock_text):
        dest = f"{VENDOR}/{name}-{version}"
        lines += [f"      - type: archive\n",
                  f"        archive-type: tar-gzip\n",
                  f"        url: https://static.crates.io/crates/{name}/{name}-{version}.crate\n",
                  f"        sha256: {sha}\n",
                  f"        dest: {dest}\n",
                  f"      - type: inline\n",
                  f"        contents: '{{\"package\": \"{sha}\", \"files\": {{}}}}'\n",
                  f"        dest: {dest}\n",
                  f"        dest-filename: .cargo-checksum.json\n"]
    lines += ["      - type: inline\n",
              f'        contents: "{CONFIG}"\n',
              "        dest: cargo\n",
              "        dest-filename: config.toml\n",
              END]
    return "".join(lines)


def current(manifest_text):
    if BEGIN not in manifest_text or END not in manifest_text:
        raise SystemExit("cargo_sources.py: the manifest has no Rust crates section to fill in")
    a = manifest_text.index(BEGIN)
    return manifest_text[a:manifest_text.index(END) + len(END)]


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    with open(LOCK, encoding="utf-8") as f:
        want = sources(f.read())
    with open(MANIFEST, encoding="utf-8") as f:
        text = f.read()
    have = current(text)
    if "--check" in argv:
        if have != want:
            print("cargo_sources.py: the Flatpak manifest's Rust crates don't match Cargo.lock: run "
                  "python3 packaging/flatpak/cargo_sources.py")
            return 1
        print("cargo_sources.py: the Flatpak manifest's Rust crates match Cargo.lock")
        return 0
    with open(MANIFEST, "w", encoding="utf-8") as f:
        f.write(text.replace(have, want))
    print(f"cargo_sources.py: {len(crates(open(LOCK, encoding='utf-8').read()))} crates written to {MANIFEST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
