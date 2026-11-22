# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('bin', 'bin'), ('descargador/legal', 'descargador/legal'), ('descargador/mascotas', 'descargador/mascotas'), ('descargador/fondos', 'descargador/fondos'), ('descargador/donar', 'descargador/donar'), ('descargador/escenarios_img', 'descargador/escenarios_img'), ('descargador/fuentes_letra', 'descargador/fuentes_letra')]
binaries = []
hiddenimports = ['descargador.juntos', 'descargador.ui.letra_viva', 'descargador.registro_fallos', 'descargador.ui.paginas.juntos', 'descargador.mixes', 'descargador.ui.paginas.resumen', 'descargador.descarga_inteligente', 'websocket', 'descargador.ui.actualizador', 'descargador.ui.dialogo_listas', 'descargador.conversion', 'descargador.listas',
                 'descargador.ui.paginas.inicio', 'descargador.ui.paginas.buscar', 'descargador.ui.paginas.explorar',
                 'descargador.ui.paginas.artista', 'descargador.ui.paginas.coleccion', 'descargador.ui.paginas.biblioteca',
                 'descargador.ui.paginas.descargas', 'descargador.ui.paginas.ajustes', 'descargador.ui.video',
                 'descargador.ui.ecualizador', 'mpv',
                 # letra a tiempo sola: reconocedor de voz local (sincronia_letra.py); el modelo se baja aparte
                 'descargador.sincronia_letra', 'descargador.ui.sincronia_auto', 'huggingface_hub',
                 # grupos para hablar (texto, canciones y notas de voz)
                 'descargador.grupos', 'descargador.notas_voz', 'descargador.ui.paginas.grupos']
for paquete in ('yt_dlp', 'ytmusicapi', 'faster_whisper', 'ctranslate2', 'tokenizers'):
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
              'PySide6.QtMultimedia', 'PySide6.QtMultimediaWidgets', 'tkinter',
              # el reconocedor de la letra no usa PyAV ni el VAD de onnxruntime (sincronia_letra._importar)
              'av', 'onnxruntime', 'torch'],
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
