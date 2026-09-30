[app]

# (str) Title of your application
title = YouTube Downloader

# (str) Package name
package.name = youtubedownloader

# (str) Package domain (needed for android/ios packaging)
package.domain = org.downloader

# (str) Source code where the main.py live
source.dir = .

# (list) Source code extensions to include
source.include_exts = py,png,jpg,kv,atlas,ico,json

# (str) Application versioning
version = 1.0.0

# (list) Application requirements
# comma separated e.g. requirements = sqlite3,kivy
requirements = python3,kivy,urllib3,certifi,chardet,idna

# (str) python-for-android branch to use, defaults to master
p4a.branch = master

# (str) Supported orientation (one of landscape, sensorLandscape, portrait or all)
orientation = portrait

# (bool) Indicate if the application should be fullscreen
fullscreen = 0

# (list) Permissions
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

# (int) Target Android API, should be as high as possible.
android.api = 33

# (int) Minimum API your APK / AAB will support.
android.minapi = 21

# (str) Android NDK version to use
android.ndk = 25b

# (bool) If True, then skip trying to update the Android sdk
# This can be useful to avoid excess Internet downloads or save time
# when an update is due and you just want to test/build your package
android.skip_update = False

# (bool) If True, then automatically accept SDK license
# agreements. This is intended for automation only.
android.accept_sdk_license = True

# (str) The Android archs to build for, choices: armeabi-v7a, arm64-v8a, x86, x86_64
# In modern Android, arm64-v8a is the standard
android.archs = arm64-v8a

# (bool) Allow backup of user data
android.allow_backup = True

# (str) Icon of the application
# icon.filename = %(source.dir)s/icon.ico

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1
