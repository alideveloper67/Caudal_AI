import 'chat.dart' show Chat;
import 'coleccion.dart' show Json;
import 'nube.dart';

/// Grupos para hablar (supabase/grupos.sql): abiertos (cualquiera entra) y privados (con código).
/// Dentro se manda texto, canciones y notas de voz; nada de imágenes ni videos (la base no tiene dónde
/// guardarlos). Todas las reglas (quién lee, quién escribe, freno de spam, reportes, moderación) las pone
/// la base: aquí solo se llama a sus funciones.

enum RolGrupo { dueno, moderador, miembro, ninguno }

RolGrupo rolDe(Object? r) => switch ('$r') {
      'dueno' => RolGrupo.dueno,
      'moderador' => RolGrupo.moderador,
      'miembro' => RolGrupo.miembro,
      _ => RolGrupo.ninguno,
    };

class Grupo {
  Grupo({
    required this.id,
    required this.nombre,
    this.descripcion = '',
    this.privado = false,
    this.miembros = 0,
    this.rol = RolGrupo.ninguno,
    this.codigo,
    this.cerrado = false,
    this.sinLeer = 0,
    this.ultimoTexto = '',
    this.ultimo,
  });

  final String id;
  final String nombre;
  final String descripcion;
  final bool privado;
  final int miembros;
  final RolGrupo rol;

  /// El código para invitar (solo los privados y solo si estás dentro).
  final String? codigo;
  final bool cerrado;
  final int sinLeer;

  /// «Ana: hola» / «♪ Una canción» / «🎤 Nota de voz».
  final String ultimoTexto;
  final DateTime? ultimo;

  bool get dentro => rol != RolGrupo.ninguno;
  bool get modero => rol == RolGrupo.dueno || rol == RolGrupo.moderador;
  String get inicial => nombre.isEmpty ? '#' : nombre.substring(0, 1).toUpperCase();

  factory Grupo.desde(Map d) {
    final u = d['ultimo_mensaje'];
    var vista = '';
    if (u is Map) {
      final quien = '${u['nombre'] ?? ''}'.isNotEmpty ? '${u['nombre']}' : '${u['usuario'] ?? ''}';
      final que = u['audio'] == true
          ? '🎤 Nota de voz'
          : u['pista'] == true
              ? '♪ Una canción'
              : '${u['texto'] ?? ''}';
      vista = quien.isEmpty ? que : '$quien: $que';
    }
    return Grupo(
      id: '${d['id']}',
      nombre: '${d['nombre'] ?? ''}',
      descripcion: '${d['descripcion'] ?? ''}',
      privado: d['tipo'] == 'privado',
      miembros: (d['miembros'] as num?)?.toInt() ?? 0,
      rol: rolDe(d['rol']),
      codigo: d['codigo'] == null ? null : '${d['codigo']}',
      cerrado: d['cerrado'] == true,
      sinLeer: (d['sin_leer'] as num?)?.toInt() ?? 0,
      ultimoTexto: vista,
      ultimo: DateTime.tryParse('${d['ultimo'] ?? ''}')?.toLocal(),
    );
  }
}

class Autor {
  const Autor(this.id, this.usuario, this.nombre, {this.fotoUrl = '', this.rol = RolGrupo.ninguno});
  final String id;
  final String usuario;
  final String nombre;
  final String fotoUrl;
  final RolGrupo rol;
  String get visible => nombre.isNotEmpty ? nombre : usuario;

  static Autor desde(Object? a) {
    if (a is! Map) return const Autor('', '', 'Alguien que ya no está');
    return Autor('${a['id']}', '${a['usuario'] ?? ''}', '${a['nombre'] ?? ''}',
        fotoUrl: '${a['foto_url'] ?? ''}', rol: rolDe(a['rol']));
  }
}

class MensajeGrupo {
  MensajeGrupo({
    required this.id,
    required this.autor,
    this.texto = '',
    this.pista,
    this.audio,
    this.audioSeg = 0,
    this.mio = false,
    this.fijado = false,
    this.oculto = false,
    required this.creado,
  });

  final int id;
  final Autor autor;
  final String texto;
  final Json? pista;

  /// Ruta de la nota de voz en el almacén «audios-grupos» (se oye con una dirección firmada).
  final String? audio;
  final int audioSeg;
  final bool mio;
  final bool fijado;

  /// Oculto por reportes: solo lo ven quien modera y quien lo escribió.
  final bool oculto;
  final DateTime creado;

  factory MensajeGrupo.desde(Map d) => MensajeGrupo(
        id: (d['id'] as num).toInt(),
        autor: Autor.desde(d['autor']),
        texto: '${d['texto'] ?? ''}',
        pista: d['pista'] is Map ? Chat.pistaJugable(Map<String, dynamic>.from(d['pista'] as Map)) : null,
        audio: d['audio'] == null ? null : '${d['audio']}',
        audioSeg: (d['audio_seg'] as num?)?.toInt() ?? 0,
        mio: d['mio'] == true,
        fijado: d['fijado'] == true,
        oculto: d['oculto'] == true,
        creado: DateTime.tryParse('${d['creado']}')?.toLocal() ?? DateTime.now(),
      );
}

class MiembroGrupo {
  MiembroGrupo(this.autor, this.silenciadoHasta);
  final Autor autor;
  final DateTime? silenciadoHasta;
  bool get silenciado => silenciadoHasta != null && silenciadoHasta!.isAfter(DateTime.now());
}

class Grupos {
  Grupos(this.sesion);
  final Sesion sesion;

  static const almacenAudios = 'audios-grupos';

  /// Nota de voz: como mucho 3 minutos (lo mismo que acepta la base).
  static const maxSegundosAudio = 180;

  List<Json> _filas(Object? r) => [for (final d in (r as List? ?? const [])) if (d is Map) Map<String, dynamic>.from(d)];

  Future<List<Grupo>> misGrupos() async => [for (final d in _filas(await sesion.rpc('mis_grupos'))) Grupo.desde(d)];

  Future<int> sinLeer() async => (await misGrupos()).fold<int>(0, (s, g) => s + g.sinLeer);

  Future<List<Grupo>> explorar({String busqueda = '', int desde = 0}) async => [
        for (final d in _filas(await sesion.rpc('grupos_explorar', {'p_busqueda': busqueda.trim(), 'p_desde': desde})))
          Grupo.desde(d)
      ];

  Future<Grupo> crear(String nombre, {String descripcion = '', bool privado = false}) async {
    final r = await sesion.rpc('grupo_crear',
        {'p_nombre': nombre.trim(), 'p_descripcion': descripcion.trim(), 'p_tipo': privado ? 'privado' : 'abierto'});
    return Grupo.desde(r as Map);
  }

  Future<Grupo?> ver(String id) async {
    final r = await sesion.rpc('grupo_ver', {'p_grupo': id});
    return r is Map ? Grupo.desde(r) : null;
  }

  Future<Grupo> unirse(String id) async => Grupo.desde(await sesion.rpc('grupo_unirse', {'p_grupo': id}) as Map);

  /// El código se escribe como sea: minúsculas, con espacios o guiones.
  static String limpiarCodigo(String c) => c.toUpperCase().replaceAll(RegExp(r'[^A-Z0-9]'), '');

  Future<Grupo> unirseConCodigo(String codigo) async =>
      Grupo.desde(await sesion.rpc('grupo_unirse_codigo', {'p_codigo': limpiarCodigo(codigo)}) as Map);

  Future<void> salir(String id) => sesion.rpc('grupo_salir', {'p_grupo': id});

  /// Los últimos mensajes, del más viejo al más nuevo; con [antes], los anteriores a ese.
  Future<List<MensajeGrupo>> mensajes(String grupo, {int? antes, int limite = 50}) async {
    final l = [
      for (final d in _filas(await sesion.rpc('grupo_mensajes', {'p_grupo': grupo, 'p_antes': antes, 'p_limite': limite})))
        MensajeGrupo.desde(d)
    ];
    return l.reversed.toList();
  }

  Future<List<MensajeGrupo>> nuevos(String grupo, int desde) async => [
        for (final d in _filas(await sesion.rpc('grupo_mensajes_desde', {'p_grupo': grupo, 'p_desde': desde})))
          MensajeGrupo.desde(d)
      ];

  /// Lo que se comparte de una canción: solo lo justo para que suene (la base descarta lo demás).
  static Json pistaParaGrupo(Json p) {
    final artistas = p['artistas'];
    var artista = '${p['artista'] ?? ''}';
    if (artista.isEmpty && artistas is List) {
      artista = artistas.map((a) => a is Map ? '${a['nombre'] ?? ''}' : '$a').where((x) => x.isNotEmpty).join(', ');
    }
    return {
      'video_id': '${p['video_id'] ?? ''}',
      'titulo': '${p['titulo'] ?? ''}',
      'artista': artista,
      'miniatura': '${p['miniatura'] ?? ''}',
      'duracion': '${(p['duracion'] as num?)?.round() ?? 0}',
    };
  }

  Future<MensajeGrupo> enviar(String grupo, {String texto = '', Json? pista, String? audio, int audioSeg = 0}) async {
    final r = await sesion.rpc('grupo_enviar', {
      'p_grupo': grupo,
      'p_texto': texto.trim(),
      'p_pista': pista == null ? null : pistaParaGrupo(pista),
      'p_audio': audio,
      'p_audio_seg': audio == null ? null : audioSeg.clamp(1, maxSegundosAudio),
    });
    return MensajeGrupo.desde(r as Map);
  }

  /// Sube una nota de voz a la carpeta del grupo y de esta cuenta; devuelve su ruta para [enviar].
  Future<String> subirAudio(String grupo, List<int> bytes, String tipo) async {
    final ext = tipo.contains('webm')
        ? 'webm'
        : tipo.contains('ogg')
            ? 'ogg'
            : tipo.contains('wav')
                ? 'wav'
                : 'm4a';
    final ruta = '$grupo/${sesion.userId}/${DateTime.now().millisecondsSinceEpoch}.$ext';
    await sesion.subir(almacenAudios, ruta, bytes, tipo);
    return ruta;
  }

  Future<String> urlAudio(String ruta) => sesion.urlFirmada(almacenAudios, ruta);

  Future<void> leido(String grupo) async {
    try {
      await sesion.rpc('grupo_leido', {'p_grupo': grupo});
    } catch (_) {}
  }

  Future<void> reportar(int mensaje, {String motivo = ''}) =>
      sesion.rpc('grupo_reportar', {'p_mensaje': mensaje, 'p_motivo': motivo});

  /// borrar · ocultar · mostrar · fijar · desfijar
  Future<void> accion(int mensaje, String accion) =>
      sesion.rpc('grupo_mensaje_accion', {'p_mensaje': mensaje, 'p_accion': accion});

  Future<List<MensajeGrupo>> fijados(String grupo) async =>
      [for (final d in _filas(await sesion.rpc('grupo_fijados', {'p_grupo': grupo}))) MensajeGrupo.desde(d)];

  Future<List<(MensajeGrupo, int, List<String>)>> reportados(String grupo) async => [
        for (final d in _filas(await sesion.rpc('grupo_reportados', {'p_grupo': grupo})))
          (MensajeGrupo.desde(d), (d['reportes'] as num?)?.toInt() ?? 0,
              [for (final m in (d['motivos'] as List? ?? const [])) '$m'])
      ];

  Future<List<MiembroGrupo>> miembros(String grupo) async => [
        for (final d in _filas(await sesion.rpc('grupo_miembros_lista', {'p_grupo': grupo})))
          MiembroGrupo(Autor.desde(d), DateTime.tryParse('${d['silenciado_hasta'] ?? ''}')?.toLocal())
      ];

  Future<void> ponerRol(String grupo, String usuario, {required bool moderador}) =>
      sesion.rpc('grupo_poner_rol', {'p_grupo': grupo, 'p_usuario': usuario, 'p_rol': moderador ? 'moderador' : 'miembro'});

  Future<void> pasarDueno(String grupo, String usuario) =>
      sesion.rpc('grupo_pasar_dueno', {'p_grupo': grupo, 'p_usuario': usuario});

  Future<void> silenciar(String grupo, String usuario, int minutos) =>
      sesion.rpc('grupo_silenciar', {'p_grupo': grupo, 'p_usuario': usuario, 'p_minutos': minutos});

  Future<void> expulsar(String grupo, String usuario) =>
      sesion.rpc('grupo_expulsar', {'p_grupo': grupo, 'p_usuario': usuario});

  Future<Grupo> editar(String grupo, String nombre, String descripcion) async => Grupo.desde(
      await sesion.rpc('grupo_editar', {'p_grupo': grupo, 'p_nombre': nombre.trim(), 'p_descripcion': descripcion.trim()})
          as Map);

  Future<String> cambiarCodigo(String grupo) async =>
      '${await sesion.rpc('grupo_cambiar_codigo', {'p_grupo': grupo})}'.replaceAll('"', '');

  Future<void> borrar(String grupo) => sesion.rpc('grupo_borrar', {'p_grupo': grupo});
}
