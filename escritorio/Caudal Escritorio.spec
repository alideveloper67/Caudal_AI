# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('bin', 'bin')]
binaries = []
hiddenimports = ['descargador.juntos', 'descargador.ui.paginas.juntos', 'descargador.mixes', 'descargador.ui.paginas.resumen', 'descargador.descarga_inteligente', 'websocket', 'descargador.ui.actualizador', 'descargador.ui.dialogo_listas', 'descargador.conversion', 'descargador.listas',
                 'descargador.ui.paginas.inicio', 'descargador.ui.paginas.buscar', 'descargador.ui.paginas.explorar',
                 'descargador.ui.paginas.artista', 'descargador.ui.paginas.coleccion', 'descargador.ui.paginas.biblioteca',
                 'descargador.ui.paginas.descargas', 'descargador.ui.paginas.ajustes', 'descargador.ui.video',
                 'descargador.ui.ecualizador', 'mpv']
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
    # sin navegador integrado: fuera Chromium (mas de 100 MB) y lo que no se usa
    excludes=['PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtWebEngineQuick',
              'PySide6.QtWebChannel', 'PySide6.QtQuick', 'PySide6.QtQml', 'PySide6.Qt3DCore',
              'PySide6.QtCharts', 'PySide6.QtDataVisualization', 'PySide6.QtPdf',
              'PySide6.QtMultimedia', 'PySide6.QtMultimediaWidgets', 'tkinter'],
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
