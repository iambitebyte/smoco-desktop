# -*- mode: python ; coding: utf-8 -*-
"""
Smoco Desktop 打包配置 - 完全排除 webrtcvad hook
"""

import sys
import os
from glob import glob

block_cipher = None

# 收集所有本地 .py 文件作为数据
py_files = [(f, '.') for f in glob('*.py') if not f.startswith('convert_') and not f.startswith('build_') and not f.startswith('bundle')]

a = Analysis(
    ['bundle.py'],  # 使用 bundle.py 作为入口点
    pathex=['.'],
    binaries=[],
    datas=[
        ('smoco_logo_circle.png', '.'),
        ('smoco_logo_circle.ico', '.'),
    ] + py_files,  # 添加所有本地 .py 文件
    hiddenimports=[
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'pyaudiowpatch',
        'numpy',
        'scipy',
        'scipy.io.wavfile',
        'scipy.signal',
        'soundfile',
        'requests',
        'aiohttp',
        # 明确指定所有本地模块
        'main_window',
        'gui_logger',
        'i18n',
        'paths',
        'utils',
        'audio_meter_worker',
        'asr_worker',
        'asr_chunker',
        'asr_logger',
        'settings_dialog',
        'startup_dialog',
        'transcript_edit',
        'local_whisper_manager',
        'translation_worker',
        'llm_client',
        # smoco 模块（如果在父目录）
        'smoco.audio',
        'smoco.chunker',
        'smoco.source.wasapi',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'pandas',
        'IPython',
        'pytest',
        'pytest.asyncio',
        'unittest',
        'email',
        'html',
        'http',
        'urllib3',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SmocoDesktop',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 无控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='smoco_logo_circle.ico',  # 应用图标
)
