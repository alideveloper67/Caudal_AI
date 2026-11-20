package com.kevinrr.caudal

import android.app.Activity
import android.graphics.Color
import android.graphics.Typeface
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.util.TypedValue
import android.view.Gravity
import android.view.View
import android.view.WindowManager
import android.widget.LinearLayout
import android.widget.TextView

/**
 * El verso que suena en grande, encima del bloqueo y sin desbloquear (se abre al tocar la
 * notificacion de la letra). Cambia sola con cada verso; se cierra al tocarla o cuando ya no hay letra.
 * No enciende la pantalla por su cuenta.
 */
class LetraBloqueoActivity : Activity() {
    private val manos = Handler(Looper.getMainLooper())
    private var cancion: TextView? = null
    private var linea: TextView? = null
    private var siguiente: TextView? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O_MR1) {
            setShowWhenLocked(true)
        } else {
            @Suppress("DEPRECATION")
            window.addFlags(WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED)
        }
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        val fondo = Color.parseColor("#06070A")
        window.statusBarColor = fondo
        window.navigationBarColor = fondo
        val dp = { v: Float -> TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_DIP, v, resources.displayMetrics).toInt() }
        val raiz = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setBackgroundColor(fondo)
            setPadding(dp(28f), dp(40f), dp(28f), dp(40f))
            setOnClickListener { finish() }
            contentDescription = "Letra de la canción. Toca para cerrar."
        }
        cancion = TextView(this).apply {
            setTextColor(Color.parseColor("#22D3EE"))
            setTextSize(TypedValue.COMPLEX_UNIT_SP, 14f)
            typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
            gravity = Gravity.CENTER
        }
        linea = TextView(this).apply {
            setTextColor(Color.parseColor("#F3F5F9"))
            setTextSize(TypedValue.COMPLEX_UNIT_SP, 30f)
            typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
            gravity = Gravity.CENTER
            setPadding(0, dp(24f), 0, dp(18f))
        }
        siguiente = TextView(this).apply {
            setTextColor(Color.parseColor("#8993A6"))
            setTextSize(TypedValue.COMPLEX_UNIT_SP, 20f)
            gravity = Gravity.CENTER
        }
        raiz.addView(cancion)
        raiz.addView(linea)
        raiz.addView(siguiente)
        setContentView(raiz)
        LetraPantallaBloqueo.alCambiar = { manos.post { pintar() } }
        pintar()
    }

    override fun onDestroy() {
        LetraPantallaBloqueo.alCambiar = null
        manos.removeCallbacksAndMessages(null)
        super.onDestroy()
    }

    private fun pintar() {
        val v = LetraPantallaBloqueo.actual
        if (v == null) {
            finish()
            return
        }
        cancion?.text = listOf(v.titulo, v.artista).filter { it.isNotBlank() }.joinToString(" · ")
        linea?.text = v.linea
        siguiente?.text = v.siguiente
        siguiente?.visibility = if (v.siguiente.isBlank()) View.GONE else View.VISIBLE
    }
}
