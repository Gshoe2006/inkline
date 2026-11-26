# Inkline's pyjnius for python-for-android's Qt bootstrap (packaging/android/deploy.py writes this as the local
# "pyjnius" recipe). python-for-android builds pyjnius to get its JNI environment from the webview bootstrap's glue
# (WebView_AndroidGetJNIEnv), which the Qt bootstrap doesn't have: "import jnius" then fails ("cannot locate symbol").
# Here pyjnius asks Qt instead, for the Java VM Qt keeps (QtAndroidPrivate::javaVM(), exported by libQt6Core), and
# links against Qt's core library.
import os

import pythonforandroid.recipes.pyjnius as upstream
from pythonforandroid.logger import info
from pythonforandroid.recipes.pyjnius import PyjniusRecipe

QT_JNIENV = '''# Inkline: on python-for-android's Qt bootstrap, the JNI environment comes from Qt's Java VM
cdef extern from *:
    """
    #include <jni.h>
    JavaVM *_ZN17QtAndroidPrivate6javaVMEv(void);  /* QtAndroidPrivate::javaVM(), in libQt6Core */
    """
    JavaVM *_ZN17QtAndroidPrivate6javaVMEv()


cdef JNIEnv *get_platform_jnienv() except NULL:
    cdef JavaVM *vm = _ZN17QtAndroidPrivate6javaVMEv()
    cdef JNIEnv *env = NULL
    if vm == NULL:
        raise Exception("Qt hasn't set up its Java VM")
    if vm[0].AttachCurrentThread(vm, <void **>&env, NULL) != 0:
        raise Exception("Couldn't attach this thread to the Java VM")
    return env
'''


class InklinePyjniusRecipe(PyjniusRecipe):
    depends = list(PyjniusRecipe.depends) + ["PySide6"]   # libQt6Core in the libs folder, to link against

    def get_recipe_dir(self):
        return os.path.dirname(upstream.__file__)   # its patches

    def apply_patches(self, arch, build_dir=None):
        super().apply_patches(arch, build_dir) if build_dir is not None else super().apply_patches(arch)
        pxi = os.path.join(build_dir or self.get_build_dir(arch.arch), "jnius", "jnius_jvm_android.pxi")
        info(f"Inkline: pyjnius gets its JNI environment from Qt ({pxi})")
        with open(pxi, "w", encoding="utf-8") as f:
            f.write(QT_JNIENV)

    def get_recipe_env(self, arch, **kwargs):
        env = super().get_recipe_env(arch, **kwargs)
        env["PYJNIUS_ANDROID_LIBMAIN"] = f"Qt6Core_{arch.arch}"   # the library pyjnius links (env.py, patched)
        return env


recipe = InklinePyjniusRecipe()
