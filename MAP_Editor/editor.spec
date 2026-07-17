# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the Warehouse Map Editor.
#
# Produces a single self-contained executable (Python + Tkinter + the app all inside),
# with a sample Magazyn.txt bundled so the editor opens with a working map out of the box.
#
# Build:  cd MAP_Editor && pyinstaller editor.spec
# PyInstaller cannot cross-compile — run this on each target OS (the release workflow does).

import os

# SPECPATH is MAP_Editor/; the sample map lives one level up in MAP_Generator/.
sample_map = os.path.join(SPECPATH, os.pardir, "MAP_Generator", "Magazyn.txt")

a = Analysis(
    ["editor.py"],
    pathex=[],
    binaries=[],
    datas=[(sample_map, ".")],  # ships as Magazyn.txt at the bundle root (sys._MEIPASS)
    hiddenimports=[],
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
    a.binaries,
    a.datas,
    [],
    name="MapEditor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,             # off: UPX-packed exes trip some Windows antivirus scanners
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,         # GUI app — no terminal window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
