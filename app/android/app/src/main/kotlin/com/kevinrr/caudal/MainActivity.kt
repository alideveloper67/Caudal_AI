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
        // la traza de un fallo de Java/Kotlin queda guardada para el informe (Salidas.kt)
        Salidas.instalarCapturaJava(this)
        super.onCreate(savedInstanceState)

        // permiso de notificaciones (avisos, mensajes, solicitudes): se pide una sola vez
        if (Build.VERSION.SDK_INT >= 33 &&
            checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS) !=
            android.content.pm.PackageManager.PERMISSION_GRANTED
        ) {
            val prefs = getSharedPreferences("caudal_novedades", MODE_PRIVATE)
            if (!prefs.getBoolean("permiso_pedido", false)) {
                prefs.edit().putBoolean("permiso_pedido", true).apply()
                requestPermissions(arrayOf(android.Manifest.permission.POST_NOTIFICATIONS), 7402)
            }
        }
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
            RevisorNovedades.programar(applicationContext)
        } catch (_: Exception) {
        }

        // widget de la pantalla de inicio (CaudalWidget.kt)
        CaudalWidget.Puente.registrar(flutterEngine, applicationContext)

        // CPU y wifi despiertos mientras suena (Energia.kt): musica con la pantalla apagada
        Energia.registrar(flutterEngine, applicationContext)

        // volumen maximo sin distorsion y aviso de cambio de salida (Sonido.kt)
        Sonido.registrar(flutterEngine, applicationContext)

        // Estos canales existían desde la 2.7.0 pero nunca se conectaban (MissingPluginException en
        // todos los teléfonos): modo coche, despertador y letra en la pantalla bloqueada. Cada uno
        // por separado, para que si uno falla los demás sigan.
        for (registrar in listOf<(FlutterEngine) -> Unit>(
            { CocheBluetooth.registrar(it, applicationContext) },
            { Despertador.registrar(it, applicationContext) },
            { LetraPantallaBloqueo.registrar(it, applicationContext) },
            // por qué se cerró Caudal la vez anterior (Salidas.kt)
            { Salidas.registrar(it, applicationContext) },
        )) {
            try {
                registrar(flutterEngine)
            } catch (_: Exception) {
            }
        }

        // pantalla encendida mientras se ve el modo vinilo (FLAG_KEEP_SCREEN_ON)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "caudal/pantalla")
            .setMethodCallHandler { llamada, resultado ->
                if (llamada.method == "mantener") {
                    val si = llamada.arguments == true
                    runOnUiThread {
                        if (si) window.addFlags(android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
                        else window.clearFlags(android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
                    }
                    resultado.success(null)
                } else {
                    resultado.notImplemented()
                }
            }

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
