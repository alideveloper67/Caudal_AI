import 'dart:async';
import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';
import 'package:sqflite/sqflite.dart';

import 'chat.dart';
import 'coleccion.dart';
import 'cosmeticos.dart';
import 'nube.dart';
import 'sincronizacion.dart';
import 'tarjeta_lista.dart';

export 'tarjeta_lista.dart';

/// Listas que se comparten con un código, listas colaborativas y listas que
/// viajan por el chat. Envuelve las funciones de la base de
/// `supabase/listas.sql` (cada una se llama con `rpc/<nombre>`).

/// Cómo se llama a una función de la base: nombre + parámetros → respuesta.
typedef LlamadaBase = Future<dynamic> Function(String nombre, Map<String, dynamic> parametros);

// ============================================================== modelos

/// Una persona tal como la devuelven las funciones de listas.
class PersonaLista {
  const PersonaLista({this.id = '', this.usuario = '', this.nombre = '', this.fotoUrl = '',
      this.marco = Cosmeticos.ninguno, this.efectoNombre = Cosmeticos.ninguno});

  /// Marco del avatar y efecto del nombre de un donador («ninguno» si no tiene).
  final String marco;
  final String efectoNombre;
  final String id;
  final String usuario;
  final String nombre;
  final String fotoUrl;

  String get visible => nombre.isNotEmpty ? nombre : (usuario.isNotEmpty ? usuario : 'Alguien');

  static PersonaLista desde(Object? d) {
    if (d is! Map) return const PersonaLista();
    String t(String k) => d[k] == null ? '' : '${d[k]}';
    return PersonaLista(id: t('id'), usuario: t('usuario'), nombre: t('nombre'), fotoUrl: t('foto_url'),
        marco: Cosmeticos.marco(d['marco']), efectoNombre: Cosmeticos.efectoNombre(d['efecto_nombre']));
  }
}

/// Una lista de otra persona donde soy miembro (`mis_listas_compartidas`).
class ListaCompartida {
  const ListaCompartida({required this.id, required this.nombre, this.descripcion = '',
      this.rol = rolOyente, this.total = 0, this.actualizada, this.dueno = const PersonaLista()});

  final String id;
  final String nombre;
  final String descripcion;
  final String rol;
  final int total;
  final DateTime? actualizada;
  final PersonaLista dueno;

  bool get puedeAnadir => rol == rolColaborador;

  static ListaCompartida desde(Map d) => ListaCompartida(
        id: '${d['id']}',
        nombre: '${d['nombre'] ?? ''}',
        descripcion: d['descripcion'] == null ? '' : '${d['descripcion']}',
        rol: '${d['rol']}' == rolColaborador ? rolColaborador : rolOyente,
        total: (d['total'] as num?)?.toInt() ?? 0,
        actualizada: DateTime.tryParse('${d['actualizada']}')?.toLocal(),
        dueno: PersonaLista.desde(d['dueno']),
      );
}

/// Una cancioncita de la vista previa (sin ids internos).
class CancionVistaPrevia {
  const CancionVistaPrevia(this.titulo, this.artista, this.miniatura);
  final String titulo;
  final String artista;
  final String miniatura;
}

/// Lo que devuelve `ver_lista_codigo`: se enseña antes de unirse.
class VistaPreviaLista {
  const VistaPreviaLista({required this.nombre, this.descripcion = '', this.total = 0,
      this.rol = rolColaborador, this.miembros = 0, this.dueno = const PersonaLista(), this.canciones = const []});

  final String nombre;
  final String descripcion;
  final int total;
  final String rol;
  final int miembros;
  final PersonaLista dueno;
  final List<CancionVistaPrevia> canciones;

  bool get puedeAnadir => rol == rolColaborador;

  /// «Puedes añadir canciones» / «Solo escuchar».
  String get permisoTexto => puedeAnadir ? 'Puedes añadir canciones' : 'Solo escuchar';

  /// Nulo si el código no existe (la base responde `null`).
  static VistaPreviaLista? desde(Object? d) {
    if (d is! Map) return null;
    return VistaPreviaLista(
      nombre: '${d['nombre'] ?? ''}',
      descripcion: d['descripcion'] == null ? '' : '${d['descripcion']}',
      total: (d['total'] as num?)?.toInt() ?? 0,
      rol: '${d['rol']}' == rolOyente ? rolOyente : rolColaborador,
      miembros: (d['miembros'] as num?)?.toInt() ?? 0,
      dueno: PersonaLista.desde(d['dueno']),
      canciones: [
        for (final c in (d['canciones'] as List? ?? const []))
          if (c is Map) CancionVistaPrevia('${c['titulo'] ?? ''}', '${c['artista'] ?? ''}', '${c['miniatura'] ?? ''}'),
      ],
    );
  }
}

/// Lo que devuelve `unirse_a_lista`.
class ResultadoUnirse {
  const ResultadoUnirse({required this.listaId, required this.nombre, required this.rol, required this.esDueno});
  final String listaId;
  final String nombre;
  final String rol;
  final bool esDueno;

  bool get puedeAnadir => rol == rolColaborador;

  static ResultadoUnirse desde(Object? d) {
    final m = d is Map ? d : const {};
    return ResultadoUnirse(
      listaId: '${m['lista_id'] ?? ''}',
      nombre: '${m['nombre'] ?? ''}',
      rol: '${m['rol']}' == rolOyente ? rolOyente : rolColaborador,
      esDueno: m['es_dueno'] == true,
    );
  }
}

/// Un miembro de la lista (`miembros_lista`); el primero es el dueño.
class MiembroLista {
  const MiembroLista({required this.persona, required this.rol, this.desde, this.esDueno = false});
  final PersonaLista persona;
  final String rol;
  final DateTime? desde;
  final bool esDueno;

  String get id => persona.id;

  static MiembroLista desdeJson(Map d) => MiembroLista(
        persona: PersonaLista.desde(d),
        rol: '${d['rol']}' == rolOyente ? rolOyente : rolColaborador,
        desde: DateTime.tryParse('${d['desde']}')?.toLocal(),
        esDueno: d['es_dueno'] == true,
      );
}

/// Una canción de la lista con quién la añadió (`pistas_de_lista`).
class PistaCompartida {
  const PistaCompartida({required this.clave, required this.datos, this.orden = 0, this.agregada,
      this.agregadaPor = const PersonaLista()});

  final String clave;
  final Json datos;
  final double orden;
  final DateTime? agregada;
  final PersonaLista agregadaPor;

  /// La canción lista para sonar (con `video_id`, carátula…).
  Json get pista => Chat.pistaJugable({...datos, 'clave': clave});

  /// «Añadida por Ana».
  String get textoAutor => agregadaPor.id.isEmpty && agregadaPor.usuario.isEmpty
      ? ''
      : 'Añadida por ${agregadaPor.visible}';

  static PistaCompartida desde(Map d) => PistaCompartida(
        clave: '${d['clave'] ?? ''}',
        datos: d['datos'] is Map ? Map<String, dynamic>.from(d['datos'] as Map) : <String, dynamic>{},
        orden: (d['orden'] as num?)?.toDouble() ?? 0,
        agregada: DateTime.tryParse('${d['agregada']}')?.toLocal(),
        agregadaPor: PersonaLista.desde(d['agregada_por']),
      );
}

/// Qué resultó de compartir una lista propia.
class ListaYaCompartida {
  const ListaYaCompartida({required this.codigo, required this.rol, required this.nueva});
  final String codigo;
  final String rol;

  /// true si se acaba de compartir (antes no tenía código en este aparato).
  final bool nueva;
}

// ================================================================ la base

class ListasCompartidas {
  ListasCompartidas(Sesion sesion) : _llamar = sesion.rpc;

  /// Para las pruebas: cualquier función que haga de base.
  ListasCompartidas.conLlamada(this._llamar);

  final LlamadaBase _llamar;

  /// El código que mandó la base, sin guion y en mayúsculas.
  Future<String> compartir(String listaUuid, {String rol = rolColaborador}) async {
    final r = await _llamar('compartir_lista', {'p_lista': listaUuid, 'p_rol': rol});
    final c = normalizarCodigoLista('$r');
    if (!codigoListaValido(c)) {
      throw const ErrorNube('No se pudo crear el código de la lista. Vuelve a intentarlo.');
    }
    return c;
  }

  Future<void> dejarDeCompartir(String listaUuid) async {
    await _llamar('dejar_de_compartir_lista', {'p_lista': listaUuid});
  }

  /// Vista previa. Nulo si el código no existe o la lista ya no se comparte.
  Future<VistaPreviaLista?> verPorCodigo(String codigo) async {
    final c = codigoListaDeTexto(codigo);
    if (c == null) {
      throw const ErrorNube('Ese código no es válido: son 8 letras o números, como K7M2-9QXP.');
    }
    return VistaPreviaLista.desde(await _llamar('ver_lista_codigo', {'p_codigo': c}));
  }

  Future<ResultadoUnirse> unirse(String codigo) async {
    final c = codigoListaDeTexto(codigo);
    if (c == null) {
      throw const ErrorNube('Ese código no es válido: son 8 letras o números, como K7M2-9QXP.');
    }
    return ResultadoUnirse.desde(await _llamar('unirse_a_lista', {'p_codigo': c}));
  }

  Future<void> salir(String listaId) async {
    await _llamar('salir_de_lista', {'p_lista': listaId});
  }

  Future<void> quitarMiembro(String listaId, String usuarioId) async {
    await _llamar('quitar_miembro', {'p_lista': listaId, 'p_usuario': usuarioId});
  }

  Future<List<MiembroLista>> miembros(String listaId) async {
    final r = await _llamar('miembros_lista', {'p_lista': listaId});
    return [for (final d in (r as List? ?? const [])) if (d is Map) MiembroLista.desdeJson(d)];
  }

  Future<List<ListaCompartida>> misListasCompartidas() async {
    final r = await _llamar('mis_listas_compartidas', {});
    return [for (final d in (r as List? ?? const [])) if (d is Map) ListaCompartida.desde(d)];
  }

  Future<List<PistaCompartida>> pistasDeLista(String listaId) async {
    final r = await _llamar('pistas_de_lista', {'p_lista': listaId});
    return [for (final d in (r as List? ?? const [])) if (d is Map) PistaCompartida.desde(d)];
  }

  /// Cómo se mandan las canciones a la base: solo las de YouTube Music (las
  /// de archivos del teléfono no le sirven a nadie más).
  static List<Map<String, dynamic>> itemsParaNube(List<Json> pistas) => [
        for (final p in pistas)
          if ('${p['clave'] ?? ''}'.startsWith('yt:')) {'clave': p['clave'], 'datos': Coleccion.paraNube(p)},
      ];

  /// Devuelve cuántas canciones entraron (las repetidas no cuentan).
  Future<int> agregar(String listaId, List<Json> pistas) async {
    final items = itemsParaNube(pistas);
    if (items.isEmpty) return 0;
    final r = await _llamar('agregar_a_lista_compartida', {'p_lista': listaId, 'p_items': items});
    return (r as num?)?.toInt() ?? 0;
  }

  Future<void> quitar(String listaId, String clave) async {
    await _llamar('quitar_de_lista_compartida', {'p_lista': listaId, 'p_clave': clave});
  }

  /// Comparte una lista PROPIA (o reutiliza su código si ya estaba compartida).
  ///
  /// - [rolGuardado]: el permiso con el que ya la compartió esta cuenta (si se
  ///   sabe). Con él se reutiliza el código tal cual, sin cambiar el permiso.
  /// - Si no estaba compartida, antes se llama a [asegurarEnNube] (que envía lo
  ///   pendiente) porque la base solo conoce las listas que ya subieron.
  Future<ListaYaCompartida> compartirPropia(String listaUuid,
      {required String rol, String? rolGuardado, Future<void> Function()? asegurarEnNube}) async {
    if (listaUuid.isEmpty) {
      throw const ErrorNube('Esta lista todavía no se envió a tu cuenta. Abre Caudal con internet y vuelve a probar.');
    }
    final usar = rolGuardado ?? rol;
    if (asegurarEnNube != null) await asegurarEnNube();
    String codigo;
    try {
      codigo = await compartir(listaUuid, rol: usar);
    } on ErrorNube catch (e) {
      // una lista recién creada puede tardar en llegar: un segundo intento
      if (asegurarEnNube == null || !e.mensaje.contains('ya no existe o no es tuya')) rethrow;
      await Future<void>.delayed(const Duration(seconds: 2));
      await asegurarEnNube();
      codigo = await compartir(listaUuid, rol: usar);
    }
    return ListaYaCompartida(codigo: codigo, rol: usar, nueva: rolGuardado == null);
  }

  /// Arma la tarjeta que se manda por el chat.
  static TarjetaLista tarjetaDe(ListaYaCompartida c, {required String nombre, required int canciones,
          String portada = ''}) =>
      TarjetaLista(codigo: c.codigo, nombre: nombre, canciones: canciones, rol: c.rol, portada: portada);
}

/// «Enviar una lista» por el chat: elige la lista → la comparte si hace falta
/// (con [rol] «colaborador» u «oyente», o reutilizando el código y el permiso
/// que ya tenía) → arma la tarjeta que se manda en el mensaje (`lista`).
///
/// [alCompartir] se llama con (uuid, permiso) para que este aparato recuerde
/// que la lista ya está compartida.
Future<TarjetaLista> tarjetaParaEnviar({
  required ListasCompartidas base,
  required String uuid,
  required String nombre,
  required int canciones,
  required String rol,
  String? rolGuardado,
  String portada = '',
  Future<void> Function()? asegurarEnNube,
  Future<void> Function(String uuid, String rol)? alCompartir,
}) async {
  final c = await base.compartirPropia(uuid,
      rol: rol, rolGuardado: rolGuardado, asegurarEnNube: rolGuardado == null ? asegurarEnNube : null);
  if (alCompartir != null) await alCompartir(uuid, c.rol);
  return ListasCompartidas.tarjetaDe(c, nombre: nombre, canciones: canciones, portada: portada);
}

/// Antes de compartir una lista propia: envía lo pendiente y espera a que no
/// quede nada sin subir (la base solo conoce lo que ya está en la nube).
Future<void> enviarPendientesYEsperar(Coleccion col, Sincronizador? sinc,
    {int intentos = 12, Duration espera = const Duration(milliseconds: 500)}) async {
  Future<int> pendientes() async =>
      Sqflite.firstIntValue(await col.db.rawQuery('SELECT COUNT(*) FROM pendientes')) ?? 0;
  if (await pendientes() == 0) return;
  if (sinc == null) {
    throw const ErrorNube('Para compartir una lista hace falta haber entrado con internet.');
  }
  for (var i = 0; i < intentos; i++) {
    await sinc.ya();
    if (await pendientes() == 0) return;
    await Future<void>.delayed(espera);
  }
  throw const ErrorNube('Tus cambios todavía se están enviando. Espera unos segundos y vuelve a probar.');
}

// ====================================================== lo que recuerda este aparato

/// Qué listas propias ya compartió esta cuenta en este aparato y con qué
/// permiso (uuid → rol). La base no deja leer los códigos directamente, así
/// que esto permite enseñar «Compartida» y reutilizar el código sin preguntar.
class ListasQueComparto {
  ListasQueComparto._(this._cuenta, this._mapa);
  final String _cuenta;
  final Map<String, String> _mapa;

  static String _clave(String cuenta) => 'listas_que_comparto_$cuenta';

  static Future<ListasQueComparto> cargar(String cuenta) async {
    final mapa = <String, String>{};
    try {
      final p = await SharedPreferences.getInstance();
      final crudo = p.getString(_clave(cuenta));
      if (crudo != null && crudo.isNotEmpty) {
        final d = jsonDecode(crudo);
        if (d is Map) {
          d.forEach((k, v) => mapa['$k'] = '$v' == rolOyente ? rolOyente : rolColaborador);
        }
      }
    } catch (_) {}
    return ListasQueComparto._(cuenta, mapa);
  }

  /// El permiso con el que está compartida (nulo si no lo está).
  String? rolDe(String uuid) => _mapa[uuid];
  bool estaCompartida(String uuid) => _mapa.containsKey(uuid);
  Set<String> get uuids => _mapa.keys.toSet();

  Future<void> marcar(String uuid, String rol) async {
    _mapa[uuid] = rol;
    await _guardar();
  }

  Future<void> quitar(String uuid) async {
    if (_mapa.remove(uuid) != null) await _guardar();
  }

  Future<void> _guardar() async {
    try {
      final p = await SharedPreferences.getInstance();
      await p.setString(_clave(_cuenta), jsonEncode(_mapa));
    } catch (_) {}
  }
}
