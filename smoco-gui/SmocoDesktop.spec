# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['bundle.py'],
    pathex=[],
    binaries=[],
    datas=[('smoco_logo_circle.png', '.'), ('main_window.py', '.'), ('gui_logger.py', '.'), ('i18n.py', '.'), ('paths.py', '.'), ('utils.py', '.'), ('audio_meter_worker.py', '.'), ('asr_worker.py', '.'), ('asr_chunker.py', '.'), ('asr_logger.py', '.'), ('settings_dialog.py', '.'), ('startup_dialog.py', '.'), ('transcript_edit.py', '.'), ('local_whisper_manager.py', '.'), ('translation_worker.py', '.'), ('llm_client.py', '.'), ('main.py', '.'), ('bundle.py', '.')],
    hiddenimports=['PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets', 'pyaudiowpatch', 'numpy', 'scipy', 'soundfile', 'requests', 'aiohttp', 'logging.handlers', 'webrtcvad', 'main_window', 'gui_logger', 'i18n', 'paths', 'utils', 'audio_meter_worker', 'asr_worker', 'asr_chunker', 'asr_logger', 'settings_dialog', 'startup_dialog', 'transcript_edit', 'local_whisper_manager', 'translation_worker', 'llm_client', 'smoco.audio', 'smoco.source.wasapi'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SmocoDesktop',
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
    icon=['smoco_logo_circle.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SmocoDesktop',
)
