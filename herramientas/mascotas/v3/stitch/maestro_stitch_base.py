# Maestro de Stitch (3/4 hacia la derecha, saludando). Lienzo 46x42.
# f = cuadro: 0 de pie; 1 orejas levantadas + brazo más arriba + cuerpo 1 px arriba.
AZUL = '#4a86e0'      # cabeza y cuerpo
AZUL_B = '#4a86e1'    # brazos y patas delante (línea interior)
OREJA = '#4a85e0'     # orejas (separadas de la cabeza con línea interior)
CELESTE = '#a6d2f7'   # panza y antifaz claro
ROSA = '#e98cbc'      # interior de las orejas
MARCA = '#2f5fb8'     # marca oscura de la frente
OJO = '#14162a'
BRILLO = '#ffffff'
NARIZ = '#1d2b5c'
NARIZ_B = '#5a6fb0'
BOCA = '#5a1630'
LENGUA = '#f06a8a'
DIENTE = '#f4f6ff'


def pose(M, f):
    up = 1 if f else 0
    hy = 16.5 - up
    t = 1.8 if f == 0 else 4.2          # cuánto suben las puntas de las orejas

    # orejas largas de punta, abiertas hacia los lados
    M.blob([(13.5, hy - 8.5), (6, hy - 10 - t * 0.6), (0.6, hy - 10.5 - t), (2.6, hy - 6.5 - t * 0.6),
            (7, hy - 2.5), (12, hy + 1.5)], OREJA)
    M.blob([(12, hy - 6.8), (6.5, hy - 8.4 - t * 0.6), (3.2, hy - 8.8 - t), (5.2, hy - 6.3 - t * 0.6), (11, hy - 1.5)], ROSA)
    M.blob([(32.5, hy - 8.5), (40, hy - 10 - t * 0.6), (45.4, hy - 10.5 - t), (43.4, hy - 6.5 - t * 0.6),
            (39, hy - 2.5), (34, hy + 1.5)], OREJA)
    M.blob([(34, hy - 6.8), (39.5, hy - 8.4 - t * 0.6), (42.8, hy - 8.8 - t), (40.8, hy - 6.3 - t * 0.6), (35, hy - 1.5)], ROSA)

    # cuerpo
    by = 32.5 - up
    M.elipse(23.5, by, 9.5, 7.5, AZUL)
    M.elipse(24.5, by + 1.0, 6.0, 5.2, CELESTE)                 # panza
    # patas
    M.elipse(17.5, 39.0, 4.2, 2.6, AZUL_B)
    M.elipse(30.0, 39.2, 4.4, 2.6, AZUL_B)
    # brazo derecho bajado, delante
    M.elipse(33.5, by + 0.5, 2.6, 4.0, AZUL_B, rot=-25)
    # brazo izquierdo saludando
    if f == 0:
        M.capsula(14.5, by - 1.0, 9.0, by - 6.5, 2.1, AZUL_B)
        M.elipse(8.4, by - 7.6, 2.5, 2.3, AZUL_B)
    else:
        M.capsula(14.5, by - 1.5, 7.5, by - 9.0, 2.1, AZUL_B)
        M.elipse(6.8, by - 10.0, 2.5, 2.3, AZUL_B)

    # cabeza ancha
    M.blob([(9, hy - 2), (14, hy - 9), (24, hy - 10.5), (34, hy - 9), (39, hy - 2), (38, hy + 6),
            (31, hy + 10.5), (23, hy + 11.2), (15, hy + 10), (9.5, hy + 5)], AZUL)
    # marca de la frente
    M.blob([(21, hy - 10), (26, hy - 10), (25, hy - 6.5), (23.5, hy - 6), (22, hy - 6.5)], MARCA)
    # antifaz claro alrededor de los ojos y hocico
    M.elipse(17.0, hy + 0.5, 5.2, 4.8, CELESTE)
    M.elipse(31.0, hy + 0.5, 5.2, 4.8, CELESTE)
    M.elipse(24.2, hy + 5.8, 8.0, 3.8, CELESTE)
    # ojos grandes negros con brillo
    for cx in (17.3, 31.3):
        M.elipse(cx, hy + 0.3, 3.6, 3.9, OJO)
        M.elipse(cx - 1.3, hy - 1.2, 1.1, 1.2, BRILLO)
        M.punto(cx + 1.4, hy + 1.8, BRILLO, r=0.5)
    # nariz grande con brillo
    M.elipse(24.4, hy + 4.0, 3.0, 1.9, NARIZ)
    M.elipse(23.4, hy + 3.4, 0.9, 0.6, NARIZ_B)
    # sonrisa ancha con dientes y lengua
    M.blob([(16.8, hy + 6.2), (24.3, hy + 7.0), (31.8, hy + 6.0), (29.0, hy + 9.4), (24.3, hy + 10.6), (19.6, hy + 9.6)], BOCA)
    M.elipse(24.6, hy + 9.6, 2.6, 1.0, LENGUA)
    M.rect(19.0, hy + 6.3, 20.6, hy + 7.4, DIENTE)
    M.rect(28.2, hy + 6.2, 29.8, hy + 7.3, DIENTE)
