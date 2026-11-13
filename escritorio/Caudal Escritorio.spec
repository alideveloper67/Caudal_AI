# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('bin', 'bin')]
binaries = []
hiddenimports = ['descargador.ui.actualizador', 'descargador.ui.dialogo_listas', 'descargador.conversion', 'descargador.listas',
                 'descargador.ui.paginas.inicio', 'descargador.ui.paginas.buscar', 'descargador.ui.paginas.explorar',
                 'descargador.ui.paginas.artista', 'descargador.ui.paginas.coleccion', 'descargador.ui.paginas.biblioteca',
                 'descargador.ui.paginas.descargas', 'descargador.ui.paginas.ajustes', 'descargador.ui.video',
                 'descargador.ui.ecualizador', 'descargador.ui.navegador', 'descargador.ui.panel_caudal', 'mpv']
for paquete in ('yt_dlp', 'ytmusicapi'):
    tmp_ret = collect_all(paquete)
    datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['ejecutar.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    name='Caudal Escritorio',
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
    icon=['icono.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Caudal Escritorio',
)
