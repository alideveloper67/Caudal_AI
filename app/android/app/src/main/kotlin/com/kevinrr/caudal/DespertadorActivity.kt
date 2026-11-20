package com.kevinrr.caudal

import android.app.Activity
import android.app.KeyguardManager
import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.util.TypedValue
import android.view.Gravity
import android.view.View
import android.view.WindowManager
import android.window.OnBackInvokedDispatcher
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextClock
import android.widget.TextView

/**
 * La pantalla de la alarma, encima del bloqueo y con la pantalla encendida: la hora en grande, el
 * nombre de la alarma, lo que suena y tres botones (Posponer, Apagar, Apagar y seguir escuchando).
 * Hecha a mano (sin Flutter) para que se abra al instante aunque la app este cerrada.
 */
class DespertadorActivity : Activity() {
    private val manos = Handler(Looper.getMainLooper())
    private var titulo: TextView? = null
    private var etiqueta: TextView? = null
    private var botonPosponer: Button? = null
    private var botonSeguir: Button? = null
    private var esperandoDesbloqueo = false

    private val fondo = Color.parseColor("#06070A")
    private val superficie = Color.parseColor("#1B1F27")
    private val acento = Color.parseColor("#22D3EE")
    private val acentoTexto = Color.parseColor("#03222B")
    private val texto = Color.parseColor("#F3F5F9")
    private val texto2 = Color.parseColor("#A9B1C0")

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        sobreElBloqueo()
        setContentView(construir())
        if (Build.VERSION.SDK_INT >= 33) {
            // con el gesto de atras de Android 13+ (enableOnBackInvokedCallback): tampoco cierra la alarma
            onBackInvokedDispatcher.registerOnBackInvokedCallback(OnBackInvokedDispatcher.PRIORITY_DEFAULT) { }
        }
        DespertadorServicio.alCambiar = { manos.post { pintar() } }
        pintar()
        // abierta tarde (la alarma ya se apago): un momento de gracia y fuera
        if (DespertadorServicio.actual == null) {
            manos.postDelayed({ if (DespertadorServicio.actual == null) finish() }, 1500)
        }
    }

    override fun onDestroy() {
        if (DespertadorServicio.alCambiar != null) DespertadorServicio.alCambiar = null
        manos.removeCallbacksAndMessages(null)
        super.onDestroy()
    }

    @Deprecated("Atras no apaga la alarma: hay que elegir posponer o apagar")
    override fun onBackPressed() {
        // nada: que no se pierda la alarma por un toque sin querer
    }

    private fun sobreElBloqueo() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O_MR1) {
            setShowWhenLocked(true)
            setTurnScreenOn(true)
        } else {
            @Suppress("DEPRECATION")
            window.addFlags(WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED or
                WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON)
        }
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        window.statusBarColor = fondo
        window.navigationBarColor = fondo
    }

    private fun dp(v: Float) = TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_DIP, v, resources.displayMetrics)

    private fun boton(t: String, relleno: Boolean, accion: () -> Unit) = Button(this).apply {
        text = t
        isAllCaps = false
        setTextSize(TypedValue.COMPLEX_UNIT_SP, 18f)
        typeface = Typeface.create(Typeface.DEFAULT, if (relleno) Typeface.BOLD else Typeface.NORMAL)
        setTextColor(if (relleno) acentoTexto else texto)
        background = GradientDrawable().apply {
            cornerRadius = dp(28f)
            setColor(if (relleno) acento else superficie)
        }
        stateListAnimator = null
        minHeight = dp(58f).toInt()
        setOnClickListener { accion() }
        layoutParams = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(58f).toInt()).apply {
            topMargin = dp(12f).toInt()
        }
    }

    private fun construir(): View {
        val raiz = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER_HORIZONTAL
            setBackgroundColor(fondo)
            val m = dp(28f).toInt()
            setPadding(m, dp(72f).toInt(), m, dp(36f).toInt())
        }
        raiz.addView(TextClock(this).apply {
            format12Hour = "h:mm"
            format24Hour = "HH:mm"
            setTextColor(texto)
            setTextSize(TypedValue.COMPLEX_UNIT_SP, 86f)
            typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
            gravity = Gravity.CENTER
        })
        etiqueta = TextView(this).apply {
            setTextColor(acento)
            setTextSize(TypedValue.COMPLEX_UNIT_SP, 24f)
            typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
            gravity = Gravity.CENTER
        }
        raiz.addView(etiqueta)
        titulo = TextView(this).apply {
            setTextColor(texto2)
            setTextSize(TypedValue.COMPLEX_UNIT_SP, 16f)
            gravity = Gravity.CENTER
            setPadding(0, dp(10f).toInt(), 0, 0)
            maxLines = 3
        }
        raiz.addView(titulo)
        raiz.addView(View(this), LinearLayout.LayoutParams(1, 0, 1f)) // empuja los botones abajo
        botonPosponer = boton("Posponer", false) { enviar(DespertadorServicio.POSPONER); finish() }
        raiz.addView(botonPosponer)
        raiz.addView(boton("Apagar", true) { enviar(DespertadorServicio.APAGAR); finish() })
        botonSeguir = Button(this).apply {
            text = "Apagar y seguir escuchando"
            isAllCaps = false
            setTextColor(acento)
            setBackgroundColor(Color.TRANSPARENT)
            setTextSize(TypedValue.COMPLEX_UNIT_SP, 15f)
            setOnClickListener { seguirEscuchando() }
        }
        raiz.addView(botonSeguir)
        return raiz
    }

    private fun pintar() {
        val s = DespertadorServicio.actual
        if (s == null) {
            if (esperandoDesbloqueo) return
            if (!isFinishing) manos.postDelayed({ if (DespertadorServicio.actual == null) finish() }, 400)
            return
        }
        etiqueta?.text = s.etiqueta.ifEmpty { "Buenos días" }
        titulo?.text = s.titulo
        botonPosponer?.text = "Posponer ${s.posponer} min"
        botonSeguir?.visibility = if (s.tono) View.GONE else View.VISIBLE
    }

    private fun enviar(accion: String) {
        try {
            startService(Intent(this, DespertadorServicio::class.java).setAction(accion))
        } catch (_: Exception) {
        }
    }

    /** Apaga la alarma, desbloquea (si hace falta) y abre Caudal, que sigue con la música de la alarma. */
    private fun seguirEscuchando() {
        esperandoDesbloqueo = true
        enviar(DespertadorServicio.SEGUIR)
        val abrir = packageManager.getLaunchIntentForPackage(packageName)?.apply {
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_REORDER_TO_FRONT)
        }
        val km = getSystemService(Context.KEYGUARD_SERVICE) as KeyguardManager
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O && km.isKeyguardLocked) {
            km.requestDismissKeyguard(this, object : KeyguardManager.KeyguardDismissCallback() {
                override fun onDismissSucceeded() {
                    abrir?.let { startActivity(it) }
                    finish()
                }

                override fun onDismissCancelled() {
                    finish()
                }

                override fun onDismissError() {
                    finish()
                }
            })
        } else {
            abrir?.let { startActivity(it) }
            finish()
        }
    }
}
