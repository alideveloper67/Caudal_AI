package com.kevinrr.caudal

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

/**
 * «Letra en la pantalla bloqueada»: el verso que suena en una notificacion propia, PUBLICA en el
 * bloqueo (se lee sin desbloquear aunque el telefono oculte el contenido de las demas). La app
 * (nucleo/letra_pantalla_bloqueo.dart) la cambia solo cuando cambia el verso. Al tocarla se abre
 * LetraBloqueoActivity: el verso en grande sobre el bloqueo, sin desbloquear.
 */
object LetraPantallaBloqueo {
    private const val CANAL = "caudal_letra_bloqueo"
    private const val NOTIF = 7401

    data class Verso(val titulo: String, val artista: String, val linea: String, val siguiente: String,
                     val sonando: Boolean)

    /** Lo ultimo que se enseño (lo lee LetraBloqueoActivity); null si no hay letra en pantalla. */
    @Volatile
    var actual: Verso? = null
        private set

    /** LetraBloqueoActivity se apunta para cambiar el verso o cerrarse. */
    @Volatile
    var alCambiar: (() -> Unit)? = null

    private fun canal(ctx: Context) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val nm = ctx.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (nm.getNotificationChannel(CANAL) != null) return
        // importancia normal (no «silenciosa»): asi sale en el bloqueo; sin sonido ni vibracion
        val c = NotificationChannel(CANAL, "Letra en la pantalla bloqueada", NotificationManager.IMPORTANCE_DEFAULT).apply {
            description = "El verso de la canción que suena"
            setSound(null, null)
            enableVibration(false)
            enableLights(false)
            setShowBadge(false)
            lockscreenVisibility = Notification.VISIBILITY_PUBLIC
        }
        nm.createNotificationChannel(c)
    }

    fun mostrar(contexto: Context, v: Verso) {
        val ctx = contexto.applicationContext
        actual = v
        alCambiar?.invoke()
        if (Build.VERSION.SDK_INT >= 33 &&
            ContextCompat.checkSelfPermission(ctx, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) return // sin permiso de notificaciones no hay donde enseñarla
        try {
            canal(ctx)
            val abrir = PendingIntent.getActivity(ctx, 7402,
                Intent(ctx, LetraBloqueoActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),
                PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
            val cancion = listOf(v.titulo, v.artista).filter { it.isNotBlank() }.joinToString(" · ")
            val grande = if (v.siguiente.isBlank()) v.linea else "${v.linea}\n${v.siguiente}"
            val n = NotificationCompat.Builder(ctx, CANAL)
                .setSmallIcon(R.drawable.ic_notificacion)
                .setContentTitle(v.linea)
                .setContentText(if (v.sonando) cancion else "En pausa · $cancion")
                .setStyle(NotificationCompat.BigTextStyle().bigText(grande).setSummaryText(cancion))
                .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
                .setPriority(NotificationCompat.PRIORITY_DEFAULT)
                .setOnlyAlertOnce(true)
                .setShowWhen(false)
                .setOngoing(v.sonando)
                .setContentIntent(abrir)
                .setCategory(NotificationCompat.CATEGORY_STATUS)
                .build()
            NotificationManagerCompat.from(ctx).notify(NOTIF, n)
        } catch (_: SecurityException) {
            // sin permiso de notificaciones (Android 13+): no hay donde enseñarla
        } catch (_: Exception) {
        }
    }

    fun quitar(contexto: Context) {
        actual = null
        alCambiar?.invoke()
        try {
            NotificationManagerCompat.from(contexto.applicationContext).cancel(NOTIF)
        } catch (_: Exception) {
        }
    }

    fun registrar(motor: FlutterEngine, contexto: Context) {
        val app = contexto.applicationContext
        MethodChannel(motor.dartExecutor.binaryMessenger, "caudal/letra_bloqueo").setMethodCallHandler { llamada, resultado ->
            when (llamada.method) {
                "mostrar" -> {
                    val m = llamada.arguments as? Map<*, *> ?: emptyMap<String, Any>()
                    mostrar(app, Verso(
                        titulo = m["titulo"] as? String ?: "",
                        artista = m["artista"] as? String ?: "",
                        linea = m["linea"] as? String ?: "",
                        siguiente = m["siguiente"] as? String ?: "",
                        sonando = m["sonando"] == true,
                    ))
                    resultado.success(null)
                }
                "quitar" -> {
                    quitar(app)
                    resultado.success(null)
                }
                else -> resultado.notImplemented()
            }
        }
    }
}
