# Plan de rendimiento de Caudal (Windows 2.4.3 · Android 2.3.3)

Objetivo: que Caudal no se trabe nunca y gaste menos CPU, memoria y batería, **sin perder calidad**
(mismo audio, mismas animaciones a la vista, misma resolución de video elegida).

Medido el 16/11/2026 en la PC del dueño (Caudal Escritorio 2.4.2 en reposo): **651 MB** de memoria
(856 MB privados), **84 hilos**, 1 700 handles y **33 % de un núcleo** sin parar.

## Lo que traba hoy (con evidencia)

| Problema | Dónde | Efecto |
|---|---|---|
| Conexiones lambda que no se sueltan: cada cambio de canción lanza decenas de errores que se escriben a disco en el hilo de la interfaz | `componentes.py:1208`, `letra_viva.py:241` | **Confirmado en `fallos.log`: 113 errores en un segundo**, ~8 000 en total |
| La sincronización abre una transacción y espera a la red con la base bloqueada | `sincronizacion.py:362-471` | La interfaz espera hasta 5 s, cada 3 min |
| El progreso de descargas sin freno | `motor.py:454` | Cientos de avisos por segundo al hilo de la interfaz |
| Posición del reproductor sin freno (escritorio y móvil) | `reproduccion.py:279`, `reproductor.dart:1123` | Decenas de repintados/reconstrucciones por segundo |
| Inicio, Biblioteca y páginas ocultas recalculan todo (40 000 escuchas, listas enteras para 4 portadas) | `inicio.py`, `biblioteca.dart`, `coleccion.py` | Tirones al arrancar y con cada «me gusta» |
| Portadas a 544 px escaladas en el hilo de la interfaz, cachés de ~280 MB | `ui/imagenes.py` | CPU y memoria |
| Animaciones a 60 fps aunque no se vean (letra, vinilo, mascota, fondo) | `letra_viva.py`, `vinilo.py`, `fondo_capa.py`, `vinilo.dart`, `fondo_ambiente.dart` | CPU/GPU continuos |
| Cachés de mpv de 200 MiB por motor (hasta 4 motores) | `reproduccion.py:240` | Hasta ~1 GB |
| Móvil: sondeos que no se pausan en segundo plano, navegador oculto siempre vivo, notificación de música cada segundo | `sincronizacion.dart`, `main.dart:233`, `servicio_audio.dart:224` | Batería y memoria |

## Qué se aplica en esta versión

**Escritorio**
1. Señales con métodos ligados (se sueltan solas al cerrar la fila/letra).
2. Sincronización: primero la red, después una escritura corta; guardar la sesión fuera del hilo de la interfaz; cada 10 min y al volver a la ventana.
3. Progreso de descargas a 4 avisos/s como máximo y conteo agrupado.
4. Posición del reproductor a ~5 avisos/s (la letra ya interpola sola); el deslizador solo repinta si cambia un píxel.
5. Catálogo de mascotas leído una vez; el temporizador de la mascota se para con la ventana oculta.
6. Inicio y Resumen sin SQL pesado en la interfaz (`LIMIT`, segundo plano, caché del día).
7. Páginas ocultas: se marcan «pendientes» y se recargan al volver a verse; conteos del panel con `COUNT(*)`.
8. Portadas: decodificar, recortar y escalar en segundo plano y a menor tamaño; topes de caché más bajos.
9. Letra viva y vinilo a fps adaptativos (fluidos en las transiciones, tranquilos en reposo, quietos en pausa o con la ventana minimizada); el vinilo repinta solo su zona; la capa de fondo se compone una vez.
10. Sin resolver el video de cada canción «por si acaso»; caché de mpv para audio 32/16 MiB.
11. Cachés con tope, una `requests.Session` reutilizada, y la ventana se muestra antes de las comprobaciones de red del arranque.

**Android**
1. Posición del reproductor frenada (~4/s; 1/s en segundo plano) y textos de tiempo separados.
2. Notificación de música solo cuando cambia algo de verdad.
3. Biblioteca: portadas por SQL con `LIMIT`, sin recargar cada minuto, pausa en segundo plano.
4. Sincronización cada 10–15 min, solo en primer plano, decodificación en un isolate.
5. Desenfoques horneados una vez (modo ambiente y Fondo de Caudal).
6. Navegador oculto bajo demanda y liberado tras no usarse.
7. Inicio y gusto calculados en un isolate, con una sola lectura del historial y caché del día.
8. Vinilo: solo gira la etiqueta; pantalla encendida solo mientras suena.
9. Sondeos de chat/listas pausados en segundo plano o con la pantalla oculta.
10. Respuestas grandes de YouTube Music decodificadas en un isolate; portadas de género en disco.

## Lo que queda para después (más grande)
Listas virtualizadas en el escritorio (`QListView` + delegado), sincronización incremental por fecha,
análisis de audio en tabla propia.

## Cómo se comprueba
Pruebas de todos los módulos que tocan los cambios (escritorio ~270, móvil ~800), y medición antes/después
de CPU y memoria con la app quieta y sonando.
