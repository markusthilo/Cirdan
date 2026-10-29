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
    cirdan_a.binaries,
    cirdan_a.datas,
    [],
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

installer_a = Analysis(
    ['installer-win.py'],
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
installer_pyz = PYZ(installer_a.pure)
installer = EXE(
    installer_pyz,
    installer_a.scripts,
    installer_a.binaries,
    installer_a.datas,
    [],
    name='installer-win',
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
    icon=['icons/installer.ico'],
)
