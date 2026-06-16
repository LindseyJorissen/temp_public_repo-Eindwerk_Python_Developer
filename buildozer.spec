[app]

# Title of your application
title = Mittens Cat Cafe Mayhem

# Package name (no spaces, all lowercase)
package.name = mittens

# Package domain
package.domain = com.blackcatstudios

# Source directory (. = same folder as this spec)
source.dir = .

# Source files to include
source.include_exts = py,png,jpg,jpeg,ttf,wav,mp3,ogg,json

# Exclude development junk
source.exclude_dirs = __pycache__, .git, .venv, venv, tests

# App version
version = 1.0
android.numeric_version = 1

# Python requirements
# Add 'kivy_deps.sdl2,kivy_deps.glew' if targeting Windows via buildozer
requirements = hostpython3==3.11.9,python3==3.11.9,kivy==2.3.0,plyer

# Orientation – landscape only (matches original game)
orientation = landscape

# Android target
android.minapi = 26
android.api    = 35
android.ndk    = 25b

# Permissions (for writing scores to storage if needed)
android.permissions = INTERNET,ACCELEROMETER

# Fullscreen
fullscreen = 1

# App icon
icon.filename = %(source.dir)s/assets/app_icon.png

# Presplash (loading screen image)
presplash.filename = %(source.dir)s/assets/presplash.png

# Presplash background colour (hex, no #)
presplash.color = #261407

# Release signing – required for Google Play upload

android.keystore = mittens.keystore
android.keystore_alias = mittens
android.keystore_password = 
android.keyalias_password = 

# Build output directory
# bin.dir = ./bin

[buildozer]
log_level = 2
warn_on_root = 1
