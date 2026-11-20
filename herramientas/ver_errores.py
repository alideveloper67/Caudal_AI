# -*- coding: utf-8 -*-
"""Lista los errores que mandaron las apps de Caudal (tabla errores_app), agrupados por traza.

Cada grupo es un mismo error (misma huella: tipo + funciones de la traza, sin números de línea),
con cuántas veces pasó, en cuántos informes, en qué plataformas y versiones, y cuándo fue la
primera y la última vez. Los informes no llevan datos personales (supabase/errores_app.sql).

  python herramientas/ver_errores.py                     # los grupos de los últimos 30 días
  python herramientas/ver_errores.py --dias 7 --plataforma android --version 2.6.1
  python herramientas/ver_errores.py --traza             # con la última traza de cada grupo
  python herramientas/ver_errores.py --huella 3fa2c1...  # los últimos informes de un grupo
  python herramientas/ver_errores.py --limpiar           # borra los de hace más de 120 días

El token de Supabase se lee de --token, de la variable SUPABASE_TOKEN o de ~/.claude/supabase-token.txt.
Es el token de ADMINISTRADOR: nunca va en el código de las apps ni en el repositorio."""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request

PROYECTO = "nztirmwqykbxadidpzzt"
PLATAFORMAS = ("windows", "android", "ios", "web", "macos", "linux", "otra")


def _token(arg):
    if arg:
        return arg
    if os.environ.get("SUPABASE_TOKEN"):
        return os.environ["SUPABASE_TOKEN"].strip()
    ruta = os.path.join(os.path.expanduser("~"), ".claude", "supabase-token.txt")
    if os.path.exists(ruta):
        with open(ruta, encoding="utf-8") as f:
            return f.read().strip()
    sys.exit("Falta el token de Supabase (--token, SUPABASE_TOKEN o ~/.claude/supabase-token.txt).")


def lit(valor):
    """Un texto como literal SQL (comillas dobladas, sin caracteres nulos)."""
    return "'" + str(valor).replace("\x00", "").replace("'", "''") + "'"


def consulta(token, sql):
    req = urllib.request.Request(
        f"https://api.supabase.com/v1/projects/{PROYECTO}/database/query",
        data=json.dumps({"query": sql}).encode("utf-8"),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        sys.exit(f"Supabase rechazó la petición ({e.code}): {e.read().decode('utf-8', 'replace')[:300]}")


def _filtros(dias, plataforma=None, version=None, huella=None):
    donde = [f"creado > now() - interval '{max(1, int(dias))} days'"]
    if plataforma:
        donde.append(f"plataforma = {lit(plataforma)}")
    if version:
        donde.append(f"version = {lit(version)}")
    if huella:
        if not re.fullmatch(r"[0-9a-f]{4,64}", huella):
            raise ValueError("la huella son letras a-f y números")
        donde.append(f"huella like {lit(huella + '%')}")
    return " and ".join(donde)


def sql_agrupados(dias=30, plataforma=None, version=None, limite=30):
    """Un grupo por huella, del que más veces pasó al que menos."""
    return (
        "select huella, "
        "(array_agg(tipo order by creado desc))[1] as tipo, "
        "(array_agg(mensaje order by creado desc))[1] as mensaje, "
        "(array_agg(pantalla order by creado desc))[1] as pantalla, "
        "(array_agg(origen order by creado desc))[1] as origen, "
        "(array_agg(traza order by creado desc))[1] as traza, "
        "sum(veces)::bigint as veces, count(*)::int as informes, "
        "array_agg(distinct plataforma order by plataforma) as plataformas, "
        "array_agg(distinct version order by version) as versiones, "
        "min(coalesce(primera_vez, creado)) as primera, max(creado) as ultima "
        f"from public.errores_app where {_filtros(dias, plataforma, version)} "
        f"group by huella order by veces desc, ultima desc limit {max(1, int(limite))}")


def sql_detalle(huella, dias=90, limite=20):
    """Los últimos informes de un grupo."""
    return ("select creado, plataforma, version, sistema, pantalla, origen, veces, tipo, mensaje, traza "
            f"from public.errores_app where {_filtros(dias, huella=huella)} "
            f"order by creado desc limit {max(1, int(limite))}")


def _corto(fecha):
    return str(fecha or "")[:16].replace("T", " ")


def formatear(grupos, con_traza=False):
    """Texto para la consola a partir de las filas de sql_agrupados."""
    if not grupos:
        return "No hay errores en ese periodo."
    lineas = []
    total = sum(int(g.get("veces") or 0) for g in grupos)
    lineas.append(f"{len(grupos)} errores distintos · {total} veces en total\n")
    for n, g in enumerate(grupos, 1):
        plats = ", ".join(g.get("plataformas") or [])
        vers = ", ".join(g.get("versiones") or [])
        lineas.append(f"#{n}  {g.get('tipo')}  ×{g.get('veces')}  ({g.get('informes')} informes)")
        if g.get("mensaje"):
            lineas.append(f"    {str(g['mensaje'])[:200]}")
        lineas.append(f"    {plats} · versiones {vers} · pantalla: {g.get('pantalla') or '-'}"
                      f"{' · ' + g['origen'] if g.get('origen') else ''}")
        lineas.append(f"    primera {_corto(g.get('primera'))} · última {_corto(g.get('ultima'))}"
                      f" · huella {str(g.get('huella'))[:12]}")
        if con_traza and g.get("traza"):
            lineas.append("    " + "\n    ".join(str(g["traza"]).rstrip().splitlines()[-25:]))
        lineas.append("")
    return "\n".join(lineas)


def formatear_detalle(filas):
    if not filas:
        return "No hay informes con esa huella."
    salida = []
    for f in filas:
        salida.append(f"[{_corto(f.get('creado'))}] {f.get('plataforma')} {f.get('version')} · {f.get('sistema')}"
                      f" · {f.get('pantalla') or '-'} · ×{f.get('veces')}")
    ultima = filas[0]
    salida.append(f"\nÚltima traza ({ultima.get('tipo')}: {ultima.get('mensaje')}):\n{ultima.get('traza')}")
    return "\n".join(salida)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dias", type=int, default=30, help="cuántos días hacia atrás (30 por defecto)")
    ap.add_argument("--plataforma", choices=PLATAFORMAS)
    ap.add_argument("--version", help="solo esa versión (p. ej. 2.7.2)")
    ap.add_argument("--limite", type=int, default=30, help="cuántos grupos (30 por defecto)")
    ap.add_argument("--traza", action="store_true", help="enseña la última traza de cada grupo")
    ap.add_argument("--huella", help="los últimos informes de un grupo (basta el principio de la huella)")
    ap.add_argument("--json", action="store_true", help="salida en JSON")
    ap.add_argument("--limpiar", action="store_true", help="borra los informes de hace más de 120 días")
    ap.add_argument("--token")
    a = ap.parse_args(argv)
    token = _token(a.token)
    if a.limpiar:
        r = consulta(token, "select public.errores_app_limpiar() as n")
        print(f"Borrados {r[0]['n']} informes viejos.")
        return 0
    if a.huella:
        try:
            filas = consulta(token, sql_detalle(a.huella, max(a.dias, 90)))
        except ValueError as e:
            ap.error(str(e))
        print(json.dumps(filas, ensure_ascii=False, indent=1) if a.json else formatear_detalle(filas))
        return 0
    grupos = consulta(token, sql_agrupados(a.dias, a.plataforma, a.version, a.limite))
    print(json.dumps(grupos, ensure_ascii=False, indent=1) if a.json else formatear(grupos, a.traza))
    return 0


if __name__ == "__main__":
    sys.exit(main())
