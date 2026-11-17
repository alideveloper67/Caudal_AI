# Maestro de Nailong (dragoncito amarillo regordete, 3/4 hacia la derecha). Lienzo 46x42.
# f = cuadro: 0 de pie con la manito levantada; 1 saluda más alto, cola arriba, parpadeo feliz y cuerpo 1 px arriba.
AMA = '#fcd34e'       # cuerpo y cabeza
AMA_B = '#fcd34f'     # brazos y patas (línea interior)
BARBILLA = '#e6a42c'  # pliegue bajo la cabeza
CUERNO = '#ffe9a0'    # cuernitos (crema, línea interior)
COLA = '#fcd44e'      # cola (línea interior)
PANZA = '#fff2b6'
OJO = '#1c1a22'
BRILLO = '#ffffff'
MEJILLA = '#f7a08e'
BOCA = '#8a2a2a'
LENGUA = '#f27a7a'


def pose(M, f):
    up = 1 if f else 0
    # cola corta redondeada (detrás, a la derecha)
    ct = 2.0 if f else 0
    M.elipse(39.5, 33.0 - ct, 5.0, 3.6, COLA, rot=-30 - ct * 8)
    # cuernitos cortos y redondeados
    hy = 15.5 - up
    M.elipse(19.4, hy - 11.6, 1.9, 2.6, CUERNO, rot=-18)
    M.elipse(28.0, hy - 11.8, 1.9, 2.6, CUERNO, rot=18)
    # cuerpo regordete
    M.elipse(23.5, 31.5 - up, 13.0, 9.6, AMA)
    M.elipse(24.6, 32.5 - up, 8.6, 7.0, PANZA)
    # patas
    M.elipse(16.0, 39.4, 4.6, 2.5, AMA_B)
    M.elipse(31.5, 39.6, 4.8, 2.5, AMA_B)
    # brazo derecho bajado, delante
    M.elipse(35.6, 30.5 - up, 2.8, 4.0, AMA_B, rot=-30)
    # cabeza redonda y ancha
    M.elipse(23.5, hy + 0.3, 17.4, 12.2, AMA)
    # pliegue de la barbilla
    M.curva([(12.5, hy + 9.6), (18.0, hy + 11.8), (24.0, hy + 12.5), (30.0, hy + 11.8), (34.5, hy + 9.8)], BARBILLA, ancho=1.1)
    # brazo izquierdo saludando (delante del cuerpo, al lado de la cabeza)
    if f == 0:
        M.capsula(12.0, 30.0 - up, 6.5, 27.0 - up, 2.5, AMA_B)
        M.elipse(5.6, 26.4 - up, 2.8, 2.7, AMA_B)
    else:
        M.capsula(12.0, 30.0 - up, 5.8, 24.0 - up, 2.5, AMA_B)
        M.elipse(5.2, 23.0 - up, 2.8, 2.7, AMA_B)
    # ojitos negros pequeños y separados (en el cuadro 1 cerrados de felicidad: ^ ^)
    for cx in (16.4, 30.6):
        if f == 0:
            M.elipse(cx, hy + 0.6, 1.75, 2.35, OJO)
            M.punto(cx - 0.4, hy - 0.4, BRILLO, r=0.45)
        else:
            M.curva([(cx - 1.8, hy + 1.4), (cx, hy - 0.2), (cx + 1.8, hy + 1.4)], OJO, ancho=1.0, suave=False)
    # mejillas
    M.elipse(12.4, hy + 4.4, 2.4, 1.2, MEJILLA)
    M.elipse(34.6, hy + 4.4, 2.4, 1.2, MEJILLA)
    # boquita abierta y alegre
    M.blob([(20.6, hy + 3.6), (23.5, hy + 3.8), (26.4, hy + 3.6), (25.8, hy + 5.8), (23.5, hy + 7.0), (21.2, hy + 5.8)], BOCA)
    M.elipse(23.5, hy + 6.0, 1.5, 0.9, LENGUA)
