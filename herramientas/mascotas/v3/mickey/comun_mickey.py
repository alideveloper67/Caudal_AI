# Mickey Mouse (frente, saludando con la mano izquierda del dibujo). Lienzo 46x42.
# Cuadro 0: mano arriba, cola abajo.  Cuadro 1: mano más afuera (vaivén del saludo), cuerpo 1 px arriba, cola levantada.
NEGRO = '#26262f'      # cabeza, cuerpo, brazos, piernas
NEGRO_O = '#26262e'    # orejas (casi igual: línea fina contra la cabeza)
NEGRO_B = '#27262f'    # brazos delante del cuerpo
BRILLO = '#62627a'     # reflejo de orejas y nariz
PIEL = '#f6c9a0'
OJO_B = '#ffffff'
PUPILA = '#14141c'
NARIZ = '#121218'
BOCA = '#6a1a22'
LENGUA = '#ec6a78'
MEJILLA = '#f39a8a'
ROJO = '#e0242e'
BOTON = '#ffd23a'
GUANTE = '#fbfbff'
ZAPATO = '#f5c21a'
ZAPATO_B = '#f5c21b'


def pose(M, f):
    up = 1 if f else 0
    # cola fina (detrás de todo)
    if f == 0:
        M.curva([(29, 34), (35, 36.5), (39.5, 35), (41, 31.5)], NEGRO, ancho=1.0)
    else:
        M.curva([(29, 33), (35, 34), (39.5, 31), (40, 27)], NEGRO, ancho=1.0)
    # brazo que saluda (detrás de la cabeza no; sale del hombro izquierdo)
    if f == 0:
        M.curva([(18, 28 - up), (12.5, 25), (8.5, 20)], NEGRO_B, ancho=2.2)
        gx, gy, rot = 7.2, 16.0, -15
    else:
        M.curva([(18, 28 - up), (12, 26), (6.8, 22.5)], NEGRO_B, ancho=2.2)
        gx, gy, rot = 4.6, 18.6, -40
    # piernas y zapatones
    M.capsula(19.5, 35, 18.5, 38.5, 1.2, NEGRO)
    M.capsula(26.5, 35, 27.5, 38.5, 1.2, NEGRO)
    M.elipse(14.8, 39.2, 5.9, 2.9, ZAPATO, rot=-6)
    M.elipse(31.2, 39.2, 5.9, 2.9, ZAPATO_B, rot=6)
    # torso y pantalón rojo con dos botones
    M.elipse(23, 29.5 - up, 6.5, 5.0, NEGRO)
    M.blob([(15.5, 31 - up), (23, 30 - up), (30.5, 31 - up), (30, 35.5 - up), (23, 36.5 - up), (16, 35.5 - up)], ROJO)
    M.elipse(20.5, 33.0 - up, 1.0, 1.0, BOTON)
    M.elipse(25.5, 33.0 - up, 1.0, 1.0, BOTON)
    # brazo derecho bajando a la cadera, guante blanco
    M.curva([(28.5, 27.5 - up), (32.5, 30 - up), (34, 32 - up)], NEGRO_B, ancho=2.2)
    M.elipse(35.3, 32.6 - up, 3.0, 2.7, GUANTE, rot=20)
    # guante que saluda (mano abierta: palma + pulgar)
    M.elipse(gx, gy - up, 3.2, 3.6, GUANTE, rot=rot)
    M.elipse(gx + 2.6, gy + 1.2 - up, 1.3, 1.0, GUANTE, rot=rot)
    # orejas redondas
    M.elipse(10.0, 7.0 - up, 6.0, 5.8, NEGRO_O)
    M.elipse(36.0, 7.0 - up, 6.0, 5.8, NEGRO_O)
    M.curva([(6.0, 6.8 - up), (8.0, 4.0 - up)], BRILLO, ancho=0.9, suave=False)
    M.curva([(32.0, 6.8 - up), (34.0, 4.0 - up)], BRILLO, ancho=0.9, suave=False)
    # cabeza
    M.elipse(23, 17.0 - up, 11.0, 10.2, NEGRO)
    # cara: dos lóbulos de los ojos + mandíbula ancha
    M.elipse(19.6, 15.0 - up, 3.9, 5.9, PIEL)
    M.elipse(26.4, 15.0 - up, 3.9, 5.9, PIEL)
    M.blob([(13.2, 19 - up), (18, 17 - up), (23, 17.5 - up), (28, 17 - up), (32.8, 19 - up), (31, 24.5 - up), (23, 27 - up), (15, 24.5 - up)], PIEL)
    # ojos: blanco ovalado con pupila abajo y brillo
    for cx in (20.0, 26.0):
        M.elipse(cx, 14.0 - up, 1.9, 3.6, OJO_B)
        M.elipse(cx + 0.3, 15.4 - up, 1.4, 2.3, PUPILA)
        M.punto(cx - 0.2, 14.5 - up, OJO_B, r=0.5)
    # mejillas
    M.elipse(16.0, 21.5 - up, 1.5, 0.8, MEJILLA)
    M.elipse(30.0, 21.5 - up, 1.5, 0.8, MEJILLA)
    # boca sonriente abierta con lengua
    M.blob([(18.8, 21.4 - up), (23, 22.2 - up), (27.2, 21.4 - up), (26.0, 24.4 - up), (23, 25.4 - up), (20.0, 24.4 - up)], BOCA)
    M.elipse(23, 24.5 - up, 1.7, 0.8, LENGUA)
    # nariz negra con brillo
    M.elipse(23, 19.6 - up, 2.1, 1.4, NARIZ)
    M.punto(22.2, 19.0 - up, BRILLO, r=0.5)
