# Inkline's optional Rust module (rust/inkline_fast) for python-for-android (packaging/android/deploy.py writes this
# as the local "inkline_fast" recipe, with INKLINE_ANDROID set to packaging/android's path). cargo cross-compiles
# the crate for the build's ABI (aarch64-linux-android or x86_64-linux-android), linked by the NDK's clang at the
# app's minimum API level against the libpython3.x python-for-android has just built (PyO3 links libpython on
# Android, even for an abi3 extension module). The library goes into site-packages as inkline_fast.abi3.so, beside
# PySide6's QtCore.abi3.so: python-for-android packs site-packages into libpybundle.so and unpacks it on the device,
# where Python imports .abi3.so modules. Its LOAD segments are checked for 16 KB pages here (check_16kb.py), as
# check_16kb.py only reads the APK's lib/<abi>/ folders. Inkline runs without the module (the Python code gives the
# same pages, only slower), but CI's emulator self-test requires it (INKLINE_EXPECT_FAST, inkline-fast.txt).
import importlib.util
import os
import shutil
import subprocess

INKLINE_ANDROID = None   # deploy.py writes packaging/android's path here

PAGE_FLAGS = "-C link-arg=-Wl,-z,max-page-size=16384"   # 16 KB pages (NDK r28's clang does this by default too)
RUST_TARGETS = {"arm64-v8a": "aarch64-linux-android", "x86_64": "x86_64-linux-android"}   # CPython's two
# what the NDK's clang or a caller's settings would otherwise slip into cargo's own build (its build scripts are
# built for this machine, with cargo's defaults)
UNSET = ("RUSTFLAGS", "CARGO_ENCODED_RUSTFLAGS", "CARGO_BUILD_TARGET", "CARGO_BUILD_RUSTFLAGS", "CC", "CXX",
         "CFLAGS", "CXXFLAGS", "CPPFLAGS", "LDFLAGS", "LDSHARED", "AR", "RANLIB")


def rust_target(abi):
    """The Rust target for an Android ABI (python-for-android's arch name)."""
    try:
        return RUST_TARGETS[abi]
    except KeyError:
        raise SystemExit(f"inkline_fast: no Rust build for {abi} (CPython supports arm64-v8a and x86_64)") from None


def env_key(target):
    return target.upper().replace("-", "_")


def linker(llvm_bin, target, api):
    """The NDK's clang wrapper for a target and API level, e.g. <ndk>/…/bin/aarch64-linux-android28-clang."""
    return os.path.join(llvm_bin, f"{target}{api}-clang")


def cargo_env(base, target, clang, python_lib_dir, python_version, target_dir):
    """The environment cargo runs in: base without UNSET, plus the target's linker and flags and PyO3's
    cross-compiling settings (the target's Python version and the folder with its libpython; no host Python is
    asked, so nothing about this machine's Python leaks in)."""
    env = {k: v for k, v in base.items() if k not in UNSET}
    key = env_key(target)
    env.update({
        f"CARGO_TARGET_{key}_LINKER": clang,
        f"CARGO_TARGET_{key}_RUSTFLAGS": PAGE_FLAGS,
        "CARGO_TARGET_DIR": target_dir,
        "CARGO_PROFILE_RELEASE_STRIP": "symbols",   # no debug symbols in the APK (the desktop builds keep cargo's)
        "PYO3_CROSS_LIB_DIR": python_lib_dir,
        "PYO3_CROSS_PYTHON_VERSION": python_version,
        "PYO3_NO_PYTHON": "1",
    })
    return env


def cargo_command(crate, target, cargo="cargo"):
    return [cargo, "build", "--release", "--locked", "--lib", "--manifest-path", os.path.join(crate, "Cargo.toml"),
            "--target", target]


def built_library(target_dir, target):
    return os.path.join(target_dir, target, "release", "libinkline_fast.so")


def _check_16kb():
    spec = importlib.util.spec_from_file_location("inkline_check_16kb", os.path.join(INKLINE_ANDROID, "check_16kb.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def check_alignment(path):
    """Fail the build if the library isn't ready for 16 KB pages."""
    check = _check_16kb()
    with open(path, "rb") as f:
        aligns = check.load_alignments(f.read())
    if not aligns or min(aligns) < check.PAGE:
        raise SystemExit(f"inkline_fast: {path} isn't aligned for 16 KB pages (LOAD alignments {aligns})")
    return min(aligns)


try:
    from pythonforandroid.logger import info
    from pythonforandroid.recipe import Recipe
except ImportError:   # tests/test_android.py reads the parts above without python-for-android
    Recipe = None

if Recipe is not None:
    class InklineFastRecipe(Recipe):
        depends = ["python3"]   # its libpython is linked
        url = None              # the crate is in Inkline's own tree
        version = "0.1.0"

        def crate(self):
            if not INKLINE_ANDROID:
                raise SystemExit("inkline_fast: deploy.py didn't say where Inkline is (INKLINE_ANDROID)")
            return os.path.normpath(os.path.join(INKLINE_ANDROID, "..", "..", "rust", "inkline_fast"))

        def build_arch(self, arch):
            target = rust_target(arch.arch)
            python = self.ctx.python_recipe
            build_dir = self.get_build_dir(arch.arch)
            os.makedirs(build_dir, exist_ok=True)
            target_dir = os.path.join(build_dir, "target")   # not the crate's own target/ folder
            env = cargo_env(os.environ, target, linker(self.ctx.ndk.llvm_bin_dir, target, self.ctx.ndk_api),
                            python.link_root(arch.arch), python.major_minor_version_string, target_dir)
            if shutil.which("rustup"):
                subprocess.run(["rustup", "target", "add", target], check=True)
            info(f"Inkline: building inkline_fast for {target} (Python {python.major_minor_version_string}, "
                 f"API {self.ctx.ndk_api})")
            subprocess.run(cargo_command(self.crate(), target), check=True, env=env)
            lib = built_library(target_dir, target)
            align = check_alignment(lib)
            dest = os.path.join(self.ctx.get_python_install_dir(arch.arch), "inkline_fast.abi3.so")
            shutil.copyfile(lib, dest)
            info(f"Inkline: inkline_fast.abi3.so ({os.path.getsize(dest) // 1024} KB, {align // 1024} KB pages) "
                 f"in {os.path.dirname(dest)}")

    recipe = InklineFastRecipe()
