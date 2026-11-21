package com.kevinrr.caudal

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.net.wifi.WifiManager
import android.os.Build
import android.os.PowerManager
import android.provider.Settings
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

/**
 * Mantiene despierto el CPU y el wifi mientras suena la musica, para que con la
 * pantalla apagada (reposo) la cancion siguiente se abra a tiempo. Sin esto,
 * Android duerme la red y los temporizadores de la app y la musica se queda
 * parada al terminar cada cancion hasta que se enciende la pantalla.
 *
 * Vive a nivel de aplicacion (no de la actividad): sigue funcionando aunque la
 * actividad se cierre y solo queda el servicio de audio.
 */
object Energia {
    private var cpu: PowerManager.WakeLock? = null
    private var wifi: WifiManager.WifiLock? = null

    @Synchronized
    fun mantener(contexto: Context, si: Boolean) {
        val app = contexto.applicationContext
        // si la app muere mientras suena, el informe lo dirá (Salidas.kt)
        Salidas.anotarSonando(app, si)
        if (si) {
            try {
                if (cpu == null) {
                    val pm = app.getSystemService(Context.POWER_SERVICE) as PowerManager
                    cpu = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "Caudal::musica").apply {
                        setReferenceCounted(false)
                    }
                }
                // con tope por si la app muere sin soltarlo: se renueva mientras siga sonando
                if (cpu?.isHeld != true) cpu?.acquire(4 * 60 * 60 * 1000L)
                else {
                    cpu?.release()
                    cpu?.acquire(4 * 60 * 60 * 1000L)
                }
            } catch (_: Exception) {
            }
            try {
                if (wifi == null) {
                    val wm = app.getSystemService(Context.WIFI_SERVICE) as WifiManager
                    val modo = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q)
                        WifiManager.WIFI_MODE_FULL_LOW_LATENCY else WifiManager.WIFI_MODE_FULL_HIGH_PERF
                    wifi = wm.createWifiLock(modo, "Caudal::musica").apply { setReferenceCounted(false) }
                }
                if (wifi?.isHeld != true) wifi?.acquire()
            } catch (_: Exception) {
            }
        } else {
            try {
                if (cpu?.isHeld == true) cpu?.release()
            } catch (_: Exception) {
            }
            try {
                if (wifi?.isHeld == true) wifi?.release()
            } catch (_: Exception) {
            }
        }
    }

    private fun sinRestriccion(contexto: Context): Boolean {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.M) return true
        val pm = contexto.getSystemService(Context.POWER_SERVICE) as PowerManager
        return pm.isIgnoringBatteryOptimizations(contexto.packageName)
    }

    /** Abre la pantalla del sistema donde se quita el ahorro de bateria a Caudal. */
    private fun abrirAjusteBateria(contexto: Context) {
        val intentos = listOf(
            Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS),
            Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:${contexto.packageName}")),
        )
        for (i in intentos) {
            try {
                i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                contexto.startActivity(i)
                return
            } catch (_: Exception) {
            }
        }
    }

    /**
     * La pregunta directa del sistema («¿Permitir que Caudal se ejecute siempre en segundo plano?»).
     * Solo la versión directa lleva el permiso; sin él (o si el teléfono no la tiene) se abre el ajuste.
     */
    private fun pedirSinRestriccion(contexto: Context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M && !sinRestriccion(contexto)) {
            try {
                val permiso = contexto.packageManager.checkPermission(
                    android.Manifest.permission.REQUEST_IGNORE_BATTERY_OPTIMIZATIONS, contexto.packageName)
                if (permiso == android.content.pm.PackageManager.PERMISSION_GRANTED) {
                    val i = Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS,
                        Uri.parse("package:${contexto.packageName}"))
                    i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                    contexto.startActivity(i)
                    return
                }
            } catch (_: Exception) {
            }
        }
        abrirAjusteBateria(contexto)
    }

    /** El fabricante, para dar los pasos de su menú (Samsung tiene además «Apps en suspensión»). */
    private fun fabricante(): String = (Build.MANUFACTURER ?: "").lowercase()

    fun registrar(motor: FlutterEngine, contexto: Context) {
        val app = contexto.applicationContext
        MethodChannel(motor.dartExecutor.binaryMessenger, "caudal/energia").setMethodCallHandler { llamada, resultado ->
            when (llamada.method) {
                "mantener" -> {
                    mantener(app, llamada.arguments == true)
                    resultado.success(null)
                }
                "sinRestriccion" -> resultado.success(sinRestriccion(app))
                "pedirSinRestriccion" -> {
                    pedirSinRestriccion(app)
                    resultado.success(null)
                }
                "fabricante" -> resultado.success(fabricante())
                "abrirAjusteBateria" -> {
                    abrirAjusteBateria(app)
                    resultado.success(null)
                }
                else -> resultado.notImplemented()
            }
        }
    }
}
