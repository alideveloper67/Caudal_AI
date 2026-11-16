package com.kevinrr.caudal

import android.app.PictureInPictureParams
import android.content.Intent
import android.content.res.Configuration
import android.os.Build
import android.os.Bundle
import android.util.Rational
import com.ryanheise.audioservice.AudioServiceActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

/**
 * Actividad principal. Hereda de AudioServiceActivity para que la musica siga
 * con la pantalla apagada, recibe lo que se comparte desde otras apps
 * ("Compartir -> Caudal" en TikTok, YouTube, Instagram...) y pasa el video a
 * una ventanita flotante (picture-in-picture) al salir de la app.
 */
class MainActivity : AudioServiceActivity() {
    private var canal: MethodChannel? = null
    private var pendiente: String? = null

    private var canalPip: MethodChannel? = null
    // true solo mientras hay un video sonando (lo decide el lado Dart)
    private var pipPermitido = false

    override fun onCreate(savedInstanceState: Bundle?) {
        // antes que nada: si el arranque se congela, queda anotado donde (Vigilante.kt)
        Vigilante.iniciar(this)
        super.onCreate(savedInstanceState)
    }

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "caudal/diagnostico")
            .setMethodCallHandler { llamada, resultado ->
                if (llamada.method == "traba") resultado.success(Vigilante.leer(applicationContext))
                else resultado.notImplemented()
            }
        canal = MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "caudal/compartido")
        canal?.setMethodCallHandler { llamada, resultado ->
            if (llamada.method == "inicial") {
                resultado.success(pendiente)
                pendiente = null
            } else {
                resultado.notImplemented()
            }
        }
        pendiente = textoDe(intent)

        // aviso de versiones nuevas aunque la app este cerrada (RevisorVersiones.kt)
        try {
            RevisorVersiones.programar(applicationContext)
        } catch (_: Exception) {
        }

        // widget de la pantalla de inicio (CaudalWidget.kt)
        CaudalWidget.Puente.registrar(flutterEngine, applicationContext)

        // CPU y wifi despiertos mientras suena (Energia.kt): musica con la pantalla apagada
        Energia.registrar(flutterEngine, applicationContext)

        canalPip = MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "caudal/pip")
        canalPip?.setMethodCallHandler { llamada, resultado ->
            if (llamada.method == "permitir") {
                pipPermitido = llamada.arguments == true
                actualizarParametrosPip()
                resultado.success(null)
            } else {
                resultado.notImplemented()
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        val texto = textoDe(intent) ?: return
        canal?.invokeMethod("compartido", texto) ?: run { pendiente = texto }
    }

    /** Texto compartido (ACTION_SEND) o enlace caudal://... entero (ACTION_VIEW). */
    private fun textoDe(intent: Intent?): String? = when (intent?.action) {
        Intent.ACTION_SEND -> intent.getStringExtra(Intent.EXTRA_TEXT)
        Intent.ACTION_VIEW -> intent.data?.toString()
        else -> null
    }

    // ---------- ventanita flotante ----------

    private fun parametrosPip(): PictureInPictureParams? {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return null
        val b = PictureInPictureParams.Builder().setAspectRatio(Rational(16, 9))
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            b.setAutoEnterEnabled(pipPermitido)
        }
        return b.build()
    }

    private fun actualizarParametrosPip() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        try {
            parametrosPip()?.let { setPictureInPictureParams(it) }
        } catch (_: Exception) {
            // sin soporte de PiP en este equipo: no pasa nada
        }
    }

    override fun onUserLeaveHint() {
        super.onUserLeaveHint()
        if (!pipPermitido || Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        // En API 31+ el sistema entra solo (setAutoEnterEnabled); antes, a mano.
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) return
        try {
            parametrosPip()?.let { enterPictureInPictureMode(it) }
        } catch (_: Exception) {
        }
    }

    override fun onPictureInPictureModeChanged(
        isInPictureInPictureMode: Boolean,
        newConfig: Configuration
    ) {
        super.onPictureInPictureModeChanged(isInPictureInPictureMode, newConfig)
        canalPip?.invokeMethod("cambio", isInPictureInPictureMode)
    }
}
