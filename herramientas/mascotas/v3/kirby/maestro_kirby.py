# Maestro de Kirby (frente, de pie, saludando). Coordenadas en píxeles del sprite (46x42; el contorno suma 1 px por lado).
ROSA = '#f7a8c6'      # cuerpo
ROSA_B = '#f7a8c7'    # brazos: casi el mismo color para que shade.py los separe con una línea fina
ROJO = '#e8364e'      # pies
OJO = '#1a1a4a'
AZUL = '#3a62e0'
BLANCO = '#ffffff'
MEJILLA = '#f2648a'
BOCA = '#9c1f3a'
LENGUA = '#f05a78'


def dibujar(M):
    M.elipse(6.5, 15, 4.6, 3.4, ROSA_B, rot=-35)          # brazo izquierdo levantado (detrás)
    M.elipse(23, 20.5, 16.5, 15.5, ROSA)                  # cuerpo
    M.elipse(39.5, 24.5, 4.2, 3.2, ROSA_B, rot=25)        # brazo derecho (delante)
    M.elipse(14, 37.5, 7.2, 3.7, ROJO, rot=-8)            # pie izquierdo
    M.elipse(32, 38, 7.6, 3.9, ROJO, rot=6)               # pie derecho
    for cx in (19.0, 27.0):                               # ojos: óvalo alto oscuro, azul DENTRO abajo, brillo arriba
        M.elipse(cx, 14.5, 1.9, 3.7, OJO)
        M.elipse(cx, 15.9, 1.0, 1.2, AZUL)
        M.elipse(cx - 0.3, 12.4, 0.8, 1.0, BLANCO)
    M.elipse(14.0, 20.0, 2.7, 1.4, MEJILLA)               # mejillas
    M.elipse(32.0, 20.0, 2.7, 1.4, MEJILLA)
    M.elipse(23.0, 21.6, 1.9, 1.6, BOCA)                  # boca abierta («o») con lengua
    M.elipse(23.0, 22.5, 1.2, 0.7, LENGUA)
