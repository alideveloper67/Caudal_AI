import 'dart:convert';
import 'dart:math';

/// Ecualizador avanzado (donadores y fundadores): 15 bandas, preamplificador, ajustes guardados
/// con nombre y un ajuste para cada salida (audífonos, parlante, bluetooth) que entra solo al
/// cambiar de salida. Mismas reglas que Caudal Escritorio (`eq_avanzado.py`).
///
/// El ecualizador normal (10 bandas) sigue igual para todos. Sin beneficios el avanzado no suena
/// aunque esté guardado, y la pantalla lo muestra con candado.
const frecuenciasAvanzado = [25, 40, 63, 100, 160, 250, 400, 630, 1000, 1600, 2500, 4000, 6300, 10000, 16000];
const etiquetasAvanzado = ['25', '40', '63', '100', '160', '250', '400', '630', '1k', '1,6k', '2,5k', '4k', '6,3k', '10k', '16k'];
const anchoOctavas = 0.67;
const rangoBanda = 12.0;
const pasoBanda = 0.5;
const preampMinimo = -12.0;
const preampMaximo = 6.0;
const maxGuardados = 30;
const largoNombre = 32;

const salidaAudifonos = 'audifonos';
const salidaParlante = 'parlante';
const salidaBluetooth = 'bluetooth';
const tiposSalida = [salidaAudifonos, salidaParlante, salidaBluetooth];
const nombresSalida = {salidaAudifonos: 'Audífonos', salidaParlante: 'Parlante', salidaBluetooth: 'Bluetooth'};

/// Puntos de partida (se pueden cambiar y guardar con otro nombre).
const inicialesAvanzado = <String, (List<double>, double)>{
  'Audífonos cálidos': ([2, 2.5, 2, 1, 0, 0, -0.5, -0.5, 0, 0.5, 1, 1, 0.5, 0, -0.5], -2.5),
  'Parlante pequeño': ([-6, -5, -3, 0, 2, 3, 2.5, 2, 1.5, 1, 1, 1.5, 1, 0, -1], -3.0),
  'Bluetooth claro': ([1, 1, 1, 0.5, 0, -0.5, -0.5, 0, 0.5, 1, 1.5, 2, 2, 1.5, 1], -2.0),
};

double _num(Object? v) {
  if (v is num && v.isFinite) return v.toDouble();
  if (v is String) return double.tryParse(v) ?? 0;
  return 0;
}

double _redondear(double v) => (v / pasoBanda).roundToDouble() * pasoBanda;

List<double> limpiarBandas(Object? bandas) {
  final lista = bandas is List ? bandas : const [];
  return [
    for (var i = 0; i < frecuenciasAvanzado.length; i++)
      _redondear((i < lista.length ? _num(lista[i]) : 0).clamp(-rangoBanda, rangoBanda).toDouble()),
  ];
}

double limpiarPreamp(Object? v) => _redondear(_num(v).clamp(preampMinimo, preampMaximo).toDouble());

String limpiarNombre(String nombre) {
  final t = nombre.trim().split(RegExp(r'\s+')).where((p) => p.isNotEmpty).join(' ');
  return t.length > largoNombre ? t.substring(0, largoNombre) : t;
}

/// Filtros `equalizer` (el único filtro de sonido que trae el motor del teléfono) de las bandas ≠ 0.
List<String> partesFiltroAvanzado(List<double> bandas) => [
      for (var i = 0; i < frecuenciasAvanzado.length && i < bandas.length; i++)
        if (bandas[i].abs() >= 0.25)
          'equalizer=f=${frecuenciasAvanzado[i]}:t=o:w=$anchoOctavas:g=${bandas[i].toStringAsFixed(1)}',
    ];

/// dB antes del ecualizador: el preamplificador y un margen automático si hay bandas subidas.
double gananciaPrevia(List<double> bandas, double preamp) {
  final maximo = bandas.fold<double>(0, max);
  return ((limpiarPreamp(preamp) - maximo * 0.6) * 100).roundToDouble() / 100;
}

class AjusteEq {
  const AjusteEq(this.bandas, this.preamp);

  final List<double> bandas;
  final double preamp;

  Map<String, Object> aJson() => {'bandas': bandas, 'preamp': preamp};

  static AjusteEq desde(Object? v) {
    final m = v is Map ? v : const {};
    return AjusteEq(limpiarBandas(m['bandas']), limpiarPreamp(m['preamp']));
  }
}

/// Todo el estado del avanzado. Se guarda en los ajustes como texto JSON (claves `eq_av_*`).
class EstadoEqAvanzado {
  EstadoEqAvanzado({
    this.activo = false,
    List<double>? bandas,
    this.preamp = 0,
    this.nombre = '',
    Map<String, AjusteEq>? guardados,
    Map<String, String>? porSalida,
  })  : bandas = limpiarBandas(bandas),
        guardados = guardados ?? {},
        porSalida = {for (final t in tiposSalida) t: porSalida?[t] ?? ''};

  bool activo;
  List<double> bandas;
  double preamp;
  String nombre;
  final Map<String, AjusteEq> guardados;
  final Map<String, String> porSalida;

  /// Los guardados, o los de fábrica si aún no hay ninguno.
  Map<String, AjusteEq> get lista => guardados.isNotEmpty
      ? guardados
      : {for (final e in inicialesAvanzado.entries) e.key: AjusteEq(limpiarBandas(e.value.$1), e.value.$2)};

  static EstadoEqAvanzado leer({bool activo = false, String bandas = '[]', double preamp = 0,
      String nombre = '', String guardados = '{}', String porSalida = '{}'}) {
    Object? dec(String t) {
      try {
        return jsonDecode(t);
      } catch (_) {
        return null;
      }
    }
    final g = dec(guardados);
    final p = dec(porSalida);
    return EstadoEqAvanzado(
      activo: activo,
      bandas: limpiarBandas(dec(bandas)),
      preamp: limpiarPreamp(preamp),
      nombre: nombre,
      guardados: g is Map ? {for (final e in g.entries) '${e.key}': AjusteEq.desde(e.value)} : {},
      porSalida: p is Map ? {for (final e in p.entries) '${e.key}': '${e.value ?? ''}'} : {},
    );
  }

  String get bandasJson => jsonEncode(bandas);
  String get guardadosJson => jsonEncode({for (final e in guardados.entries) e.key: e.value.aJson()});
  String get porSalidaJson => jsonEncode(porSalida);

  EstadoEqAvanzado copia() => EstadoEqAvanzado(
      activo: activo, bandas: List.of(bandas), preamp: preamp, nombre: nombre,
      guardados: Map.of(guardados), porSalida: Map.of(porSalida));

  /// Guarda (o sobrescribe) un ajuste con nombre. Devuelve el nombre limpio, o '' si no vale.
  String guardarComo(String nombre) {
    final n = limpiarNombre(nombre);
    if (n.isEmpty) return '';
    final todos = Map.of(lista);
    if (!todos.containsKey(n) && todos.length >= maxGuardados) return '';
    todos[n] = AjusteEq(List.of(bandas), preamp);
    guardados
      ..clear()
      ..addAll(todos);
    this.nombre = n;
    return n;
  }

  bool cargar(String n) {
    final a = lista[n];
    if (a == null) return false;
    bandas = List.of(a.bandas);
    preamp = a.preamp;
    nombre = n;
    return true;
  }

  void borrar(String n) {
    final todos = Map.of(lista)..remove(n);
    guardados
      ..clear()
      ..addAll(todos);
    if (guardados.isEmpty) guardados['Plano'] = AjusteEq(limpiarBandas(const []), 0);
    for (final t in tiposSalida) {
      if (porSalida[t] == n) porSalida[t] = '';
    }
    if (nombre == n) nombre = '';
  }

  void asignar(String tipo, String n) {
    if (!tiposSalida.contains(tipo)) return;
    porSalida[tipo] = lista.containsKey(n) ? n : '';
  }

  /// Al cambiar la salida: si es otra y tiene un ajuste asignado, lo pone y enciende el avanzado.
  /// Devuelve el nombre puesto o null. La primera lectura (al abrir la app) solo se anota.
  String? alCambiarSalida({required bool premium, String? antes, required String ahora}) {
    if (!premium || antes == null || antes == ahora) return null;
    final n = porSalida[ahora] ?? '';
    if (n.isEmpty || !cargar(n)) return null;
    activo = true;
    return n;
  }
}
