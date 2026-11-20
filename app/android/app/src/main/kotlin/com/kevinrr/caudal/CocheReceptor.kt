package com.kevinrr.caudal

import android.bluetooth.BluetoothDevice
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

/**
 * Se entera de que se conectó un Bluetooth aunque Caudal esté cerrado (las
 * conexiones ACL son de los avisos que Android sigue entregando a los receptores
 * del manifiesto). Si es el coche que se eligió en Ajustes > Modo coche y Caudal
 * no está a la vista, deja un aviso: con un toque se abre el modo coche.
 *
 * Lo elegido lo guarda Dart con shared_preferences: archivo FlutterSharedPreferences,
 * claves con el prefijo "flutter.".
 */
class CocheReceptor : BroadcastReceiver() {
    override fun onReceive(contexto: Context, intent: Intent) {
        when (intent.action) {
            BluetoothDevice.ACTION_ACL_CONNECTED -> alConectar(contexto, intent)
            BluetoothDevice.ACTION_ACL_DISCONNECTED -> {
                val d = CocheBluetooth.dispositivoDe(intent) ?: return
                if (elegido(contexto, d.address ?: "")) CocheBluetooth.quitarAviso(contexto)
            }
        }
    }

    private fun alConectar(contexto: Context, intent: Intent) {
        // con Caudal a la vista lo atiende Dart (abre el modo coche al momento)
        if (CocheBluetooth.actividadVisible) return
        val prefs = contexto.getSharedPreferences("FlutterSharedPreferences", Context.MODE_PRIVATE)
        if (!prefs.getBoolean("flutter.coche_abrir_solo", false)) return
        val d = CocheBluetooth.dispositivoDe(intent) ?: return
        val direccion = d.address ?: return
        if (!elegido(contexto, direccion)) return
        val nombre = CocheBluetooth.nombreDe(d).ifBlank { nombreGuardado(contexto, direccion) }
        CocheBluetooth.notificar(contexto, nombre)
    }

    private fun lineas(contexto: Context): List<Pair<String, String>> {
        val prefs = contexto.getSharedPreferences("FlutterSharedPreferences", Context.MODE_PRIVATE)
        val texto = prefs.getString("flutter.coche_dispositivos", "") ?: ""
        return texto.split('\n').mapNotNull { linea ->
            val i = linea.indexOf('|')
            val dir = (if (i < 0) linea else linea.substring(0, i)).trim().uppercase()
            if (dir.isEmpty()) null else dir to (if (i < 0) "" else linea.substring(i + 1))
        }
    }

    private fun elegido(contexto: Context, direccion: String): Boolean =
        lineas(contexto).any { it.first == direccion.uppercase() }

    private fun nombreGuardado(contexto: Context, direccion: String): String =
        lineas(contexto).firstOrNull { it.first == direccion.uppercase() }?.second ?: ""
}
