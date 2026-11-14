# -*- coding: utf-8 -*-
"""Copia los textos legales (fuente unica: esta carpeta) a la app del telefono,
al escritorio y a la web, rellenando el correo y la direccion de la web.

    python legal/sincronizar.py

Si cambias algo importante de los textos, sube tambien VERSION (aqui y en
app/lib/nucleo/legal.dart y escritorio/descargador/legal.py): a todos se les
pedira aceptarlos de nuevo.
"""

import json
import os
import re

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
DATOS = json.load(open(os.path.join(AQUI, "datos.json"), encoding="utf-8"))
TEXTOS = ("terminos", "privacidad")


def rellenar(texto):
    return texto.replace("{{CORREO}}", DATOS["correo"]).replace("{{WEB}}", DATOS["web"].rstrip("/"))


def a_html(md):
    """Markdown sencillo (titulos, listas, negritas) a HTML."""
    salida, en_lista = [], False
    for linea in md.splitlines():
        l = linea.rstrip()
        l_html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>",
                        l.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
        l_html = re.sub(r"(https?://[^\s)]+)", r'<a href="\1">\1</a>', l_html)
        if l.startswith("- "):
            if not en_lista:
                salida.append("<ul>")
                en_lista = True
            salida.append(f"<li>{l_html[2:]}</li>")
            continue
        if en_lista:
            salida.append("</ul>")
            en_lista = False
        if l.startswith("# "):
            salida.append(f"<h1>{l_html[2:]}</h1>")
        elif l.startswith("## "):
            salida.append(f"<h2>{l_html[3:]}</h2>")
        elif l:
            salida.append(f"<p>{l_html}</p>")
    if en_lista:
        salida.append("</ul>")
    return "\n".join(salida)


def main():
    destinos_md = [os.path.join(RAIZ, "app", "assets", "legal"),
                   os.path.join(RAIZ, "escritorio", "descargador", "legal")]
    for d in destinos_md:
        os.makedirs(d, exist_ok=True)
    plantilla = open(os.path.join(AQUI, "plantilla_web.html"), encoding="utf-8").read()
    for nombre in TEXTOS:
        md = rellenar(open(os.path.join(AQUI, f"{nombre}.md"), encoding="utf-8").read())
        for d in destinos_md:
            open(os.path.join(d, f"{nombre}.md"), "w", encoding="utf-8").write(md)
        titulo = md.splitlines()[0].lstrip("# ").strip()
        html = plantilla.replace("{{TITULO}}", titulo).replace("{{CUERPO}}", a_html(md))
        open(os.path.join(RAIZ, "web", f"{nombre}.html"), "w", encoding="utf-8").write(html)
    print("textos legales copiados (correo:", DATOS["correo"], "| web:", DATOS["web"], ")")


if __name__ == "__main__":
    main()
