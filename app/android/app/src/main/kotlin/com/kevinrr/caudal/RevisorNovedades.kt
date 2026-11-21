package com.kevinrr.caudal

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import androidx.work.Constraints
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.Worker
import androidx.work.WorkerParameters
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.text.SimpleDateFormat
import java.util.Locale
import java.util.TimeZone
import java.util.concurrent.TimeUnit

/**
 * Cada 15 minutos (minimo de Android), con internet y aunque Caudal este
 * cerrada, revisa tres cosas en Supabase:
 *  - avisos del equipo de Caudal (tabla "avisos"),
 *  - solicitudes de amistad nuevas para este dispositivo,
 *  - mensajes nuevos en los chats de este dispositivo.
 *
 * Cada aviso o novedad se notifica una sola vez. La primera vez que corre no
 * notifica avisos viejos: solo guarda el ultimo id visto.
 */
class RevisorNovedades(contexto: Context, parametros: WorkerParameters) : Worker(contexto, parametros) {

    override fun doWork(): Result {
        val ctx = applicationContext
        try {
            revisarAvisos(ctx)
        } catch (_: Exception) {
            // sin red o respuesta rara: se intenta en la siguiente pasada
        }
        try {
            revisarNovedades(ctx)
        } catch (_: Exception) {
        }
        return Result.success()
    }

    companion object {
        private const val TRABAJO = "caudal_revisar_novedades"
        private const val PREFS = "caudal_novedades"
        private const val PREFS_FLUTTER = "FlutterSharedPreferences"
        private const val CLAVE_TOKEN = "flutter.caudal_token_aviso"

        private const val BASE = "https://nztirmwqykbxadidpzzt.supabase.co/rest/v1/"
        private const val CLAVE = "sb_publishable_ga4gKRk0czj044G-xPptSQ_BZ_sTZLl"
        private const val URL_AVISOS =
            BASE + "avisos?select=id,titulo,texto,plataformas,activo,caduca&activo=eq.true&order=id.desc&limit=5"
        private const val URL_RPC = BASE + "rpc/novedades_dispositivo"

        private const val CANAL_AVISOS = "app.caudal.avisos"
        private const val CANAL_AMIGOS = "app.caudal.amigos"
        private const val CANAL_MENSAJES = "app.caudal.mensajes"

        private const val MAX_SOLICITUDES_GUARDADAS = 50

        /** Se llama al abrir la app: si ya estaba programado, no lo duplica. */
        fun programar(contexto: Context) {
            val pedido = PeriodicWorkRequestBuilder<RevisorNovedades>(15, TimeUnit.MINUTES)
                .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
                .build()
            WorkManager.getInstance(contexto)
                .enqueueUniquePeriodicWork(TRABAJO, ExistingPeriodicWorkPolicy.KEEP, pedido)
        }

        // ---------- avisos ----------

        private fun revisarAvisos(ctx: Context) {
            val prefs = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            val texto = peticion(URL_AVISOS, "GET", null) ?: return
            val lista = JSONArray(texto)
            val primeraVez = !prefs.contains("aviso_max")
            val ultimo = prefs.getLong("aviso_max", 0L)

            var maxVisto = ultimo
            val pendientes = ArrayList<JSONObject>()
            for (i in 0 until lista.length()) {
                val aviso = lista.getJSONObject(i)
                val id = aviso.optLong("id", 0L)
                if (id > maxVisto) maxVisto = id
                if (primeraVez) continue
                if (id <= ultimo) continue
                if (!paraAndroid(aviso.opt("plataformas"))) continue
                val caduca = if (aviso.isNull("caduca")) null else aviso.optString("caduca")
                if (!vigente(caduca)) continue
                pendientes.add(aviso)
            }

            // primera vez: solo se guarda el id mayor, sin notificar nada
            prefs.edit().putLong("aviso_max", maxVisto).apply()

            pendientes.sortedBy { it.optLong("id", 0L) }.forEach { aviso ->
                val id = aviso.optLong("id", 0L)
                notificar(
                    ctx,
                    CANAL_AVISOS,
                    CANAL_AVISOS_NOMBRE,
                    NotificationManager.IMPORTANCE_DEFAULT,
                    (5000 + (id and 0x3FF)).toInt(),
                    aviso.optString("titulo").ifBlank { "Aviso de Caudal" },
                    aviso.optString("texto")
                )
            }
        }

        /** plataformas puede venir como lista JSON o como texto; debe contener "todas" o "android". */
        private fun paraAndroid(plataformas: Any?): Boolean {
            val valores: List<String> = when (plataformas) {
                is JSONArray -> (0 until plataformas.length()).map { plataformas.optString(it) }
                is String -> plataformas.split(',')
                else -> emptyList()
            }
            return valores.map { it.trim().lowercase(Locale.ROOT) }.any { it == "todas" || it == "android" }
        }

        /** caduca null o en el futuro. Si la fecha no se entiende, se muestra. */
        private fun vigente(caduca: String?): Boolean {
            if (caduca.isNullOrBlank()) return true
            val s = caduca.trim()
            val ms = try {
                val fecha = s.length >= 19 && (s[10] == 'T' || s[10] == ' ')
                val formato = SimpleDateFormat(
                    if (fecha) "yyyy-MM-dd'T'HH:mm:ss" else "yyyy-MM-dd",
                    Locale.US
                )
                formato.timeZone = TimeZone.getTimeZone("UTC")
                val texto = if (fecha) s.substring(0, 19).replace(' ', 'T') else s.substring(0, 10)
                formato.parse(texto)?.time
            } catch (_: Exception) {
                null
            }
            return ms == null || ms > System.currentTimeMillis()
        }

        // ---------- solicitudes y mensajes ----------

        private fun revisarNovedades(ctx: Context) {
            val token = ctx.getSharedPreferences(PREFS_FLUTTER, Context.MODE_PRIVATE)
                .getString(CLAVE_TOKEN, null)
                ?.takeIf { it.isNotBlank() }
                ?: return

            val cuerpo = JSONObject().put("p_token", token).toString()
            val respuestaTexto = peticion(URL_RPC, "POST", cuerpo)?.trim() ?: return
            if (respuestaTexto.isEmpty() || respuestaTexto == "null") return
            val respuesta = JSONObject(respuestaTexto)

            val prefs = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            val editor = prefs.edit()

            // solicitudes de amistad: una notificacion por id, sin repetir
            val solicitudes = respuesta.optJSONArray("solicitudes") ?: JSONArray()
            val yaAvisadas = HashSet(prefs.getStringSet("solicitudes_avisadas", emptySet()) ?: emptySet())
            for (i in 0 until solicitudes.length()) {
                val s = solicitudes.getJSONObject(i)
                val id = s.optLong("id", 0L)
                if (id <= 0L) continue
                val clave = id.toString()
                if (yaAvisadas.contains(clave)) continue
                yaAvisadas.add(clave)
                val nombre = s.optString("nombre").ifBlank { "Alguien" }
                notificar(
                    ctx,
                    CANAL_AMIGOS,
                    CANAL_AMIGOS_NOMBRE,
                    NotificationManager.IMPORTANCE_DEFAULT,
                    (20000 + (id and 0x3FFF)).toInt(),
                    "Nueva solicitud de amistad",
                    "$nombre quiere ser tu amigo en Caudal"
                )
            }
            val conservar = yaAvisadas.mapNotNull { it.toLongOrNull() }
                .sorted()
                .takeLast(MAX_SOLICITUDES_GUARDADAS)
                .map { it.toString() }
                .toSet()
            editor.putStringSet("solicitudes_avisadas", conservar)

            // mensajes: una notificacion por chat, que se reemplaza
            val mensajes = respuesta.optJSONArray("mensajes") ?: JSONArray()
            for (i in 0 until mensajes.length()) {
                val m = mensajes.getJSONObject(i)
                val chat = m.optString("chat")
                if (chat.isBlank()) continue
                val ultimo = m.optLong("ultimo", 0L)
                val clave = "chat_$chat"
                val previo = prefs.getLong(clave, 0L)
                if (ultimo <= previo) continue
                editor.putLong(clave, ultimo)
                val cuantos = m.optInt("cuantos", 1)
                val texto1 = m.optString("texto")
                val cuerpoMensaje = if (cuantos > 1) "$texto1 (+${cuantos - 1} más)" else texto1
                notificar(
                    ctx,
                    CANAL_MENSAJES,
                    CANAL_MENSAJES_NOMBRE,
                    NotificationManager.IMPORTANCE_HIGH,
                    9000 + (chat.hashCode() and 0x3FF),
                    m.optString("nombre").ifBlank { "Caudal" },
                    cuerpoMensaje
                )
            }

            editor.apply()
        }

        // ---------- notificaciones ----------

        private const val CANAL_AVISOS_NOMBRE = "Avisos de Caudal"
        private const val CANAL_AMIGOS_NOMBRE = "Solicitudes de amistad"
        private const val CANAL_MENSAJES_NOMBRE = "Mensajes"

        private fun permitido(ctx: Context): Boolean =
            Build.VERSION.SDK_INT < 33 ||
                ContextCompat.checkSelfPermission(ctx, Manifest.permission.POST_NOTIFICATIONS) ==
                PackageManager.PERMISSION_GRANTED

        private fun notificar(
            ctx: Context,
            canalId: String,
            canalNombre: String,
            importancia: Int,
            id: Int,
            titulo: String,
            texto: String
        ) {
            if (!permitido(ctx)) return
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                val canal = NotificationChannel(canalId, canalNombre, importancia)
                ctx.getSystemService(NotificationManager::class.java).createNotificationChannel(canal)
            }
            val abrir = Intent(ctx, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            }
            val toque = PendingIntent.getActivity(
                ctx, id, abrir, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )
            val prioridad = if (importancia >= NotificationManager.IMPORTANCE_HIGH) {
                NotificationCompat.PRIORITY_HIGH
            } else {
                NotificationCompat.PRIORITY_DEFAULT
            }
            val n = NotificationCompat.Builder(ctx, canalId)
                .setSmallIcon(R.drawable.ic_notificacion)
                .setContentTitle(titulo)
                .setContentText(texto)
                .setStyle(NotificationCompat.BigTextStyle().bigText(texto))
                .setPriority(prioridad)
                .setContentIntent(toque)
                .setAutoCancel(true)
                .build()
            try {
                NotificationManagerCompat.from(ctx).notify(id, n)
            } catch (_: SecurityException) {
            }
        }

        // ---------- red ----------

        /** Devuelve el cuerpo de la respuesta, o null si no es 2xx. Timeouts de 10 s. */
        private fun peticion(url: String, metodo: String, cuerpo: String?): String? {
            val c = URL(url).openConnection() as HttpURLConnection
            c.connectTimeout = 10000
            c.readTimeout = 10000
            c.requestMethod = metodo
            c.setRequestProperty("apikey", CLAVE)
            c.setRequestProperty("Authorization", "Bearer $CLAVE")
            c.setRequestProperty("Accept", "application/json")
            try {
                if (cuerpo != null) {
                    c.doOutput = true
                    c.setRequestProperty("Content-Type", "application/json")
                    c.outputStream.use { it.write(cuerpo.toByteArray(Charsets.UTF_8)) }
                }
                if (c.responseCode !in 200..299) return null
                return c.inputStream.bufferedReader(Charsets.UTF_8).use { it.readText() }
            } finally {
                c.disconnect()
            }
        }
    }
}
