# -*- coding: utf-8 -*-
"""Escenarios hechos con las ilustraciones que eligió la persona (en `escenarios_img`). Cada uno solo declara
su imagen y sus efectos, con coordenadas en píxeles de la propia imagen; el motor (imagen_motor.py) hace el
resto: paralaje, interacción con el ratón, golpes de bajo y que todo vaya ligero."""
from .imagen_motor import (Agua, Aura, Brillo, Cascada, Caida, Destellos, EscenarioImagen, Flashes, Humo,
                           Luciernagas, Lluvia, Nubes, Ondas, Rayos, Reflejos, Salpicaduras, Vehiculo, Voladores)


class EscenarioCyberpunk(EscenarioImagen):
    """Neo-Tokio bajo la lluvia (1600×852)."""
    NOMBRE = "Cyberpunk"
    ACENTO = "#05D9E8"
    SEMILLA = 23
    IMAGEN = "cyberpunk.jpg"
    INTERACCION = ("chispa", ("#05D9E8", "#FF2A6D", "#F9F002"))

    def crear_efectos(self):
        return (
            # reflejos de neón sobre el asfalto mojado
            Reflejos(1, rect=(0, 640, 1600, 212), n=90, largo=34, alfa=95,
                     colores=("#FF2A6D", "#05D9E8", "#FFB347", "#B14AED")),
            Salpicaduras(2, rect=(260, 650, 1150, 200), n=22, radio=16),
            # letreros de neón: casi siempre encendidos, con algún parpadeo
            Brillo(3, punto=(90, 270), radio=80, color="#FFC14D", modo="neon", alfa=0.45),
            Brillo(4, punto=(190, 330), radio=70, color="#FF3D8B", modo="neon", alfa=0.5),
            Brillo(5, punto=(190, 405), radio=60, color="#2EE6F0", modo="neon", alfa=0.45),
            Brillo(6, punto=(1430, 230), radio=95, color="#2EE6F0", modo="neon", alfa=0.5),
            Brillo(7, punto=(1350, 425), radio=60, color="#FFC14D", modo="neon", alfa=0.45),
            Brillo(8, punto=(1345, 360), radio=45, color="#FF3D8B", modo="neon", alfa=0.5),
            Brillo(9, punto=(455, 265), radio=120, color="#2EE6F0", modo="neon", alfa=0.25),
            # el koi del holograma y el sol de neón laten con la música
            Brillo(10, punto=(905, 330), radio=170, color="#3FF2E0", modo="musica", banda=6, alfa=0.45),
            Brillo(11, punto=(810, 140), radio=240, color="#FF2A9D", modo="musica", banda=2, alfa=0.30),
            Brillo(12, punto=(1500, 590), radio=70, color="#2EE6F0", modo="respira", alfa=0.35),
            Brillo(13, punto=(105, 515), radio=40, color="#FF4D4D", modo="respira", alfa=0.5),
            Brillo(14, punto=(355, 545), radio=40, color="#FF4D4D", modo="respira", alfa=0.5),
            Brillo(15, punto=(1300, 690), radio=60, color="#FF2A9D", modo="musica", banda=1, alfa=0.45),
            # vapor del puesto de ramen y de la rejilla
            Humo(16, punto=(300, 565), alto=150, ancho=26, tam=26, alfa=0.35, vel=0.14),
            Humo(17, punto=(1478, 470), alto=120, ancho=20, tam=22, alfa=0.30, vel=0.12),
            # coches voladores que cruzan entre las torres
            Vehiculo(18, de=(250, 140), a=(1450, 110), periodo=19, dur=8, color="#7FF5FF"),
            Vehiculo(19, de=(1500, 200), a=(300, 230), periodo=23, dur=10, desfase=9, color="#FF7FD0"),
            Lluvia(20, rect=(0, 0, 1600, 852), n=240, angulo=10, vel=1.1, alfa=60),
            Ondas(21, x0=470, y=790, ancho=660, alto=60),
        )


class EscenarioSamurai(EscenarioImagen):
    """Japón antiguo junto al lago, al atardecer (1600×852)."""
    NOMBRE = "Japón antiguo"
    ACENTO = "#FF7AA8"
    SEMILLA = 21
    IMAGEN = "japon.jpg"
    INTERACCION = ("petalo", ("#FFC2D9", "#F48FB8", "#FFE0EC"))

    def crear_efectos(self):
        return (
            # agua del lago: destellos del atardecer y ondas suaves
            Reflejos(1, rect=(640, 560, 960, 290), n=70, largo=30, alfa=70, colores=("#FFD9B0", "#FFB3D0", "#FFFFFF")),
            Reflejos(2, rect=(430, 395, 640, 70), n=25, largo=18, alfa=55, colores=("#FFD9B0", "#FFFFFF")),
            Agua(3, rect=(900, 600, 680, 230), n=6, radio=46),
            # humo del puesto de comida
            Humo(4, punto=(270, 545), alto=190, ancho=34, tam=30, alfa=0.42, vel=0.12),
            Humo(5, punto=(318, 505), alto=150, ancho=26, tam=24, alfa=0.30, vel=0.10),
            # farolillos y linternas de piedra que respiran
            Brillo(6, punto=(110, 425), radio=55, color="#FFB870", alfa=0.55),
            Brillo(7, punto=(360, 457), radio=45, color="#FFB870", alfa=0.5),
            Brillo(8, punto=(461, 342), radio=34, color="#FFB870", modo="musica", banda=3, alfa=0.55),
            Brillo(9, punto=(511, 368), radio=30, color="#FFB870", modo="musica", banda=6, alfa=0.55),
            Brillo(10, punto=(557, 382), radio=30, color="#FFB870", modo="musica", banda=9, alfa=0.55),
            Brillo(11, punto=(600, 385), radio=30, color="#FFB870", modo="musica", banda=12, alfa=0.55),
            Brillo(12, punto=(636, 380), radio=30, color="#FFB870", modo="musica", banda=15, alfa=0.55),
            Brillo(13, punto=(722, 605), radio=55, color="#FFC888", alfa=0.6),
            Brillo(14, punto=(1080, 368), radio=30, color="#FFC888", alfa=0.5),
            Brillo(15, punto=(1160, 378), radio=26, color="#FFC888", alfa=0.5),
            Brillo(16, punto=(1372, 378), radio=26, color="#FFC888", alfa=0.5),
            Brillo(17, punto=(1205, 568), radio=40, color="#FFC888", alfa=0.6),
            Brillo(18, punto=(650, 178), radio=90, color="#FFB27A", modo="musica", banda=1, alfa=0.35),
            # bruma que pasa entre las colinas
            Nubes(19, rect=(330, 215, 950, 120), n=3, tam=360, alfa=0.22, color="#E8D2F0", vel=0.004),
            # luciérnagas entre los lirios
            Luciernagas(20, rect=(0, 560, 900, 290), n=14, radio=7, color="#E6FFA8"),
            # pétalos y algunas hojas que caen
            Caida(21, rect=(0, -40, 1600, 900), n=50, tipo="petalo", tam=20, vel=0.05, deriva=0.025,
                  colores=("#FFC2D9", "#F48FB8", "#FFE0EC")),
            Caida(22, rect=(0, -40, 1600, 900), n=8, tipo="hoja", tam=15, vel=0.045, deriva=0.03,
                  colores=("#E6A23C", "#B9C46A", "#D9773B")),
            Ondas(23, x0=880, y=760, ancho=640, alto=55, color="#FFB3D0"),
        )


class EscenarioCinnamoroll(EscenarioImagen):
    """Terraza en las nubes (1600×900)."""
    NOMBRE = "Cinnamoroll"
    ACENTO = "#7FB6F2"
    SEMILLA = 31
    IMAGEN = "cinnamoroll.jpg"
    INTERACCION = ("estrella", ("#FFF3A6", "#FFFFFF", "#BFE0FF"))
    VINETA = 35

    def crear_efectos(self):
        return (
            Destellos(1, rect=(540, 20, 1060, 320), n=20, tam=20, color="#FFF6B8"),
            Brillo(2, punto=(1148, 82), radio=110, color="#FFF2B0", alfa=0.40),
            Brillo(3, punto=(623, 268), radio=55, color="#FFE27A", modo="musica", banda=4, alfa=0.6),
            Brillo(4, punto=(522, 350), radio=50, color="#FFE27A", modo="musica", banda=8, alfa=0.6),
            Brillo(5, punto=(1225, 265), radio=140, color="#FFD9F2", alfa=0.25, frec=0.5),
            Humo(6, punto=(1062, 450), alto=90, ancho=12, tam=14, alfa=0.35, vel=0.12),
            Cascada(7, rect=(902, 195, 14, 45), n=6),
            Cascada(8, rect=(1392, 210, 18, 55), n=6),
            Cascada(9, rect=(1466, 395, 18, 60), n=6),
            Nubes(10, rect=(0, 690, 1600, 210), n=4, tam=520, alfa=0.30, color="#FFFFFF", vel=0.005),
            Caida(11, rect=(0, 0, 1600, 900), n=22, tipo="chispa", tam=12, vel=-0.03, deriva=0.01,
                  colores=("#FFF3A6", "#FFFFFF", "#D6E8FF"), voltea=False),
            Ondas(12, x0=330, y=880, ancho=940, alto=50, color="#7FB6F2"),
        )


class EscenarioPompompurin(EscenarioImagen):
    """Cafetería de flan (1600×900)."""
    NOMBRE = "Pompompurin"
    ACENTO = "#E9A23B"
    SEMILLA = 33
    IMAGEN = "pompompurin.jpg"
    INTERACCION = ("flor", ("#FFFFFF", "#FFE69A"))
    VINETA = 45

    def crear_efectos(self):
        return (
            Brillo(1, punto=(200, 140), radio=120, color="#FFD27A", modo="musica", banda=3, alfa=0.45),
            Brillo(2, punto=(375, 140), radio=120, color="#FFD27A", modo="musica", banda=7, alfa=0.45),
            Brillo(3, punto=(1350, 200), radio=260, color="#FFF1B0", alfa=0.30, frec=0.4),
            Luciernagas(4, rect=(1120, 40, 440, 520), n=26, radio=5, color="#FFF4C8", parpadeo=1, alfa=0.7,
                        sube=0.02),
            Caida(5, rect=(1175, 60, 360, 350), n=7, tipo="hoja", tam=14, vel=0.05, deriva=0.02,
                  colores=("#C9C64A", "#E2B33C", "#8FB04A"), recortar=True),
            Humo(6, punto=(355, 670), alto=80, ancho=10, tam=13, alfa=0.35, vel=0.12),
            Humo(7, punto=(1465, 545), alto=80, ancho=10, tam=13, alfa=0.35, vel=0.11),
            Destellos(8, rect=(130, 330, 220, 110), n=6, tam=16, color="#FFFFFF"),
            Ondas(9, x0=470, y=880, ancho=660, alto=45, color="#E9A23B"),
        )


class EscenarioMyMelody(EscenarioImagen):
    """Jardín de rosas con casita (1600×900)."""
    NOMBRE = "My Melody"
    ACENTO = "#F47FAE"
    SEMILLA = 35
    IMAGEN = "mymelody.jpg"
    INTERACCION = ("petalo", ("#FFC2D9", "#F48FB8", "#FFFFFF"))
    VINETA = 40

    def crear_efectos(self):
        return (
            Humo(1, punto=(300, 190), alto=120, ancho=24, tam=22, alfa=0.40, vel=0.09),
            Brillo(2, punto=(493, 445), radio=40, color="#FFD27A", alfa=0.5),
            Humo(3, punto=(1245, 690), alto=70, ancho=10, tam=12, alfa=0.3, vel=0.12),
            Voladores(4, rect=(820, 160, 600, 300), n=2, tipo="mariposa", tam=18, color="#FFE38A"),
            Destellos(5, rect=(250, 80, 1100, 220), n=10, tam=16, color="#FFFFFF"),
            Caida(6, rect=(0, -40, 1600, 940), n=32, tipo="petalo", tam=14, vel=0.045, deriva=0.02,
                  colores=("#FFC2D9", "#F48FB8", "#FFE0EC")),
            Ondas(7, x0=430, y=885, ancho=740, alto=45, color="#F47FAE"),
        )


class EscenarioHelloKitty(EscenarioImagen):
    """Jardín con estanque de corazón (1600×900)."""
    NOMBRE = "Hello Kitty"
    ACENTO = "#F25C8A"
    SEMILLA = 37
    IMAGEN = "hellokitty.jpg"
    INTERACCION = ("corazon", ("#FF7FAE", "#FFC2D9", "#E8295C"))
    VINETA = 40

    def crear_efectos(self):
        return (
            Reflejos(1, rect=(1130, 600, 370, 130), n=24, largo=20, alfa=90, colores=("#FFFFFF", "#FFE0EC")),
            Agua(2, rect=(1180, 610, 280, 100), n=3, radio=30),
            Brillo(3, punto=(1180, 382), radio=40, color="#FFD27A", alfa=0.5),
            Brillo(4, punto=(1347, 382), radio=40, color="#FFD27A", alfa=0.5),
            Humo(5, punto=(1370, 140), alto=110, ancho=22, tam=20, alfa=0.38, vel=0.09),
            Humo(6, punto=(250, 465), alto=70, ancho=10, tam=12, alfa=0.3, vel=0.12),
            Voladores(7, rect=(350, 150, 900, 260), n=2, tipo="mariposa", tam=16, color="#FFFFFF"),
            Caida(8, rect=(0, -40, 1600, 940), n=26, tipo="petalo", tam=14, vel=0.045, deriva=0.02,
                  colores=("#FFC2D9", "#F48FB8", "#FFE0EC")),
            Caida(9, rect=(0, -40, 1600, 940), n=7, tipo="corazon", tam=16, vel=0.035, deriva=0.015,
                  colores=("#FF7FAE", "#FFB3CF"), voltea=False, alfa=0.85),
            Ondas(10, x0=440, y=885, ancho=720, alto=45, color="#F25C8A"),
        )


class EscenarioKuromi(EscenarioImagen):
    """Jardín gótico de noche (1600×900)."""
    NOMBRE = "Kuromi"
    ACENTO = "#B57BFF"
    SEMILLA = 39
    IMAGEN = "kuromi.jpg"
    INTERACCION = ("corazon", ("#B57BFF", "#7A2E8E", "#FF9AD8"))

    def crear_efectos(self):
        return (
            Destellos(1, rect=(0, 0, 1600, 330), n=24, tam=20, color="#FFF0FF"),
            Brillo(2, punto=(1162, 100), radio=130, color="#FFE8C8", alfa=0.35, frec=0.5),
            # los tres corazones laten con la música
            Brillo(3, punto=(722, 150), radio=80, color="#C04CFF", modo="musica", banda=1, alfa=0.55),
            Brillo(4, punto=(855, 157), radio=60, color="#C04CFF", modo="musica", banda=4, alfa=0.55),
            Brillo(5, punto=(790, 240), radio=80, color="#C04CFF", modo="latido", alfa=0.6),
            Brillo(6, punto=(146, 330), radio=55, color="#FFC88A", alfa=0.5),
            Brillo(7, punto=(385, 345), radio=55, color="#FFC88A", alfa=0.5),
            Brillo(8, punto=(1222, 460), radio=50, color="#FFC88A", alfa=0.5),
            Brillo(9, punto=(1556, 432), radio=50, color="#FFC88A", alfa=0.5),
            Destellos(10, rect=(60, 660, 120, 130), n=4, tam=18, color="#E9C6FF"),
            Destellos(11, rect=(1400, 660, 120, 130), n=4, tam=18, color="#E9C6FF"),
            Voladores(12, rect=(300, 120, 1100, 220), n=2, tipo="murcielago", tam=22, color="#1A0F24"),
            Nubes(13, rect=(880, 360, 720, 130), n=2, tam=380, alfa=0.20, color="#D7B8F0", vel=0.004),
            Caida(14, rect=(0, 0, 1600, 900), n=18, tipo="chispa", tam=12, vel=-0.035, deriva=0.01,
                  colores=("#D9A8FF", "#FF9AD8", "#FFFFFF"), voltea=False),
            Ondas(15, x0=420, y=880, ancho=760, alto=50, color="#B57BFF"),
        )


class EscenarioIppo(EscenarioImagen):
    """Hajime no Ippo en el ring, con el público detrás (1672×941). Épico."""
    NOMBRE = "Hajime no Ippo"
    ACENTO = "#FF4B3A"
    SEMILLA = 43
    IMAGEN = "ippo.jpg"
    EPICO = True
    INTERACCION = ("chispa", ("#FFFFFF", "#FFD27A", "#FF6B4A"))

    def crear_efectos(self):
        focos = (152, 285, 420, 580, 912, 1100, 1245, 1375, 1513)
        return tuple(
            Brillo(1 + k, punto=(x, 165), radio=60, color="#FFD08A", modo="musica", banda=1 + 3 * k, alfa=0.55)
            for k, x in enumerate(focos)
        ) + (
            Brillo(20, punto=(225, 318), radio=70, color="#FFB060", alfa=0.35),
            Brillo(21, punto=(435, 318), radio=70, color="#FFB060", alfa=0.35),
            Brillo(22, punto=(1245, 318), radio=70, color="#FFB060", alfa=0.35),
            Brillo(23, punto=(1445, 318), radio=70, color="#FFB060", alfa=0.35),
            Flashes(24, rect=(0, 360, 1672, 380), frec=1.8, radio=24),
            Flashes(25, rect=(0, 180, 1672, 60), frec=0.9, radio=14),
            Luciernagas(26, rect=(0, 0, 1672, 360), n=30, radio=5, color="#FFE6C0", parpadeo=1, alfa=0.5, sube=0.01),
            Caida(27, rect=(660, 260, 400, 420), n=8, tipo="gota", tam=14, vel=0.25, deriva=0.0,
                  colores=("#FFFFFF",), voltea=False, alfa=0.8),
            Brillo(28, punto=(836, 470), radio=520, color="#FF7A4A", modo="latido", alfa=0.22, dureza=0.2),
            Ondas(29, x0=330, y=905, ancho=1010, alto=70, color="#FF4B3A"),
        )


class EscenarioKaneki(EscenarioImagen):
    """Kaneki entre glicinas y lirios (1600×900)."""
    NOMBRE = "Kaneki"
    ACENTO = "#E0245E"
    SEMILLA = 45
    IMAGEN = "kaneki.jpg"
    INTERACCION = ("petalo", ("#C58BFF", "#FF7FC8", "#9B6BFF"))

    def crear_efectos(self):
        return (
            Caida(1, rect=(0, -40, 1600, 940), n=46, tipo="petalo", tam=13, vel=0.04, deriva=0.012,
                  colores=("#C58BFF", "#FF7FC8", "#9B6BFF", "#F2B5FF")),
            Destellos(2, rect=(0, 60, 1600, 800), n=26, tam=16, color="#E9D2FF"),
            Luciernagas(3, rect=(0, 300, 1600, 600), n=20, radio=6, color="#FFB066", sube=0.03, alfa=0.7),
            # el ojo rojo late con la música
            Brillo(4, punto=(786, 192), radio=26, color="#FF2040", modo="musica", banda=1, alfa=0.9, dureza=0.25),
            Brillo(5, punto=(786, 192), radio=70, color="#FF2040", modo="latido", alfa=0.35),
            Ondas(6, x0=400, y=885, ancho=800, alto=50, color="#E0245E"),
        )


class EscenarioGoku(EscenarioImagen):
    """Goku con el aura del instinto superior (1600×900). Épico."""
    NOMBRE = "Goku"
    ACENTO = "#8FD8FF"
    SEMILLA = 47
    IMAGEN = "goku.jpg"
    EPICO = True
    INTERACCION = ("chispa", ("#BFF2FF", "#C79BFF", "#FFFFFF"))

    def crear_efectos(self):
        return (
            Destellos(1, rect=(0, 0, 1600, 900), n=28, tam=18, color="#E6F4FF"),
            Brillo(2, punto=(1385, 92), radio=110, color="#C27BFF", alfa=0.35, frec=0.6),
            Aura(3, rect=(250, 120, 1100, 780), n=60, tam=26, vel=0.5, colores=("#9CE8FF", "#C79BFF", "#FFFFFF")),
            Rayos(4, rects=[(0, 80, 480, 780), (1120, 80, 480, 780), (420, 0, 760, 260)], n=4,
                  colores=("#7FE0FF", "#C38BFF", "#E8F6FF")),
            Brillo(5, punto=(800, 380), radio=520, color="#8FB8FF", modo="latido", alfa=0.25, dureza=0.2),
            Brillo(6, punto=(752, 455), radio=16, color="#E6F4FF", modo="musica", banda=3, alfa=0.8),
            Brillo(7, punto=(848, 455), radio=16, color="#E6F4FF", modo="musica", banda=3, alfa=0.8),
            Ondas(8, x0=300, y=885, ancho=1000, alto=60, color="#8FD8FF"),
        )


class EscenarioLofi(EscenarioImagen):
    """Lo-fi: chica estudiando con el gato en la ventana (1600×896)."""
    NOMBRE = "Lo-fi"
    ACENTO = "#FFB86B"
    SEMILLA = 41
    IMAGEN = "lofi.jpg"
    INTERACCION = ("chispa", ("#FFE2B0", "#FFFFFF"))
    VINETA = 60

    def crear_efectos(self):
        return (
            Brillo(1, punto=(490, 250), radio=200, color="#FFC27A", modo="musica", banda=3, alfa=0.45),
            Luciernagas(2, rect=(360, 260, 380, 460), n=40, radio=5, color="#FFE6C0", parpadeo=1, alfa=0.6,
                        sube=0.015),
            Humo(3, punto=(352, 730), alto=110, ancho=14, tam=16, alfa=0.38, vel=0.11),
            Brillo(4, punto=(65, 635), radio=90, color="#9FD8FF", modo="neon", alfa=0.30),
            Voladores(5, rect=(335, 10, 745, 90), n=2, tipo="murcielago", tam=10, color="#3A2A3A"),
            Ondas(7, x0=335, y=118, ancho=745, alto=40),
        )
