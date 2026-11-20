package com.kevinrr.caudal

import android.content.ContentProvider
import android.content.ContentValues
import android.content.Context
import android.database.Cursor
import android.net.Uri
import android.os.ParcelFileDescriptor
import java.io.File
import java.io.FileNotFoundException

/**
 * Entrega las carátulas guardadas en el teléfono a Android Auto (otra app, que
 * no puede abrir los archivos de Caudal por su ruta). Dart arma las direcciones
 * con `uriCaratulaCoche` (lib/coche/caratula_coche.dart):
 *
 *     content://com.kevinrr.caudal.caratulas/<ruta absoluta de la imagen>
 *
 * Solo lectura, solo imágenes y solo de las carpetas de Caudal: nada más del
 * teléfono sale por aquí.
 */
class CaratulaProveedor : ContentProvider() {
    override fun onCreate(): Boolean = true

    override fun openFile(uri: Uri, mode: String): ParcelFileDescriptor {
        if (mode != "r") throw SecurityException("Las carátulas son de solo lectura")
        val c = context ?: throw FileNotFoundException()
        val ruta = uri.path ?: throw FileNotFoundException()
        val archivo = File(ruta).canonicalFile
        if (!permitido(c, archivo)) throw FileNotFoundException("No es una carátula de Caudal")
        return ParcelFileDescriptor.open(archivo, ParcelFileDescriptor.MODE_READ_ONLY)
    }

    override fun getType(uri: Uri): String? = when (extension(uri.path ?: "")) {
        "jpg", "jpeg" -> "image/jpeg"
        "png" -> "image/png"
        "webp" -> "image/webp"
        else -> null
    }

    override fun query(
        uri: Uri, projection: Array<out String>?, selection: String?,
        selectionArgs: Array<out String>?, sortOrder: String?
    ): Cursor? = null

    override fun insert(uri: Uri, values: ContentValues?): Uri? = null
    override fun delete(uri: Uri, selection: String?, selectionArgs: Array<out String>?): Int = 0
    override fun update(uri: Uri, values: ContentValues?, selection: String?, selectionArgs: Array<out String>?): Int = 0

    companion object {
        private val imagenes = setOf("jpg", "jpeg", "png", "webp")

        private fun extension(ruta: String): String = ruta.substringAfterLast('.', "").lowercase()

        /** Las carpetas donde Caudal guarda cosas suyas. */
        private fun raices(c: Context): List<File> {
            val r = mutableListOf<File>()
            r.add(File(c.applicationInfo.dataDir))
            try {
                c.getExternalFilesDirs(null).filterNotNull().forEach { it.parentFile?.let(r::add) }
            } catch (_: Exception) {
            }
            try {
                c.externalCacheDirs.filterNotNull().forEach { r.add(it) }
            } catch (_: Exception) {
            }
            // las descargas públicas de Caudal (Descargas/Caudal)
            r.add(File("/storage/emulated/0/Download/Caudal"))
            r.add(File("/sdcard/Download/Caudal"))
            return r.mapNotNull {
                try {
                    it.canonicalFile
                } catch (_: Exception) {
                    null
                }
            }
        }

        fun permitido(c: Context, archivo: File): Boolean {
            if (extension(archivo.name) !in imagenes || !archivo.isFile) return false
            val ruta = archivo.path
            return raices(c).any { ruta.startsWith(it.path + File.separator) }
        }
    }
}
