package com.kevinrr.caudal

import android.Manifest
import android.app.Activity
import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothClass
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothManager
import android.bluetooth.BluetoothProfile
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.EventChannel
import io.flutter.plugin.common.MethodChannel

/**
 * El Bluetooth del coche para el «modo coche»:
 *  - canal `caudal/coche`: si hay permiso, los aparatos emparejados y los conectados;
 *  - canal de eventos `caudal/coche/eventos`: cada vez que uno se conecta o se desconecta.
 *
 * Con Caudal a la vista, Dart decide y abre el modo coche. Con Caudal de fondo o
 * cerrado, Android no deja abrir pantallas solas: [CocheReceptor] deja un aviso
 * que con un toque abre caudal://coche.
 */
object CocheBluetooth {
    private const val CANAL_AVISO = "caudal_coche"
    private const val ID_AVISO = 4207

    /** true mientras la pantalla de Caudal se ve (entonces el aviso sobra). */
    @Volatile
    var actividadVisible = false
        private set

    private var vigilandoActividades = false

    fun registrar(flutterEngine: FlutterEngine, contexto: Context) {
        val app = contexto.applicationContext
        vigilarActividades(app)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "caudal/coche")
            .setMethodCallHandler { llamada, resultado ->
                when (llamada.method) {
                    "permiso" -> resultado.success(hayPermiso(app))
                    "emparejados" -> resultado.success(emparejados(app))
                    "conectados" -> conectados(app) { resultado.success(it) }
                    else -> resultado.notImplemented()
                }
            }
        EventChannel(flutterEngine.dartExecutor.binaryMessenger, "caudal/coche/eventos")
            .setStreamHandler(object : EventChannel.StreamHandler {
                private var receptor: BroadcastReceiver? = null

                override fun onListen(arguments: Any?, sumidero: EventChannel.EventSink?) {
                    val r = object : BroadcastReceiver() {
                        override fun onReceive(c: Context?, intent: Intent?) {
                            val conectado = when (intent?.action) {
                                BluetoothDevice.ACTION_ACL_CONNECTED -> true
                                BluetoothDevice.ACTION_ACL_DISCONNECTED -> false
                                else -> return
                            }
                            val d = dispositivoDe(intent) ?: return
                            val m = HashMap(mapa(d))
                            m["evento"] = if (conectado) "conectado" else "desconectado"
                            sumidero?.success(m)
                        }
                    }
                    val filtro = IntentFilter().apply {
                        addAction(BluetoothDevice.ACTION_ACL_CONNECTED)
                        addAction(BluetoothDevice.ACTION_ACL_DISCONNECTED)
                    }
                    try {
                        // los envía el servicio de Bluetooth (otra app del sistema): tiene que ser EXPORTED
                        ContextCompat.registerReceiver(app, r, filtro, ContextCompat.RECEIVER_EXPORTED)
                        receptor = r
                    } catch (_: Exception) {
                    }
                }

                override fun onCancel(arguments: Any?) {
                    receptor?.let {
                        try {
                            app.unregisterReceiver(it)
                        } catch (_: Exception) {
                        }
                    }
                    receptor = null
                }
            })
    }

    private fun vigilarActividades(app: Context) {
        if (vigilandoActividades) return
        val aplicacion = app as? Application ?: return
        vigilandoActividades = true
        aplicacion.registerActivityLifecycleCallbacks(object : Application.ActivityLifecycleCallbacks {
            override fun onActivityResumed(a: Activity) {
                actividadVisible = true
                // ya se ve Caudal: el aviso del coche sobra
                try {
                    NotificationManagerCompat.from(a).cancel(ID_AVISO)
                } catch (_: Exception) {
                }
            }

            override fun onActivityPaused(a: Activity) {
                actividadVisible = false
            }

            override fun onActivityCreated(a: Activity, b: Bundle?) {}
            override fun onActivityStarted(a: Activity) {}
            override fun onActivityStopped(a: Activity) {}
            override fun onActivitySaveInstanceState(a: Activity, b: Bundle) {}
            override fun onActivityDestroyed(a: Activity) {}
        })
    }

    fun hayPermiso(c: Context): Boolean =
        Build.VERSION.SDK_INT < Build.VERSION_CODES.S ||
            ContextCompat.checkSelfPermission(c, Manifest.permission.BLUETOOTH_CONNECT) == PackageManager.PERMISSION_GRANTED

    private fun adaptador(c: Context): BluetoothAdapter? = try {
        (c.getSystemService(Context.BLUETOOTH_SERVICE) as? BluetoothManager)?.adapter
    } catch (_: Exception) {
        null
    }

    private fun emparejados(c: Context): List<Map<String, Any>> {
        if (!hayPermiso(c)) return emptyList()
        return try {
            adaptador(c)?.bondedDevices?.map { mapa(it) } ?: emptyList()
        } catch (_: SecurityException) {
            emptyList()
        }
    }

    /** Los que suenan conectados ahora (A2DP y manos libres), sin repetir. */
    private fun conectados(c: Context, listo: (List<Map<String, Any>>) -> Unit) {
        val principal = Handler(Looper.getMainLooper())
        val a = adaptador(c)
        if (a == null || !hayPermiso(c)) {
            listo(emptyList())
            return
        }
        val perfiles = listOf(BluetoothProfile.A2DP, BluetoothProfile.HEADSET)
        val hallados = LinkedHashMap<String, Map<String, Any>>()
        var faltan = perfiles.size
        var respondido = false
        fun terminar() {
            if (respondido) return
            respondido = true
            listo(hallados.values.toList())
        }
        // si un perfil no contesta, no se queda esperando para siempre
        principal.postDelayed({ terminar() }, 2500)
        for (perfil in perfiles) {
            val ok = try {
                a.getProfileProxy(c, object : BluetoothProfile.ServiceListener {
                    override fun onServiceConnected(p: Int, proxy: BluetoothProfile) {
                        try {
                            for (d in proxy.connectedDevices) hallados[d.address] = mapa(d)
                        } catch (_: SecurityException) {
                        }
                        try {
                            a.closeProfileProxy(p, proxy)
                        } catch (_: Exception) {
                        }
                        principal.post {
                            faltan--
                            if (faltan <= 0) terminar()
                        }
                    }

                    override fun onServiceDisconnected(p: Int) {}
                }, perfil)
            } catch (_: Exception) {
                false
            }
            if (!ok) principal.post {
                faltan--
                if (faltan <= 0) terminar()
            }
        }
    }

    fun dispositivoDe(intent: Intent): BluetoothDevice? = try {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            intent.getParcelableExtra(BluetoothDevice.EXTRA_DEVICE, BluetoothDevice::class.java)
        } else {
            @Suppress("DEPRECATION")
            intent.getParcelableExtra(BluetoothDevice.EXTRA_DEVICE)
        }
    } catch (_: Exception) {
        null
    }

    fun nombreDe(d: BluetoothDevice): String = try {
        d.name ?: ""
    } catch (_: SecurityException) {
        ""
    }

    private fun mapa(d: BluetoothDevice): Map<String, Any> {
        val clase = try {
            d.bluetoothClass
        } catch (_: SecurityException) {
            null
        }
        val coche = clase?.deviceClass == BluetoothClass.Device.AUDIO_VIDEO_CAR_AUDIO ||
            clase?.deviceClass == BluetoothClass.Device.AUDIO_VIDEO_HANDSFREE
        val audio = clase?.majorDeviceClass == BluetoothClass.Device.Major.AUDIO_VIDEO
        return mapOf(
            "direccion" to (d.address ?: ""),
            "nombre" to nombreDe(d),
            "coche" to coche,
            "audio" to audio,
        )
    }

    // ---------- el aviso con Caudal cerrado ----------

    fun notificar(c: Context, nombre: String) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            ContextCompat.checkSelfPermission(c, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) return
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val gestor = c.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            if (gestor.getNotificationChannel(CANAL_AVISO) == null) {
                gestor.createNotificationChannel(
                    NotificationChannel(CANAL_AVISO, "Modo coche", NotificationManager.IMPORTANCE_HIGH).apply {
                        description = "Aviso para abrir el modo coche al conectar el Bluetooth del coche"
                        setSound(null, null)
                    }
                )
            }
        }
        val abrir = Intent(c, MainActivity::class.java).apply {
            action = Intent.ACTION_VIEW
            data = Uri.parse("caudal://coche")
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP)
        }
        val pendiente = PendingIntent.getActivity(
            c, ID_AVISO, abrir, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        val donde = if (nombre.isBlank()) "al coche" else "a $nombre"
        val aviso = NotificationCompat.Builder(c, CANAL_AVISO)
            .setSmallIcon(R.drawable.ic_notificacion)
            .setContentTitle("Modo coche")
            .setContentText("Conectado $donde. Toca para abrir el modo coche.")
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setCategory(NotificationCompat.CATEGORY_RECOMMENDATION)
            .setContentIntent(pendiente)
            .setAutoCancel(true)
            .setTimeoutAfter(20 * 60 * 1000L)
            .build()
        try {
            NotificationManagerCompat.from(c).notify(ID_AVISO, aviso)
        } catch (_: SecurityException) {
        }
    }

    fun quitarAviso(c: Context) {
        try {
            NotificationManagerCompat.from(c).cancel(ID_AVISO)
        } catch (_: Exception) {
        }
    }
}
