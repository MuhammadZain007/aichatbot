[app]

# ── App Info ──────────────────────────────────────────────────────────────────
title           = AI ChatBot
package.name    = aichatbot
package.domain  = com.user.chatbot
version         = 1.0

# ── Source ────────────────────────────────────────────────────────────────────
source.dir           = .
source.include_exts  = py,png,jpg,jpeg,kv,atlas,json
source.exclude_dirs  = tests, __pycache__, .git

# ── Dependencies ──────────────────────────────────────────────────────────────
# plain kivy UI + requests for Groq API calls
requirements = python3,kivy==2.3.0,requests,certifi,charset-normalizer,urllib3,idna

# ── UI ────────────────────────────────────────────────────────────────────────
orientation = portrait
fullscreen   = 0

# ── Android ───────────────────────────────────────────────────────────────────
android.permissions  = android.permission.INTERNET
android.api          = 33
android.minapi       = 21
android.ndk          = 25b
android.archs        = arm64-v8a, armeabi-v7a
android.allow_backup = True

# Optional: uncomment and add icon.png (512x512) in the android_app folder
# icon.filename = %(source.dir)s/icon.png

# ── Buildozer ─────────────────────────────────────────────────────────────────
[buildozer]
log_level   = 2
warn_on_root = 1
