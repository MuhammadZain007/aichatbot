[app]

# ── App Info ─────────────────────────────────────────
title = AI ChatBot
package.name = aichatbot
package.domain = com.user.chatbot
version = 1.0

# ── Source ───────────────────────────────────────────
source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,json
source.exclude_dirs = tests,__pycache__,.git

# ── Dependencies ─────────────────────────────────────
requirements = python3,kivy==2.2.1,cython==0.29.36,requests

# ── UI ───────────────────────────────────────────────
orientation = portrait
fullscreen = 0

# ── Android ──────────────────────────────────────────
android.permissions = INTERNET
android.api = 33
android.minapi = 21
android.build_tools_version = 33.0.2
android.ndk = 25b
android.archs = arm64-v8a
android.allow_backup = True
android.accept_sdk_license = True

# Optional icon
# icon.filename = %(source.dir)s/icon.png

# ── Buildozer ────────────────────────────────────────
[buildozer]
log_level = 2
warn_on_root = 1