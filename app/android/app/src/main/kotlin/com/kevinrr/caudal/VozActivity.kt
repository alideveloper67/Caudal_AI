package com.kevinrr.caudal

import android.app.Activity
import android.app.SearchManager
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.provider.MediaStore

/**
 * Puerta de entrada de la voz, sin pantalla propia. Convierte lo que manda el
 * asistente de Google en un enlace caudal://... y se lo pasa a la actividad
 * principal, que ya sabe abrir esos enlaces:
 *
 *  - «Ok Google, pon <canción> en Caudal» (MEDIA_PLAY_FROM_SEARCH) -> caudal://sonar?q=...
 *  - «Ok Google, busca <algo> en Caudal» (SEARCH_ACTION / SEARCH)  -> caudal://buscar?q=...
 *
 * Con Caudal ya sonando, el asistente le habla directo a la sesión de música
 * (playFromSearch de ServicioAudio) y esta actividad ni se abre.
 */
class VozActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val enlace = enlaceDe(intent)
        if (enlace != null) {
            startActivity(Intent(this, MainActivity::class.java).apply {
                action = Intent.ACTION_VIEW
                data = Uri.parse(enlace)
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP)
            })
        }
        finish()
    }

    private fun enlaceDe(intent: Intent?): String? {
        val consulta = (intent?.getStringExtra(SearchManager.QUERY) ?: "").trim()
        return when (intent?.action) {
            MediaStore.INTENT_ACTION_MEDIA_PLAY_FROM_SEARCH ->
                if (consulta.isEmpty()) "caudal://sonar" else "caudal://sonar?q=" + Uri.encode(consulta)
            Intent.ACTION_SEARCH, "com.google.android.gms.actions.SEARCH_ACTION" ->
                if (consulta.isEmpty()) "caudal://buscar" else "caudal://buscar?q=" + Uri.encode(consulta)
            else -> null
        }
    }
}
