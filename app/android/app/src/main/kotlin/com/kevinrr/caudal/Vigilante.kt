package com.kevinrr.caudal

import android.content.Context
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.os.Process
import android.os.SystemClock
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Vigila el hilo principal de Android durante el primer minuto de la app.
 *
 * Si ese hilo deja de responder mas de 6 segundos (la pantalla se congela,
 * por ejemplo en el logo), anota en un archivo en que linea estaba trabado.
 * La proxima vez que se abra, Caudal lo lee, arranca en modo seguro y le
 * muestra el detalle al usuario para que nos lo pueda enviar.
 */
object Vigilante {
    private const val ARCHIVO = "caudal_traba.txt"
    @Volatile private var ultimoLatido = 0L
    @Volatile private var activo = false

    fun iniciar(contexto: Context) {
        if (activo) return
        activo = true
        val app = contexto.applicationContext
        val principal = Handler(Looper.getMainLooper())
        ultimoLatido = SystemClock.uptimeMillis()
        val inicio = ultimoLatido
        Thread({
            var anotado = false
            while (SystemClock.uptimeMillis() - inicio < 90_000) {
                principal.post { ultimoLatido = SystemClock.uptimeMillis() }
                try {
                    Thread.sleep(1000)
                } catch (_: InterruptedException) {
                    break
                }
                val quieto = SystemClock.uptimeMillis() - ultimoLatido
                if (!anotado && quieto > 6000) {
                    anotado = true
                    anotar(app, quieto)
                }
            }
            activo = false
        }, "caudal-vigilante").apply { isDaemon = true }.start()
    }

    private fun anotar(contexto: Context, quietoMs: Long) {
        try {
            val hilo = Looper.getMainLooper().thread
            val pila = hilo.stackTrace.take(40).joinToString("\n") { "  at $it" }
            val fecha = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.US).format(Date())
            val texto = buildString {
                append("Caudal ${version(contexto)} · ${Build.MANUFACTURER} ${Build.MODEL} · Android ${Build.VERSION.RELEASE} (API ${Build.VERSION.SDK_INT})\n")
                append("$fecha · hilo principal quieto ${quietoMs / 1000} s · estado ${hilo.state}\n")
                append(pila)
            }
            // la primera linea dice que proceso lo escribio: solo cuenta en el arranque siguiente
            File(contexto.filesDir, ARCHIVO).writeText("pid=${Process.myPid()}\n$texto")
        } catch (_: Throwable) {
        }
    }

    private fun version(contexto: Context): String = try {
        contexto.packageManager.getPackageInfo(contexto.packageName, 0).versionName ?: "?"
    } catch (_: Exception) {
        "?"
    }

    /** Devuelve lo anotado (si hay) y lo borra. */
    fun leer(contexto: Context): String? {
        val f = File(contexto.filesDir, ARCHIVO)
        if (!f.exists()) return null
        return try {
            val texto = f.readText()
            val primera = texto.substringBefore('\n')
            // escrito por este mismo arranque (p. ej. un inicio lento): aun no se cuenta
            if (primera == "pid=${Process.myPid()}") return null
            f.delete()
            texto.substringAfter('\n')
        } catch (_: Exception) {
            null
        }
    }
}
