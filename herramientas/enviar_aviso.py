# -*- coding: utf-8 -*-
"""Manda un aviso a las apps de Caudal (web, Android, Windows, iPhone) sin sacar versión nueva.

Cada app lo lee al abrirse y lo muestra una sola vez por dispositivo.

  python herramientas/enviar_aviso.py "Título" "Texto del aviso" --para web
  python herramientas/enviar_aviso.py "Nueva versión" "Ya puedes actualizar" --para android windows \
         --enlace https://caudal-musica.netlify.app/#descargar --etiqueta "Descargar" --dias 14
  python herramientas/enviar_aviso.py --lista          # los avisos vigentes
  python herramientas/enviar_aviso.py --quitar 3       # deja de mostrar el aviso 3

El token de Supabase se lee de --token, de la variable SUPABASE_TOKEN o de ~/.claude/supabase-token.txt.
Es el token de ADMINISTRADOR: nunca va en el código de las apps ni en el repositorio."""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

PROYECTO = "nztirmwqykbxadidpzzt"
PLATAFORMAS = ("todas", "web", "android", "windows", "ios")


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


def sql_insertar(titulo, texto, para, enlace=None, etiqueta=None, dias=None):
    plat = "array[" + ", ".join(lit(p) for p in para) + "]"
    caduca = f"now() + interval '{int(dias)} days'" if dias else "null"
    return (f"insert into public.avisos (titulo, texto, plataformas, enlace, etiqueta_enlace, caduca) values "
            f"({lit(titulo)}, {lit(texto)}, {plat}, {lit(enlace) if enlace else 'null'}, "
            f"{lit(etiqueta) if etiqueta else 'null'}, {caduca}) returning id")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("titulo", nargs="?")
    ap.add_argument("texto", nargs="?")
    ap.add_argument("--para", nargs="+", default=["todas"], choices=PLATAFORMAS, metavar="PLATAFORMA",
                    help="todas (por defecto), web, android, windows, ios")
    ap.add_argument("--enlace", help="un botón que abre esta dirección (https://…)")
    ap.add_argument("--etiqueta", help="texto del botón (por defecto «Abrir»)")
    ap.add_argument("--dias", type=int, help="días que sigue vigente (si no, hasta quitarlo)")
    ap.add_argument("--lista", action="store_true", help="muestra los avisos vigentes")
    ap.add_argument("--quitar", type=int, metavar="ID", help="deja de mostrar ese aviso")
    ap.add_argument("--token")
    a = ap.parse_args(argv)
    token = _token(a.token)

    if a.lista:
        for f in consulta(token, "select id, titulo, plataformas, caduca, activo from public.avisos order by id"):
            print(f"#{f['id']} [{', '.join(f['plataformas'])}] {f['titulo']}"
                  f"{'' if f['activo'] else ' (quitado)'}{' · caduca ' + f['caduca'] if f['caduca'] else ''}")
        return 0
    if a.quitar:
        consulta(token, f"update public.avisos set activo = false where id = {int(a.quitar)}")
        print(f"Aviso {a.quitar} quitado.")
        return 0
    if not a.titulo or not a.texto:
        ap.error("hacen falta el título y el texto (o --lista / --quitar)")
    if len(a.titulo) > 80 or len(a.texto) > 600:
        ap.error("el título admite 80 caracteres y el texto 600")
    if a.enlace and not a.enlace.startswith("https://"):
        ap.error("el enlace tiene que empezar por https://")
    r = consulta(token, sql_insertar(a.titulo, a.texto, a.para, a.enlace, a.etiqueta, a.dias))
    print(f"Aviso {r[0]['id']} enviado a: {', '.join(a.para)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
