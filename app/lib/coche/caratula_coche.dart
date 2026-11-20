/// Carátulas que el coche sí puede leer.
///
/// Android Auto es otra app: no puede abrir los archivos de Caudal por su ruta
/// (`/data/...` o `file://...`), así que las carátulas guardadas en el teléfono
/// no salían en las listas del coche. Se le pasan como `content://` a través de
/// `CaratulaProveedor.kt`, que solo entrega imágenes de las carpetas de Caudal.
library;

/// La autoridad del proveedor de `AndroidManifest.xml` (`${applicationId}.caratulas`).
const autoridadCaratulas = 'com.kevinrr.caudal.caratulas';

const _extensiones = {'jpg', 'jpeg', 'png', 'webp'};

/// La dirección de la carátula [arte] para el coche, o `null` si no hay una que sirva.
///
///  * `http(s)://...` va tal cual (el coche la descarga).
///  * `content://...` va tal cual.
///  * una ruta del teléfono (o `file://`) de una imagen pasa por el proveedor.
Uri? uriCaratulaCoche(String? arte, {String autoridad = autoridadCaratulas}) {
  final a = (arte ?? '').trim();
  if (a.isEmpty || a == 'null') return null;
  final baja = a.toLowerCase();
  if (baja.startsWith('http://') || baja.startsWith('https://') || baja.startsWith('content://')) {
    return Uri.tryParse(a);
  }
  String ruta;
  if (baja.startsWith('file://')) {
    final u = Uri.tryParse(a);
    if (u == null) return null;
    ruta = u.toFilePath(windows: false);
  } else if (a.startsWith('/')) {
    ruta = a;
  } else {
    return null;
  }
  if (ruta.contains('/../') || ruta.endsWith('/..')) return null;
  final punto = ruta.lastIndexOf('.');
  if (punto < 0 || !_extensiones.contains(ruta.substring(punto + 1).toLowerCase())) return null;
  return Uri(scheme: 'content', host: autoridad, path: ruta);
}
