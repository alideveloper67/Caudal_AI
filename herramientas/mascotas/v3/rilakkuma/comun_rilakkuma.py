# Rilakkuma (frente, saludando con calma). Lienzo 46x42.
# Cuadro 0: patita a un lado.  Cuadro 1: patita arriba saludando, cabeza ladeada, cuerpo 1 px arriba.
CAFE = '#b8834f'       # cabeza
CAFE_O = '#b8834e'     # orejas
CAFE_C = '#b8824f'     # cuerpo
CAFE_B = '#b7834f'     # brazos y pies (delante)
CREMA = '#fbe6c0'      # hocico, barriga, interior de orejas
CREMA_P = '#fbe6c1'    # almohadillas
HOCICO = '#fbe7c0'     # hocico (fijo: no hace sombra sobre la cabeza)
OJO = '#22140c'
BLANCO = '#ffffff'
NARIZ = '#3a2010'
BOCA = '#4a2a16'
MEJILLA = '#f4a08a'
CIERRE = '#c8ccd8'
CIERRE_O = '#7a7f94'


def pose(M, f):
    up = 1 if f else 0
    rot = -5 if f else 0
    # cuerpo
    M.elipse(23, 31.5 - up * 0.5, 11.6, 8.6, CAFE_C)
    M.elipse(23, 32.4 - up * 0.5, 6.6, 5.6, CREMA)                 # barriga
    # cierre en la barriga (tirador plateado)
    M.rect(22.4, 26.8 - up, 23.6, 29.4 - up, CIERRE_O)
    M.rect(22.4, 29.0 - up, 23.6, 31.2 - up, CIERRE)
    # pies
    M.elipse(16, 39.0, 4.8, 2.8, CAFE_B)
    M.elipse(30, 39.0, 4.8, 2.8, CAFE_B)
    M.elipse(16.4, 39.3, 2.4, 1.5, CREMA_P)
    M.elipse(29.6, 39.3, 2.4, 1.5, CREMA_P)
    # brazos
    M.elipse(34.2, 30.5 - up, 3.0, 4.0, CAFE_B, rot=-25)
    if f == 0:
        M.elipse(11.8, 30.5, 3.0, 4.0, CAFE_B, rot=25)
    else:
        M.elipse(7.0, 20.5, 2.8, 4.0, CAFE_B, rot=-30)
    # orejas con interior claro
    M.elipse(10.8 - (0.6 if f else 0), 6.6 - up, 4.6, 4.4, CAFE_O)
    M.elipse(35.2 - (0.6 if f else 0), 6.6 - up + (0.6 if f else 0), 4.6, 4.4, CAFE_O)
    M.elipse(10.8 - (0.6 if f else 0), 7.0 - up, 2.4, 2.2, CREMA)
    M.elipse(35.2 - (0.6 if f else 0), 7.0 - up + (0.6 if f else 0), 2.4, 2.2, CREMA)
    # cabeza grande
    M.elipse(23, 16 - up, 15.0, 11.6, CAFE, rot=rot)
    # hocico crema, nariz y boca
    M.elipse(23, 19.6 - up, 5.0, 3.6, HOCICO, rot=rot)
    M.elipse(23, 17.9 - up, 1.9, 1.0, NARIZ)
    M.curva([(21.2, 20.5 - up), (22.1, 21.4 - up), (23, 20.9 - up), (23.9, 21.4 - up), (24.8, 20.5 - up)], BOCA, ancho=0.8)
    # ojitos tranquilos, bien separados
    for cx in (15.6, 30.4):
        M.elipse(cx, 15.6 - up, 1.4, 1.6, OJO)
        M.rect(cx - 1.0, 14.0 - up, cx, 15.0 - up, BLANCO)
    M.elipse(13.2, 19.2 - up, 1.8, 0.9, MEJILLA)
    M.elipse(32.8, 19.2 - up, 1.8, 0.9, MEJILLA)
