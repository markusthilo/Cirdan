# -*- mode: python ; coding: utf-8 -*-

cirdan_a = Analysis(
    ['cirdan.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
cirdan_pyz = PYZ(cirdan_a.pure)
cirdan_exe = EXE(
    cirdan_pyz,
    cirdan_a.scripts,
    [],
    exclude_binaries=True,
    name='cirdan',
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
    icon=['icons/cirdan.ico'],
)

downloader_a = Analysis(
    ['downloader.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
downloader_pyz = PYZ(downloader_a.pure)
downloader_exe = EXE(
    downloader_pyz,
    downloader_a.scripts,
    [],
    exclude_binaries=True,
    name='downloader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icons/downloader.ico'],
)

coll = COLLECT(
    cirdan_exe,
    cirdan_a.binaries,
    cirdan_a.datas,
    downloader_exe,
    downloader_a.binaries,
    downloader_a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='cirdan',
)
