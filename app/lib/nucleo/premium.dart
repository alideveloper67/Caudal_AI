import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'coleccion.dart' show Json;
import 'cosmeticos.dart';
import 'letras_cache.dart' show lineasConTiempo;
import 'mixes.dart' show Escucha;
import 'nube.dart';
import 'social.dart';
import 'vida_app.dart';

/// Lo que dice el servidor sobre los beneficios de la cuenta (`mi_premium`).
class EstadoPremium {
  const EstadoPremium({this.premium = false, this.tipo = '', this.vence});

  /// ¿Tiene los beneficios de donador ahora mismo?
  final bool premium;

  /// donador, fundador o prueba ('' si no tiene).
  final String tipo;

  /// Cuándo se acaban (solo las pruebas vencen; null = sin fecha).
  final DateTime? vence;

  static const ninguno = EstadoPremium();

  bool get esPrueba => tipo == 'prueba';

  /// Vigente a [ahora]: el servidor lo dice, pero una prueba guardada en el teléfono
  /// también se corta sola cuando pasa su fecha, aunque no haya internet.
  bool vigente([DateTime? ahora]) {
    if (!premium) return false;
    final v = vence;
    return v == null || v.isAfter(ahora ?? DateTime.now());
  }

  /// Días que quedan (se redondea hacia arriba: «hoy vence» es 1). Null sin fecha.
  int? diasRestantes([DateTime? ahora]) {
    final v = vence;
    if (v == null) return null;
    final ms = v.difference(ahora ?? DateTime.now()).inMilliseconds;
    return ms <= 0 ? 0 : (ms / Duration.millisecondsPerDay).ceil();
  }

  /// Una prueba a punto de acabarse (quedan [dias] días o menos).
  bool pocaPrueba({int dias = 2, DateTime? ahora}) {
    if (!esPrueba || !vigente(ahora)) return false;
    final d = diasRestantes(ahora);
    return d != null && d <= dias;
  }

  static EstadoPremium desde(Object? v) {
    final m = v is List && v.isNotEmpty ? v.first : v;
    if (m is! Map) return ninguno;
    final premium = m['premium'] == true;
    final tipo = '${m['tipo'] ?? ''}'.trim().toLowerCase();
    return EstadoPremium(
      premium: premium,
      tipo: premium ? tipo : '',
      vence: m['vence'] == null ? null : DateTime.tryParse('${m['vence']}')?.toLocal(),
    );
  }

  Map<String, Object?> aJson() =>
      {'premium': premium, 'tipo': tipo, 'vence': vence?.toUtc().toIso8601String()};

  @override
  bool operator ==(Object other) =>
      other is EstadoPremium &&
      other.premium == premium &&
      other.tipo == tipo &&
      // el mismo instante, venga en UTC o en hora local
      other.vence?.millisecondsSinceEpoch == vence?.millisecondsSinceEpoch;

  @override
  int get hashCode => Object.hash(premium, tipo, vence?.millisecondsSinceEpoch);
}

/// La respuesta de `canjear_pase`.
class ResultadoPase {
  const ResultadoPase({required this.ok, required this.mensaje, this.dias = 0, this.vence});
  final bool ok;
  final String mensaje;
  final int dias;
  final DateTime? vence;

  static ResultadoPase desde(Object? v) {
    final m = v is List && v.isNotEmpty ? v.first : v;
    if (m is! Map) return const ResultadoPase(ok: false, mensaje: 'No se pudo canjear el código. Inténtalo otra vez.');
    final dias = m['dias'];
    return ResultadoPase(
      ok: m['ok'] == true,
      mensaje: '${m['mensaje'] ?? ''}'.trim(),
      dias: dias is num ? dias.toInt() : int.tryParse('${dias ?? ''}') ?? 0,
      vence: m['vence'] == null ? null : DateTime.tryParse('${m['vence']}')?.toLocal(),
    );
  }
}

/// Los beneficios de donador de esta cuenta y lo que personalizó con ellos: marco del
/// avatar, efecto del nombre y tema de color. Una sola instancia ([Premium.i]); al cambiar
/// repinta lo que escucha.
///
/// El servidor manda (`mi_premium`, `canjear_pase`); aquí solo se pregunta y se recuerda en
/// el teléfono para que, sin internet, lo último que se supo siga valiendo (una prueba se
/// corta sola cuando pasa su fecha).
class Premium extends ChangeNotifier {
  Premium._();
  static final Premium i = Premium._();

  EstadoPremium estado = EstadoPremium.ninguno;

  /// Lo elegido, tal cual está guardado (puede haber elecciones de cuando era premium).
  String marco = Cosmeticos.ninguno;
  String efectoNombre = Cosmeticos.ninguno;
  String tema = Cosmeticos.ninguno;

  /// Color propio del nombre («#RRGGBB») o null. Se guarda aunque se acaben los beneficios.
  String? colorNombre;

  /// ¿Aparece en la pared de agradecimiento? (casilla del perfil, apagada por defecto).
  bool enPared = false;

  String _cuenta = '';

  bool get activo => estado.vigente();

  /// Lo que de verdad se ve: sin beneficios, todo vuelve a lo normal (sin borrar la elección).
  String get marcoEfectivo => activo ? marco : Cosmeticos.ninguno;
  String get efectoNombreEfectivo => activo ? efectoNombre : Cosmeticos.ninguno;
  String get temaEfectivo => activo ? tema : Cosmeticos.ninguno;
  String? get colorNombreEfectivo => activo ? colorNombre : null;

  /// Donador o fundador de verdad (la prueba no cuenta): la pared y la mascota propia son solo para ellos.
  bool get donaDeVerdad => esDonadorDeVerdad(estado);
  static bool esDonadorDeVerdad(EstadoPremium e, [DateTime? ahora]) =>
      e.vigente(ahora) && (e.tipo == 'donador' || e.tipo == 'fundador');

  static const _columnas = 'marco,efecto_nombre,tema_premium';

  /// Al entrar a una cuenta: primero lo guardado en el teléfono (instantáneo) y después lo de la nube.
  Future<void> iniciar(String cuentaId, Social? social) async {
    _pararTemporizadores();
    _cuenta = cuentaId;
    await _leerLocal();
    if (social == null) return;
    await refrescar(social);
  }

  /// Esperas entre reintentos cuando la pregunta al servidor falla (al abrir hay mucho tráfico a la
  /// vez). Antes era un solo intento: un donador podía quedarse sin sus beneficios toda la sesión.
  @visibleForTesting
  static List<Duration> esperasReintento = const [
    Duration(seconds: 4), Duration(seconds: 10), Duration(seconds: 30),
    Duration(minutes: 1), Duration(minutes: 2), Duration(minutes: 5),
  ];

  /// Al volver a la app, si la última respuesta buena es más vieja que esto, se pregunta de nuevo
  /// (una donación nueva se nota sola, sin relojes gastando batería en segundo plano).
  static const cadaCuanto = Duration(minutes: 20);

  Timer? _reintento;
  int _fallosSeguidos = 0;
  DateTime? _ultimaBuena;
  Social? _social;
  bool _escuchaVida = false;

  @visibleForTesting
  int get fallosSeguidos => _fallosSeguidos;

  void _programar(Social social, {required bool salioBien}) {
    final cuenta = _cuenta;
    _social = social;
    _reintento?.cancel();
    _reintento = null;
    if (!_escuchaVida) {
      _escuchaVida = true;
      VidaApp.primerPlano.addListener(_alVolver);
    }
    if (salioBien) {
      _fallosSeguidos = 0;
      _ultimaBuena = DateTime.now();
      return;
    }
    final espera = esperasReintento[_fallosSeguidos.clamp(0, esperasReintento.length - 1)];
    _fallosSeguidos++;
    _reintento = Timer(espera, () {
      _reintento = null;
      if (_cuenta == cuenta) unawaited(refrescar(social));
    });
  }

  void _alVolver() {
    final s = _social;
    if (!VidaApp.primerPlano.value || s == null || _reintento != null || _cuenta.isEmpty) return;
    final u = _ultimaBuena;
    if (u == null || DateTime.now().difference(u) >= cadaCuanto) unawaited(refrescar(s));
  }

  void _pararTemporizadores() {
    _reintento?.cancel();
    _reintento = null;
    _fallosSeguidos = 0;
    _ultimaBuena = null;
    _social = null;
  }

  /// Vuelve a preguntar al servidor (al entrar y tras canjear un pase). Si falla, se reintenta solo.
  Future<void> refrescar(Social social) async {
    var salioBien = false;
    try {
      EstadoPremium nuevo;
      try {
        nuevo = EstadoPremium.desde(await social.sesion.rpc('mi_premium'));
      } on SinConexion {
        rethrow;
      } on ErrorNube {
        // un servidor sin `mi_premium` todavía: se usa la pregunta de siempre
        final puede = await social.sesion.rpc('puede_poner_fondo') == true;
        nuevo = EstadoPremium(premium: puede, tipo: puede ? 'donador' : '');
      }
      var m = marco, e = efectoNombre, t = tema;
      if (nuevo.premium) {
        final filas = await social.sesion.pedir('GET', 'perfiles?select=$_columnas&id=eq.${social.yo}');
        final f = filas is List && filas.isNotEmpty && filas.first is Map ? filas.first as Map : const {};
        m = Cosmeticos.marco(f['marco']);
        e = Cosmeticos.efectoNombre(f['efecto_nombre']);
        t = Cosmeticos.tema(f['tema_premium']);
      }
      // el color y la casilla de la pared van aparte: si la base aún no tiene esas columnas, lo de
      // siempre se sigue leyendo bien
      var cn = colorNombre, ep = enPared;
      try {
        final filas = await social.sesion.pedir('GET', 'perfiles?select=color_nombre,en_pared&id=eq.${social.yo}');
        final f = filas is List && filas.isNotEmpty && filas.first is Map ? filas.first as Map : const {};
        if (f.containsKey('color_nombre')) cn = Cosmeticos.colorNombre(f['color_nombre']);
        if (f.containsKey('en_pared')) ep = f['en_pared'] == true;
      } on SinConexion {
        rethrow;
      } catch (_) {}
      if (nuevo != estado || m != marco || e != efectoNombre || t != tema || cn != colorNombre || ep != enPared) {
        estado = nuevo;
        marco = m;
        efectoNombre = e;
        tema = t;
        colorNombre = cn;
        enPared = ep;
        await _guardarLocal();
        notifyListeners();
      }
      salioBien = true;
    } catch (_) {
      // sin conexión se queda lo guardado en el teléfono (y se vuelve a intentar en un rato)
    }
    _programar(social, salioBien: salioBien);
  }

  /// Canjea un código de prueba. Los mensajes del servidor se devuelven tal cual.
  Future<ResultadoPase> canjear(Social social, String codigo) async {
    final limpio = codigo.trim().toUpperCase();
    if (limpio.isEmpty) return const ResultadoPase(ok: false, mensaje: 'Escribe el código que te dieron.');
    ResultadoPase r;
    try {
      r = ResultadoPase.desde(await social.sesion.rpc('canjear_pase', {'p_codigo': limpio}));
    } on ErrorNube catch (e) {
      return ResultadoPase(ok: false, mensaje: e.mensaje);
    } catch (_) {
      return const ResultadoPase(ok: false, mensaje: 'No se pudo canjear el código. Revisa tu internet.');
    }
    if (r.ok) await refrescar(social);
    return r;
  }

  /// Guarda lo elegido: se ve al momento y se sube; si falla la nube se avisa con un [ErrorNube].
  Future<void> guardar(Social social, {String? marco, String? efectoNombre, String? tema}) async {
    final antes = (this.marco, this.efectoNombre, this.tema);
    if (marco != null) this.marco = Cosmeticos.marco(marco);
    if (efectoNombre != null) this.efectoNombre = Cosmeticos.efectoNombre(efectoNombre);
    if (tema != null) this.tema = Cosmeticos.tema(tema);
    notifyListeners();
    await _guardarLocal();
    try {
      await social.sesion.pedir('PATCH', 'perfiles?id=eq.${social.yo}', cuerpo: {
        if (marco != null) 'marco': this.marco,
        if (efectoNombre != null) 'efecto_nombre': this.efectoNombre,
        if (tema != null) 'tema_premium': this.tema,
      });
    } catch (_) {
      // no se pudo guardar: se deshace para no mostrar algo que los demás no ven
      this.marco = antes.$1;
      this.efectoNombre = antes.$2;
      this.tema = antes.$3;
      notifyListeners();
      await _guardarLocal();
      rethrow;
    }
  }

  /// Guarda el color del nombre ([color] null lo quita). Se ve al momento; si la nube falla se deshace y
  /// se lanza un [ErrorNube] con un mensaje claro.
  Future<void> guardarColorNombre(Social social, String? color) =>
      _guardarCampo(social, 'color_nombre', Cosmeticos.colorNombre(color), () => colorNombre, (v) => colorNombre = v as String?);

  /// La casilla «Aparecer en la pared de agradecimiento».
  Future<void> guardarEnPared(Social social, bool valor) =>
      _guardarCampo(social, 'en_pared', valor, () => enPared, (v) => enPared = v as bool);

  Future<void> _guardarCampo(Social social, String columna, Object? valor, Object? Function() leer,
      void Function(Object?) poner) async {
    final antes = leer();
    poner(valor);
    notifyListeners();
    await _guardarLocal();
    try {
      await social.sesion.pedir('PATCH', 'perfiles?id=eq.${social.yo}', cuerpo: {columna: valor});
    } catch (e) {
      poner(antes);
      notifyListeners();
      await _guardarLocal();
      if (e is SinConexion) throw const ErrorNube('Sin internet: no se pudo guardar. Inténtalo otra vez.');
      // un 400 sin explicación: la base todavía no tiene la columna (falta aplicar donadores_extra.sql)
      if (e is ErrorNube && e.mensaje.contains('respondió un error (4')) {
        throw const ErrorNube('Esto todavía no está disponible en tu cuenta. Prueba más tarde.');
      }
      if (e is ErrorNube) rethrow;
      throw const ErrorNube('No se pudo guardar. Revisa tu internet e inténtalo otra vez.');
    }
  }

  /// Al cerrar sesión: nada de la cuenta anterior se queda a la vista.
  void reiniciar() {
    _pararTemporizadores();
    _cuenta = '';
    estado = EstadoPremium.ninguno;
    marco = efectoNombre = tema = Cosmeticos.ninguno;
    colorNombre = null;
    enPared = false;
    notifyListeners();
  }

  // ------------------------------------------------------------ en el teléfono

  String get _clave => 'premium_$_cuenta';

  Future<void> _leerLocal() async {
    try {
      final p = await SharedPreferences.getInstance();
      final texto = p.getString(_clave);
      if (texto == null) return;
      final d = jsonDecode(texto) as Map;
      estado = EstadoPremium.desde(d['estado']);
      marco = Cosmeticos.marco(d['marco']);
      efectoNombre = Cosmeticos.efectoNombre(d['efecto_nombre']);
      tema = Cosmeticos.tema(d['tema']);
      colorNombre = Cosmeticos.colorNombre(d['color_nombre']);
      enPared = d['en_pared'] == true;
      notifyListeners();
    } catch (_) {}
  }

  Future<void> _guardarLocal() async {
    if (_cuenta.isEmpty) return;
    try {
      final p = await SharedPreferences.getInstance();
      await p.setString(_clave, jsonEncode({
        'estado': estado.aJson(), 'marco': marco, 'efecto_nombre': efectoNombre, 'tema': tema,
        'color_nombre': colorNombre, 'en_pared': enPared,
      }));
    } catch (_) {}
  }
}


// =============================================================== ¿Qué canción era?

/// Lo que se entendió de lo que escribió la persona: cuándo (fecha, rango o franja del día),
/// palabras del título o del artista y, si las hay, una frase de la letra.
class ConsultaHistorial {
  const ConsultaHistorial({
    this.desde,
    this.hasta,
    this.etiqueta = '',
    this.franja,
    this.terminos = const [],
    this.frase = '',
  });

  /// El rango de fechas: de [desde] (incluido) a [hasta] (no incluido).
  final DateTime? desde;
  final DateTime? hasta;

  /// El rango en palabras («ayer», «el martes 14 de octubre»), para decírselo a la persona.
  final String etiqueta;

  /// 0 mañana, 1 tarde, 2 noche, 3 madrugada.
  final int? franja;

  /// Palabras que deben estar en el título, el artista o el álbum (ya sin tildes).
  final List<String> terminos;

  /// Una frase que debe estar en la letra (sin tildes ni signos).
  final String frase;

  bool get tieneFecha => desde != null;
  bool get sinCriterios => !tieneFecha && franja == null && terminos.isEmpty && frase.isEmpty;
}

/// Una canción hallada en el historial.
class HalladaHistorial {
  const HalladaHistorial({
    required this.pista,
    required this.ultima,
    required this.veces,
    required this.donde,
    this.fragmento = '',
  });

  final Json pista;

  /// La última vez que sonó dentro de lo buscado.
  final DateTime ultima;
  final int veces;

  /// Por qué salió: `titulo`, `artista`, `letra` o `fecha`.
  final String donde;

  /// Si salió por la letra, la línea donde aparece.
  final String fragmento;
}

class ResultadoHistorial {
  const ResultadoHistorial(this.consulta, this.resultados);
  final ConsultaHistorial consulta;
  final List<HalladaHistorial> resultados;
}

/// «¿Qué canción era?»: busca en lo que escuchaste por fecha («el martes», «ayer», «del 3 al 5
/// de noviembre»), por texto del título o artista y, si la letra está guardada en el teléfono,
/// por lo que dice la canción. Todo sale del historial local: funciona sin conexión.
/// La lógica es pura (recibe el historial y las letras) para poder probarla.
class QueCancionEra {
  QueCancionEra._();

  static const _meses = [
    'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre',
    'noviembre', 'diciembre'
  ];
  static const _dias = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo'];
  static const _numeros = {
    'un': 1, 'una': 1, 'dos': 2, 'tres': 3, 'cuatro': 4, 'cinco': 5, 'seis': 6, 'siete': 7, 'ocho': 8,
    'nueve': 9, 'diez': 10, 'once': 11, 'doce': 12,
  };
  static const _relleno = {
    'la', 'el', 'los', 'las', 'un', 'una', 'unos', 'unas', 'de', 'del', 'que', 'cual', 'cuales', 'era', 'fue',
    'fui', 'es', 'cancion', 'canciones', 'tema', 'temas', 'musica', 'escuche', 'escuchaba', 'escuchando',
    'escuchado', 'escuchamos', 'puse', 'pusiste', 'oi', 'sono', 'sonaba', 'se', 'llamaba', 'llama', 'nombre',
    'algo', 'donde', 'con', 'en', 'por', 'me', 'mi', 'mis', 'a', 'al', 'y', 'o', 'busca', 'buscar', 'busco',
    'quiero', 'encontrar', 'sobre', 'lo', 'le', 'habia', 'hay', 'esa', 'ese', 'esta', 'este', 'pasado',
    'pasada', 'ultimo', 'ultima', 'aquella', 'aquel', 'ayer', 'hoy',
  };

  /// Pasa a minúsculas y quita tildes y signos: «¡Corazón!» -> «corazon».
  static String normalizar(String t) {
    const de = 'áàäâéèëêíìïîóòöôúùüûñç';
    const a = 'aaaaeeeeiiiioooouuuunc';
    final b = StringBuffer();
    for (final r in t.toLowerCase().runes) {
      final c = String.fromCharCode(r);
      final i = de.indexOf(c);
      b.write(i >= 0 ? a[i] : c);
    }
    return b.toString().replaceAll(RegExp(r'[^a-z0-9\s]'), ' ').replaceAll(RegExp(r'\s+'), ' ').trim();
  }

  static DateTime _dia(DateTime d, [int mas = 0]) => DateTime(d.year, d.month, d.day + mas);

  static int? _mes(String? n) {
    if (n == null) return null;
    if (n == 'setiembre') return 9;
    final i = _meses.indexOf(n);
    return i < 0 ? null : i + 1;
  }

  static const _reMes = '(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)';
  static const _reDia = '(lunes|martes|miercoles|jueves|viernes|sabado|domingo)';

  /// La fecha más reciente (sin pasarse de [hoy]) que cae en [dia] de [mes]; sin [mes], el
  /// último día [dia] de algún mes; con [anio], exacta.
  static DateTime? _fecha(int dia, int? mes, int? anio, DateTime hoy) {
    if (dia < 1 || dia > 31) return null;
    DateTime? ok(int y, int m) {
      final d = DateTime(y, m, dia);
      return d.month == m ? d : null; // el 31 de febrero no existe
    }

    if (anio != null && mes != null) return ok(anio, mes);
    if (mes != null) {
      var d = ok(hoy.year, mes);
      if (d == null || d.isAfter(hoy)) d = ok(hoy.year - 1, mes);
      return d;
    }
    var y = hoy.year, m = hoy.month;
    for (var k = 0; k < 14; k++) {
      final d = ok(y, m);
      if (d != null && !d.isAfter(hoy)) return d;
      m--;
      if (m == 0) {
        m = 12;
        y--;
      }
    }
    return null;
  }

  /// Entiende lo escrito. [ahora] es «hoy» (se puede cambiar para probar).
  static ConsultaHistorial interpretar(String entrada, {DateTime? ahora}) {
    final hoy = _dia(ahora ?? DateTime.now());
    var crudo = entrada;
    var frase = '';
    // lo que va entre comillas es una frase de la letra
    final cita = RegExp('[«"“”](.+?)[»"“”]').firstMatch(crudo);
    if (cita != null) {
      frase = normalizar(cita.group(1)!);
      crudo = crudo.replaceRange(cita.start, cita.end, ' ');
    }
    var t = ' ${normalizar(crudo)} ';
    DateTime? desde, hasta;
    var etiqueta = '';
    int? franja;

    Match? quitar(RegExp re) {
      final m = re.firstMatch(t);
      if (m != null) t = t.replaceRange(m.start, m.end, ' ');
      return m;
    }

    void dia(DateTime d, String e) {
      desde = d;
      hasta = _dia(d, 1);
      etiqueta = e;
    }

    String largo(DateTime d) => '${d.day} de ${_meses[d.month - 1]}${d.year != hoy.year ? ' de ${d.year}' : ''}';

    // palabras sueltas del día
    if (quitar(RegExp(r'\s(antes de ayer|anteayer|antier)\s')) != null) {
      dia(_dia(hoy, -2), 'anteayer');
    } else if (quitar(RegExp(r'\sanoche\s')) != null) {
      dia(_dia(hoy, -1), 'anoche');
      franja = 2;
    } else if (quitar(RegExp(r'\sayer\s')) != null) {
      dia(_dia(hoy, -1), 'ayer');
    } else if (quitar(RegExp(r'\shoy\s')) != null) {
      dia(hoy, 'hoy');
    }

    // «hace 3 días», «hace dos semanas», «hace un mes»
    if (desde == null) {
      final m = quitar(RegExp(
          r'\shace (\d{1,3}|un|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce) (dias?|semanas?|mes|meses)\s'));
      if (m != null) {
        final n = int.tryParse(m.group(1)!) ?? _numeros[m.group(1)!] ?? 1;
        final u = m.group(2)!;
        if (u.startsWith('dia')) {
          dia(_dia(hoy, -n), n == 1 ? 'ayer' : 'hace $n días');
        } else if (u.startsWith('semana')) {
          final c = _dia(hoy, -7 * n);
          desde = _dia(c, -3);
          hasta = _dia(c, 4);
          etiqueta = n == 1 ? 'hace una semana' : 'hace $n semanas';
        } else {
          final c = DateTime(hoy.year, hoy.month - n, hoy.day);
          desde = _dia(c, -10);
          hasta = _dia(c, 11);
          etiqueta = n == 1 ? 'hace un mes' : 'hace $n meses';
        }
      }
    }

    // semanas y meses completos
    if (desde == null) {
      if (quitar(RegExp(r'\s(la )?semana pasada\s')) != null) {
        final lunes = _dia(hoy, -(hoy.weekday - 1) - 7);
        desde = lunes;
        hasta = _dia(lunes, 7);
        etiqueta = 'la semana pasada';
      } else if (quitar(RegExp(r'\s(en )?(esta|la) semana\s')) != null) {
        desde = _dia(hoy, -(hoy.weekday - 1));
        hasta = _dia(hoy, 1);
        etiqueta = 'esta semana';
      } else if (quitar(RegExp(r'\s(en )?(el )?mes pasado\s')) != null) {
        desde = DateTime(hoy.year, hoy.month - 1, 1);
        hasta = DateTime(hoy.year, hoy.month, 1);
        etiqueta = 'el mes pasado';
      } else if (quitar(RegExp(r'\s(en )?(este|el) mes\s')) != null) {
        desde = DateTime(hoy.year, hoy.month, 1);
        hasta = _dia(hoy, 1);
        etiqueta = 'este mes';
      }
    }

    // «del 3 al 5 de noviembre», «entre el 3 y el 5»
    if (desde == null) {
      final m = quitar(RegExp(r'\s(?:del|desde el|entre el)\s(\d{1,2})\s(?:al|hasta el|y el|a|y)\s(\d{1,2})(?:\sde\s' +
          _reMes +
          r')?(?:\sde(?:l)?\s(\d{4}))?\s'));
      if (m != null) {
        final a = int.parse(m.group(1)!), b = int.parse(m.group(2)!);
        final mes = _mes(m.group(3));
        final anio = int.tryParse(m.group(4) ?? '');
        final fin = _fecha(b, mes, anio, hoy);
        final ini = fin == null ? null : DateTime(fin.year, fin.month, a);
        if (fin != null && ini != null && ini.month == fin.month && !ini.isAfter(fin)) {
          desde = ini;
          hasta = _dia(fin, 1);
          etiqueta = 'del $a al ${largo(fin)}';
        }
      }
    }

    // «el 12 de octubre», «12 de octubre de 2025»
    if (desde == null) {
      final m = quitar(RegExp(r'\s(?:el\s)?(\d{1,2})\sde\s' + _reMes + r'(?:\sde(?:l)?\s(\d{4}))?\s'));
      if (m != null) {
        final f = _fecha(int.parse(m.group(1)!), _mes(m.group(2)), int.tryParse(m.group(3) ?? ''), hoy);
        if (f != null) dia(f, 'el ${largo(f)}');
      }
    }

    // «el martes», «el sábado pasado»: la última vez que cayó ese día (sin contar hoy)
    if (desde == null) {
      final m = quitar(RegExp(r'\s(?:el\s)?(?:pasado\s|este\s)?' + _reDia + r'(?:\spasado)?\s'));
      if (m != null) {
        const nombres = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo'];
        final n = nombres.indexOf(m.group(1)!) + 1;
        var atras = (hoy.weekday - n) % 7;
        if (atras == 0) atras = 7;
        final f = _dia(hoy, -atras);
        dia(f, 'el ${_dias[n - 1]} ${largo(f)}');
      }
    }

    // «en octubre», «de octubre de 2025»
    if (desde == null) {
      final m = quitar(RegExp(r'\s(?:en|de|durante)\s(?:el mes de\s)?' + _reMes + r'(?:\sde(?:l)?\s(\d{4}))?\s'));
      if (m != null) {
        final mes = _mes(m.group(1))!;
        var anio = int.tryParse(m.group(2) ?? '') ?? hoy.year;
        if (m.group(2) == null && DateTime(anio, mes, 1).isAfter(hoy)) anio--;
        desde = DateTime(anio, mes, 1);
        hasta = DateTime(anio, mes + 1, 1);
        etiqueta = 'en ${_meses[mes - 1]}${anio != hoy.year ? ' de $anio' : ''}';
      }
    }

    // «el 12» (el último día 12)
    if (desde == null) {
      final m = quitar(RegExp(r'\sel (\d{1,2})\s'));
      if (m != null) {
        final f = _fecha(int.parse(m.group(1)!), null, null, hoy);
        if (f != null) dia(f, 'el ${largo(f)}');
      }
    }

    // por la mañana / tarde / noche / madrugada
    final fr = quitar(RegExp(r'\s(?:(?:por|en|durante) la|de) (manana|tarde|noche|madrugada)\s'));
    if (fr != null) {
      franja = const {'manana': 0, 'tarde': 1, 'noche': 2, 'madrugada': 3}[fr.group(1)!];
    }

    // «decía ...», «la letra dice ...»: lo que sigue es de la letra
    final marca = RegExp(r'\s(?:que\s)?(?:decia|dice|dicia|cantaba|canta|letra(?:\sque\sdice)?)\s(.*)$').firstMatch(t);
    if (marca != null) {
      if (frase.isEmpty) {
        frase = marca.group(1)!.trim();
        t = t.substring(0, marca.start);
      } else {
        t = t.replaceRange(marca.start, marca.start + marca.group(0)!.length - marca.group(1)!.length, ' ');
      }
    }

    final terminos = <String>[];
    for (final w in t.split(' ')) {
      if (w.isEmpty || _relleno.contains(w) || (w.length < 2 && int.tryParse(w) == null)) continue;
      if (!terminos.contains(w)) terminos.add(w);
    }
    return ConsultaHistorial(
        desde: desde, hasta: hasta, etiqueta: etiqueta, franja: franja, terminos: terminos, frase: frase);
  }

  static bool _enFranja(int hora, int franja) => switch (franja) {
        0 => hora >= 5 && hora < 12,
        1 => hora >= 12 && hora < 19,
        2 => hora >= 19,
        _ => hora < 5,
      };

  static String _campos(Json p) {
    final alb = p['album'];
    final arts = p['artistas'];
    return normalizar('${p['titulo'] ?? ''} ${p['artista'] ?? ''} '
        '${arts is List ? arts.map((a) => a is Map ? a['nombre'] ?? '' : '').join(' ') : ''} '
        '${alb is Map ? alb['nombre'] ?? '' : ''}');
  }

  /// Busca en [historial] lo que describe [entrada]. [letras] es lo que hay guardado
  /// (clave de canción -> letra) para buscar por lo que dice la canción.
  static ResultadoHistorial buscar(
    List<Escucha> historial,
    String entrada, {
    DateTime? ahora,
    Map<String, Map<String, dynamic>> letras = const {},
    int limite = 40,
  }) {
    final q = interpretar(entrada, ahora: ahora);
    if (q.sinCriterios) return ResultadoHistorial(q, const []);

    final grupos = <String, _Grupo>{};
    for (final e in historial) {
      if (e.clave.isEmpty) continue;
      final f = e.fecha;
      if (q.desde != null && (f.isBefore(q.desde!) || !f.isBefore(q.hasta!))) continue;
      if (q.franja != null && !_enFranja(f.hour, q.franja!)) continue;
      final g = grupos.putIfAbsent(e.clave, () => _Grupo(e.pista, f));
      g.veces++;
      if (f.isAfter(g.ultima)) g.ultima = f;
    }

    final salida = <(HalladaHistorial, int)>[];
    for (final e in grupos.entries) {
      final g = e.value;
      var donde = 'fecha';
      var fragmento = '';
      var puntos = 0;
      final campos = _campos(g.pista);
      var ok = true;
      final l = letras[e.key];
      final textoLetra = l == null ? '' : normalizar('${l['texto'] ?? ''}');

      if (q.terminos.isNotEmpty) {
        if (q.terminos.every(campos.contains)) {
          final titulo = normalizar('${g.pista['titulo'] ?? ''}');
          donde = q.terminos.every(titulo.contains) ? 'titulo' : 'artista';
          puntos = donde == 'titulo' ? 3 : 2;
        } else if (textoLetra.isNotEmpty && q.frase.isEmpty && q.terminos.every(textoLetra.contains)) {
          // las palabras no están en el nombre pero sí en la letra
          donde = 'letra';
          puntos = 1;
          fragmento = _linea(l!, q.terminos.first);
        } else {
          ok = false;
        }
      }
      if (ok && q.frase.isNotEmpty) {
        if (textoLetra.contains(q.frase)) {
          if (donde == 'fecha') donde = 'letra';
          fragmento = _linea(l!, q.frase);
          puntos += 1;
        } else if (campos.contains(q.frase)) {
          // la frase también puede ser el nombre de la canción
          if (donde == 'fecha') donde = 'titulo';
          puntos += 3;
        } else {
          ok = false;
        }
      }
      if (!ok) continue;
      salida.add((
        HalladaHistorial(pista: g.pista, ultima: g.ultima, veces: g.veces, donde: donde, fragmento: fragmento),
        puntos
      ));
    }
    salida.sort((a, b) {
      final c = b.$2.compareTo(a.$2);
      return c != 0 ? c : b.$1.ultima.compareTo(a.$1.ultima);
    });
    return ResultadoHistorial(q, [for (final s in salida.take(limite)) s.$1]);
  }

  /// La línea de la letra donde aparece [buscado] (ya sin tildes).
  static String _linea(Map<String, dynamic> letra, String buscado) {
    final lineas = [for (final x in lineasConTiempo(letra)) x.$2];
    final fuente = lineas.isNotEmpty ? lineas : '${letra['texto'] ?? ''}'.split('\n');
    for (final l in fuente) {
      if (normalizar(l).contains(buscado)) return l.trim();
    }
    final primera = buscado.split(' ').first;
    for (final l in fuente) {
      if (normalizar(l).contains(primera)) return l.trim();
    }
    return '';
  }
}

class _Grupo {
  _Grupo(this.pista, this.ultima);
  final Json pista;
  DateTime ultima;
  int veces = 0;
}
