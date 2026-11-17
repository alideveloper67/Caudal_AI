# Bigotes finos (1 px) que cruzan el borde de la cara, como en el personaje.
BIG = '#3a3450'


def retocar(px, f):
    dy = -1 if f else 0
    lineas = [  # (x0, x1, y)
        (1, 3, 14), (4, 8, 15), (1, 8, 18), (4, 8, 21), (1, 3, 22),
        (41, 43, 14), (36, 40, 15), (36, 43, 18), (36, 40, 21), (41, 43, 22)]
    for x0, x1, y in lineas:
        for x in range(x0, x1 + 1):
            px(x, y + dy, BIG)
