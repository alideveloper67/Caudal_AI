package com.kevinrr.caudal

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.os.Handler
import android.os.Looper
import android.os.Process
import android.view.KeyEvent
import android.view.View
import android.widget.RemoteViews
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import java.io.File
import java.io.FileOutputStream
import java.net.HttpURLConnection
import java.net.URL
import kotlin.concurrent.thread

/**
 * Widget de la pantalla de inicio: caratula, titulo, play/pausa y siguiente.
 *
 * Dart (widget_inicio.dart) publica lo que suena por el canal `caudal/widget`;
 * aqui se guarda en preferencias y se pinta. Los botones vuelven a Dart por el
 * mismo canal mientras la app esta viva. Si el proceso murio, el boton de play
 * abre la app (arrancar el servicio de musica en frio desde un widget no es
 * fiable en Android 12+).
 */
class CaudalWidget : AppWidgetProvider() {

    override fun onUpdate(context: Context, manager: AppWidgetManager, ids: IntArray) {
        pintar(context, manager, ids)
    }

    override fun onReceive(context: Context, intent: Intent) {
        when (intent.action) {
            ACCION_ALTERNAR -> tocar(context, "alternar", KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE)
            ACCION_SIGUIENTE -> tocar(context, "siguiente", KeyEvent.KEYCODE_MEDIA_NEXT)
            else -> super.onReceive(context, intent)
        }
    }

    private fun tocar(context: Context, metodo: String, tecla: Int) {
        val canal = Puente.canal
        if (Puente.vivo(context) && canal != null) {
            Handler(Looper.getMainLooper()).post { canal.invokeMethod(metodo, null) }
            return
        }
        if (Puente.vivo(context)) {
            // motor sin actividad (p. ej. lo arranco Android Auto): tecla multimedia
            mandarTecla(context, tecla)
            return
        }
        // la app no esta corriendo: abrirla y dejar el widget en reposo
        Puente.marcarDormido(context)
        try {
            context.startActivity(abrirApp(context).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
        } catch (_: Exception) {
        }
        refrescar(context)
    }

    private fun mandarTecla(context: Context, tecla: Int) {
        val receptor = ComponentName(context.packageName, "com.ryanheise.audioservice.MediaButtonReceiver")
        for (accion in intArrayOf(KeyEvent.ACTION_DOWN, KeyEvent.ACTION_UP)) {
            context.sendBroadcast(
                Intent(Intent.ACTION_MEDIA_BUTTON)
                    .setComponent(receptor)
                    .putExtra(Intent.EXTRA_KEY_EVENT, KeyEvent(accion, tecla))
            )
        }
    }

    companion object {
        const val ACCION_ALTERNAR = "com.kevinrr.caudal.widget.ALTERNAR"
        const val ACCION_SIGUIENTE = "com.kevinrr.caudal.widget.SIGUIENTE"

        fun refrescar(context: Context) {
            val manager = AppWidgetManager.getInstance(context)
            val ids = manager.getAppWidgetIds(ComponentName(context, CaudalWidget::class.java))
            if (ids.isNotEmpty()) pintar(context, manager, ids)
        }

        private fun abrirApp(context: Context): Intent =
            Intent(context, MainActivity::class.java)
                .setAction(Intent.ACTION_MAIN)
                .addCategory(Intent.CATEGORY_LAUNCHER)

        private fun difusion(context: Context, accion: String, codigo: Int): PendingIntent =
            PendingIntent.getBroadcast(
                context, codigo,
                Intent(context, CaudalWidget::class.java).setAction(accion),
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )

        private fun pintar(context: Context, manager: AppWidgetManager, ids: IntArray) {
            val p = Puente.prefs(context)
            val vivo = Puente.vivo(context)
            val hay = p.getBoolean("hay", false)
            val sonando = vivo && p.getBoolean("sonando", false)
            val v = RemoteViews(context.packageName, R.layout.widget_caudal)

            v.setTextViewText(R.id.widget_titulo, if (hay) p.getString("titulo", "") else "Caudal")
            v.setTextViewText(
                R.id.widget_artista,
                if (hay) p.getString("artista", "") else "Toca para escuchar música"
            )
            val caratula = if (hay) Puente.caratula(context) else null
            if (caratula != null) {
                v.setImageViewBitmap(R.id.widget_caratula, caratula)
            } else {
                v.setImageViewResource(R.id.widget_caratula, R.mipmap.ic_launcher)
            }
            v.setImageViewResource(
                R.id.widget_alternar,
                if (sonando) R.drawable.ic_widget_pausa else R.drawable.ic_widget_play
            )
            v.setContentDescription(R.id.widget_alternar, if (sonando) "Pausar" else "Reproducir")
            v.setViewVisibility(R.id.widget_siguiente, if (hay) View.VISIBLE else View.GONE)

            val abrir = PendingIntent.getActivity(
                context, 0, abrirApp(context),
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )
            v.setOnClickPendingIntent(R.id.widget_raiz, abrir)
            // sin la app corriendo, play abre la app directamente
            v.setOnClickPendingIntent(
                R.id.widget_alternar,
                if (vivo && hay) difusion(context, ACCION_ALTERNAR, 1) else abrir
            )
            v.setOnClickPendingIntent(R.id.widget_siguiente, difusion(context, ACCION_SIGUIENTE, 2))
            manager.updateAppWidget(ids, v)
        }
    }

    /** Lo que comparte el widget con el lado Dart. */
    object Puente {
        var canal: MethodChannel? = null
        private var arteCargado: String? = null

        fun prefs(context: Context) =
            context.applicationContext.getSharedPreferences("caudal_widget", Context.MODE_PRIVATE)

        /** El proceso que publico sigue vivo (si murio, el PID guardado es de otro). */
        fun vivo(context: Context) = prefs(context).getInt("pid", -1) == Process.myPid()

        fun marcarDormido(context: Context) {
            prefs(context).edit().putBoolean("sonando", false).putInt("pid", -1).apply()
        }

        fun registrar(engine: FlutterEngine, context: Context) {
            val app = context.applicationContext
            val c = MethodChannel(engine.dartExecutor.binaryMessenger, "caudal/widget")
            c.setMethodCallHandler { llamada, resultado ->
                if (llamada.method == "publicar") {
                    publicar(app, llamada.arguments as? Map<*, *> ?: emptyMap<String, Any>())
                    resultado.success(null)
                } else {
                    resultado.notImplemented()
                }
            }
            canal = c
            // que Dart repita lo ultimo por si lo envio antes de conectarnos
            c.invokeMethod("pedir", null)
        }

        private fun publicar(context: Context, d: Map<*, *>) {
            val arte = d["arte"] as? String ?: ""
            val antes = prefs(context).getString("arte", "")
            prefs(context).edit()
                .putInt("pid", Process.myPid())
                .putBoolean("hay", d["hay"] == true)
                .putBoolean("sonando", d["sonando"] == true)
                .putString("titulo", d["titulo"] as? String ?: "")
                .putString("artista", d["artista"] as? String ?: "")
                .putString("arte", arte)
                .apply()
            refrescar(context)
            if (arte != antes || arteCargado != arte) {
                arteCargado = arte
                thread(name = "caudal-widget-caratula") {
                    guardarCaratula(context, arte)
                    Handler(Looper.getMainLooper()).post { refrescar(context) }
                }
            }
        }

        private fun archivo(context: Context) = File(context.filesDir, "widget_caratula.png")

        fun caratula(context: Context): Bitmap? {
            val f = archivo(context)
            return if (f.exists()) BitmapFactory.decodeFile(f.path) else null
        }

        private fun guardarCaratula(context: Context, arte: String) {
            val destino = archivo(context)
            val bmp = try {
                when {
                    arte.isEmpty() -> null
                    arte.startsWith("http") -> descargar(arte)
                    else -> BitmapFactory.decodeFile(android.net.Uri.parse(arte).path ?: arte)
                }
            } catch (_: Exception) {
                null
            }
            // si otra cancion empezo mientras tanto, esta caratula ya no vale
            if (prefs(context).getString("arte", "") != arte) return
            if (bmp == null) {
                destino.delete()
                return
            }
            val lado = 256
            val escala = lado.toFloat() / maxOf(bmp.width, bmp.height)
            val chica = if (escala < 1f) {
                Bitmap.createScaledBitmap(bmp, (bmp.width * escala).toInt(), (bmp.height * escala).toInt(), true)
            } else bmp
            FileOutputStream(destino).use { chica.compress(Bitmap.CompressFormat.PNG, 100, it) }
        }

        private fun descargar(url: String): Bitmap? {
            val con = URL(url).openConnection() as HttpURLConnection
            con.connectTimeout = 8000
            con.readTimeout = 8000
            return try {
                con.inputStream.use { BitmapFactory.decodeStream(it) }
            } finally {
                con.disconnect()
            }
        }
    }
}
