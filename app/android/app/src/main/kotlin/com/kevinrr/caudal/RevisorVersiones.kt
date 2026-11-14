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
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.TimeUnit

/**
 * Una vez al dia, aunque Caudal este cerrada, mira en GitHub si hay una
 * version nueva del movil (etiquetas "movil-vX.Y.Z") y, si la hay, avisa con
 * una notificacion. Al tocarla se abre Caudal, que ya ofrece "Instalar ahora".
 *
 * Avisa una sola vez por version. Android decide el momento exacto (ahorro de
 * bateria), siempre con internet.
 */
class RevisorVersiones(contexto: Context, parametros: WorkerParameters) : Worker(contexto, parametros) {

    override fun doWork(): Result {
        return try {
            revisar(applicationContext)
            Result.success()
        } catch (_: Exception) {
            Result.retry()
        }
    }

    companion object {
        private const val TRABAJO = "caudal_revisar_version"
        private const val CANAL = "app.caudal.novedades"
        private const val API = "https://api.github.com/repos/alideveloper67/Caudal_AI/releases?per_page=40"
        private const val PREFS = "caudal_revisor"
        private const val AVISADA = "avisada"
        private const val ID_NOTIFICACION = 7401

        /** Se llama al abrir la app: si ya estaba programado, no lo duplica. */
        fun programar(contexto: Context) {
            val pedido = PeriodicWorkRequestBuilder<RevisorVersiones>(1, TimeUnit.DAYS)
                .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
                .setInitialDelay(2, TimeUnit.HOURS)
                .build()
            WorkManager.getInstance(contexto)
                .enqueueUniquePeriodicWork(TRABAJO, ExistingPeriodicWorkPolicy.KEEP, pedido)
        }

        fun revisar(contexto: Context) {
            val instalada = versionInstalada(contexto) ?: return
            val nueva = ultimaVersion() ?: return
            if (comparar(nueva, instalada) <= 0) return
            val prefs = contexto.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            if (prefs.getString(AVISADA, "") == nueva) return
            if (avisar(contexto, nueva)) prefs.edit().putString(AVISADA, nueva).apply()
        }

        private fun versionInstalada(contexto: Context): String? = try {
            contexto.packageManager.getPackageInfo(contexto.packageName, 0).versionName
        } catch (_: Exception) {
            null
        }

        /** La version mas alta publicada (sin borradores ni pruebas) con APK adjunto. */
        private fun ultimaVersion(): String? {
            val c = URL(API).openConnection() as HttpURLConnection
            c.connectTimeout = 15000
            c.readTimeout = 15000
            c.setRequestProperty("Accept", "application/vnd.github+json")
            c.setRequestProperty("User-Agent", "Caudal")
            try {
                if (c.responseCode != 200) return null
                val lista = JSONArray(c.inputStream.bufferedReader().use { it.readText() })
                var mejor: String? = null
                for (i in 0 until lista.length()) {
                    val r = lista.getJSONObject(i)
                    if (r.optBoolean("draft") || r.optBoolean("prerelease")) continue
                    val etiqueta = r.optString("tag_name")
                    if (!etiqueta.startsWith("movil-v")) continue
                    val adjuntos = r.optJSONArray("assets") ?: continue
                    var conApk = false
                    for (j in 0 until adjuntos.length()) {
                        if (adjuntos.getJSONObject(j).optString("name").endsWith(".apk")) conApk = true
                    }
                    if (!conApk) continue
                    val v = etiqueta.removePrefix("movil-v")
                    if (mejor == null || comparar(v, mejor) > 0) mejor = v
                }
                return mejor
            } finally {
                c.disconnect()
            }
        }

        /** 2.0.10 > 2.0.9; lo que no es numero cuenta como 0. */
        fun comparar(a: String, b: String): Int {
            val x = a.split('.', '-', '+').map { it.toIntOrNull() ?: 0 }
            val y = b.split('.', '-', '+').map { it.toIntOrNull() ?: 0 }
            for (i in 0 until maxOf(x.size, y.size)) {
                val d = x.getOrElse(i) { 0 } - y.getOrElse(i) { 0 }
                if (d != 0) return d
            }
            return 0
        }

        private fun avisar(contexto: Context, version: String): Boolean {
            if (Build.VERSION.SDK_INT >= 33 &&
                ContextCompat.checkSelfPermission(contexto, Manifest.permission.POST_NOTIFICATIONS) !=
                PackageManager.PERMISSION_GRANTED
            ) return false
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                val canal = NotificationChannel(CANAL, "Versiones nuevas", NotificationManager.IMPORTANCE_DEFAULT)
                canal.description = "Te avisa cuando hay una versión nueva de Caudal"
                contexto.getSystemService(NotificationManager::class.java).createNotificationChannel(canal)
            }
            val abrir = Intent(contexto, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            }
            val toque = PendingIntent.getActivity(
                contexto, 0, abrir, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )
            val n = NotificationCompat.Builder(contexto, CANAL)
                .setSmallIcon(R.drawable.ic_notificacion)
                .setContentTitle("Caudal $version ya está lista")
                .setContentText("Toca para abrir Caudal e instalarla.")
                .setContentIntent(toque)
                .setAutoCancel(true)
                .build()
            return try {
                NotificationManagerCompat.from(contexto).notify(ID_NOTIFICACION, n)
                true
            } catch (_: SecurityException) {
                false
            }
        }
    }
}
