package com.kevinrr.caudal

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.media.AudioAttributes
import android.media.AudioFocusRequest
import android.media.AudioManager
import android.media.MediaPlayer
import android.net.Uri
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.PowerManager
import android.os.SystemClock
import android.os.VibrationEffect
import android.os.Vibrator
import androidx.core.app.NotificationCompat
import org.json.JSONObject
import java.io.File
import kotlin.random.Random

/**
 * La alarma sonando: servicio en primer plano que toca la musica de la alarma con MediaPlayer
 * (flujo de ALARMA, asi suena aunque el telefono este en silencio de multimedia), subiendo el
 * volumen poco a poco, y una notificacion de pantalla completa que enciende DespertadorActivity
 * sobre el bloqueo. Sin la app abierta y sin internet: toca archivos que ya estan en el telefono.
 *
 * Que suena, en orden: el archivo preparado de la alarma (la cancion elegida o una de tus «me gusta»
 * descargadas, al azar), si no una cancion descargada del respaldo y, si no hay nada, el sonido suave
 * que trae Caudal (res/raw/despertador_amanecer.wav).
 */
class DespertadorServicio : Service() {
    companion object {
        const val SONAR = "com.kevinrr.caudal.despertador.SERVICIO_SONAR"
        const val POSPONER = "com.kevinrr.caudal.despertador.POSPONER"
        const val APAGAR = "com.kevinrr.caudal.despertador.APAGAR"
        const val SEGUIR = "com.kevinrr.caudal.despertador.SEGUIR"
        private const val CANAL = "caudal_despertador"
        private const val NOTIF = 7301
        private const val MAX_MS = 10 * 60 * 1000L

        /** Lo que suena ahora (para DespertadorActivity); null si nada. */
        @Volatile
        var actual: Sonando? = null
            private set

        /** DespertadorActivity se apunta para cerrarse cuando la alarma se apaga. */
        @Volatile
        var alCambiar: (() -> Unit)? = null
    }

    data class Sonando(val id: String, val etiqueta: String, val titulo: String, val posponer: Int,
                       val tono: Boolean, val prueba: Boolean)

    private val manos = Handler(Looper.getMainLooper())
    private var reproductor: MediaPlayer? = null
    private var alarma: JSONObject? = null
    private var prueba = false
    private var inicio = 0L
    private var volumenAntes = -1
    private var foco: AudioFocusRequest? = null
    private var despierto: PowerManager.WakeLock? = null
    private var vibrando = false

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            SONAR -> empezar(intent.getStringExtra("id") ?: "", intent.getBooleanExtra("prueba", false))
            POSPONER -> posponer()
            APAGAR -> apagar(false)
            SEGUIR -> apagar(true)
            else -> if (alarma == null) parar()
        }
        return START_NOT_STICKY
    }

    // ------------------------------------------------------------ empezar

    private fun empezar(id: String, esPrueba: Boolean) {
        val a = Despertador.alarma(this, id, esPrueba)
        if (a == null) {
            // la alarma ya no existe: Android exige el primer plano igual (5 s) y se va enseguida
            ponerPrimerPlano(notificacion("", "", 9, conPantalla = false))
            parar()
            return
        }
        if (alarma != null) soltarSonido() // otra alarma encima de la que sonaba: manda la nueva
        alarma = a
        prueba = esPrueba
        val (ruta, titulo) = elegirSonido(a)
        // «actual» antes que la notificacion: la pantalla sobre el bloqueo lo lee al abrirse
        actual = Sonando(id, a.optString("etiqueta"), titulo ?: "Sonido suave de Caudal",
            a.optInt("posponer", 9), ruta == null, esPrueba)
        ponerPrimerPlano(notificacion(a.optString("etiqueta"), actual?.titulo ?: "", a.optInt("posponer", 9)))
        if (!esPrueba) Despertador.programarTodas(this) // la siguiente vez ya queda programada
        despertar()
        tocar(ruta, a)
        alCambiar?.invoke()
        manos.postDelayed({ if (alarma != null) apagar(false) }, MAX_MS) // nadie la apago: se calla sola
    }

    private fun existe(r: String) = r.isNotEmpty() && File(r).let { it.exists() && it.length() > 1000 }

    /** (ruta, titulo) de lo que suena, o (null, null) para el sonido suave. */
    private fun elegirSonido(a: JSONObject): Pair<String?, String?> {
        val fuente = a.optJSONObject("fuente")
        if (fuente?.optString("tipo") == "tono") return Pair(null, null)
        val propios = mutableListOf<Pair<String, String>>()
        a.optJSONArray("archivos")?.let {
            for (i in 0 until it.length()) {
                val x = it.optJSONObject(i) ?: continue
                val r = x.optString("archivo")
                if (existe(r)) propios.add(Pair(r, x.optString("titulo")))
            }
        }
        if (propios.isNotEmpty()) {
            val alAzar = fuente?.optString("tipo") == "me_gusta"
            return propios[if (alAzar) Random.nextInt(propios.size) else 0]
        }
        val reserva = mutableListOf<Pair<String, String>>()
        val r = Despertador.respaldo(this)
        for (i in 0 until r.length()) {
            val x = r.optJSONObject(i) ?: continue
            val ruta = x.optString("archivo")
            if (existe(ruta)) reserva.add(Pair(ruta, x.optString("titulo")))
        }
        if (reserva.isNotEmpty()) return reserva[Random.nextInt(reserva.size)]
        return Pair(null, null)
    }

    private fun despertar() {
        try {
            val pm = getSystemService(Context.POWER_SERVICE) as PowerManager
            despierto = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "Caudal::despertador").apply {
                setReferenceCounted(false)
                acquire(MAX_MS + 60_000L)
            }
        } catch (_: Exception) {
        }
    }

    // ------------------------------------------------------------ sonido

    private val atributos: AudioAttributes = AudioAttributes.Builder()
        .setUsage(AudioAttributes.USAGE_ALARM)
        .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
        .build()

    private fun tocar(ruta: String?, a: JSONObject) {
        val am = getSystemService(Context.AUDIO_SERVICE) as AudioManager
        // el volumen de ALARMA del telefono al elegido; al apagar se devuelve el de antes
        try {
            volumenAntes = am.getStreamVolume(AudioManager.STREAM_ALARM)
            val max = am.getStreamMaxVolume(AudioManager.STREAM_ALARM)
            val objetivo = (max * a.optInt("volumen", 80).coerceIn(5, 100) / 100.0).toInt().coerceIn(1, max)
            am.setStreamVolume(AudioManager.STREAM_ALARM, objetivo, 0)
        } catch (_: Exception) {
            volumenAntes = -1
        }
        pedirFoco(am)
        val mp = crear(ruta) ?: crear(null)
        reproductor = mp
        if (mp == null) return
        inicio = SystemClock.elapsedRealtime()
        val f = Despertador.factorVolumen(0.0, a.optInt("subida", 60))
        mp.setVolume(f, f)
        try {
            mp.start()
        } catch (_: Exception) {
        }
        subir()
    }

    /** Un MediaPlayer listo en bucle con [ruta] (null = el sonido suave), o null si no se pudo abrir. */
    private fun crear(ruta: String?): MediaPlayer? = try {
        MediaPlayer().apply {
            setAudioAttributes(atributos)
            if (ruta == null) {
                setDataSource(this@DespertadorServicio,
                    Uri.parse("android.resource://$packageName/${R.raw.despertador_amanecer}"))
            } else {
                setDataSource(ruta)
            }
            isLooping = true
            setOnErrorListener { mp, _, _ ->
                // el archivo se estropeo a mitad: sigue el sonido suave
                try {
                    mp.release()
                } catch (_: Exception) {
                }
                if (reproductor === mp && alarma != null) {
                    reproductor = crear(null)?.also {
                        it.setVolume(1f, 1f)
                        it.start()
                    }
                }
                true
            }
            prepare()
        }
    } catch (_: Exception) {
        null
    }

    private fun pedirFoco(am: AudioManager) {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                val r = AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN_TRANSIENT)
                    .setAudioAttributes(atributos)
                    .setOnAudioFocusChangeListener { }
                    .build()
                foco = r
                am.requestAudioFocus(r)
            } else {
                @Suppress("DEPRECATION")
                am.requestAudioFocus(null, AudioManager.STREAM_ALARM, AudioManager.AUDIOFOCUS_GAIN_TRANSIENT)
            }
        } catch (_: Exception) {
        }
    }

    private val paso = object : Runnable {
        override fun run() {
            val a = alarma ?: return
            val mp = reproductor ?: return
            val subida = a.optInt("subida", 60)
            val t = (SystemClock.elapsedRealtime() - inicio) / 1000.0
            val f = Despertador.factorVolumen(t, subida)
            try {
                mp.setVolume(f, f)
            } catch (_: Exception) {
            }
            // vibra suave cuando el volumen ya subio bastante (o a los 20 s si sube de golpe)
            if (!vibrando && a.optBoolean("vibrar", true) && t >= maxOf(20.0, subida * 0.6)) vibrar()
            if (t < subida + 1 || !vibrando) manos.postDelayed(this, 250)
        }
    }

    private fun subir() {
        manos.removeCallbacks(paso)
        manos.post(paso)
    }

    private fun vibrar() {
        vibrando = true
        try {
            @Suppress("DEPRECATION")
            val v = getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
            val patron = longArrayOf(0, 400, 900, 400, 1800)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                v.vibrate(VibrationEffect.createWaveform(patron, intArrayOf(0, 90, 0, 90, 0), 1),
                    atributos)
            } else {
                @Suppress("DEPRECATION")
                v.vibrate(patron, 1)
            }
        } catch (_: Exception) {
        }
    }

    private fun soltarSonido() {
        manos.removeCallbacksAndMessages(null)
        try {
            reproductor?.stop()
        } catch (_: Exception) {
        }
        try {
            reproductor?.release()
        } catch (_: Exception) {
        }
        reproductor = null
        if (vibrando) {
            try {
                @Suppress("DEPRECATION")
                val v = getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
                v.cancel()
            } catch (_: Exception) {
            }
            vibrando = false
        }
        val am = getSystemService(Context.AUDIO_SERVICE) as AudioManager
        try {
            if (volumenAntes >= 0) am.setStreamVolume(AudioManager.STREAM_ALARM, volumenAntes, 0)
        } catch (_: Exception) {
        }
        volumenAntes = -1
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                foco?.let { am.abandonAudioFocusRequest(it) }
            } else {
                @Suppress("DEPRECATION")
                am.abandonAudioFocus(null)
            }
        } catch (_: Exception) {
        }
        foco = null
    }

    // ------------------------------------------------------------ posponer / apagar

    private fun posponer() {
        val a = alarma ?: return parar()
        val id = a.optString("id")
        val minutos = a.optInt("posponer", 9).coerceIn(1, 60)
        if (!prueba) {
            Despertador.cambiar(this, id) {
                it.put("pospuesta_hasta", System.currentTimeMillis() + minutos * 60_000L)
            }
        }
        parar()
    }

    private fun apagar(seguir: Boolean) {
        val a = alarma
        if (a != null && !prueba) {
            val id = a.optString("id")
            Despertador.cambiar(this, id) {
                it.put("pospuesta_hasta", 0)
                val dias = it.optJSONArray("dias")
                if (dias == null || dias.length() == 0) it.put("activa", false) // era de una vez
            }
            if (seguir) Despertador.anotarSeguir(this, id)
        } else if (a != null && seguir) {
            Despertador.anotarSeguir(this, a.optString("id"))
        }
        parar()
    }

    private fun parar() {
        soltarSonido()
        alarma = null
        actual = null
        try {
            despierto?.let { if (it.isHeld) it.release() }
        } catch (_: Exception) {
        }
        despierto = null
        alCambiar?.invoke()
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
                stopForeground(STOP_FOREGROUND_REMOVE)
            } else {
                @Suppress("DEPRECATION")
                stopForeground(true)
            }
        } catch (_: Exception) {
        }
        stopSelf()
    }

    override fun onDestroy() {
        if (alarma != null) soltarSonido()
        actual = null
        super.onDestroy()
    }

    // ------------------------------------------------------------ notificacion

    private fun canal() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (nm.getNotificationChannel(CANAL) != null) return
        val c = NotificationChannel(CANAL, "Despertador", NotificationManager.IMPORTANCE_HIGH).apply {
            description = "La alarma con música de Caudal"
            setSound(null, null) // la musica la pone el servicio
            enableVibration(false)
            lockscreenVisibility = Notification.VISIBILITY_PUBLIC
            setBypassDnd(true)
        }
        nm.createNotificationChannel(c)
    }

    private fun pendienteServicio(accion: String, codigo: Int): PendingIntent =
        PendingIntent.getService(this, codigo, Intent(this, DespertadorServicio::class.java).setAction(accion),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)

    private fun notificacion(etiqueta: String, titulo: String, posponer: Int,
                             conPantalla: Boolean = true): Notification {
        canal()
        val pantalla = PendingIntent.getActivity(this, 7310,
            Intent(this, DespertadorActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_NO_USER_ACTION),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        val b = NotificationCompat.Builder(this, CANAL)
            .setSmallIcon(R.drawable.ic_notificacion)
            .setContentTitle(etiqueta.ifEmpty { "Despertador" })
            .setContentText(titulo.ifEmpty { "Buenos días" })
            .setCategory(NotificationCompat.CATEGORY_ALARM)
            .setPriority(NotificationCompat.PRIORITY_MAX)
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
            .setOngoing(true)
            .setAutoCancel(false)
        if (!conPantalla) return b.build()
        return b.setContentIntent(pantalla)
            .setFullScreenIntent(pantalla, true)
            .addAction(0, "Posponer $posponer min", pendienteServicio(POSPONER, 7311))
            .addAction(0, "Apagar", pendienteServicio(APAGAR, 7312))
            .build()
    }

    private fun ponerPrimerPlano(n: Notification) {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                startForeground(NOTIF, n, ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK)
            } else {
                startForeground(NOTIF, n)
            }
        } catch (_: Exception) {
            // sin permiso de primer plano: al menos que se vea
            try {
                (getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager).notify(NOTIF, n)
            } catch (_: Exception) {
            }
        }
    }
}
