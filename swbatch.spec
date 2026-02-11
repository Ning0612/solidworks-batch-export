# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec 檔案 - SolidWorks 批次轉檔工具
單一入口點方案，支援 CLI 與 GUI 雙模式
"""

from PyInstaller.utils.hooks import collect_all

# 收集 rich 的所有內容(包含 unicode 資料、hooks 等)
# 解決 ModuleNotFoundError: No module named 'rich._unicode_data.unicode17-0-0'
rich_datas, rich_binaries, rich_hiddenimports = collect_all('rich')


block_cipher = None

a = Analysis(
    ['runner.py'],
    pathex=[],
    binaries=rich_binaries,
    datas=rich_datas,
    hiddenimports=[
        # pywin32 COM 支援(關鍵!)
        'pythoncom',
        'pywintypes',
        'win32com.client',
        # CLI 相關
        'typer',
        'rich',
        *rich_hiddenimports,
        # tkinter GUI 相關
        'tkinter',
        'tkinter.filedialog',
        'tkinter.messagebox',
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='swbatch',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Console 模式，支援 CLI 輸出（GUI 會有黑視窗）
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
