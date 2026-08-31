# -*- mode: python ; coding: utf-8 -*-

import os
import sys

block_cipher = None

# Collect models, config, and web dashboard
datas = [
    ('models/vosk-model-small-en-us-0.15', 'models/vosk-model-small-en-us-0.15'),
    ('config/settings.json', 'config'),
    ('backend/data/manual_apps.json', 'backend/data'),
    ('web', 'web'),
]

a = Analysis(
    ['desktop_app.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'win32com.client',
        'pythoncom',
        'vosk',
        'sounddevice',
        'speech_recognition',
        'pyttsx3.drivers',
        'pyttsx3.drivers.sapi5',
        'fastapi',
        'uvicorn',
        'feedparser',
        'PIL',
        'sqlite3',
        'websockets',
        'websockets.sync.client',
        'cloud.main',
        'cloud.devices',
        'backend.services.cloud_connector',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='DraxAI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DraxAI',
)
