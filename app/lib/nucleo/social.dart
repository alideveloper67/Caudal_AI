import 'dart:async';
import 'dart:math';
import 'dart:typed_data';
import 'dart:ui' show Color;

import 'package:flutter/foundation.dart' show compute;
import 'package:image/image.dart' as img;

import 'coleccion.dart' show Json;
import 'cosmeticos.dart';
import 'nube.dart';

/// La parte social de Caudal: perfiles, amigos, me gusta y la música de la
/// gente. Todo pasa por las funciones de supabase/social.sql; aquí solo se
/// llaman y se convierten sus respuestas en objetos.
///
/// Los modelos son tolerantes: un campo que falte o llegue raro no rompe nada.

// ============================================================ lectura tolerante

String _s(Object? v, [String defecto = '']) => v == null ? defecto : '$v';
int _i(Object? v, [int defecto = 0]) => v is num ? v.toInt() : int.tryParse('$v') ?? defecto;
bool _b(Object? v, [bool defecto = false]) => v is bool ? v : (v == null ? defecto : '$v' == 'true');
DateTime? _f(Object? v) => v == null ? null : DateTime.tryParse('$v')?.toLocal();
List<Map> _maps(Object? v) => v is List ? [for (final x in v) if (x is Map) x] : const [];
Map<String, dynamic>? _mapa(Object? v) => v is Map ? Map<String, dynamic>.from(v) : null;

/// Cómo está la relación con otra persona (campo `relacion` de la base).
class Relacion {
  Relacion._();
  static const yo = 'yo';
  static const amigo = 'amigo';
  static const enviada = 'enviada';
  static const recibida = 'recibida';
  static const ninguna = 'ninguna';
  static const bloqueado = 'bloqueado';

  /// Un valor desconocido se trata como «ninguna».
  static String normal(Object? v) {
    final t = _s(v);
    return const {yo, amigo, enviada, recibida, ninguna, bloqueado}.contains(t) ? t : ninguna;
  }
}

// ============================================================ modelos

/// La canción favorita del perfil.
class CancionFav {
  const CancionFav({this.videoId = '', this.titulo = '', this.artista = '', this.miniatura = ''});
  final String videoId;
  final String titulo;
  final String artista;
  final String miniatura;

  bool get vacia => titulo.isEmpty && artista.isEmpty;

  static CancionFav? desde(Object? v) {
    final m = _mapa(v);
    if (m == null) return null;
    final c = CancionFav(
      videoId: _s(m['video_id']),
      titulo: _s(m['titulo']),
      artista: _s(m['artista']),
      miniatura: _s(m['miniatura']),
    );
    return c.vacia ? null : c;
  }

  /// A partir de una pista del catálogo (resultado del buscador).
  static CancionFav dePista(Json p) => CancionFav(
        videoId: _s(p['video_id']),
        titulo: _s(p['titulo']),
        artista: _s(p['artista']),
        miniatura: _s(p['miniatura']),
      );

  Map<String, dynamic> toJson() =>
      {'video_id': videoId, 'titulo': titulo, 'artista': artista, 'miniatura': miniatura};

  /// Para reproducirla como cualquier pista de YouTube Music.
  Json comoPista() => {
        'tipo': 'pista',
        'clave': 'yt:$videoId',
        'video_id': videoId,
        'titulo': titulo,
        'artista': artista,
        'miniatura': miniatura,
      };
}

class Insignia {
  const Insignia({required this.clave, required this.titulo, this.detalle = ''});
  final String clave;
  final String titulo;
  final String detalle;

  static Insignia? desde(Object? v) {
    final m = _mapa(v);
    if (m == null) return null;
    final clave = _s(m['clave']);
    final titulo = _s(m['titulo']);
    if (clave.isEmpty && titulo.isEmpty) return null;
    return Insignia(clave: clave, titulo: titulo.isEmpty ? clave : titulo, detalle: _s(m['detalle']));
  }
}

/// Un título especial (`fundador_caudal`, `rey_de_la_musica`...). Se dibuja
/// con el [nombre] que llega; una clave desconocida sale como chip dorado.
class TituloEspecial {
  const TituloEspecial({required this.clave, required this.nombre});
  final String clave;
  final String nombre;

  static TituloEspecial? desde(Object? v) {
    final m = _mapa(v);
    if (m == null) return null;
    final nombre = _s(m['nombre']);
    final clave = _s(m['clave']);
    if (nombre.isEmpty && clave.isEmpty) return null;
    return TituloEspecial(clave: clave, nombre: nombre.isEmpty ? clave : nombre);
  }

  /// Lista tolerante; si `fundador_caudal` viene como bool pero no en la
  /// lista, se añade. «Fundador de Caudal» va siempre primero.
  static List<TituloEspecial> lista(Object? v, {bool fundadorCaudal = false}) {
    final l = [for (final x in (v is List ? v : const [])) ?TituloEspecial.desde(x)];
    if (fundadorCaudal && !l.any((t) => t.clave == 'fundador_caudal')) {
      l.add(const TituloEspecial(clave: 'fundador_caudal', nombre: 'Fundador de Caudal'));
    }
    l.sort((a, b) => (a.clave == 'fundador_caudal' ? 0 : 1).compareTo(b.clave == 'fundador_caudal' ? 0 : 1));
    return l;
  }
}

class ArtistaTop {
  const ArtistaTop({required this.nombre, this.portada = '', this.veces = 0});
  final String nombre;
  final String portada;
  final int veces;

  static ArtistaTop? desde(Object? v) {
    final m = _mapa(v);
    if (m == null || _s(m['nombre']).isEmpty) return null;
    return ArtistaTop(nombre: _s(m['nombre']), portada: _s(m['portada']), veces: _i(m['veces']));
  }
}

/// Una fila del directorio «Perfiles de Caudal» (`explorar_perfiles`).
class PerfilTarjeta {
  const PerfilTarjeta({
    required this.id,
    required this.usuario,
    this.nombre = '',
    this.fotoUrl = '',
    this.bio = '',
    this.cancionFav,
    this.colorPerfil = '',
    this.relacion = Relacion.ninguna,
    this.likes = 0,
    this.diLike = false,
    this.numSubidas = 0,
    this.esArtista = false,
    this.fundador = false,
    this.titulos = const [],
    this.bannerUrl = '',
    this.marco = Cosmeticos.ninguno,
    this.efectoNombre = Cosmeticos.ninguno,
  });

  /// Imagen de fondo (ruta `<id>/banner.jpg`), vacía si no tiene.
  final String bannerUrl;

  /// Marco del avatar y efecto del nombre de un donador («ninguno» si no tiene).
  final String marco;
  final String efectoNombre;

  /// Una de las 100 primeras personas de Caudal («Usuario fundador ★»).
  final bool fundador;
  final List<TituloEspecial> titulos;

  final String id;
  final String usuario;
  final String nombre;
  final String fotoUrl;
  final String bio;
  final CancionFav? cancionFav;
  final String colorPerfil;
  final String relacion;
  final int likes;
  final bool diLike;
  final int numSubidas;
  final bool esArtista;

  String get visible => nombre.trim().isNotEmpty ? nombre.trim() : usuario;
  bool get esMio => relacion == Relacion.yo;

  factory PerfilTarjeta.desde(Map d) => PerfilTarjeta(
        id: _s(d['id']),
        usuario: _s(d['usuario']),
        nombre: _s(d['nombre']),
        fotoUrl: _s(d['foto_url']),
        bio: _s(d['bio']),
        cancionFav: CancionFav.desde(d['cancion_fav']),
        colorPerfil: _s(d['color_perfil']),
        relacion: Relacion.normal(d['relacion']),
        likes: _i(d['likes']),
        diLike: _b(d['di_like']),
        numSubidas: _i(d['num_subidas']),
        esArtista: _b(d['es_artista']),
        fundador: _b(d['fundador']),
        titulos: TituloEspecial.lista(d['titulos'], fundadorCaudal: _b(d['fundador_caudal'])),
        bannerUrl: _s(d['banner_url']),
        marco: Cosmeticos.marco(d['marco']),
        efectoNombre: Cosmeticos.efectoNombre(d['efecto_nombre']),
      );

  PerfilTarjeta conLike(bool di, int total) => PerfilTarjeta(
        id: id, usuario: usuario, nombre: nombre, fotoUrl: fotoUrl, bio: bio, cancionFav: cancionFav,
        colorPerfil: colorPerfil, relacion: relacion, likes: total, diLike: di, numSubidas: numSubidas,
        esArtista: total >= Social.likesParaArtista || esArtista, fundador: fundador, titulos: titulos,
        bannerUrl: bannerUrl, marco: marco, efectoNombre: efectoNombre,
      );

  PerfilTarjeta conRelacion(String r) => PerfilTarjeta(
        id: id, usuario: usuario, nombre: nombre, fotoUrl: fotoUrl, bio: bio, cancionFav: cancionFav,
        colorPerfil: colorPerfil, relacion: r, likes: likes, diLike: diLike, numSubidas: numSubidas,
        esArtista: esArtista, fundador: fundador, titulos: titulos,
        bannerUrl: bannerUrl, marco: marco, efectoNombre: efectoNombre,
      );
}

/// Una lista que se ve en un perfil (`listas_de_perfil`).
class ListaPerfil {
  const ListaPerfil({
    required this.id,
    required this.nombre,
    this.total = 0,
    this.publica = false,
    this.enPerfil = false,
    this.miniatura = '',
  });

  final String id;
  final String nombre;
  final int total;
  final bool publica;
  final bool enPerfil;
  final String miniatura;

  static ListaPerfil desde(Map m) {
    final canciones = m['canciones'] is List ? m['canciones'] as List : const [];
    String mini = '';
    for (final c in canciones) {
      if (c is Map && '${c['miniatura'] ?? ''}'.isNotEmpty) {
        mini = '${c['miniatura']}';
        break;
      }
    }
    return ListaPerfil(
      id: '${m['id'] ?? ''}',
      nombre: '${m['nombre'] ?? 'Lista'}',
      total: m['total'] is num ? (m['total'] as num).toInt() : 0,
      publica: m['publica'] == true,
      enPerfil: m['publica'] == true && m['en_perfil'] == true,
      miniatura: mini,
    );
  }

  /// Las canciones de una lista abierta con `ver_lista_publica`, listas para reproducir.
  static List<Json> pistasDe(Map? lista) {
    final items = lista != null && lista['canciones'] is List ? lista['canciones'] as List : const [];
    final salida = <Json>[];
    for (final i in items) {
      if (i is! Map) continue;
      final datos = i['datos'] is Map ? Map<String, dynamic>.from(i['datos'] as Map) : <String, dynamic>{};
      final clave = '${i['clave'] ?? datos['clave'] ?? ''}';
      if (!clave.startsWith('yt:')) continue; // solo lo que suena en linea: lo local no viaja
      datos['clave'] = clave;
      datos.putIfAbsent('video_id', () => clave.substring(3));
      salida.add(datos);
    }
    return salida;
  }
}

/// El perfil completo de alguien (`ver_perfil`).
class Perfil {
  const Perfil({
    required this.id,
    required this.usuario,
    this.nombre = '',
    this.fotoUrl = '',
    this.relacion = Relacion.ninguna,
    this.privado = false,
    this.bio = '',
    this.cancionFav,
    this.artistaFav = '',
    this.generos = const [],
    this.frase = '',
    this.colorPerfil = '',
    this.creado,
    this.esMio = false,
    this.publico = false,
    this.mostrarTop = true,
    this.topArtistas = const [],
    this.topCanciones = const [],
    this.insignias = const [],
    this.afinidad,
    this.likes = 0,
    this.diLike = false,
    this.esArtista = false,
    this.numSubidas = 0,
    this.subidas = const [],
    this.fundador = false,
    this.numero,
    this.titulos = const [],
    this.bannerUrl = '',
    this.marco = Cosmeticos.ninguno,
    this.efectoNombre = Cosmeticos.ninguno,
  });

  /// Imagen de fondo del perfil (ruta `<id>/banner.jpg`), vacía si no tiene.
  final String bannerUrl;

  /// Marco del avatar y efecto del nombre de un donador («ninguno» si no tiene).
  final String marco;
  final String efectoNombre;

  /// Una de las 100 primeras personas; [numero] es su orden de llegada.
  final bool fundador;
  final int? numero;
  final List<TituloEspecial> titulos;

  final String id;
  final String usuario;
  final String nombre;
  final String fotoUrl;
  final String relacion;

  /// Perfil privado de alguien que no es amigo: solo se ve lo básico.
  final bool privado;
  final String bio;
  final CancionFav? cancionFav;
  final String artistaFav;
  final List<String> generos;
  final String frase;
  final String colorPerfil;
  final DateTime? creado;
  final bool esMio;
  final bool publico;
  final bool mostrarTop;
  final List<ArtistaTop> topArtistas;
  final List<Json> topCanciones;
  final List<Insignia> insignias;
  final int? afinidad;
  final int likes;
  final bool diLike;
  final bool esArtista;
  final int numSubidas;
  final List<Subida> subidas;

  String get visible => nombre.trim().isNotEmpty ? nombre.trim() : usuario;

  /// Solo se pueden dar me gusta a perfiles públicos de otras personas.
  bool get sePuedeDarLike => !esMio && !privado;

  static Perfil? desde(Object? v) {
    final d = _mapa(v);
    if (d == null || _s(d['id']).isEmpty) return null;
    final usuario = _s(d['usuario']);
    final subidas = [for (final m in _maps(d['subidas'])) Subida.desde({...m, 'usuario': usuario, 'user_id': d['id']})];
    final likes = _i(d['likes']);
    return Perfil(
      id: _s(d['id']),
      usuario: usuario,
      nombre: _s(d['nombre']),
      fotoUrl: _s(d['foto_url']),
      relacion: Relacion.normal(d['relacion']),
      privado: _b(d['privado']),
      bio: _s(d['bio']),
      cancionFav: CancionFav.desde(d['cancion_fav']),
      artistaFav: _s(d['artista_fav']),
      generos: d['generos'] is List ? [for (final g in d['generos'] as List) _s(g)] : const [],
      frase: _s(d['frase']),
      colorPerfil: _s(d['color_perfil']),
      creado: _f(d['creado']),
      esMio: _b(d['es_mio']) || Relacion.normal(d['relacion']) == Relacion.yo,
      publico: _b(d['publico']),
      mostrarTop: _b(d['mostrar_top'], true),
      topArtistas: [for (final x in (d['top_artistas'] as List? ?? const [])) ?ArtistaTop.desde(x)],
      topCanciones: [for (final m in _maps(d['top_canciones'])) Map<String, dynamic>.from(m)],
      insignias: [for (final x in (d['insignias'] as List? ?? const [])) ?Insignia.desde(x)],
      afinidad: d['afinidad'] is num ? (d['afinidad'] as num).toInt() : null,
      likes: likes,
      diLike: _b(d['di_like']),
      esArtista: _b(d['es_artista']),
      numSubidas: _i(d['num_subidas'], subidas.length),
      subidas: subidas,
      fundador: _b(d['fundador']),
      numero: d['numero'] is num ? (d['numero'] as num).toInt() : null,
      titulos: TituloEspecial.lista(d['titulos'], fundadorCaudal: _b(d['fundador_caudal'])),
      bannerUrl: _s(d['banner_url']),
      marco: Cosmeticos.marco(d['marco']),
      efectoNombre: Cosmeticos.efectoNombre(d['efecto_nombre']),
    );
  }

  Perfil conRelacion(String r) => _copia(relacion: r);
  Perfil conLike(bool di, int total) => _copia(diLike: di, likes: total);

  Perfil _copia({String? relacion, bool? diLike, int? likes}) => Perfil(
        id: id, usuario: usuario, nombre: nombre, fotoUrl: fotoUrl, relacion: relacion ?? this.relacion,
        privado: privado, bio: bio, cancionFav: cancionFav, artistaFav: artistaFav, generos: generos,
        frase: frase, colorPerfil: colorPerfil, creado: creado, esMio: esMio, publico: publico,
        mostrarTop: mostrarTop, topArtistas: topArtistas, topCanciones: topCanciones, insignias: insignias,
        afinidad: afinidad, likes: likes ?? this.likes, diLike: diLike ?? this.diLike,
        esArtista: (likes ?? this.likes) >= Social.likesParaArtista || esArtista, numSubidas: numSubidas,
        subidas: subidas, fundador: fundador, numero: numero, titulos: titulos,
        bannerUrl: bannerUrl, marco: marco, efectoNombre: efectoNombre,
      );
}

/// Una canción subida por alguien de la comunidad.
class Subida {
  const Subida({
    required this.id,
    this.userId = '',
    this.usuario = '',
    this.titulo = '',
    this.artista = '',
    this.album = '',
    this.duracion = 0,
    this.ruta = '',
    this.portada = '',
    this.escuchas = 0,
    this.estado = 'publicada',
    this.creado,
    this.esArtista = false,
    this.nota = '',
  });

  /// Motivo del rechazo (solo cuando está `retirada`).
  final String nota;

  final String id;
  final String userId;
  final String usuario;
  final String titulo;
  final String artista;
  final String album;
  final int duracion;
  final String ruta;
  final String portada;
  final int escuchas;

  /// `pendiente`, `publicada`, `revision` o `retirada` (lo no publicado solo lo ve su dueño).
  final String estado;
  final DateTime? creado;
  final bool esArtista;

  bool get publicada => estado == 'publicada';
  String get urlAudio => Social.urlMusica(ruta);
  String get urlPortada => Social.urlMusica(portada);
  String get tituloVisible => titulo.trim().isEmpty ? 'Sin título' : titulo.trim();

  /// «Artista · Álbum» sin huecos raros.
  String get linea => [artista.trim(), album.trim()].where((x) => x.isNotEmpty).join(' · ');

  factory Subida.desde(Map d) => Subida(
        id: _s(d['id']),
        userId: _s(d['user_id']),
        usuario: _s(d['usuario']),
        titulo: _s(d['titulo']),
        artista: _s(d['artista']),
        album: _s(d['album']),
        duracion: _i(d['duracion']),
        ruta: _s(d['ruta']),
        portada: _s(d['portada']),
        escuchas: _i(d['escuchas']),
        estado: _s(d['estado'], 'publicada'),
        creado: _f(d['creado']),
        esArtista: _b(d['es_artista']),
        nota: _s(d['nota']),
      );

  /// Texto del estado para mostrarlo a su dueño (vacío si está publicada).
  String get textoEstado => switch (estado) {
        'pendiente' => 'En revisión',
        'revision' => 'En revisión por reportes',
        'retirada' => nota.trim().isEmpty ? 'Rechazada' : 'Rechazada: ${nota.trim()}',
        _ => '',
      };

  /// Cómo se representa una canción de la comunidad en el reproductor.
  ///
  /// Las pistas que no son de YouTube se reconocen por no tener `video_id`;
  /// el reproductor las abre desde `archivo`. Aquí `archivo` es una dirección
  /// de internet (lo que `Fuente.archivo` entiende igual que una ruta). Además
  /// lleva `subida_id` y `url_directa` por si la pista se guarda en una lista:
  /// al guardarse en la nube se pierde `archivo`, pero estos dos se conservan.
  Json comoPista() => {
        'tipo': 'pista',
        'clave': 'sub:$id',
        'video_id': '',
        'titulo': tituloVisible,
        'artista': artista.trim().isEmpty ? (usuario.isEmpty ? 'Comunidad Caudal' : '@$usuario') : artista.trim(),
        'album': album,
        'duracion': duracion,
        'miniatura': urlPortada,
        'archivo': urlAudio,
        'es_audio': true,
        'subida_id': id,
        'url_directa': urlAudio,
        'subido_por': usuario,
      };
}

/// Una canción esperando revisión (`revision_pendientes`).
class SubidaRevision {
  const SubidaRevision({
    required this.subida,
    this.nombre = '',
    this.tamano = 0,
    this.reportes = 0,
    this.motivos = const [],
  });
  final Subida subida;
  final String nombre;
  final int tamano;
  final int reportes;
  final List<String> motivos;

  String get quien => nombre.trim().isNotEmpty ? nombre.trim() : subida.usuario;

  factory SubidaRevision.desde(Map d) => SubidaRevision(
        subida: Subida.desde(d),
        nombre: _s(d['nombre']),
        tamano: _i(d['tamano']),
        reportes: _i(d['reportes']),
        motivos: d['motivos'] is List ? [for (final m in d['motivos'] as List) if (_s(m).isNotEmpty) _s(m)] : const [],
      );
}

/// Alguien de las listas de amigos, solicitudes, bloqueados o de una búsqueda.
class Contacto {
  const Contacto({
    required this.id,
    required this.usuario,
    this.nombre = '',
    this.fotoUrl = '',
    this.relacion = Relacion.ninguna,
    this.solicitudId,
    this.fecha,
    this.marco = Cosmeticos.ninguno,
    this.efectoNombre = Cosmeticos.ninguno,
  });

  /// Marco del avatar y efecto del nombre de un donador («ninguno» si no tiene).
  final String marco;
  final String efectoNombre;

  /// Identificador de la persona (no el de la solicitud).
  final String id;
  final String usuario;
  final String nombre;
  final String fotoUrl;
  final String relacion;

  /// Solo en las solicitudes recibidas: lo que se pasa a `responder_solicitud`.
  final int? solicitudId;
  final DateTime? fecha;

  String get visible => nombre.trim().isNotEmpty ? nombre.trim() : usuario;

  /// Solicitud recibida (`mis_solicitudes`).
  factory Contacto.recibida(Map d) => Contacto(
        id: _s(d['de']),
        usuario: _s(d['usuario']),
        nombre: _s(d['nombre']),
        fotoUrl: _s(d['foto_url']),
        relacion: Relacion.recibida,
        solicitudId: d['id'] is num ? (d['id'] as num).toInt() : null,
        fecha: _f(d['creado']),
        marco: Cosmeticos.marco(d['marco']),
        efectoNombre: Cosmeticos.efectoNombre(d['efecto_nombre']),
      );

  /// Solicitud enviada (`mis_enviadas`).
  factory Contacto.enviada(Map d) => Contacto(
        id: _s(d['para']),
        usuario: _s(d['usuario']),
        nombre: _s(d['nombre']),
        fotoUrl: _s(d['foto_url']),
        relacion: Relacion.enviada,
        fecha: _f(d['creado']),
        marco: Cosmeticos.marco(d['marco']),
        efectoNombre: Cosmeticos.efectoNombre(d['efecto_nombre']),
      );

  /// Amigo (`mis_amigos`).
  factory Contacto.amigo(Map d) => Contacto(
        id: _s(d['id']),
        usuario: _s(d['usuario']),
        nombre: _s(d['nombre']),
        fotoUrl: _s(d['foto_url']),
        relacion: Relacion.amigo,
        fecha: _f(d['desde']),
        marco: Cosmeticos.marco(d['marco']),
        efectoNombre: Cosmeticos.efectoNombre(d['efecto_nombre']),
      );

  /// Bloqueado (`mis_bloqueados`).
  factory Contacto.bloqueado(Map d) => Contacto(
        id: _s(d['id']),
        usuario: _s(d['usuario']),
        nombre: _s(d['nombre']),
        fotoUrl: _s(d['foto_url']),
        relacion: Relacion.bloqueado,
        marco: Cosmeticos.marco(d['marco']),
        efectoNombre: Cosmeticos.efectoNombre(d['efecto_nombre']),
      );

  /// Resultado de buscar por usuario exacto (`buscar_persona`).
  factory Contacto.busqueda(Map d) => Contacto(
        id: _s(d['id']),
        usuario: _s(d['usuario']),
        nombre: _s(d['nombre']),
        fotoUrl: _s(d['foto_url']),
        relacion: Relacion.normal(d['relacion']),
        marco: Cosmeticos.marco(d['marco']),
        efectoNombre: Cosmeticos.efectoNombre(d['efecto_nombre']),
      );

  Contacto conRelacion(String r) => Contacto(
        id: id, usuario: usuario, nombre: nombre, fotoUrl: fotoUrl, relacion: r,
        solicitudId: solicitudId, fecha: fecha, marco: marco, efectoNombre: efectoNombre,
      );
}

/// Lo que se puede editar del perfil propio.
class PerfilEditable {
  const PerfilEditable({
    this.nombre = '',
    this.bio = '',
    this.frase = '',
    this.fotoUrl = '',
    this.cancionFav,
    this.artistaFav = '',
    this.generos = const [],
    this.colorPerfil = '',
    this.perfilPublico = false,
    this.mostrarTop = true,
    this.fechaNacimiento,
    this.bannerUrl = '',
  });

  /// Imagen de fondo (ruta `<id>/banner.jpg`), vacía si no tiene.
  final String bannerUrl;

  final String nombre;
  final String bio;
  final String frase;
  final String fotoUrl;
  final CancionFav? cancionFav;
  final String artistaFav;
  final List<String> generos;
  final String colorPerfil;
  final bool perfilPublico;
  final bool mostrarTop;
  final DateTime? fechaNacimiento;

  /// Menor de 18: la base no le deja tener el perfil público. Sin fecha
  /// conocida se asume que sí puede (la base decide al guardar).
  bool get esMenor {
    final n = fechaNacimiento;
    if (n == null) return false;
    final h = DateTime.now();
    var edad = h.year - n.year;
    if (h.month < n.month || (h.month == n.month && h.day < n.day)) edad--;
    return edad < 18;
  }

  factory PerfilEditable.desde(Map d) => PerfilEditable(
        nombre: _s(d['nombre']),
        bio: _s(d['bio']),
        frase: _s(d['frase']),
        fotoUrl: _s(d['foto_url']),
        cancionFav: CancionFav.desde(d['cancion_fav']),
        artistaFav: _s(d['artista_fav']),
        generos: d['generos'] is List ? [for (final g in d['generos'] as List) _s(g)] : const [],
        colorPerfil: _s(d['color_perfil']),
        perfilPublico: _b(d['perfil_publico']),
        mostrarTop: _b(d['mostrar_top'], true),
        fechaNacimiento: DateTime.tryParse(_s(d['fecha_nacimiento'])),
        bannerUrl: _s(d['banner_url']),
      );

  /// El cuerpo del PATCH. `cancion_fav`, `foto_url` y `color_perfil` van como
  /// null cuando están vacíos (así la base los deja sin valor).
  Map<String, dynamic> paraGuardar() => {
        'nombre': nombre.trim(),
        'bio': bio.trim(),
        'frase': frase.trim(),
        'foto_url': fotoUrl.isEmpty ? null : fotoUrl,
        'banner_url': bannerUrl.isEmpty ? null : bannerUrl,
        'cancion_fav': cancionFav?.toJson(),
        'artista_fav': artistaFav.trim(),
        'generos': generos,
        'color_perfil': colorPerfil.isEmpty ? null : colorPerfil,
        'perfil_publico': perfilPublico,
        'mostrar_top': mostrarTop,
      };

  PerfilEditable copiar({
    String? nombre, String? bio, String? frase, String? fotoUrl, Object? cancionFav = _igual,
    String? artistaFav, List<String>? generos, String? colorPerfil, bool? perfilPublico, bool? mostrarTop,
    String? bannerUrl,
  }) =>
      PerfilEditable(
        nombre: nombre ?? this.nombre,
        bio: bio ?? this.bio,
        frase: frase ?? this.frase,
        fotoUrl: fotoUrl ?? this.fotoUrl,
        cancionFav: identical(cancionFav, _igual) ? this.cancionFav : cancionFav as CancionFav?,
        artistaFav: artistaFav ?? this.artistaFav,
        generos: generos ?? this.generos,
        colorPerfil: colorPerfil ?? this.colorPerfil,
        perfilPublico: perfilPublico ?? this.perfilPublico,
        mostrarTop: mostrarTop ?? this.mostrarTop,
        fechaNacimiento: fechaNacimiento,
        bannerUrl: bannerUrl ?? this.bannerUrl,
      );
}

const Object _igual = Object();

// ============================================================ imágenes

/// Recorte cuadrado y compresión de las fotos (se hace fuera del hilo de la
/// pantalla para no trabar la interfaz).
class ImagenSocial {
  ImagenSocial._();

  /// Foto de perfil: cuadrada, 512 px, JPEG que pese menos de 2 MB.
  static Future<Uint8List> foto(Uint8List original) => compute(_fotoPerfil, original);

  /// Imagen de fondo: recorte al centro de 1280×480 (8:3), JPEG < 2 MB.
  static Future<Uint8List> banner(Uint8List original) => compute(_bannerPerfil, original);

  /// Portada de una lista: recorte al centro en cuadrado, 800 px, JPEG.
  static Future<Uint8List> cuadrada(Uint8List original) => compute(_portadaLista, original);

  /// Carátula: como mucho 800 px de lado, JPEG.
  static Future<Uint8List> caratula(Uint8List original) => compute(_caratula, original);
}

Uint8List _fotoPerfil(Uint8List b) => cuadrarYComprimir(b, 512, recortar: true);
Uint8List _bannerPerfil(Uint8List b) => recortarBanner(b, 1280, 480);
Uint8List _portadaLista(Uint8List b) => cuadrarYComprimir(b, 800, recortar: true);
Uint8List _caratula(Uint8List b) => cuadrarYComprimir(b, 800, recortar: false);

/// Decodifica, corrige la orientación, recorta al centro (o solo reduce) y
/// devuelve un JPEG. Lanza [ErrorNube] si no es una imagen válida.
Uint8List cuadrarYComprimir(Uint8List bytes, int lado, {required bool recortar, int maxBytes = 1900000}) {
  img.Image? im;
  try {
    im = img.decodeImage(bytes);
  } catch (_) {}
  if (im == null) {
    throw const ErrorNube('No se pudo leer esa imagen. Prueba con una foto JPG o PNG.');
  }
  im = img.bakeOrientation(im);
  if (recortar) {
    final m = min(im.width, im.height);
    im = img.copyCrop(im, x: (im.width - m) ~/ 2, y: (im.height - m) ~/ 2, width: m, height: m);
  }
  if (max(im.width, im.height) > lado) {
    im = im.width >= im.height ? img.copyResize(im, width: lado) : img.copyResize(im, height: lado);
  }
  var calidad = 88;
  var salida = img.encodeJpg(im, quality: calidad);
  while (salida.length > maxBytes && calidad > 40) {
    calidad -= 12;
    salida = img.encodeJpg(im, quality: calidad);
  }
  return Uint8List.fromList(salida);
}

/// Recorta al centro con la proporción [ancho]:[alto] y lo deja exactamente
/// de ese tamaño (si la imagen es más chica, se amplía lo justo). JPEG < 2 MB.
Uint8List recortarBanner(Uint8List bytes, int ancho, int alto, {int maxBytes = 1900000}) {
  img.Image? im;
  try {
    im = img.decodeImage(bytes);
  } catch (_) {}
  if (im == null) {
    throw const ErrorNube('No se pudo leer esa imagen. Prueba con una foto JPG o PNG.');
  }
  im = img.bakeOrientation(im);
  final proporcion = ancho / alto;
  var w = im.width, h = (im.width / proporcion).round();
  if (h > im.height) {
    h = im.height;
    w = (im.height * proporcion).round();
  }
  im = img.copyCrop(im, x: (im.width - w) ~/ 2, y: (im.height - h) ~/ 2, width: w, height: h);
  if (im.width != ancho) im = img.copyResize(im, width: ancho, height: alto);
  var calidad = 86;
  var salida = img.encodeJpg(im, quality: calidad);
  while (salida.length > maxBytes && calidad > 40) {
    calidad -= 12;
    salida = img.encodeJpg(im, quality: calidad);
  }
  return Uint8List.fromList(salida);
}

// ============================================================ la capa de datos

class Social {
  Social(this.sesion);
  final Sesion sesion;

  String get yo => sesion.userId;

  /// Con 200 me gusta llega la nota ARTISTA.
  static const likesParaArtista = 200;
  static const maxAudioBytes = 15 * 1024 * 1024;
  static const extensionesAudio = ['mp3', 'm4a', 'aac', 'flac', 'ogg', 'wav', 'webm'];

  static String urlPublica(String bucket, String ruta) =>
      ruta.isEmpty ? '' : '${Nube.url}/storage/v1/object/public/$bucket/$ruta';

  /// URL de un archivo del almacén `musica` (audio o carátula).
  static String urlMusica(String ruta) => urlPublica('musica', ruta);

  /// URL de la foto de perfil. [marca] salta la caché cuando la foto cambia;
  /// sin marca se usa el día de hoy (se refresca una vez al día).
  static String urlFoto(String fotoUrl, {Object? marca}) {
    if (fotoUrl.isEmpty) return '';
    if (fotoUrl.startsWith('http')) return fotoUrl;
    final v = marca ?? _marcaDelDia();
    return '${urlPublica('avatares', fotoUrl)}?v=$v';
  }

  /// URL de la imagen de fondo del perfil (misma idea que [urlFoto]).
  static String urlBanner(String bannerUrl, {Object? marca}) => urlFoto(bannerUrl, marca: marca);

  static int _marcaDelDia() => DateTime.now().millisecondsSinceEpoch ~/ Duration.millisecondsPerDay;

  /// «#RRGGBB» → Color (null si no es válido).
  static Color? colorDe(String hex) {
    final m = RegExp(r'^#([0-9A-Fa-f]{6})$').firstMatch(hex.trim());
    if (m == null) return null;
    return Color(0xFF000000 | int.parse(m.group(1)!, radix: 16));
  }

  static String hexDe(Color c) {
    String h(double v) => (v * 255).round().clamp(0, 255).toRadixString(16).padLeft(2, '0');
    return '#${h(c.r)}${h(c.g)}${h(c.b)}'.toUpperCase();
  }

  /// Extensión permitida para el audio (null si no lo es).
  static String? extensionAudio(String nombre) {
    final i = nombre.lastIndexOf('.');
    if (i < 0) return null;
    final e = nombre.substring(i + 1).toLowerCase();
    return extensionesAudio.contains(e) ? e : null;
  }

  static String tipoAudio(String ext) => switch (ext) {
        'mp3' => 'audio/mpeg',
        'm4a' => 'audio/mp4',
        'aac' => 'audio/aac',
        'flac' => 'audio/flac',
        'ogg' => 'audio/ogg',
        'wav' => 'audio/wav',
        'webm' => 'audio/webm',
        _ => 'application/octet-stream',
      };

  /// Un nombre de archivo seguro para la ruta del almacén.
  static String nombreSeguro(String base, String ext) {
    final limpio = base.toLowerCase().replaceAll(RegExp(r'[^a-z0-9]+'), '-').replaceAll(RegExp(r'^-+|-+$'), '');
    final corto = limpio.length > 40 ? limpio.substring(0, 40) : limpio;
    return '${DateTime.now().millisecondsSinceEpoch}-${corto.isEmpty ? 'cancion' : corto}.$ext';
  }

  Future<List<Map>> _lista(String fn, [Map<String, dynamic> p = const {}]) async =>
      _maps(await sesion.rpc(fn, p));

  // ------------------------------------------------------------ amistades

  Future<List<Contacto>> amigos() async => [for (final d in await _lista('mis_amigos')) Contacto.amigo(d)];
  Future<List<Contacto>> solicitudes() async =>
      [for (final d in await _lista('mis_solicitudes')) Contacto.recibida(d)];
  Future<List<Contacto>> enviadas() async => [for (final d in await _lista('mis_enviadas')) Contacto.enviada(d)];
  Future<List<Contacto>> bloqueados() async =>
      [for (final d in await _lista('mis_bloqueados')) Contacto.bloqueado(d)];

  /// Cuántas solicitudes están esperando respuesta (para la insignia).
  Future<int> contarSolicitudes() async => (await solicitudes()).length;

  /// Busca por usuario exacto.
  Future<Contacto?> buscarPersona(String usuario) async {
    final u = usuario.trim().replaceFirst('@', '').toLowerCase();
    if (u.isEmpty) return null;
    final l = await _lista('buscar_persona', {'p_usuario': u});
    return l.isEmpty ? null : Contacto.busqueda(l.first);
  }

  /// Devuelve `enviada`, `aceptada`, `ya_amigos` o `ya_enviada`.
  Future<String> enviarSolicitud(String otro) async =>
      _s(await sesion.rpc('enviar_solicitud', {'p_otro': otro}));

  Future<void> responderSolicitud(int id, bool acepta) =>
      sesion.rpc('responder_solicitud', {'p_id': id, 'p_acepta': acepta});
  Future<void> cancelarSolicitud(String otro) => sesion.rpc('cancelar_solicitud', {'p_otro': otro});
  Future<void> quitarAmigo(String otro) => sesion.rpc('quitar_amigo', {'p_otro': otro});
  Future<void> bloquear(String otro) => sesion.rpc('bloquear', {'p_otro': otro});
  Future<void> desbloquear(String otro) => sesion.rpc('desbloquear', {'p_otro': otro});

  /// Frase de lo que pasó al enviar una solicitud.
  static String resultadoSolicitud(String r, String nombre) => switch (r) {
        'aceptada' => '¡Ahora tú y $nombre son amigos!',
        'ya_amigos' => 'Ya eres amigo de $nombre.',
        'ya_enviada' => 'Ya le enviaste una solicitud a $nombre. Espera su respuesta.',
        _ => 'Solicitud enviada a $nombre.',
      };

  /// La relación que queda después de enviar la solicitud.
  static String relacionTras(String r) => switch (r) {
        'aceptada' || 'ya_amigos' => Relacion.amigo,
        _ => Relacion.enviada,
      };

  // ------------------------------------------------------------ perfiles

  Future<List<PerfilTarjeta>> explorarPerfiles({String busqueda = '', int limite = 24, int desde = 0}) async => [
        for (final d in await _lista('explorar_perfiles',
            {'p_busqueda': busqueda.trim(), 'p_limite': limite, 'p_desde': desde}))
          PerfilTarjeta.desde(d)
      ];

  /// `null` si no existe o hay un bloqueo de por medio.
  Future<Perfil?> verPerfil(String usuario) async =>
      Perfil.desde(await sesion.rpc('ver_perfil', {'p_usuario': usuario.trim().toLowerCase()}));

  /// Las listas que se ven en el perfil de alguien (en el mio, todas, con sus ajustes). Si la nube aun no
  /// tiene la funcion nueva devuelve vacio en vez de romper el perfil.
  Future<List<ListaPerfil>> listasDePerfil(String usuario) async {
    final u = usuario.trim().toLowerCase();
    if (u.isEmpty) return const [];
    try {
      final d = await sesion.rpc('listas_de_perfil', {'p_usuario': u});
      return [
        for (final x in d is List ? d : const [])
          if (x is Map) ListaPerfil.desde(x)
      ];
    } on ErrorNube {
      return const [];
    }
  }

  /// Una lista publica (o mia) con todas sus canciones; `null` si no se puede abrir.
  Future<Map?> verListaPublica(String id) async {
    final d = await sesion.rpc('ver_lista_publica', {'p_lista': id});
    return d is Map ? d : null;
  }

  Future<int> darLike(String otro) async => _i(await sesion.rpc('dar_like', {'p_otro': otro}));
  Future<int> quitarLike(String otro) async => _i(await sesion.rpc('quitar_like', {'p_otro': otro}));

  static const _columnasEditables =
      'nombre,bio,frase,foto_url,cancion_fav,artista_fav,generos,color_perfil,perfil_publico,mostrar_top,fecha_nacimiento,banner_url';

  Future<PerfilEditable> miPerfilEditable() async {
    final filas = await sesion.pedir('GET', 'perfiles?select=$_columnasEditables&id=eq.$yo');
    final l = _maps(filas);
    return l.isEmpty ? const PerfilEditable() : PerfilEditable.desde(l.first);
  }

  /// Guarda el perfil y devuelve cómo quedó de verdad en la base (la base
  /// puede cambiar `perfil_publico` si la persona es menor de edad).
  Future<PerfilEditable> guardarPerfil(PerfilEditable p) async {
    final r = await sesion.pedir('PATCH', 'perfiles?id=eq.$yo',
        cuerpo: p.paraGuardar(), cabeceras: {'Prefer': 'return=representation'});
    final l = _maps(r);
    return l.isEmpty ? p : PerfilEditable.desde({...l.first, 'fecha_nacimiento': p.fechaNacimiento?.toIso8601String()});
  }

  /// Sube la foto (ya recortada y comprimida) y devuelve la ruta guardada.
  Future<String> subirFoto(Uint8List jpeg) => _subirImagenPerfil(jpeg, 'avatar.jpg', 'tu foto');

  /// Sube un GIF animado como foto (solo donadores; el servidor lo impone).
  Future<String> subirFotoGif(Uint8List gif) => _subirImagenPerfil(gif, 'avatar.gif', 'tu foto', tipo: 'image/gif');

  /// Sube un GIF animado como imagen de fondo (solo donadores).
  Future<String> subirBannerGif(Uint8List gif) => _subirImagenPerfil(gif, 'banner.gif', 'tu imagen de fondo', tipo: 'image/gif');

  /// Sube la imagen de fondo y devuelve la ruta guardada.
  Future<String> subirBanner(Uint8List jpeg) => _subirImagenPerfil(jpeg, 'banner.jpg', 'tu imagen de fondo');

  Future<String> _subirImagenPerfil(Uint8List jpeg, String nombre, String que, {String tipo = 'image/jpeg'}) async {
    final ruta = '$yo/$nombre';
    try {
      await sesion.subir('avatares', ruta, jpeg, tipo, reemplazar: true);
    } on SinConexion {
      rethrow;
    } on ErrorNube catch (e) {
      throw ErrorNube('No se pudo guardar $que. ${e.mensaje} Vuelve a intentarlo; si sigue igual, '
          'cierra sesión, entra de nuevo y prueba otra vez.');
    }
    return ruta;
  }

  // ------------------------------------------------------------ revisión de música

  /// ¿Lo que subo se publica sin revisión? (si falla, se asume que no)
  Future<bool> publicaDirecto() async {
    try {
      return await sesion.rpc('publica_directo') == true;
    } catch (_) {
      return false;
    }
  }

  Future<bool> soyModerador() async {
    try {
      return await sesion.rpc('soy_moderador') == true;
    } catch (_) {
      return false;
    }
  }

  Future<int> revisionContar() async {
    try {
      return _i(await sesion.rpc('revision_contar'));
    } catch (_) {
      return 0;
    }
  }

  Future<List<SubidaRevision>> revisionPendientes({int limite = 60}) async =>
      [for (final d in await _lista('revision_pendientes', {'p_limite': limite})) SubidaRevision.desde(d)];

  Future<void> revisionResolver(String id, bool aprobar, {String nota = ''}) =>
      sesion.rpc('revision_resolver', {'p_id': id, 'p_aprobar': aprobar, 'p_nota': nota.trim()});

  /// Lo que se le dice a quien acaba de subir una canción.
  static String mensajeTrasSubir(bool publicaDirecto) => publicaDirecto
      ? 'Listo: tu canción ya está en la comunidad.'
      : 'Tu canción quedó en revisión. El equipo de Caudal la revisará y te avisaremos aquí si se aprueba.';

  // ------------------------------------------------------------ música de la gente

  Future<List<Subida>> explorarSubidas({String busqueda = '', int limite = 30, int desde = 0}) async => [
        for (final d in await _lista('explorar_subidas',
            {'p_busqueda': busqueda.trim(), 'p_limite': limite, 'p_desde': desde}))
          Subida.desde(d)
      ];

  Future<void> contarEscucha(String id) async {
    try {
      await sesion.rpc('contar_escucha_subida', {'p_id': id});
    } catch (_) {}
  }

  Future<void> borrarSubida(String id) => sesion.rpc('borrar_subida', {'p_id': id});
  Future<void> reportarSubida(String id, String motivo) =>
      sesion.rpc('reportar_subida', {'p_id': id, 'p_motivo': motivo});

  /// Sube audio y carátula, y registra la canción. Si el registro falla,
  /// borra lo que acababa de subir. [alAvanzar] recibe (0..1, qué está pasando).
  Future<String> subirCancion({
    required Uint8List audio,
    required String extension,
    required Uint8List caratula,
    required String titulo,
    String artista = '',
    String album = '',
    int duracion = 0,
    void Function(double, String)? alAvanzar,
  }) async {
    if (audio.length > maxAudioBytes) {
      throw const ErrorNube('El audio pesa más de 15 MB. Elige un archivo más liviano.');
    }
    final base = nombreSeguro(titulo, extension);
    final rutaAudio = '$yo/$base';
    final rutaPortada = '$yo/${nombreSeguro(titulo, 'jpg')}';
    final subidos = <String>[];
    try {
      // la carátula pesa poco: ocupa el primer 10 % de la barra
      alAvanzar?.call(0, 'Subiendo la carátula…');
      await sesion.subir('musica', rutaPortada, caratula, 'image/jpeg');
      subidos.add(rutaPortada);
      alAvanzar?.call(0.1, 'Subiendo el audio…');
      await sesion.subir('musica', rutaAudio, audio, tipoAudio(extension),
          alAvanzar: (f) => alAvanzar?.call(0.1 + f * 0.85, 'Subiendo el audio…'));
      subidos.add(rutaAudio);
      alAvanzar?.call(0.97, 'Guardando tu canción…');
      final id = await sesion.rpc('registrar_subida', {
        'p_titulo': titulo.trim(),
        'p_artista': artista.trim(),
        'p_album': album.trim(),
        'p_duracion': duracion,
        'p_ruta': rutaAudio,
        'p_portada': rutaPortada,
        'p_tamano': audio.length + caratula.length,
      });
      alAvanzar?.call(1, 'Listo');
      return _s(id);
    } catch (_) {
      if (subidos.isNotEmpty) await sesion.borrarArchivos('musica', subidos);
      rethrow;
    }
  }

  /// Un mensaje comprensible para cualquier error.
  static String error(Object e) =>
      e is ErrorNube ? e.mensaje : 'No se pudo conectar. Revisa tu internet y vuelve a probar.';
}
