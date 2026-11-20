package com.kevinrr.caudal

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import androidx.core.content.ContextCompat

/**
 * Llega la hora de una alarma (AlarmManager) -> arranca DespertadorServicio, que la hace sonar.
 * Tambien vuelve a programarlas todas al reiniciar el telefono, al cambiar la hora o la zona horaria,
 * al actualizar Caudal y al dar el permiso de «Alarmas y recordatorios».
 */
class DespertadorReceptor : BroadcastReceiver() {
    companion object {
        const val SONAR = "com.kevinrr.caudal.despertador.SONAR"
    }

    override fun onReceive(contexto: Context, intent: Intent) {
        when (intent.action) {
            SONAR -> {
                val id = intent.getStringExtra("id") ?: return
                val i = Intent(contexto, DespertadorServicio::class.java)
                    .setAction(DespertadorServicio.SONAR)
                    .putExtra("id", id)
                try {
                    // permitido desde segundo plano: lo dispara una alarma exacta (setAlarmClock)
                    ContextCompat.startForegroundService(contexto, i)
                } catch (_: Exception) {
                    // muy raro (Android no dejo): que al menos la proxima siga programada
                    Despertador.programarTodas(contexto)
                }
            }
            else -> Despertador.programarTodas(contexto)
        }
    }
}
