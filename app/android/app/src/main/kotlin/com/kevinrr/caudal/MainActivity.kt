package com.kevinrr.caudal

import android.app.PictureInPictureParams
import android.content.Intent
import android.content.res.Configuration
import android.os.Build
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

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
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

    private fun textoDe(intent: Intent?): String? {
        if (intent?.action != Intent.ACTION_SEND) return null
        return intent.getStringExtra(Intent.EXTRA_TEXT)
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
