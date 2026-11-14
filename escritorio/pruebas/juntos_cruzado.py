# -*- coding: utf-8 -*-
"""Prueba cruzada PC <-> telefono: este guion (Python, como Caudal Windows) y
`flutter test` (la app movil) en las mismas salas reales de Supabase.

  1) Python crea la sala y pone la musica; Flutter entra y la sigue.
  2) Flutter crea la sala y pone la musica; Python entra y la sigue.

Se coordinan con dos archivos: <dir>/sala_py.txt y <dir>/sala_dart.txt.
Uso: python pruebas/juntos_cruzado.py <dir>   (y a la vez el test de Dart)
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from descargador import juntos as J  # noqa: E402
from pruebas.test_juntos import ReproductorFalso  # noqa: E402


def esperar(cond, que, maximo=60):
    fin = time.time() + maximo
    while not cond():
        if time.time() > fin:
            raise SystemExit(f"FALLO: no pasó a tiempo: {que}")
        time.sleep(0.1)
    print("ok:", que, flush=True)


def abrir(bucle, sala):
    res = []
    sala.al_abierta = res.append
    bucle.salas.append(sala)
    bucle.llamar(sala.abrir)
    esperar(lambda: res, "sala abierta", 30)
    if res[0] is not None:
        raise SystemExit(f"FALLO: {res[0]}")


def main(carpeta):
    os.makedirs(carpeta, exist_ok=True)
    for f in ("sala_py.txt", "sala_dart.txt"):
        try:
            os.remove(os.path.join(carpeta, f))
        except OSError:
            pass
    bucle = J.BucleSimple()

    # ---- 1) Python es el anfitrion
    a = ReproductorFalso()
    a.poner({"video_id": "dQw4w9WgXcQ", "titulo": "Desde la PC", "artista": "Caudal",
             "duracion": 213}, 40000)
    reacciones = []
    anf = J.SalaJuntos(J.nuevo_codigo(), a, "PC Windows", "pc", anfitrion=True,
                       despachar=bucle.despachar, al_reaccion=lambda e, n, m: reacciones.append((e, n)))
    abrir(bucle, anf)
    with open(os.path.join(carpeta, "sala_py.txt"), "w", encoding="utf-8") as f:
        f.write(anf.codigo)
    print("sala de Python:", anf.codigo, flush=True)
    esperar(lambda: any(m.nombre == "Telefono Flutter" for m in anf.miembros),
            "el teléfono aparece en la lista de la PC", 120)
    esperar(lambda: ("🎉", "Telefono Flutter") in reacciones, "llega la reacción del teléfono")
    bucle.llamar(lambda: anf.reaccionar("❤️"))
    # salto en la PC: el telefono debe seguirlo (lo comprueba el lado Dart)
    time.sleep(3)
    bucle.llamar(lambda: (a.buscar(150000), anf.al_cambiar_reproductor()))
    esperar(lambda: len(anf.miembros) == 1, "el teléfono sale de la sala", 90)
    bucle.llamar(anf.salir)

    # ---- 2) Flutter es el anfitrion
    ruta = os.path.join(carpeta, "sala_dart.txt")
    esperar(lambda: os.path.exists(ruta) and open(ruta, encoding="utf-8").read().strip(),
            "Flutter crea su sala", 90)
    codigo = open(ruta, encoding="utf-8").read().strip()
    b = ReproductorFalso()
    inv = J.SalaJuntos(codigo, b, "PC Windows", "pc", despachar=bucle.despachar)
    abrir(bucle, inv)
    esperar(lambda: (b.pista or {}).get("video_id") == "kJQP7kiw5Fk", "la PC carga la canción del teléfono")
    esperar(lambda: b.sonando, "la PC suena")
    esperar(lambda: inv.anfitrion is not None and inv.anfitrion.nombre == "Telefono Flutter",
            "el teléfono es quien pone la música")
    # la PC se desvia a proposito: debe corregirse sola
    time.sleep(2)
    b.buscar(b.posicion_ms + 8000)
    pos_tras = []

    def a_la_par():
        e = inv.ultimo_estado or {}
        esperada = J.posicion_esperada(int(e.get("pos") or 0), e.get("sonando") is True,
                                       int(e.get("t") or 0), inv.diferencia_reloj)
        pos_tras.append(abs(b.posicion_ms - esperada))
        return pos_tras[-1] < 1500
    time.sleep(2.5)
    esperar(a_la_par, "la PC corrige la deriva respecto al teléfono")
    print(f"desfase final PC-teléfono: {pos_tras[-1]} ms", flush=True)
    bucle.llamar(lambda: inv.reaccionar("🔥"))
    with open(os.path.join(carpeta, "py_listo.txt"), "w", encoding="utf-8") as f:
        f.write("1")
    esperar(lambda: inv.soy_anfitrion or not inv.miembros or len(inv.miembros) == 1,
            "el teléfono sale y la PC toma el mando", 90)
    bucle.llamar(inv.salir)
    bucle.parar()
    print("CRUZADA OK", flush=True)


if __name__ == "__main__":
    main(sys.argv[1])
