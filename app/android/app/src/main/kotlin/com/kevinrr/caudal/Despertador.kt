package com.kevinrr.caudal

import android.app.AlarmManager
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.PowerManager
import android.provider.Settings
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import org.json.JSONArray
import org.json.JSONObject
import java.util.Calendar

/**
 * Despertador con musica: guarda las alarmas que manda la app (nucleo/despertador_control.dart) y
 * programa cada una con AlarmManager.setAlarmClock, que suena a la hora exacta aunque la app este
 * cerrada, el telefono bloqueado o en reposo. Al sonar, DespertadorReceptor arranca
 * DespertadorServicio (musica que sube poco a poco + pantalla sobre el bloqueo).
 *
 * Todo lo que hace falta para sonar sin la app vive aqui (SharedPreferences "caudal_despertador"):
 * las alarmas, los archivos de musica ya preparados y el respaldo de canciones descargadas.
 * Tras reiniciar el telefono o cambiar la hora se vuelven a programar solas.
 */
object Despertador {
    const val PREFS = "caudal_despertador"
    private const val CLAVE_DATOS = "datos"
    private const val CLAVE_PROGRAMADAS = "programadas"
    private const val CLAVE_SEGUIR = "seguir"
    private const val CLAVE_PRUEBA = "prueba"

    // ------------------------------------------------------------ guardado

    private fun prefs(ctx: Context) = ctx.applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    fun leerDatos(ctx: Context): JSONObject = try {
        JSONObject(prefs(ctx).getString(CLAVE_DATOS, null) ?: "{}")
    } catch (_: Exception) {
        JSONObject()
    }

    private fun guardarDatos(ctx: Context, datos: JSONObject) {
        prefs(ctx).edit().putString(CLAVE_DATOS, datos.toString()).apply()
    }

    fun alarma(ctx: Context, id: String, prueba: Boolean = false): JSONObject? {
        if (prueba) {
            try {
                val p = JSONObject(prefs(ctx).getString(CLAVE_PRUEBA, null) ?: "{}")
                if (p.optString("id") == id) return p
            } catch (_: Exception) {
            }
        }
        val l = leerDatos(ctx).optJSONArray("alarmas") ?: return null
        for (i in 0 until l.length()) {
            val a = l.optJSONObject(i) ?: continue
            if (a.optString("id") == id) return a
        }
        return null
    }

    /** Cambia una alarma guardada (posponer / apagar) y vuelve a programar todas. */
    fun cambiar(ctx: Context, id: String, cambio: (JSONObject) -> Unit) {
        val datos = leerDatos(ctx)
        val l = datos.optJSONArray("alarmas") ?: return
        for (i in 0 until l.length()) {
            val a = l.optJSONObject(i) ?: continue
            if (a.optString("id") == id) cambio(a)
        }
        guardarDatos(ctx, datos)
        programarTodas(ctx)
    }

    fun respaldo(ctx: Context): JSONArray = leerDatos(ctx).optJSONArray("respaldo") ?: JSONArray()

    fun anotarSeguir(ctx: Context, id: String) {
        prefs(ctx).edit().putString(CLAVE_SEGUIR, id).apply()
    }

    // ------------------------------------------------------------ cuando suena

    /** Lunes = 1 ... domingo = 7 (como DateTime.weekday en Dart). */
    fun diaSemana(c: Calendar): Int = ((c.get(Calendar.DAY_OF_WEEK) + 5) % 7) + 1

    /** La proxima vez que suena (ms), o null si esta apagada. Igual que proximaVez() de la app. */
    fun proximaVez(a: JSONObject, ahora: Long): Long? {
        if (!a.optBoolean("activa", true)) return null
        val pospuesta = a.optLong("pospuesta_hasta", 0L)
        if (pospuesta > ahora) return pospuesta
        val hora = a.optInt("hora", 7).coerceIn(0, 23)
        val minuto = a.optInt("minuto", 0).coerceIn(0, 59)
        val dias = mutableSetOf<Int>()
        a.optJSONArray("dias")?.let { for (i in 0 until it.length()) dias.add(it.optInt(i)) }
        for (d in 0..7) {
            val c = Calendar.getInstance()
            c.timeInMillis = ahora
            c.add(Calendar.DAY_OF_MONTH, d)
            c.set(Calendar.HOUR_OF_DAY, hora)
            c.set(Calendar.MINUTE, minuto)
            c.set(Calendar.SECOND, 0)
            c.set(Calendar.MILLISECOND, 0)
            if (c.timeInMillis <= ahora) continue
            if (dias.isEmpty() || dias.contains(diaSemana(c))) return c.timeInMillis
        }
        return null
    }

    /** De casi nada al volumen elegido en [subida] s (curva cuadratica), como factorVolumen() de la app. */
    fun factorVolumen(segundo: Double, subida: Int): Float {
        if (subida <= 0) return 1f
        val p = (segundo / subida).coerceIn(0.0, 1.0)
        return (0.03 + 0.97 * p * p).toFloat()
    }

    // ------------------------------------------------------------ programar

    private fun codigo(id: String) = id.hashCode() and 0x3ffffff0

    private fun intentSonar(ctx: Context, id: String) =
        Intent(ctx, DespertadorReceptor::class.java).setAction(DespertadorReceptor.SONAR).putExtra("id", id)

    private fun pendienteSonar(ctx: Context, id: String, crear: Boolean): PendingIntent? {
        val modo = if (crear) PendingIntent.FLAG_UPDATE_CURRENT else PendingIntent.FLAG_NO_CREATE
        val banderas = PendingIntent.FLAG_IMMUTABLE or modo
        return PendingIntent.getBroadcast(ctx, codigo(id), intentSonar(ctx, id), banderas)
    }

    fun puedeExactas(ctx: Context): Boolean {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) return true
        val am = ctx.getSystemService(Context.ALARM_SERVICE) as AlarmManager
        return am.canScheduleExactAlarms()
    }

    @Synchronized
    fun programarTodas(contexto: Context) {
        val ctx = contexto.applicationContext
        val am = ctx.getSystemService(Context.ALARM_SERVICE) as AlarmManager
        val p = prefs(ctx)
        for (id in p.getStringSet(CLAVE_PROGRAMADAS, emptySet()) ?: emptySet()) {
            pendienteSonar(ctx, id, false)?.let {
                am.cancel(it)
                it.cancel()
            }
        }
        val nuevas = mutableSetOf<String>()
        val ahora = System.currentTimeMillis()
        val l = leerDatos(ctx).optJSONArray("alarmas") ?: JSONArray()
        for (i in 0 until l.length()) {
            val a = l.optJSONObject(i) ?: continue
            val id = a.optString("id")
            if (id.isEmpty()) continue
            val cuando = proximaVez(a, ahora) ?: continue
            if (programarUna(ctx, am, id, cuando)) nuevas.add(id)
        }
        p.edit().putStringSet(CLAVE_PROGRAMADAS, nuevas).apply()
    }

    private fun programarUna(ctx: Context, am: AlarmManager, id: String, cuando: Long): Boolean {
        val pi = pendienteSonar(ctx, id, true) ?: return false
        // tocar el reloj de la barra de estado abre Caudal
        val abrir = ctx.packageManager.getLaunchIntentForPackage(ctx.packageName)
        val mostrar = abrir?.let {
            PendingIntent.getActivity(ctx, codigo(id) + 1, it,
                PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        }
        try {
            if (puedeExactas(ctx) && mostrar != null) {
                // la alarma del sistema: exacta, despierta al telefono y sale en el reloj de la barra
                am.setAlarmClock(AlarmManager.AlarmClockInfo(cuando, mostrar), pi)
                return true
            }
        } catch (_: SecurityException) {
            // sin «Alarmas y recordatorios»: va la inexacta (puede llegar unos minutos tarde)
        }
        return try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                am.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, cuando, pi)
            } else {
                am.set(AlarmManager.RTC_WAKEUP, cuando, pi)
            }
            true
        } catch (_: Exception) {
            false
        }
    }

    // ------------------------------------------------------------ permisos

    private fun permisos(ctx: Context): Map<String, Boolean> {
        val pantalla = if (Build.VERSION.SDK_INT >= 34) {
            val nm = ctx.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            nm.canUseFullScreenIntent()
        } else true
        val bateria = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            val pm = ctx.getSystemService(Context.POWER_SERVICE) as PowerManager
            pm.isIgnoringBatteryOptimizations(ctx.packageName)
        } else true
        return mapOf(
            "exactas" to puedeExactas(ctx),
            "pantallaCompleta" to pantalla,
            "notificaciones" to NotificationManagerCompat.from(ctx).areNotificationsEnabled(),
            "bateria" to bateria,
        )
    }

    private fun abrirAjuste(ctx: Context, cual: String) {
        val paquete = Uri.parse("package:${ctx.packageName}")
        val intentos = mutableListOf<Intent>()
        when (cual) {
            "exactas" -> if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S)
                intentos.add(Intent("android.settings.REQUEST_SCHEDULE_EXACT_ALARM", paquete))
            "pantallaCompleta" -> if (Build.VERSION.SDK_INT >= 34)
                intentos.add(Intent("android.settings.MANAGE_APP_USE_FULL_SCREEN_INTENT", paquete))
            "notificaciones" -> if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O)
                intentos.add(Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS)
                    .putExtra(Settings.EXTRA_APP_PACKAGE, ctx.packageName))
            "bateria" -> intentos.add(Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS))
        }
        intentos.add(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, paquete))
        for (i in intentos) {
            try {
                i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                ctx.startActivity(i)
                return
            } catch (_: Exception) {
            }
        }
    }

    // ------------------------------------------------------------ canal con la app

    fun registrar(motor: FlutterEngine, contexto: Context) {
        val app = contexto.applicationContext
        MethodChannel(motor.dartExecutor.binaryMessenger, "caudal/despertador").setMethodCallHandler { llamada, resultado ->
            try {
                when (llamada.method) {
                    "programar" -> {
                        val datos = JSONObject(llamada.arguments as? String ?: "{}")
                        val prueba = datos.optJSONObject("prueba")
                        datos.remove("prueba")
                        if (prueba != null) prefs(app).edit().putString(CLAVE_PRUEBA, prueba.toString()).apply()
                        guardarDatos(app, datos)
                        programarTodas(app)
                        resultado.success(null)
                    }
                    "leer" -> resultado.success(leerDatos(app).toString())
                    "permisos" -> resultado.success(permisos(app))
                    "abrirAjuste" -> {
                        abrirAjuste(app, llamada.arguments as? String ?: "")
                        resultado.success(null)
                    }
                    "probar" -> {
                        val id = llamada.arguments as? String ?: ""
                        val i = Intent(app, DespertadorServicio::class.java)
                            .setAction(DespertadorServicio.SONAR)
                            .putExtra("id", id)
                            .putExtra("prueba", true)
                        ContextCompat.startForegroundService(app, i)
                        resultado.success(null)
                    }
                    "consumirSeguir" -> {
                        val p = prefs(app)
                        val id = p.getString(CLAVE_SEGUIR, null)
                        if (id != null) p.edit().remove(CLAVE_SEGUIR).apply()
                        resultado.success(id)
                    }
                    else -> resultado.notImplemented()
                }
            } catch (e: Exception) {
                resultado.error("despertador", e.message, null)
            }
        }
    }
}
