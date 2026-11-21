package com.kevinrr.caudal

import android.app.ActivityManager
import android.app.ApplicationExitInfo
import android.content.Context
import android.os.Build
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import java.io.File

/**
 * Por qué se cerró Caudal la vez anterior.
 *
 * Los informes de errores de Dart no ven los cierres que pasan por debajo: un fallo nativo del
 * motor de sonido, Android matando la app por memoria, una traba (ANR) o el ahorro de batería
 * del fabricante (Samsung, Xiaomi, Huawei...) apagándola con la música sonando. Android 11+ guarda
 * la causa de cada salida (ApplicationExitInfo); aquí se leen las que aún no se informaron y la
 * app las manda a la nube como un error más (nucleo/salidas_android.dart).
 *
 * Además se anota si la música sonaba en ese momento (Energia.kt marca «sonando»), para saber
 * cuándo un cierre cortó una canción, y se guarda la traza de los fallos de Java/Kotlin.
 */
object Salidas {
    private const val PREFS = "caudal_salidas"
    private const val CLAVE_VISTO = "ultima_vista"
    private const val CLAVE_SONANDO = "sonando"
    private const val CLAVE_SONANDO_DESDE = "sonando_desde"
    private const val ARCHIVO_JAVA = "ultimo_fallo_java.txt"

    private var instalado = false

    private fun prefs(c: Context) = c.applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    /** Lo llama Energia al empezar y al dejar de sonar. */
    fun anotarSonando(c: Context, si: Boolean) {
        try {
            prefs(c).edit().putBoolean(CLAVE_SONANDO, si)
                .putLong(CLAVE_SONANDO_DESDE, if (si) System.currentTimeMillis() else 0L).apply()
        } catch (_: Exception) {
        }
    }

    /** Guarda la traza de un fallo de Java/Kotlin antes de que la app muera (y deja seguir al de siempre). */
    fun instalarCapturaJava(c: Context) {
        if (instalado) return
        instalado = true
        val app = c.applicationContext
        val anterior = Thread.getDefaultUncaughtExceptionHandler()
        Thread.setDefaultUncaughtExceptionHandler { hilo, e ->
            try {
                val texto = "hilo ${hilo.name}\n" + android.util.Log.getStackTraceString(e)
                File(app.filesDir, ARCHIVO_JAVA).writeText(texto.take(8000))
            } catch (_: Throwable) {
            }
            anterior?.uncaughtException(hilo, e)
        }
    }

    private fun motivo(r: Int): String = when (r) {
        ApplicationExitInfo.REASON_ANR -> "anr"
        ApplicationExitInfo.REASON_CRASH -> "fallo_java"
        ApplicationExitInfo.REASON_CRASH_NATIVE -> "fallo_nativo"
        ApplicationExitInfo.REASON_DEPENDENCY_DIED -> "dependencia"
        ApplicationExitInfo.REASON_EXCESSIVE_RESOURCE_USAGE -> "exceso_recursos"
        ApplicationExitInfo.REASON_EXIT_SELF -> "salida_propia"
        ApplicationExitInfo.REASON_INITIALIZATION_FAILURE -> "fallo_arranque"
        ApplicationExitInfo.REASON_LOW_MEMORY -> "poca_memoria"
        ApplicationExitInfo.REASON_OTHER -> "sistema"
        ApplicationExitInfo.REASON_PERMISSION_CHANGE -> "permiso"
        ApplicationExitInfo.REASON_SIGNALED -> "senal"
        ApplicationExitInfo.REASON_USER_REQUESTED -> "usuario"
        ApplicationExitInfo.REASON_USER_STOPPED -> "usuario_detuvo"
        10 -> "paquete_actualizado" // REASON_PACKAGE_UPDATED (API 33)
        11 -> "estado_paquete" // REASON_PACKAGE_STATE_CHANGE
        14 -> "congelada" // REASON_FREEZER (API 34)
        else -> "desconocido_$r"
    }

    private fun importancia(i: Int): String = when {
        i <= ActivityManager.RunningAppProcessInfo.IMPORTANCE_FOREGROUND -> "en_pantalla"
        i <= ActivityManager.RunningAppProcessInfo.IMPORTANCE_FOREGROUND_SERVICE -> "servicio_musica"
        i <= ActivityManager.RunningAppProcessInfo.IMPORTANCE_VISIBLE -> "visible"
        i <= ActivityManager.RunningAppProcessInfo.IMPORTANCE_PERCEPTIBLE -> "perceptible"
        i <= ActivityManager.RunningAppProcessInfo.IMPORTANCE_SERVICE -> "servicio"
        i <= ActivityManager.RunningAppProcessInfo.IMPORTANCE_CACHED -> "en_segundo_plano"
        else -> "ninguna"
    }

    /** Librerías y nombres que dicen QUÉ cayó (lo demás de un tombstone son hilos esperando). */
    private val CLAVES = Regex(
        "libmpv|libav(codec|format|util|filter|device)|libsw(resample|scale)|libffmpegkit|libmediakit|" +
            "libflutter|libapp\\.so|libc\\+\\+_shared|CodecLooper|MediaCodec|AudioTrack|Abort message|Scudo|abort"
    )

    /**
     * Lo útil de un tombstone (Android 12+ lo da en protobuf): la cabecera (señal, mensaje de aborto,
     * hilo que cayó) y los trozos donde aparecen nuestras librerías, sin los cientos de hilos que
     * solo esperaban (antes se cortaba a 7000 caracteres y la causa quedaba fuera).
     */
    private fun resumenNativo(crudo: String): String {
        val t = crudo.replace(Regex("[^\\x20-\\x7E\\n]+"), " ").replace(Regex("[ \\n]{2,}"), " ")
        val cabecera = t.take(900)
        val trozos = LinkedHashSet<String>()
        for (m in CLAVES.findAll(t)) {
            if (m.range.first < 900) continue
            val ini = (m.range.first - 160).coerceAtLeast(0)
            val fin = (m.range.last + 60).coerceAtMost(t.length)
            trozos.add(t.substring(ini, fin).trim())
            if (trozos.size >= 30) break
        }
        return (cabecera + if (trozos.isEmpty()) "" else "\n--- marcos con librerías ---\n" + trozos.joinToString("\n…\n"))
            .take(7000)
    }

    /** La traza del ANR o del fallo nativo (tombstone en Android 12+), recortada a lo útil. */
    private fun traza(info: ApplicationExitInfo): String {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.R) return ""
        return try {
            info.traceInputStream?.use { s ->
                // el tombstone entero (hasta 1 MB): la causa puede estar lejos del principio
                val t = String(s.readBytes().let { if (it.size > 1_048_576) it.copyOf(1_048_576) else it }, Charsets.UTF_8)
                if (info.reason == ApplicationExitInfo.REASON_CRASH_NATIVE) resumenNativo(t) else t.take(7000)
            } ?: ""
        } catch (_: Throwable) {
            ""
        }
    }

    /**
     * Los fallos nativos del proceso principal desde que se instaló esta versión (no se marcan
     * como vistos: es para elegir el motor al abrir, ver motor_eleccion.dart). Los de antes de
     * actualizar no cuentan: son de otra versión, que puede ser justo la que fallaba.
     */
    fun fallosNativos(c: Context): List<Map<String, Any?>> {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.R) return emptyList()
        val app = c.applicationContext
        val desde = try {
            app.packageManager.getPackageInfo(app.packageName, 0).lastUpdateTime
        } catch (_: Exception) {
            0L
        }
        val am = app.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
        val lista = try {
            am.getHistoricalProcessExitReasons(app.packageName, 0, 16)
        } catch (_: Exception) {
            emptyList()
        }
        return lista.filter {
            it.processName == app.packageName && it.reason == ApplicationExitInfo.REASON_CRASH_NATIVE &&
                it.timestamp > desde
        }.map { mapOf("cuando" to it.timestamp, "texto" to traza(it)) }
    }

    /**
     * Cómo terminó la vez anterior el proceso principal (sin marcarla como vista): lo usa el
     * diagnóstico del arranque para no llamar «traba» a lo que fue un cierre del motor o a la
     * persona cerrando la app antes de que terminara de abrir.
     */
    fun ultimaSalida(c: Context): Map<String, Any?>? {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.R) return null
        val app = c.applicationContext
        val am = app.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
        val info = try {
            am.getHistoricalProcessExitReasons(app.packageName, 0, 8)
                .filter { it.processName == app.packageName }.maxByOrNull { it.timestamp }
        } catch (_: Exception) {
            null
        } ?: return null
        return mapOf(
            "motivo" to motivo(info.reason),
            "importancia" to importancia(info.importance),
            "cuando" to info.timestamp,
            "texto" to if (info.reason == ApplicationExitInfo.REASON_CRASH_NATIVE) traza(info) else "",
        )
    }

    /** Cómo va el proceso: mapas de memoria, hilos y memoria residente (lo mira vigia_proceso.dart). */
    fun proceso(): Map<String, Any?> {
        var hilos = -1
        var rssKb = -1L
        try {
            File("/proc/self/status").forEachLine { l ->
                when {
                    l.startsWith("Threads:") -> hilos = l.substringAfter(':').trim().toIntOrNull() ?: -1
                    l.startsWith("VmRSS:") -> rssKb = l.substringAfter(':').trim().substringBefore(' ').toLongOrNull() ?: -1L
                }
            }
        } catch (_: Exception) {
        }
        var mapas = -1
        try {
            var n = 0
            File("/proc/self/maps").bufferedReader().use { r -> while (r.readLine() != null) n++ }
            mapas = n
        } catch (_: Exception) {
        }
        return mapOf("mapas" to mapas, "hilos" to hilos, "rss_kb" to rssKb)
    }

    /**
     * Las salidas nuevas desde la última vez (de la más vieja a la más nueva). Después de leerlas
     * quedan marcadas: no se vuelven a mandar.
     */
    fun nuevas(c: Context): List<Map<String, Any?>> {
        val app = c.applicationContext
        val p = prefs(app)
        val sonaba = p.getBoolean(CLAVE_SONANDO, false)
        val sonabaDesde = p.getLong(CLAVE_SONANDO_DESDE, 0L)
        // al arrancar de nuevo, la marca de la vez anterior ya se usó
        p.edit().putBoolean(CLAVE_SONANDO, false).putLong(CLAVE_SONANDO_DESDE, 0L).apply()
        val java = try {
            val f = File(app.filesDir, ARCHIVO_JAVA)
            if (f.exists()) f.readText().also { f.delete() } else ""
        } catch (_: Exception) {
            ""
        }
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.R) {
            if (java.isEmpty()) return emptyList()
            return listOf(mapOf("motivo" to "fallo_java", "descripcion" to "", "importancia" to "",
                "cuando" to System.currentTimeMillis(), "memoria_kb" to 0L, "sonaba" to sonaba,
                "minutos_sonando" to 0L, "traza" to java))
        }
        val visto = p.getLong(CLAVE_VISTO, 0L)
        val am = app.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
        val lista = try {
            am.getHistoricalProcessExitReasons(app.packageName, 0, 12)
        } catch (_: Exception) {
            emptyList()
        }
        val salida = mutableListOf<Map<String, Any?>>()
        var masNueva = visto
        var javaUsada = false
        // primera vez con este módulo: no se manda la historia vieja, solo se marca
        val primera = visto == 0L
        val ultimaPrincipal = lista.filter { it.processName == app.packageName }.maxByOrNull { it.timestamp }
        for (info in lista.sortedBy { it.timestamp }) {
            if (info.timestamp <= visto) continue
            masNueva = maxOf(masNueva, info.timestamp)
            if (primera) continue
            // del proceso principal; los demás (p. ej. :despertador) no cuentan
            if (info.processName != app.packageName) continue
            val m = motivo(info.reason)
            var t = traza(info)
            if (info.reason == ApplicationExitInfo.REASON_CRASH && java.isNotEmpty() && !javaUsada) {
                t = java
                javaUsada = true
            }
            val esUltima = info == ultimaPrincipal
            salida.add(mapOf(
                "motivo" to m,
                "descripcion" to (info.description ?: ""),
                "importancia" to importancia(info.importance),
                "cuando" to info.timestamp,
                "memoria_kb" to info.pss,
                "rss_kb" to info.rss,
                "estado" to info.status,
                // solo la última salida sabe si sonaba (la marca es de esa vida del proceso)
                "sonaba" to (esUltima && sonaba),
                "minutos_sonando" to if (esUltima && sonaba && sonabaDesde > 0)
                    ((info.timestamp - sonabaDesde) / 60000L).coerceAtLeast(0L) else 0L,
                "traza" to t,
            ))
        }
        if (masNueva > visto) p.edit().putLong(CLAVE_VISTO, masNueva).apply()
        return salida
    }

    fun registrar(motor: FlutterEngine, contexto: Context) {
        val app = contexto.applicationContext
        MethodChannel(motor.dartExecutor.binaryMessenger, "caudal/salidas").setMethodCallHandler { llamada, resultado ->
            when (llamada.method) {
                "nuevas" -> try {
                    resultado.success(nuevas(app))
                } catch (e: Exception) {
                    resultado.success(emptyList<Map<String, Any?>>())
                }
                // fuera del hilo principal: leer tombstones y /proc puede tardar
                "fallosNativos" -> Thread {
                    val r = try { fallosNativos(app) } catch (_: Throwable) { emptyList() }
                    android.os.Handler(android.os.Looper.getMainLooper()).post { resultado.success(r) }
                }.start()
                "ultimaSalida" -> Thread {
                    val r = try { ultimaSalida(app) } catch (_: Throwable) { null }
                    android.os.Handler(android.os.Looper.getMainLooper()).post { resultado.success(r) }
                }.start()
                "proceso" -> Thread {
                    val r = try { proceso() } catch (_: Throwable) { null }
                    android.os.Handler(android.os.Looper.getMainLooper()).post { resultado.success(r) }
                }.start()
                "memoria" -> try {
                    val am = app.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
                    val mi = ActivityManager.MemoryInfo()
                    am.getMemoryInfo(mi)
                    resultado.success(mapOf(
                        "total_mb" to mi.totalMem / (1024 * 1024),
                        "libre_mb" to mi.availMem / (1024 * 1024),
                        "baja" to mi.lowMemory,
                        "clase_mb" to am.memoryClass,
                        "ram_baja" to am.isLowRamDevice,
                    ))
                } catch (e: Exception) {
                    resultado.success(null)
                }
                else -> resultado.notImplemented()
            }
        }
    }
}
