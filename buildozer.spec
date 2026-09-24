# buildozer.spec

[app]
title = PythonPocket IDE
package.name = pythonpocket
package.domain = org.pythonpocket
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,txt
source.main = main.py
version = 1.0

requirements = python3,kivy,pygments

orientation = portrait
fullscreen = 0

android.api = 35
android.minapi = 23
android.arch = arm64-v8a
android.enable_androidx = True
android.private_storage = True

p4a.bootstrap = sdl2
p4a.extra_args = --enable-androidx

[buildozer]
log_level = 2
warn_on_root = 1