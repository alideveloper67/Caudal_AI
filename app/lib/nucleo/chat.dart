import 'dart:async';

import 'coleccion.dart';
import 'cosmeticos.dart';
import 'dedicatorias.dart';
import 'nube.dart';
import 'social.dart' show Relacion;
import 'tarjeta_lista.dart';

/// Mensajes entre dos personas (como los de Spotify): texto y canciones.
/// Todo pasa por Supabase con las reglas de supabase/esquema.sql: cada uno
/// solo ve sus conversaciones.
class ResumenChat {
  ResumenChat({required this.id, required this.otro, required this.usuario, required this.nombre,
      required this.ultimo, this.ultimoTexto = '', this.ultimaPista, this.ultimaLista, this.ultimoMio = false, this.sinLeer = 0,
      this.fotoUrl = '', this.marco = Cosmeticos.ninguno, this.efectoNombre = Cosmeticos.ninguno});

  /// Marco del avatar y efecto del nombre de un donador («ninguno» si no tiene).
  final String marco;
  final String efectoNombre;

  final String id;
  final String otro;
  final String usuario;
  final String nombre;
  final DateTime ultimo;
  final String ultimoTexto;
  final Json? ultimaPista;

  /// La última cosa que se mandó fue una lista (tarjeta).
  final TarjetaLista? ultimaLista;
  final bool ultimoMio;
  final int sinLeer;

  /// Ruta de su foto de perfil (vacía si no tiene).
  final String fotoUrl;

  String get inicial => (nombre.isNotEmpty ? nombre : usuario).substring(0, 1).toUpperCase();
  String get visible => nombre.isNotEmpty ? nombre : usuario;

  /// "Tú: hola" / "🎵 Canción — Artista".
  String get vistaPrevia {
    final quien = ultimoMio ? 'Tú: ' : '';
    if (ultimaPista != null) {
      if (Dedicatoria.esDedicatoria(ultimaPista)) return '$quien${Dedicatoria.vistaPrevia(ultimaPista!)}';
      return '$quien♪ ${ultimaPista!['titulo'] ?? 'Una canción'}';
    }
    if (ultimaLista != null) return '$quien${ultimaLista!.vistaPrevia}';
    if (ultimoTexto.isEmpty) return 'Di hola 👋';
    return '$quien$ultimoTexto';
  }

  factory ResumenChat.desde(Map d, String yo) => ResumenChat(
        id: '${d['id']}',
        otro: '${d['otro']}',
        usuario: '${d['usuario'] ?? ''}',
        nombre: '${d['nombre'] ?? ''}',
        ultimo: DateTime.tryParse('${d['ultimo']}')?.toLocal() ?? DateTime.now(),
        ultimoTexto: '${d['ultimo_texto'] ?? ''}',
        ultimaPista: d['ultimo_pista'] is Map ? Map<String, dynamic>.from(d['ultimo_pista'] as Map) : null,
        ultimaLista: TarjetaLista.desde(d['ultimo_lista']),
        ultimoMio: '${d['ultimo_autor']}' == yo,
        sinLeer: (d['sin_leer'] as num?)?.toInt() ?? 0,
        fotoUrl: '${d['foto_url'] ?? ''}',
        marco: Cosmeticos.marco(d['marco']),
        efectoNombre: Cosmeticos.efectoNombre(d['efecto_nombre']),
      );
}

class Mensaje {
  Mensaje({required this.id, required this.autor, required this.texto, this.pista, this.lista, required this.creado});
  final int id;
  final String autor;
  final String texto;
  final Json? pista;

  /// Una lista compartida que viaja en el mensaje (tarjeta con botón «Unirme»).
  final TarjetaLista? lista;
  final DateTime creado;

  factory Mensaje.desde(Map d) => Mensaje(
        id: (d['id'] as num).toInt(),
        autor: '${d['autor']}',
        texto: '${d['texto'] ?? ''}',
        pista: d['pista'] is Map ? Chat.pistaJugable(Map<String, dynamic>.from(d['pista'] as Map)) : null,
        lista: TarjetaLista.desde(d['lista']),
        creado: DateTime.tryParse('${d['creado']}')?.toLocal() ?? DateTime.now(),
      );
}

class Persona {
  Persona(this.id, this.usuario, this.nombre,
      {this.fotoUrl = '', this.relacion = 'ninguna', this.marco = Cosmeticos.ninguno, this.efectoNombre = Cosmeticos.ninguno});
  final String marco;
  final String efectoNombre;
  final String id;
  final String usuario;
  final String nombre;
  final String fotoUrl;

  /// yo, amigo, enviada, recibida, ninguna o bloqueado (ver [Relacion]).
  final String relacion;

  /// Solo a los amigos se les puede escribir.
  bool get esAmigo => relacion == 'amigo';
}

class Chat {
  Chat(this.sesion);
  final Sesion sesion;

  String get yo => sesion.userId;

  Future<List<ResumenChat>> misChats() async {
    final r = await sesion.pedir('POST', 'rpc/mis_chats', cuerpo: {});
    return [for (final d in (r as List? ?? const [])) if (d is Map) ResumenChat.desde(d, yo)];
  }

  Future<int> sinLeer() async {
    final l = await misChats();
    return l.fold<int>(0, (s, c) => s + c.sinLeer);
  }

  Future<Persona?> buscar(String usuario) async {
    final u = usuario.trim().replaceFirst('@', '').toLowerCase();
    if (u.isEmpty) return null;
    final r = await sesion.pedir('POST', 'rpc/buscar_persona', cuerpo: {'p_usuario': u});
    final l = r as List? ?? const [];
    if (l.isEmpty || l.first is! Map) return null;
    final d = l.first as Map;
    return Persona('${d['id']}', '${d['usuario']}', '${d['nombre'] ?? ''}',
        fotoUrl: '${d['foto_url'] ?? ''}', relacion: Relacion.normal(d['relacion']),
        marco: Cosmeticos.marco(d['marco']), efectoNombre: Cosmeticos.efectoNombre(d['efecto_nombre']));
  }

  /// Abre (o crea) el chat con un amigo. Con alguien que no es amigo la base
  /// responde «primero deben ser amigos» y aquí sale como un [ErrorNube] claro.
  Future<String> abrir(String otro) async {
    final r = await sesion.pedir('POST', 'rpc/abrir_chat', cuerpo: {'p_otro': otro});
    return '$r'.replaceAll('"', '');
  }

  /// Los mensajes de un chat; con [desde], solo los nuevos.
  Future<List<Mensaje>> mensajes(String chat, {int desde = 0, int limite = 200}) async {
    final filtro = desde > 0 ? '&id=gt.$desde' : '';
    final orden = desde > 0 ? 'id.asc' : 'id.desc';
    final r = await sesion.pedir('GET',
        'mensajes?chat=eq.$chat$filtro&select=id,autor,texto,pista,lista,creado&order=$orden&limit=$limite');
    final l = [for (final d in (r as List? ?? const [])) if (d is Map) Mensaje.desde(d)];
    return desde > 0 ? l : l.reversed.toList();
  }

  /// Manda texto, una canción o una lista (tarjeta).
  Future<Mensaje> enviar(String chat, {String texto = '', Json? pista, TarjetaLista? lista}) async {
    final r = await sesion.pedir('POST', 'mensajes',
        cuerpo: {
          'chat': chat,
          'texto': texto.trim(),
          if (pista != null) 'pista': Coleccion.paraNube(pista),
          if (lista != null) 'lista': lista.aJson(),
        },
        cabeceras: {'Prefer': 'return=representation'});
    return Mensaje.desde((r as List).first as Map);
  }

  Future<void> marcarLeido(String chat) async {
    try {
      await sesion.pedir('POST', 'rpc/marcar_leido', cuerpo: {'p_chat': chat});
    } catch (_) {}
  }

  /// "Mezcla con un amigo": {afinidad, comunes, mezcla, artistas_comunes}.
  Future<Json> mezcla(String chat) async {
    final r = await sesion.pedir('POST', 'rpc/mezcla', cuerpo: {'p_chat': chat});
    return r is Map ? Map<String, dynamic>.from(r) : {};
  }

  /// Arma el mix de la mezcla para abrirlo como cualquier otro.
  static Json mixDeMezcla(Json m, String nombreAmigo, String chat) {
    final pistas = <Json>[];
    final vistas = <String>{};
    final comunes = (m['comunes'] as List? ?? const []).whereType<Map>().toList();
    final resto = (m['mezcla'] as List? ?? const []).whereType<Map>().toList();
    // primero algo en común, luego alternando lo de cada uno
    var i = 0, j = 0;
    while (i < comunes.length || j < resto.length) {
      for (final p in [if (i < comunes.length) comunes[i++], if (j < resto.length) resto[j++],
        if (j < resto.length) resto[j++]]) {
        final x = pistaJugable(Map<String, dynamic>.from(p));
        if (x['video_id'] != '' && vistas.add('${x['video_id']}')) pistas.add(x);
      }
    }
    final afinidad = (m['afinidad'] as num?)?.toInt() ?? 0;
    final artistas = [for (final a in (m['artistas_comunes'] as List? ?? const [])) '$a'];
    return {
      'tipo': 'mix',
      'id': 'mezcla_$chat',
      'titulo': 'Tu mezcla con $nombreAmigo',
      'subtitulo': 'Coinciden en un $afinidad %'
          '${artistas.isEmpty ? '' : ' · Los dos escuchan a ${artistas.take(3).join(', ')}'}',
      'descripcion': 'Lo que más escuchan los dos, mezclado. Se actualiza con lo que vayan oyendo.',
      'miniatura': pistas.isEmpty ? '' : '${pistas.first['miniatura'] ?? ''}',
      'afinidad': afinidad,
      'pistas': pistas,
      'total': pistas.length,
    };
  }

  /// Una canción guardada en la nube vuelve a poder sonar (video_id y portada).
  static Json pistaJugable(Json p) {
    final clave = '${p['clave'] ?? ''}';
    var vid = '${p['video_id'] ?? ''}';
    if (vid.isEmpty && clave.startsWith('yt:')) vid = clave.substring(3);
    return {
      ...p,
      'tipo': 'pista',
      'clave': clave.isNotEmpty ? clave : 'yt:$vid',
      'video_id': vid,
      if ('${p['miniatura'] ?? ''}'.isEmpty && vid.isNotEmpty) 'miniatura': 'https://i.ytimg.com/vi/$vid/hqdefault.jpg',
    };
  }
}
