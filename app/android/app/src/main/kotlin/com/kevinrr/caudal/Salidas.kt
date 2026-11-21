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

    /** La traza del ANR o del fallo nativo (tombstone en Android 12+), recortada. */
    private fun traza(info: ApplicationExitInfo): String {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.R) return ""
        return try {
            info.traceInputStream?.use { s ->
                val bytes = ByteArray(64 * 1024)
                val n = s.read(bytes).coerceAtLeast(0)
                val t = String(bytes, 0, n, Charsets.UTF_8)
                // el tombstone en Android 12+ es protobuf: nos quedamos con lo legible
                if (info.reason == ApplicationExitInfo.REASON_CRASH_NATIVE)
                    t.replace(Regex("[^\\x20-\\x7E\\n]+"), " ").replace(Regex(" {2,}"), " ")
                else t
            } ?: ""
        } catch (_: Exception) {
            ""
        }.take(7000)
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
