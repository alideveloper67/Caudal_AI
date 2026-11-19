import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'premium.dart';
import 'social.dart' show CancionFav;

/// Cápsula del tiempo (donadores): eliges una canción y un mensaje hoy, y Caudal te los vuelve a enseñar
/// en la fecha elegida (por defecto, dentro de un año) con una tarjeta al abrir la app.
/// Todo se queda en este teléfono, por cuenta: no hay nada en el servidor.
class CapsulaTiempo {
  const CapsulaTiempo({
    required this.id,
    required this.cancion,
    required this.mensaje,
    required this.creada,
    required this.abre,
    this.vista,
  });

  /// Letras que admite el mensaje.
  static const maxMensaje = 400;

  final String id;
  final CancionFav cancion;
  final String mensaje;
  final DateTime creada;

  /// El día en que se abre (a las 00:00, hora del teléfono).
  final DateTime abre;

  /// Cuándo se enseñó la tarjeta (null = todavía no).
  final DateTime? vista;

  /// Ya llegó su día.
  bool lista([DateTime? ahora]) => !(ahora ?? DateTime.now()).isBefore(abre);

  /// Toca enseñarla: llegó su día y aún no se había visto.
  bool pendiente([DateTime? ahora]) => vista == null && lista(ahora);

  /// Días que faltan (0 = hoy; los días se cuentan por fecha, no por horas).
  int diasFaltan([DateTime? ahora]) {
    final h = ahora ?? DateTime.now();
    // en UTC para que el cambio de hora de verano no se coma un día
    final dias = DateTime.utc(abre.year, abre.month, abre.day).difference(DateTime.utc(h.year, h.month, h.day)).inDays;
    return dias.clamp(0, 1 << 30);
  }

  /// «Hace un año», «Hace 3 meses», «Hace 12 días», «Hoy»: desde que se guardó hasta [ahora].
  String haceCuanto([DateTime? ahora]) {
    final h = ahora ?? DateTime.now();
    // por fechas del calendario: la que se guardó el 19 de noviembre dice «un año» el 19 de noviembre siguiente
    final a = DateTime(creada.year, creada.month, creada.day), b = DateTime(h.year, h.month, h.day);
    final meses = (b.year - a.year) * 12 + b.month - a.month - (b.day < a.day ? 1 : 0);
    if (meses >= 12) {
      final anios = meses ~/ 12;
      return anios == 1 ? 'Hace un año' : 'Hace $anios años';
    }
    if (meses >= 1) return meses == 1 ? 'Hace un mes' : 'Hace $meses meses';
    final dias = DateTime.utc(b.year, b.month, b.day).difference(DateTime.utc(a.year, a.month, a.day)).inDays;
    if (dias < 1) return 'Hoy';
    return dias == 1 ? 'Hace un día' : 'Hace $dias días';
  }

  CapsulaTiempo conVista(DateTime? cuando) => CapsulaTiempo(
      id: id, cancion: cancion, mensaje: mensaje, creada: creada, abre: abre, vista: cuando);

  Map<String, Object?> aJson() => {
        'id': id,
        'cancion': cancion.toJson(),
        'mensaje': mensaje,
        'creada': creada.toUtc().toIso8601String(),
        'abre': '${abre.year.toString().padLeft(4, '0')}-${abre.month.toString().padLeft(2, '0')}-${abre.day.toString().padLeft(2, '0')}',
        'vista': vista?.toUtc().toIso8601String(),
      };

  /// Tolerante: una entrada rota se descarta (nulo) sin llevarse las demás.
  static CapsulaTiempo? desde(Object? v) {
    if (v is! Map) return null;
    final c = CancionFav.desde(v['cancion']);
    final id = '${v['id'] ?? ''}';
    final abre = DateTime.tryParse('${v['abre'] ?? ''}');
    final creada = DateTime.tryParse('${v['creada'] ?? ''}')?.toLocal();
    if (c == null || c.videoId.isEmpty || id.isEmpty || abre == null || creada == null) return null;
    return CapsulaTiempo(
      id: id,
      cancion: c,
      mensaje: limpiarMensaje('${v['mensaje'] ?? ''}'),
      creada: creada,
      abre: DateTime(abre.year, abre.month, abre.day),
      vista: v['vista'] == null ? null : DateTime.tryParse('${v['vista']}')?.toLocal(),
    );
  }

  static String limpiarMensaje(String t) {
    final limpio = t.replaceAll('\r', '').replaceAll(RegExp(r'\n{3,}'), '\n\n').trim();
    return limpio.length <= maxMensaje ? limpio : limpio.substring(0, maxMensaje).trimRight();
  }

  /// El mismo día del año que viene. Un 29 de febrero cae en el 28 si el año siguiente no es bisiesto.
  static DateTime unAnioDespues(DateTime d) {
    final y = d.year + 1;
    final ultimo = DateTime(y, d.month + 1, 0).day;
    return DateTime(y, d.month, d.day > ultimo ? ultimo : d.day);
  }

  /// El mismo día [n] meses después; si ese mes no tiene ese día (31 de enero + 1 mes), cae en el último.
  static DateTime masMeses(DateTime d, int n) {
    final total = d.year * 12 + (d.month - 1) + n;
    final y = total ~/ 12, m = total % 12 + 1;
    final ultimo = DateTime(y, m + 1, 0).day;
    return DateTime(y, m, d.day > ultimo ? ultimo : d.day);
  }

  /// Lo más lejos que se puede programar (10 años).
  static DateTime masLejos([DateTime? ahora]) {
    final h = ahora ?? DateTime.now();
    return DateTime(h.year + 10, h.month, h.day);
  }

  /// La fecha más cercana permitida: mañana.
  static DateTime manana([DateTime? ahora]) {
    final h = ahora ?? DateTime.now();
    return DateTime(h.year, h.month, h.day + 1);
  }
}

/// Por qué no se pudo guardar una cápsula.
enum ProblemaCapsula { sinPremium, sinCancion, fechaPasada, fechaLejana, llena }

class ResultadoCapsula {
  const ResultadoCapsula.ok(this.capsula) : problema = null;
  const ResultadoCapsula.mal(ProblemaCapsula this.problema) : capsula = null;
  final CapsulaTiempo? capsula;
  final ProblemaCapsula? problema;
  bool get ok => capsula != null;

  String get mensaje => switch (problema) {
        null => '',
        ProblemaCapsula.sinPremium => 'Las cápsulas del tiempo son exclusivas de donadores.',
        ProblemaCapsula.sinCancion => 'Elige la canción que quieres guardar.',
        ProblemaCapsula.fechaPasada => 'Elige una fecha a partir de mañana.',
        ProblemaCapsula.fechaLejana => 'La fecha más lejana son 10 años.',
        ProblemaCapsula.llena => 'Ya guardaste ${CapsulasTiempo.maximo} cápsulas, que es el máximo. Borra alguna para crear otra.',
      };
}

/// Las cápsulas de esta cuenta en este teléfono. Una sola instancia ([CapsulasTiempo.i]).
class CapsulasTiempo extends ChangeNotifier {
  CapsulasTiempo._();
  static final CapsulasTiempo i = CapsulasTiempo._();

  /// Cuántas se pueden tener a la vez.
  static const maximo = 24;

  String _cuenta = '';
  List<CapsulaTiempo> _todas = const [];
  int _serie = 0;

  String get cuenta => _cuenta;

  /// Las que faltan por abrir, la más cercana primero; después las ya vistas, la más reciente primero.
  List<CapsulaTiempo> get todas => _todas;

  List<CapsulaTiempo> get guardadas => [for (final c in _todas) if (c.vista == null) c];
  List<CapsulaTiempo> get vistas => [for (final c in _todas) if (c.vista != null) c];

  /// Las que ya llegaron a su día y esperan su tarjeta (la más antigua primero).
  List<CapsulaTiempo> pendientes([DateTime? ahora]) => [for (final c in _todas) if (c.pendiente(ahora)) c];

  String get _llave => 'capsulas_tiempo_$_cuenta';

  static List<CapsulaTiempo> _ordenar(Iterable<CapsulaTiempo> l) {
    final lista = l.toList();
    lista.sort((a, b) {
      final va = a.vista != null, vb = b.vista != null;
      if (va != vb) return va ? 1 : -1;
      return va ? b.vista!.compareTo(a.vista!) : a.abre.compareTo(b.abre);
    });
    return lista;
  }

  /// Al entrar a una cuenta: lo guardado en el teléfono.
  Future<void> iniciar(String cuenta) async {
    _cuenta = cuenta;
    _todas = const [];
    if (cuenta.isEmpty) {
      notifyListeners();
      return;
    }
    try {
      final p = await SharedPreferences.getInstance();
      final t = p.getString(_llave);
      if (t != null) {
        final d = jsonDecode(t);
        if (d is List) _todas = _ordenar([for (final x in d) ?CapsulaTiempo.desde(x)]);
      }
    } catch (_) {
      _todas = const [];
    }
    notifyListeners();
  }

  Future<void> _guardar() async {
    if (_cuenta.isEmpty) return;
    try {
      final p = await SharedPreferences.getInstance();
      await p.setString(_llave, jsonEncode([for (final c in _todas) c.aJson()]));
    } catch (_) {}
  }

  /// Guarda una cápsula nueva. [abre] es la fecha elegida (por defecto, dentro de un año).
  Future<ResultadoCapsula> crear({
    required CancionFav? cancion,
    required String mensaje,
    DateTime? abre,
    DateTime? ahora,
    bool? premium,
  }) async {
    final h = ahora ?? DateTime.now();
    if (!(premium ?? Premium.i.activo)) return const ResultadoCapsula.mal(ProblemaCapsula.sinPremium);
    if (cancion == null || cancion.videoId.isEmpty) return const ResultadoCapsula.mal(ProblemaCapsula.sinCancion);
    final fecha = abre ?? CapsulaTiempo.unAnioDespues(h);
    final dia = DateTime(fecha.year, fecha.month, fecha.day);
    if (dia.isBefore(CapsulaTiempo.manana(h))) return const ResultadoCapsula.mal(ProblemaCapsula.fechaPasada);
    if (dia.isAfter(CapsulaTiempo.masLejos(h))) return const ResultadoCapsula.mal(ProblemaCapsula.fechaLejana);
    if (guardadas.length >= maximo) return const ResultadoCapsula.mal(ProblemaCapsula.llena);
    final c = CapsulaTiempo(
      id: '${h.microsecondsSinceEpoch}-${_serie++}',
      cancion: cancion,
      mensaje: CapsulaTiempo.limpiarMensaje(mensaje),
      creada: h,
      abre: dia,
    );
    _todas = _ordenar([..._todas, c]);
    notifyListeners();
    await _guardar();
    return ResultadoCapsula.ok(c);
  }

  /// La tarjeta ya se enseñó: no vuelve a salir sola, pero se puede ver desde la lista.
  Future<void> marcarVista(String id, [DateTime? ahora]) async {
    if (!_todas.any((c) => c.id == id && c.vista == null)) return;
    _todas = _ordenar([for (final c in _todas) c.id == id ? c.conVista(ahora ?? DateTime.now()) : c]);
    notifyListeners();
    await _guardar();
  }

  Future<void> borrar(String id) async {
    if (!_todas.any((c) => c.id == id)) return;
    _todas = [for (final c in _todas) if (c.id != id) c];
    notifyListeners();
    await _guardar();
  }

  /// Al cerrar sesión: nada de la cuenta anterior se queda a la vista.
  void reiniciar() {
    _cuenta = '';
    _todas = const [];
    notifyListeners();
  }
}
