# Nyan Cat de perfil volando a la derecha (sin arcoíris: lo dibuja la app). Lienzo 54x42 (cuadro 56x44).
# Cuadro 0: patitas adelante, cola arriba.  Cuadro 1: patitas atrás, cola abajo, cabeza 1 px arriba.
GALLETA = '#f8cf9a'
GLASEADO = '#ff9ee0'
GRIS = '#9c9ca6'       # cabeza
GRIS_P = '#9c9ca7'     # patitas y cola (casi igual: línea fina contra la cabeza y la galleta)
OJO = '#1c1c26'
BLANCO = '#ffffff'
MEJILLA = '#ff8fa8'
BOCA = '#3a2a36'
LINEA = '#46465a'
PUNTOS = ['#e8308a', '#e8308a', '#ffd23a', '#e8308a', '#4ac8f0', '#e8308a', '#e8308a', '#ffd23a',
          '#e8308a', '#4ac8f0', '#e8308a', '#e8308a', '#e8308a', '#4ac8f0', '#e8308a']
SITIOS = [(15.5, 12), (21, 11), (28, 12.5), (33, 11), (17.5, 17), (24.5, 16.5), (30.5, 17.5),
          (14.5, 22.5), (21.5, 21.5), (27, 23), (17.5, 27.5), (24, 27), (14, 17.5), (28.5, 26.5), (25, 8.5)]


def pose(M, f):
    hu = 1 if f else 0
    # cola (detrás)
    if f == 0:
        M.curva([(11, 25), (6.5, 25), (3.5, 22.5), (3, 18.5)], GRIS_P, ancho=2.6)
    else:
        M.curva([(11, 25), (7, 26.5), (4, 28.5), (2.5, 31.5)], GRIS_P, ancho=2.6)
    # patitas (detrás de la galleta y la cabeza)
    pat = [(12.5, 33.5), (18, 34), (34, 33.5), (40, 34)] if f == 0 else [(10.5, 33), (16, 33.5), (36, 33), (42, 33.5)]
    for x, y in pat:
        M.elipse(x, y, 2.1, 2.2, GRIS_P)
    # galleta con borde crema y glaseado rosa
    M.rect(9, 6, 39, 33, GALLETA, radio=3.5)
    M.rect(11.8, 8.8, 36.2, 30.2, GLASEADO, radio=3.5)
    for (x, y), c in zip(SITIOS, PUNTOS):
        M.rect(x - 0.6, y - 0.5, x + 0.6, y + 0.5, c)
    # cabeza gris con orejas
    cy = 24 - hu
    for dx, col in ((-1.0, LINEA), (0.0, GRIS)):         # copia corrida a la izquierda = línea fina contra la galleta
        M.blob([(33.2 + dx, 20 - hu), (34.6 + dx, 11.2 - hu), (40.5 + dx, 16.8 - hu)], col)
        M.blob([(43.5 + dx, 16.8 - hu), (49.4 + dx, 11.2 - hu), (50.8 + dx, 20 - hu)], col)
        M.elipse(42 + dx, cy, 10.2, 7.6, col)
    # cara
    for x in (37.8, 46.2):
        M.elipse(x, cy - 1.2, 1.3, 1.7, OJO)
        M.rect(x - 1.0, cy - 2.6, x, cy - 1.6, BLANCO)
    M.elipse(35.2, cy + 2.2, 1.6, 0.9, MEJILLA)
    M.elipse(48.8, cy + 2.2, 1.6, 0.9, MEJILLA)
    M.punto(42, cy + 0.6, BOCA, r=0.55)
    M.curva([(39.6, cy + 1.8), (40.8, cy + 2.9), (42, cy + 2.0), (43.2, cy + 2.9), (44.4, cy + 1.8)], BOCA, ancho=0.9)
