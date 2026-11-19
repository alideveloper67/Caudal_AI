# -*- coding: utf-8 -*-
"""Pases de prueba de Caudal: códigos que dan unos días de beneficios de donador a quien los canjea
(una sola prueba por cuenta). Se canjean desde la app, en Ajustes.

  python herramientas/pase_prueba.py crear                       # 1 código de 7 días, 1 uso, 30 días para canjearlo
  python herramientas/pase_prueba.py crear --dias 14 --usos 5 --caduca-en-dias 60
  python herramientas/pase_prueba.py crear --cantidad 10         # diez códigos de un solo uso
  python herramientas/pase_prueba.py --lista                     # los pases y cuántas veces se usaron
  python herramientas/pase_prueba.py --quitar ABCD-2345          # borra un pase (las pruebas ya activadas siguen)
  python herramientas/pase_prueba.py --ver-canjes                # quién canjeó qué y cuándo vence

Los códigos no llevan 0, O, 1 ni I para que no se confundan al dictarlos.
El token de Supabase se lee de --token, de la variable SUPABASE_TOKEN o de ~/.claude/supabase-token.txt.
Es el token de ADMINISTRADOR: nunca va en el código de las apps ni en el repositorio."""

import argparse
import json
import os
import re
import secrets
import sys
import urllib.error
import urllib.request

PROYECTO = "nztirmwqykbxadidpzzt"
ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"   # sin 0 O 1 I


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


def codigo_nuevo():
    """ABCD-2345: ocho caracteres legibles, de una fuente aleatoria segura."""
    c = "".join(secrets.choice(ALFABETO) for _ in range(8))
    return c[:4] + "-" + c[4:]


def sql_crear(codigos, dias, usos, caduca_dias):
    caduca = f"now() + interval '{int(caduca_dias)} days'" if caduca_dias else "null"
    filas = ", ".join(f"('{c}', {int(dias)}, {int(usos)}, {caduca})" for c in codigos)
    return (f"insert into public.pases_prueba (codigo, dias, usos_max, caduca) values {filas} "
            f"on conflict do nothing returning codigo")


def normalizar(texto):
    """abcd 2345 -> ABCD-2345 (o None si no tiene ocho letras o números)."""
    limpio = re.sub(r"[^A-Za-z0-9]", "", texto or "").upper()
    return limpio[:4] + "-" + limpio[4:] if len(limpio) == 8 else None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("accion", nargs="?", choices=["crear"], help="crear: genera códigos nuevos")
    ap.add_argument("--dias", type=int, default=7, help="días de beneficios que da cada código (1 a 30, por defecto 7)")
    ap.add_argument("--usos", type=int, default=1, help="cuántas cuentas pueden canjearlo (por defecto 1)")
    ap.add_argument("--caduca-en-dias", type=int, default=30, dest="caduca",
                    help="días que el código se puede canjear (por defecto 30; 0 = no caduca)")
    ap.add_argument("--cantidad", type=int, default=1, help="cuántos códigos crear (por defecto 1)")
    ap.add_argument("--lista", action="store_true", help="muestra los pases")
    ap.add_argument("--quitar", metavar="CODIGO", help="borra ese pase")
    ap.add_argument("--ver-canjes", action="store_true", dest="canjes", help="muestra quién canjeó qué")
    ap.add_argument("--token")
    a = ap.parse_args(argv)

    if a.accion == "crear":
        if not 1 <= a.dias <= 30:
            ap.error("--dias va de 1 a 30")
        if a.usos < 1:
            ap.error("--usos debe ser al menos 1")
        if not 1 <= a.cantidad <= 500:
            ap.error("--cantidad va de 1 a 500")
        if a.caduca < 0:
            ap.error("--caduca-en-dias no puede ser negativo")
        token = _token(a.token)
        hechos = []
        while len(hechos) < a.cantidad:
            lote = {codigo_nuevo() for _ in range(a.cantidad - len(hechos))}
            hechos += [f["codigo"] for f in consulta(token, sql_crear(sorted(lote), a.dias, a.usos, a.caduca))]
        vig = f"vale hasta {a.caduca} días desde hoy" if a.caduca else "no caduca"
        print(f"{len(hechos)} {'código' if len(hechos) == 1 else 'códigos'} de {a.dias} días, "
              f"{a.usos} {'uso' if a.usos == 1 else 'usos'} cada uno ({vig}):")
        for c in hechos:
            print("  " + c)
        return 0
    token = _token(a.token)
    if a.lista:
        filas = consulta(token, "select codigo, dias, usos, usos_max, caduca, creado from public.pases_prueba order by creado desc")
        if not filas:
            print("No hay pases.")
        for f in filas:
            estado = "agotado" if f["usos"] >= f["usos_max"] else "libre"
            print(f"{f['codigo']}  {f['dias']} días  usos {f['usos']}/{f['usos_max']}  ({estado})"
                  f"{'  caduca ' + f['caduca'][:10] if f['caduca'] else ''}")
        return 0
    if a.quitar:
        cod = normalizar(a.quitar)
        if not cod:
            ap.error("ese código no tiene el formato ABCD-2345")
        r = consulta(token, f"delete from public.pases_prueba where codigo = '{cod}' returning codigo")
        print(f"Pase {cod} borrado." if r else f"No existe el pase {cod}.")
        return 0
    if a.canjes:
        filas = consulta(token, """
            select p.usuario, c.codigo, c.canjeado, t.vence
            from public.pases_canjeados c
            join public.perfiles p on p.id = c.user_id
            left join public.titulos_especiales t on t.user_id = c.user_id and t.titulo = 'invitado_caudal'
            order by c.canjeado desc""")
        if not filas:
            print("Todavía nadie canjeó un pase.")
        for f in filas:
            vence = f["vence"][:10] if f["vence"] else "—"
            print(f"{f['usuario']:<22} {f['codigo']}  canjeado {f['canjeado'][:10]}  vence {vence}")
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
