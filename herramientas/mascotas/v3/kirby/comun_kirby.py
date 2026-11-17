# Kirby (frente, saludando). Lienzo 46x42; el contorno de shade.py suma 1 px por lado.
# Cuadro 0: brazo a un lado, boquita «o».  Cuadro 1: brazo arriba saludando, cuerpo 1 px arriba, sonrisa abierta y estrellita.
ROSA = '#f7a8c6'      # cuerpo
ROSA_B = '#f7a8c7'    # brazos (casi igual: shade.py los separa con línea fina)
LUZ = '#fcd2e2'       # reflejo suave del cuerpo
ROJO = '#e8364e'      # pies
SUELA = '#e8364f'
OJO = '#1a1a4a'
AZUL = '#3a62e0'
AZUL_L = '#7fa6ff'
BLANCO = '#ffffff'
MEJILLA = '#f2648a'
BOCA = '#9c1f3a'
LENGUA = '#f05a78'
ESTRELLA = '#ffd84a'


def estrella(M, cx, cy, r, color):
    import math
    pts = []
    for k in range(8):
        rr = r if k % 2 == 0 else r * 0.3
        a = -math.pi / 2 + k * math.pi / 4
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    M.poligono(pts, color)


def pose(M, f):
    up = 1 if f else 0
    if f == 0:
        M.elipse(6.8, 16, 4.6, 3.5, ROSA_B, rot=-30)          # brazo izquierdo a un lado
    else:
        M.elipse(8.6, 9.0, 3.4, 4.9, ROSA_B, rot=-30)         # brazo izquierdo arriba (saluda)
    M.elipse(23, 20.5 - up, 16.5, 15.5 - up * 0.5, ROSA)    # cuerpo
    M.elipse(15.5, 9.5 - up, 3.2, 1.8, LUZ, rot=-35)          # reflejo arriba-izquierda
    M.elipse(39.5, 24.5 - up, 4.2, 3.2, ROSA_B, rot=25)       # brazo derecho (delante)
    M.elipse(14, 37.6, 7.2, 3.8, ROJO, rot=-8)                # pies
    M.elipse(32, 38.0, 7.6, 3.9, SUELA, rot=6)
    for cx in (19.0, 27.0):                                   # ojos grandes: azul abajo, brillo grande arriba
        M.elipse(cx, 14.4 - up, 2.1, 4.0, OJO)
        M.elipse(cx, 16.4 - up, 1.2, 1.6, AZUL)
        M.elipse(cx, 17.2 - up, 0.6, 0.6, AZUL_L)
        M.elipse(cx - 0.4, 12.2 - up, 0.9, 1.3, BLANCO)
    M.elipse(14.0, 20.0 - up, 3.0, 1.0, MEJILLA)
    M.elipse(32.0, 20.0 - up, 3.0, 1.0, MEJILLA)
    if f == 0:
        M.elipse(23.0, 21.4, 1.8, 1.5, BOCA)                  # boquita «o»
        M.elipse(23.0, 22.3, 1.1, 0.6, LENGUA)
    else:
        M.blob([(20.2, 19.4), (23, 19.9), (25.8, 19.4), (25.0, 22.2), (23, 23.0), (21.0, 22.2)], BOCA)   # sonrisa abierta
        M.elipse(23.0, 22.0, 1.5, 0.8, LENGUA)
        estrella(M, 3.0, 3.5, 3.5, ESTRELLA)
