package com.kevinrr.caudal

import android.content.Context
import android.media.AudioDeviceCallback
import android.media.AudioDeviceInfo
import android.media.AudioManager
import android.media.audiofx.DynamicsProcessing
import android.media.audiofx.LoudnessEnhancer
import android.os.Build
import android.os.Handler
import android.os.Looper
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

/**
 * «Volumen máximo» y el ecualizador por salida (canal "caudal/sonido").
 *
 * El libmpv del teléfono no trae ni `volume` ni `alimiter`: subir el volumen por encima del
 * 100 % recortaba la onda. Aquí cada motor de mpv suena en su propia sesión de audio de Android
 * (mpv: `ao=audiotrack` + `audiotrack-session-id`) y a esa sesión se le pone un
 * DynamicsProcessing del sistema (Android 9+): ganancia de entrada (la de cada canción) y un
 * limitador a -1,5 dB, así la ganancia extra no distorsiona. En Android 7-8 se usa
 * LoudnessEnhancer, que también comprime sus picos, solo para subir.
 *
 * Además avisa a Dart cuando cambia la salida (audífonos, parlante, bluetooth).
 */
object Sonido {
    private class Efecto(val sesion: Int) {
        var dp: DynamicsProcessing? = null
        var realce: LoudnessEnhancer? = null
    }

    private val efectos = HashMap<Int, Efecto>()
    private var canal: MethodChannel? = null
    private var vigia: AudioDeviceCallback? = null

    fun registrar(engine: FlutterEngine, contexto: Context) {
        val app = contexto.applicationContext
        val c = MethodChannel(engine.dartExecutor.binaryMessenger, "caudal/sonido")
        canal = c
        c.setMethodCallHandler { llamada, resultado ->
            try {
                when (llamada.method) {
                    "sesion" -> resultado.success(nuevaSesion(app))
                    "ganancia" -> {
                        val sesion = (llamada.argument<Number>("sesion") ?: 0).toInt()
                        val db = (llamada.argument<Number>("db") ?: 0.0).toFloat()
                        resultado.success(ganancia(sesion, db))
                    }
                    "salida" -> resultado.success(tipoSalida(app))
                    else -> resultado.notImplemented()
                }
            } catch (_: Throwable) {
                // nunca debe callar la música: sin efecto, suena como siempre
                resultado.success(null)
            }
        }
        vigilarSalida(app)
    }

    /** Una sesión de audio nueva con su efecto ya puesto (o null si no se pudo). */
    @Synchronized
    private fun nuevaSesion(app: Context): Int? {
        val am = app.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        val sesion = am.generateAudioSessionId()
        if (sesion <= 0) return null
        val e = Efecto(sesion)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            try {
                val cfg = DynamicsProcessing.Config.Builder(
                    DynamicsProcessing.VARIANT_FAVOR_FREQUENCY_RESOLUTION, 2,
                    false, 0, false, 0, false, 0, true
                ).build()
                val dp = DynamicsProcessing(0, sesion, cfg)
                // limitador: ataque 1 ms, suelta 60 ms, 10:1 desde -1,5 dB
                dp.setLimiterAllChannelsTo(DynamicsProcessing.Limiter(true, true, 0, 1f, 60f, 10f, -1.5f, 0f))
                dp.setInputGainAllChannelsTo(0f)
                dp.setEnabled(true)
                e.dp = dp
            } catch (_: Throwable) {
                e.dp = null
            }
        }
        if (e.dp == null) {
            try {
                e.realce = LoudnessEnhancer(sesion).apply {
                    setTargetGain(0)
                    setEnabled(true)
                }
            } catch (_: Throwable) {
                e.realce = null
            }
        }
        if (e.dp == null && e.realce == null) return null
        efectos[sesion] = e
        return sesion
    }

    /**
     * Ganancia de la canción en dB. Devuelve quién la aplicó: "dp" (toda, con limitador),
     * "realce" (solo la parte positiva: la negativa la pone Dart con el volumen) o "ninguno".
     */
    @Synchronized
    private fun ganancia(sesion: Int, db: Float): String {
        val e = efectos[sesion] ?: return "ninguno"
        e.dp?.let {
            it.setInputGainAllChannelsTo(db.coerceIn(-24f, 18f))
            return "dp"
        }
        e.realce?.let {
            it.setTargetGain((db.coerceIn(0f, 12f) * 100f).toInt())
            return "realce"
        }
        return "ninguno"
    }

    // ---------- por dónde sale el sonido ----------

    private fun tipoSalida(app: Context): String {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.M) return "parlante"
        val am = app.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        var tipo = "parlante"
        for (d in am.getDevices(AudioManager.GET_DEVICES_OUTPUTS)) {
            when (d.type) {
                // 26 y 27: audífonos y parlantes Bluetooth LE (Android 12)
                AudioDeviceInfo.TYPE_BLUETOOTH_A2DP, 26, 27 -> return "bluetooth"
                AudioDeviceInfo.TYPE_WIRED_HEADPHONES, AudioDeviceInfo.TYPE_WIRED_HEADSET,
                AudioDeviceInfo.TYPE_USB_HEADSET -> tipo = "audifonos"
            }
        }
        return tipo
    }

    private fun vigilarSalida(app: Context) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.M || vigia != null) return
        val am = app.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        val principal = Handler(Looper.getMainLooper())
        val v = object : AudioDeviceCallback() {
            override fun onAudioDevicesAdded(agregados: Array<out AudioDeviceInfo>?) = avisar()
            override fun onAudioDevicesRemoved(quitados: Array<out AudioDeviceInfo>?) = avisar()
            private fun avisar() {
                // el sistema tarda un momento en mover el sonido a la salida nueva
                principal.postDelayed({
                    try {
                        canal?.invokeMethod("salida", tipoSalida(app))
                    } catch (_: Throwable) {
                    }
                }, 600)
            }
        }
        try {
            am.registerAudioDeviceCallback(v, principal)
            vigia = v
        } catch (_: Throwable) {
        }
    }
}
