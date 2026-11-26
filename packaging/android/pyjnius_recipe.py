# Inkline's pyjnius for python-for-android's Qt bootstrap (packaging/android/deploy.py writes this as the local
# "pyjnius" recipe). python-for-android builds pyjnius to get its JNI environment from the webview bootstrap's glue
# (WebView_AndroidGetJNIEnv), which the Qt bootstrap doesn't have: "import jnius" then fails ("cannot locate symbol").
# Here pyjnius asks Qt instead, for the Java VM Qt keeps (QtAndroidPrivate::javaVM(), exported by libQt6Core), found
# at run time in Qt's core library, which is loaded before Python starts.
import os

import pythonforandroid.recipes.pyjnius as upstream
from pythonforandroid.logger import info
from pythonforandroid.recipes.pyjnius import PyjniusRecipe

QT_JNIENV = '''# Inkline: on python-for-android's Qt bootstrap, the JNI environment comes from Qt's Java VM
cdef extern from *:
    """
    #include <jni.h>
    #include <dlfcn.h>
    #include <android/log.h>
    /* Qt's Java VM, looked up in Qt's core library (loaded before Python starts) rather than linked: the APK names it
       libQt6Core_<abi>.so. QJniEnvironment::javaVM() is Qt's public call; QtAndroidPrivate::javaVM() the older one. */
    static JavaVM *inkline_qt_javavm(void) {
        static const char *libs[] = {"libQt6Core_arm64-v8a.so", "libQt6Core_x86_64.so",
                                     "libQt6Core_armeabi-v7a.so", "libQt6Core_x86.so", NULL};
        static const char *calls[] = {"_ZN15QJniEnvironment6javaVMEv", "_ZN17QtAndroidPrivate6javaVMEv", NULL};
        for (int i = 0; libs[i]; i++) {
            void *qt = dlopen(libs[i], RTLD_NOW | RTLD_NOLOAD);
            if (!qt) qt = dlopen(libs[i], RTLD_NOW);
            if (!qt) continue;
            for (int k = 0; calls[k]; k++) {
                JavaVM *(*java_vm)(void) = (JavaVM *(*)(void)) dlsym(qt, calls[k]);
                JavaVM *vm = java_vm ? java_vm() : NULL;
                __android_log_print(ANDROID_LOG_INFO, "python", "inkline: %s %s: %s", libs[i], calls[k],
                                    vm ? "found the Java VM" : (java_vm ? "returned no Java VM" : dlerror()));
                if (vm) return vm;
            }
        }
        for (int k = 0; calls[k]; k++) {   /* already loaded under another name */
            JavaVM *(*java_vm)(void) = (JavaVM *(*)(void)) dlsym(RTLD_DEFAULT, calls[k]);
            if (java_vm && java_vm()) return java_vm();
        }
        __android_log_print(ANDROID_LOG_INFO, "python", "inkline: Qt's core library wasn't found: %s", dlerror());
        return NULL;
    }
    """
    JavaVM *inkline_qt_javavm()


cdef JNIEnv *get_platform_jnienv() except NULL:
    cdef JavaVM *vm = inkline_qt_javavm()
    cdef JNIEnv *env = NULL
    if vm == NULL:
        raise Exception("Qt hasn't set up its Java VM")
    if vm[0].AttachCurrentThread(vm, <void **>&env, NULL) != 0:
        raise Exception("Couldn't attach this thread to the Java VM")
    return env
'''


class InklinePyjniusRecipe(PyjniusRecipe):
    depends = list(PyjniusRecipe.depends) + ["PySide6"]

    def get_recipe_dir(self):
        return os.path.dirname(upstream.__file__)   # its patches

    def apply_patches(self, arch, build_dir=None):
        super().apply_patches(arch, build_dir) if build_dir is not None else super().apply_patches(arch)
        pxi = os.path.join(build_dir or self.get_build_dir(arch.arch), "jnius", "jnius_jvm_android.pxi")
        info(f"Inkline: pyjnius gets its JNI environment from Qt ({pxi})")
        with open(pxi, "w", encoding="utf-8") as f:
            f.write(QT_JNIENV)

recipe = InklinePyjniusRecipe()
