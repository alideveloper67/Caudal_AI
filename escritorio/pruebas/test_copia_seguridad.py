# -*- coding: utf-8 -*-
"""Copia de seguridad (.caudal): ida y vuelta, juntar sin duplicar, reemplazar, archivos dañados,
versión futura y la copia hecha en el teléfono leída en la PC (y al revés: la de la PC queda en
app/test/datos para que la lea la prueba de Flutter).

Todo en carpetas temporales: no toca los datos reales de Caudal.
"""

import io
import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="caudal_pruebas_copia_")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from descargador import copia_seguridad as CS  # noqa: E402
from descargador.coleccion import Coleccion  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
DATOS_APP = RAIZ / "app" / "test" / "datos"
COPIA_PC = DATOS_APP / "copia_escritorio.caudal"
COPIA_MOVIL = DATOS_APP / "copia_movil.caudal"


class AjustesFalsos(dict):
    """Lo que la copia usa de config.Ajustes: leer, poner y guardar."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.guardados = 0

    @property
    def datos(self):
        return self

    def guardar(self):
        self.guardados += 1


def pista(vid, titulo, artista="Artista", album=""):
    return {"tipo": "pista", "clave": f"yt:{vid}", "video_id": vid, "titulo": titulo,
            "artista": artista, "artistas": [{"nombre": artista, "id": f"UC{artista[:3]}"}],
            "album": {"nombre": album} if album else {}, "duracion": 200,
            "miniatura": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"}


def poblar(col, carpeta_audio):
    """Una colección con de todo un poco (incluida una descarga con su archivo)."""
    audio = Path(carpeta_audio) / "cancion local.mp3"
    audio.write_bytes(b"ID3 falso")
    cur = col.con.execute(
        "INSERT INTO descargas (url, titulo, plataforma, archivo, tamano, duracion, calidad, estado,"
        " fecha, caratula, es_audio, autor) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        ("https://www.youtube.com/watch?v=LOCAL000001", "Canción descargada", "YouTube", str(audio),
         1234, 180, "320", "completada", 1_700_000_000, "", 1, "Grupo Local"))
    col.con.commit()
    local = f"local:{cur.lastrowid}"
    p1, p2, p3 = pista("aaaaaaaaaa1", "Uno", "Ana"), pista("bbbbbbbbbb2", "Dos", "Beto"), \
        pista("cccccccccc3", "Tres", "Ana", "Disco")
    for p in (p1, p2, p3):
        col.alternar_me_gusta(p)
    col.alternar_me_gusta(col.pista(local))
    l1 = col.crear_lista("Para correr", "rápidas")
    col.agregar_a_lista(l1, [p1, p2, col.pista(local)])
    l2 = col.crear_lista("Tranquilas")
    col.agregar_a_lista(l2, [p3])
    col.editar_lista(l2, fijada=True)
    col.registrar_escucha(p1, {"tipo": "mi_lista", "id": l1, "titulo": "Para correr"})
    col.registrar_escucha(p2)
    col.registrar_escucha(p3)
    col.guardar({"tipo": "album", "id": "MPREb_1", "titulo": "Disco", "pistas": [p3]})
    col.guardar({"tipo": "artista", "id": "UCAna", "titulo": "Ana"})
    col.anotar_busqueda("ana")
    col.anotar_busqueda("beto en vivo")
    col.guardar_estado("saltos", {"canciones": {"bbbbbbbbbb2": 2}, "artistas": {}, "hoy": {}})
    col.guardar_estado("gustos", {"lista": [{"nombre": "Ana", "id": "UCAna", "portada": ""}],
                                  "elegidos": True, "pendiente": False})
    return {"local": local, "l1": l1, "l2": l2, "p": (p1, p2, p3)}


def foto():
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", (300, 200), (200, 40, 40)).save(b, "PNG")
    return b.getvalue()


def huella(col):
    """La colección sin ids internos, para comparar dos equipos."""
    datos, _p = CS._datos_coleccion(col)

    def sin_local(c):
        return "local" if c.startswith("local:") else c
    return {
        "me_gusta": sorted(sin_local(g["clave"]) for g in datos["me_gusta"]),
        "listas": sorted((l["nombre"], l["uuid"], l["descripcion"], l["fijada"],
                          tuple(sin_local(i["clave"]) for i in l["items"])) for l in datos["listas"]),
        "escuchas": sorted((sin_local(e["clave"]), round(e["fecha"])) for e in datos["escuchas"]),
        "guardados": sorted((g["tipo"], g["id"]) for g in datos["guardados"]),
        "busquedas": sorted(b["texto"] for b in datos["busquedas"]),
        "descargas": sorted((d["titulo"], d["archivo"]) for d in datos["descargas"]),
        "pistas": sorted(datos["pistas"]),
    }


@pytest.fixture
def equipo(tmp_path):
    """Dos «equipos»: A con datos y B vacío."""
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    a = Coleccion(tmp_path / "a" / "historial.db")
    b = Coleccion(tmp_path / "b" / "historial.db")
    info = poblar(a, tmp_path / "a")
    yield a, b, info, tmp_path
    a.con.close()
    b.con.close()


# ---------------------------------------------------------------------- ida y vuelta


def test_ida_y_vuelta_da_los_mismos_datos(equipo):
    a, b, info, tmp = equipo
    a.poner_portada_lista(info["l1"], foto())
    aj = AjustesFalsos(eq_bandas=[3, 2, 1, 0, 0, 0, 0, 1, 2, 3], ecualizador=True, acento="rosa",
                       volumen=55, spotify_secreto="NO-DEBE-SALIR", sesion_token="tampoco",
                       proxy="socks5://usuario:clave@x", carpeta=str(tmp))
    contenido = CS.crear_copia(a, aj, carpeta=tmp / "a", mascota="gatito")
    # lo sensible no viaja
    crudo = zipfile.ZipFile(io.BytesIO(contenido)).read("datos.json").decode("utf-8")
    for secreto in ("NO-DEBE-SALIR", "tampoco", "usuario:clave"):
        assert secreto not in crudo
    ruta = CS.guardar_copia(tmp / "copia", contenido)
    assert ruta.suffix == ".caudal" and ruta.exists()

    copia = CS.abrir_copia(ruta)
    assert copia.origen == "escritorio"
    r = copia.resumen()
    assert r["me_gusta"] == 4 and r["listas"] == 2 and r["canciones_en_listas"] == 4
    assert r["escuchas"] == 3 and r["guardados"] == 2 and r["descargas"] == 1
    assert "4 canciones en me gusta" in copia.texto_resumen()
    assert "2 listas (4 canciones)" in copia.texto_resumen()

    hecho = CS.restaurar_coleccion(b, copia, "reemplazar")
    assert hecho["me_gusta"] == 4 and hecho["listas"] == 2
    assert huella(a) == huella(b)
    # la descarga mantiene su archivo (está en este equipo) y la lista la sigue nombrando
    claves = [p["clave"] for p in b.pistas_de_lista(b.listas(filtro="correr")[0]["id"])]
    assert any(c.startswith("local:") for c in claves)
    # portada propia restaurada
    lb = b.lista_por_uuid(a.lista(info["l1"])["uuid"])
    assert b.portada_personalizada(lb["id"])
    # ajustes: los de la PC vuelven en la PC; los secretos ni se intentan
    aj2 = AjustesFalsos()
    CS.restaurar_extras(copia, "reemplazar", ajustes=aj2, carpeta=tmp / "b", col=b)
    assert aj2["eq_bandas"] == [3, 2, 1, 0, 0, 0, 0, 1, 2, 3]
    assert aj2["acento"] == "rosa" and aj2["volumen"] == 55 and aj2["carpeta"] == str(tmp)
    assert "spotify_secreto" not in aj2 and "sesion_token" not in aj2
    assert json.loads((tmp / "b" / "mascota.json").read_text("utf-8"))["clave"] == "gatito"
    assert b.estado("gustos")["lista"][0]["nombre"] == "Ana"
    assert b.estado("saltos")["canciones"]["bbbbbbbbbb2"] == 2


def test_juntar_no_duplica(equipo):
    a, b, info, tmp = equipo
    copia = CS.abrir_copia(CS.crear_copia(a, AjustesFalsos(), carpeta=tmp / "a"))
    # B ya tenía algo propio, que se queda
    propia = pista("zzzzzzzzzz9", "Mía")
    b.alternar_me_gusta(propia)
    lb = b.crear_lista("Para correr")          # misma lista por nombre: se juntan
    b.agregar_a_lista(lb, [info["p"][0]])
    primera = CS.restaurar_coleccion(b, copia, "juntar")
    assert primera["me_gusta"] == 4
    antes = huella(b)
    segunda = CS.restaurar_coleccion(b, copia, "juntar")
    assert segunda == {k: 0 for k in segunda}, segunda
    assert huella(b) == antes
    assert b.total_me_gusta() == 5               # 4 de la copia + la propia
    assert len(b.listas()) == 2
    correr = [l for l in b.listas() if l["nombre"] == "Para correr"][0]
    assert correr["n"] == 3                      # p1 ya estaba: no se repite
    assert b.con.execute("SELECT COUNT(*) n FROM reproducciones").fetchone()["n"] == 3
    assert b.con.execute("SELECT COUNT(*) n FROM descargas").fetchone()["n"] == 1


def test_reemplazar_quita_lo_que_no_esta_pero_no_las_descargas(equipo):
    a, b, info, tmp = equipo
    copia = CS.abrir_copia(CS.crear_copia(a, None, carpeta=tmp / "a"))
    b.alternar_me_gusta(pista("zzzzzzzzzz9", "Mía"))
    b.crear_lista("Solo en B")
    b.con.execute("INSERT INTO descargas (url, titulo, archivo, estado, fecha, es_audio) VALUES "
                  "('u', 'Mía', 'C:/x.mp3', 'completada', 1, 1)")
    b.con.commit()
    CS.restaurar_coleccion(b, copia, "reemplazar")
    assert not b.me_gusta("yt:zzzzzzzzzz9")
    assert [l["nombre"] for l in b.listas()] == ["Tranquilas", "Para correr"]
    assert b.con.execute("SELECT COUNT(*) n FROM descargas").fetchone()["n"] == 2


def test_con_cuenta_deja_las_ordenes_para_la_nube(equipo):
    a, b, _info, tmp = equipo
    copia = CS.abrir_copia(CS.crear_copia(a, None, carpeta=tmp / "a"))
    b.sincronizador = MagicMock()
    CS.restaurar_coleccion(b, copia, "juntar")
    ops = [f["op"] for f in b.con.execute("SELECT op FROM pendientes")]
    assert ops.count("me_gusta_poner") == 3        # solo las de internet (yt:)
    assert ops.count("lista_poner") == 2 and "items_poner" in ops and "guardado_poner" in ops
    b.sincronizador.pronto.assert_called()


def test_descarga_de_otro_equipo_suena_desde_internet(equipo):
    """Si el archivo no está en este equipo, la canción sigue en tus me gusta y listas como yt:."""
    a, b, info, tmp = equipo
    copia = CS.abrir_copia(CS.crear_copia(a, None, carpeta=tmp / "a"))
    CS.restaurar_coleccion(b, copia, "reemplazar", existe=lambda _r: False)
    assert b.me_gusta("yt:LOCAL000001")
    p = b.pista("yt:LOCAL000001")
    assert p["titulo"] == "Canción descargada" and p["artista"] == "Grupo Local"


def test_estudio_ida_y_vuelta(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    (tmp_path / "a" / "estudio_notas.json").write_text(json.dumps([
        {"id": "n1", "texto": "Repasar integrales", "fecha": "2026-11-18T10:00:00"},
        {"id": "n2", "texto": "Leer cap. 3", "fecha": "2026-11-17T09:00:00"}]), "utf-8")
    (tmp_path / "a" / "estudio_historial.json").write_text(json.dumps(
        {"dias": {"2026-11-17": 1500, "2026-11-18": 3000}, "sesiones": []}), "utf-8")
    col = Coleccion(tmp_path / "a" / "h.db")
    copia = CS.abrir_copia(CS.crear_copia(col, None, carpeta=tmp_path / "a"))
    assert copia.resumen()["notas"] == 2
    (tmp_path / "b" / "estudio_notas.json").write_text(json.dumps([
        {"id": "x", "texto": "Mía", "fecha": "2026-11-19T08:00:00"}]), "utf-8")
    for _ in range(2):           # dos veces: no duplica
        CS.restaurar_extras(copia, "juntar", carpeta=tmp_path / "b")
    notas = json.loads((tmp_path / "b" / "estudio_notas.json").read_text("utf-8"))
    assert [n["texto"] for n in notas] == ["Mía", "Repasar integrales", "Leer cap. 3"]
    dias = json.loads((tmp_path / "b" / "estudio_historial.json").read_text("utf-8"))["dias"]
    assert dias == {"2026-11-17": 1500, "2026-11-18": 3000}
    col.con.close()


# ---------------------------------------------------------------------- errores claros


def _zip(archivos):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
        for n, v in archivos.items():
            z.writestr(n, v)
    return b.getvalue()


MANIFIESTO_OK = {"formato": "caudal-copia", "version": 1, "lee_desde": 1, "origen": {"app": "escritorio"}}


@pytest.mark.parametrize("contenido, frase", [
    (b"", "vacío"),
    (b"esto no es un zip" * 20, "no es una copia de Caudal"),
    (_zip({"hola.txt": "x"}), "no es una copia de seguridad"),
    (_zip({"manifiesto.json": json.dumps({"formato": "otra-cosa"})}), "no es una copia de seguridad"),
    (_zip({"manifiesto.json": "{roto"}), "dañada"),
    (_zip({"manifiesto.json": json.dumps(MANIFIESTO_OK)}), "incompleta"),
    (_zip({"manifiesto.json": json.dumps(MANIFIESTO_OK), "datos.json": "[1, 2"}), "dañada"),
    (_zip({"manifiesto.json": json.dumps({**MANIFIESTO_OK, "version": 3, "lee_desde": 2}),
           "datos.json": "{}"}), "versión más nueva"),
])
def test_archivos_malos_dan_un_error_claro(contenido, frase):
    with pytest.raises(CS.ErrorCopia) as e:
        CS.abrir_copia(contenido)
    assert frase in str(e.value)


def test_version_futura_compatible_se_abre():
    """Una versión 2 que dice «me leen desde la 1» se abre (lo nuevo se ignora)."""
    c = CS.abrir_copia(_zip({"manifiesto.json": json.dumps({**MANIFIESTO_OK, "version": 2, "lee_desde": 1}),
                             "datos.json": json.dumps({"coleccion": {"me_gusta": [], "cosa_nueva": 1}})}))
    assert c.resumen()["me_gusta"] == 0


def test_archivo_cortado_o_alterado(equipo):
    a, _b, _i, tmp = equipo
    contenido = CS.crear_copia(a, None, carpeta=tmp / "a")
    with pytest.raises(CS.ErrorCopia):
        CS.abrir_copia(contenido[: len(contenido) // 2])
    # se cambia un byte dentro de datos.json: el CRC ya no cuadra
    z = zipfile.ZipFile(io.BytesIO(contenido))
    info = z.getinfo("datos.json")
    inicio = info.header_offset + 30 + len(info.filename.encode()) + len(info.extra)
    roto = bytearray(contenido)
    roto[inicio + info.compress_size // 2] ^= 0xFF
    with pytest.raises(CS.ErrorCopia) as e:
        CS.abrir_copia(bytes(roto))
    assert "dañada" in str(e.value)
    with pytest.raises(CS.ErrorCopia) as e:
        CS.abrir_copia(tmp / "no_existe.caudal")
    assert "No se encuentra" in str(e.value)


# ---------------------------------------------------------------------- copia automática


def test_copia_automatica_semanal_y_poda(equipo):
    a, _b, _i, tmp = equipo
    carpeta = tmp / "a"
    destino = tmp / "copias"
    assert CS.hacer_automatica(a, None, carpeta) is None          # apagada por defecto
    CS.guardar_config({**CS.CONFIG_DEFECTO, "automatica": True, "carpeta": str(destino), "conservar": 2},
                      carpeta)
    hechas = []
    for i in range(4):
        ahora = 1_800_000_000 + i * 8 * 86400
        ruta = CS.hacer_automatica(a, None, carpeta, ahora=ahora)
        assert ruta is not None
        hechas.append(ruta)
        # al día siguiente no toca
        assert CS.hacer_automatica(a, None, carpeta, ahora=ahora + 86400) is None
    quedan = sorted(p.name for p in destino.glob("*.caudal"))
    assert len(quedan) == 2 and hechas[-1].name in quedan
    assert CS.abrir_copia(hechas[-1]).resumen()["me_gusta"] == 4


# ---------------------------------------------------------------------- entre la PC y el teléfono


def _copia_de_ejemplo_pc(tmp_path):
    col = Coleccion(tmp_path / "ejemplo.db")
    info = poblar(col, tmp_path)
    col.poner_portada_lista(info["l2"], foto())
    aj = AjustesFalsos(eq_bandas=[4, 3, 2, 1, 0, 0, 1, 2, 3, 4], ecualizador=True, eq_preset="Graves",
                       acento="rosa", fondo="oscuro", region="MX", crossfade=4, velocidad=1.25,
                       super_volumen=2, volumen=70, al_cerrar="bandeja")
    (tmp_path / "estudio_notas.json").write_text(json.dumps([
        {"id": "a1b2c3", "texto": "Nota hecha en la PC", "fecha": "2026-11-18T10:00:00"}]), "utf-8")
    (tmp_path / "estudio_historial.json").write_text(json.dumps({"dias": {"2026-11-18": 1800}}), "utf-8")
    contenido = CS.crear_copia(col, aj, carpeta=tmp_path, mascota="gatito")
    col.con.close()
    return contenido


def test_genera_la_copia_de_ejemplo_de_la_pc(tmp_path):
    """La deja en app/test/datos/ para la prueba de Flutter (se rehace con CAUDAL_REGENERAR_COPIAS=1)."""
    contenido = _copia_de_ejemplo_pc(tmp_path)
    assert CS.abrir_copia(contenido).resumen()["me_gusta"] == 4
    if os.environ.get("CAUDAL_REGENERAR_COPIAS") == "1" or not COPIA_PC.exists():
        DATOS_APP.mkdir(parents=True, exist_ok=True)
        COPIA_PC.write_bytes(contenido)
    assert CS.abrir_copia(COPIA_PC).origen == "escritorio"


@pytest.mark.skipif(not COPIA_MOVIL.exists(), reason="falta la copia de ejemplo del teléfono "
                                                     "(la genera app/test/copia_seguridad_test.dart)")
def test_la_copia_del_telefono_se_lee_en_la_pc(tmp_path):
    copia = CS.abrir_copia(COPIA_MOVIL)
    assert copia.origen == "movil"
    r = copia.resumen()
    assert r["me_gusta"] == 3 and r["listas"] == 2 and r["notas"] == 1
    col = Coleccion(tmp_path / "pc.db")
    CS.restaurar_coleccion(col, copia, "juntar")
    assert col.total_me_gusta() == 3
    assert col.me_gusta("yt:movil000001")
    assert col.pista("yt:movil000001")["titulo"] == "Hecha en el teléfono"
    nombres = {l["nombre"]: l["n"] for l in col.listas()}
    assert nombres == {"Del teléfono": 2, "Gimnasio": 1}
    # la descarga del teléfono no está en esta PC: suena desde internet
    gim = [l for l in col.listas() if l["nombre"] == "Gimnasio"][0]
    assert [p["clave"] for p in col.pistas_de_lista(gim["id"])] == ["yt:movildesc01"]
    assert col.con.execute("SELECT COUNT(*) n FROM reproducciones").fetchone()["n"] == 2
    # portada propia que venía del teléfono
    tel = [l for l in col.listas() if l["nombre"] == "Del teléfono"][0]
    assert col.portada_personalizada(tel["id"])
    aj = AjustesFalsos()
    (tmp_path / "perfil").mkdir()
    hecho = CS.restaurar_extras(copia, "juntar", ajustes=aj, carpeta=tmp_path / "perfil", col=col)
    assert "ajustes" in hecho and "estudio" in hecho
    # comunes sí; los propios del teléfono no
    assert aj["eq_bandas"] == [1, 2, 3, 4, 5, 5, 4, 3, 2, 1] and aj["ecualizador"] is True
    assert aj["region"] == "CO" and isinstance(aj["crossfade"], int)
    assert "modo_ligero" not in aj and "volumen" not in aj
    notas = json.loads((tmp_path / "perfil" / "estudio_notas.json").read_text("utf-8"))
    assert notas[0]["texto"] == "Nota hecha en el teléfono"
    dias = json.loads((tmp_path / "perfil" / "estudio_historial.json").read_text("utf-8"))["dias"]
    assert dias == {"2026-11-17": 1200}
    assert col.estado("gustos")["lista"][0]["nombre"] == "Karol G"
    col.con.close()
