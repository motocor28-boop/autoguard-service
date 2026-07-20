# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all

numpy_datas, numpy_binaries, numpy_hidden = collect_all('numpy')
matplotlib_datas, matplotlib_binaries, matplotlib_hidden = collect_all('matplotlib')
reportlab_datas, reportlab_binaries, reportlab_hidden = collect_all('reportlab')

analysis = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=numpy_binaries + matplotlib_binaries + reportlab_binaries,
    datas=numpy_datas + matplotlib_datas + reportlab_datas,
    hiddenimports=numpy_hidden + matplotlib_hidden + reportlab_hidden + [
        'serial',
        'serial.tools.list_ports_windows',
        'tkinter',
        'tkinter.ttk',
        'sqlite3',
        'matplotlib.backends.backend_tkagg',
        'numpy.core._multiarray_umath',
        'numpy.core._multiarray_tests',
        'numpy.linalg._umath_linalg',
        'numpy.random._common',
        'numpy.random._bounded_integers',
        'numpy.random._mt19937',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5', 'PyQt6', 'PySide2', 'PySide6'],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(analysis.pure)

exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name='SuperScan 2.0',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    name='SuperScan 2.0',
)
