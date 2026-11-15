import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

import '../../nucleo/coleccion.dart';
import '../../nucleo/nube.dart';
import '../../nucleo/social.dart';
import '../comunes.dart';
import '../plataforma.dart';
import '../servicios.dart';
import '../tema.dart';
import 'perfil_pagina.dart';

// Piezas que comparten el perfil, el directorio, los amigos y la música de la
// comunidad: foto, insignias, botones de amistad y me gusta, y la fila de una
// canción subida.

/// La capa social de la cuenta (null sin sesión: se entró sin internet).
Social? socialDe(BuildContext context) {
  final s = Caudal.leer(context).cuenta.sesion;
  return s == null || s.acceso.isEmpty ? null : Social(s);
}

/// El color del perfil (o el de acento de la app si no eligió uno).
Color colorDelPerfil(String hex) => Social.colorDe(hex) ?? C.acento;

/// Abre el perfil de alguien por su usuario.
Future<void> abrirPerfil(BuildContext context, String usuario) =>
    Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => PerfilPagina(usuario: usuario)));

String textoSinConexion(BuildContext context) =>
    'Esta función necesita internet. Vuelve a abrir Caudal con conexión.';

// ============================================================ foto

/// Foto redonda; sin foto, un círculo con la inicial y el color del perfil.
class AvatarPerfil extends StatelessWidget {
  const AvatarPerfil({super.key, required this.nombre, this.fotoUrl = '', this.color, this.radio = 24, this.marca});

  final String nombre;
  final String fotoUrl;
  final Color? color;
  final double radio;

  /// Para saltarse la caché cuando la foto acaba de cambiar.
  final Object? marca;

  @override
  Widget build(BuildContext context) {
    final tono = color ?? C.acento;
    final inicial = nombre.trim().isEmpty ? '?' : nombre.trim().substring(0, 1).toUpperCase();
    final relleno = Container(
      width: radio * 2,
      height: radio * 2,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color.lerp(tono, Colors.white, 0.12)!, Color.lerp(tono, Colors.black, 0.35)!],
        ),
      ),
      child: Text(inicial,
          style: TextStyle(fontSize: radio * 0.95, fontWeight: FontWeight.w900, color: Colors.white.withValues(alpha: 0.95))),
    );
    final url = Social.urlFoto(fotoUrl, marca: marca);
    if (url.isEmpty) return Semantics(label: 'Foto de $nombre', child: relleno);
    final dpr = MediaQuery.devicePixelRatioOf(context);
    return Semantics(
      label: 'Foto de $nombre',
      child: ClipOval(
        child: SizedBox(
          width: radio * 2,
          height: radio * 2,
          child: CachedNetworkImage(
            imageUrl: url,
            fit: BoxFit.cover,
            memCacheWidth: (radio * 2 * dpr).round(),
            fadeInDuration: const Duration(milliseconds: 160),
            placeholder: (_, _) => relleno,
            errorWidget: (_, _, _) => relleno,
          ),
        ),
      ),
    );
  }
}

// ============================================================ insignias

/// La nota «ARTISTA»: dorada, con estrella.
class InsigniaArtista extends StatelessWidget {
  const InsigniaArtista({super.key, this.compacta = false});
  final bool compacta;

  static const dorado = Color(0xFFF5C451);

  @override
  Widget build(BuildContext context) => Semantics(
        label: 'Artista de Caudal',
        child: Container(
          padding: EdgeInsets.symmetric(horizontal: compacta ? 7 : 10, vertical: compacta ? 2 : 4),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(999),
            gradient: const LinearGradient(colors: [Color(0xFFFFE08A), Color(0xFFE8A93B)]),
            boxShadow: [BoxShadow(color: dorado.withValues(alpha: 0.35), blurRadius: 10)],
          ),
          child: Row(mainAxisSize: MainAxisSize.min, children: [
            Icon(Icons.star_rounded, size: compacta ? 11 : 14, color: const Color(0xFF3B2A00)),
            SizedBox(width: compacta ? 2 : 4),
            Text('ARTISTA',
                style: TextStyle(
                    fontSize: compacta ? 9.5 : 11.5,
                    fontWeight: FontWeight.w900,
                    letterSpacing: 0.8,
                    color: const Color(0xFF3B2A00))),
          ]),
        ),
      );
}

/// «Usuario fundador ★» (o «Fundador n.º 17» si se conoce el número).
class NotaFundador extends StatelessWidget {
  const NotaFundador({super.key, this.numero, this.compacta = false});
  final int? numero;
  final bool compacta;

  @override
  Widget build(BuildContext context) {
    final texto = numero != null && !compacta ? 'Fundador n.º $numero' : 'Usuario fundador';
    return Semantics(
      label: texto,
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Text(texto,
            style: TextStyle(fontSize: compacta ? 10.5 : 12.5, fontWeight: FontWeight.w700, color: InsigniaArtista.dorado)),
        const SizedBox(width: 3),
        Icon(Icons.star_rounded, size: compacta ? 12 : 15, color: InsigniaArtista.dorado),
      ]),
    );
  }
}

/// Un título especial: chip destacado. «Fundador de Caudal» lleva degradado
/// cian a dorado; «Rey de la música» corona dorada; una clave desconocida, estrella dorada.
class ChipTitulo extends StatelessWidget {
  const ChipTitulo({super.key, required this.titulo, this.compacto = false});
  final TituloEspecial titulo;
  final bool compacto;

  @override
  Widget build(BuildContext context) {
    final fundador = titulo.clave == 'fundador_caudal';
    final icono = fundador
        ? Icons.water_drop_rounded
        : titulo.clave == 'rey_de_la_musica'
            ? Icons.workspace_premium_rounded
            : Icons.star_rounded;
    return Semantics(
      label: titulo.nombre,
      child: Container(
        padding: EdgeInsets.symmetric(horizontal: compacto ? 8 : 12, vertical: compacto ? 3 : 6),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(999),
          gradient: fundador
              ? const LinearGradient(colors: [Color(0xFF22D3EE), Color(0xFFF5C451)])
              : const LinearGradient(colors: [Color(0xFFFFE08A), Color(0xFFE8A93B)]),
          boxShadow: [BoxShadow(color: InsigniaArtista.dorado.withValues(alpha: 0.35), blurRadius: 12)],
        ),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(icono, size: compacto ? 12 : 16, color: const Color(0xFF2B1F00)),
          const SizedBox(width: 4),
          Flexible(
            child: Text(titulo.nombre,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(fontSize: compacto ? 10.5 : 12.5, fontWeight: FontWeight.w900, color: const Color(0xFF2B1F00))),
          ),
        ]),
      ),
    );
  }
}

/// Títulos, nota de fundador y ARTISTA, en ese orden, para el perfil y las tarjetas.
class DistincionesPerfil extends StatelessWidget {
  const DistincionesPerfil({super.key, required this.titulos, this.fundador = false, this.numero,
      this.artista = false, this.compacto = false, this.alineacion = WrapAlignment.center});
  final List<TituloEspecial> titulos;
  final bool fundador;
  final int? numero;
  final bool artista;
  final bool compacto;
  final WrapAlignment alineacion;

  @override
  Widget build(BuildContext context) {
    if (titulos.isEmpty && !fundador && !artista) return const SizedBox.shrink();
    return Wrap(alignment: alineacion, crossAxisAlignment: WrapCrossAlignment.center, spacing: 6, runSpacing: 4, children: [
      for (final t in titulos) ChipTitulo(titulo: t, compacto: compacto),
      if (fundador) NotaFundador(numero: numero, compacta: compacto),
      if (artista) InsigniaArtista(compacta: compacto),
    ]);
  }
}

/// Icono y color de cada insignia automática.
(IconData, Color) visualInsignia(String clave) => switch (clave) {
      'veterano' => (Icons.military_tech_rounded, const Color(0xFFE0A458)),
      'fiel' => (Icons.local_fire_department_rounded, const Color(0xFFFF7A4D)),
      'explorador' => (Icons.explore_rounded, const Color(0xFF4DD6B0)),
      'coleccionista' => (Icons.library_music_rounded, const Color(0xFFB08CFF)),
      'maratonista' => (Icons.headphones_rounded, const Color(0xFF5CB8FF)),
      'creador' => (Icons.auto_awesome_rounded, const Color(0xFFFF6FB1)),
      _ => (Icons.emoji_events_rounded, const Color(0xFFA9B1C0)),
    };

class ChipInsignia extends StatelessWidget {
  const ChipInsignia({super.key, required this.insignia});
  final Insignia insignia;

  @override
  Widget build(BuildContext context) {
    final (icono, color) = visualInsignia(insignia.clave);
    return Tooltip(
      message: insignia.detalle.isEmpty ? insignia.titulo : insignia.detalle,
      triggerMode: TooltipTriggerMode.tap,
      child: Semantics(
        label: '${insignia.titulo}. ${insignia.detalle}',
        child: Container(
          padding: const EdgeInsets.fromLTRB(8, 5, 12, 5),
          decoration: BoxDecoration(
            color: color.withValues(alpha: 0.14),
            borderRadius: BorderRadius.circular(999),
            border: Border.all(color: color.withValues(alpha: 0.35)),
          ),
          child: Row(mainAxisSize: MainAxisSize.min, children: [
            Icon(icono, size: 17, color: color),
            const SizedBox(width: 5),
            Text(insignia.titulo, style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700)),
          ]),
        ),
      ),
    );
  }
}

// ============================================================ botones

/// Me gusta: el corazón rebota al marcarse y el número cambia con suavidad.
class BotonLike extends StatelessWidget {
  const BotonLike({super.key, required this.di, required this.total, required this.alPulsar, this.compacto = false});
  final bool di;
  final int total;
  final VoidCallback? alPulsar;
  final bool compacto;

  @override
  Widget build(BuildContext context) {
    final color = di ? const Color(0xFFFF5C8A) : C.texto2;
    return Semantics(
      button: true,
      toggled: di,
      label: di ? 'Quitar me gusta. Tiene $total' : 'Dar me gusta. Tiene $total',
      child: InkWell(
        borderRadius: BorderRadius.circular(999),
        onTap: alPulsar == null
            ? null
            : () {
                Haptico.seleccion();
                alPulsar!();
              },
        child: Padding(
          padding: EdgeInsets.symmetric(horizontal: compacto ? 8 : 12, vertical: compacto ? 6 : 8),
          child: Row(mainAxisSize: MainAxisSize.min, children: [
            TweenAnimationBuilder<double>(
              key: ValueKey(di),
              tween: Tween(begin: di ? 0.6 : 1.0, end: 1.0),
              duration: const Duration(milliseconds: 380),
              curve: Curves.elasticOut,
              builder: (_, v, hijo) => Transform.scale(scale: v, child: hijo),
              child: Icon(di ? Icons.favorite_rounded : Icons.favorite_border_rounded,
                  size: compacto ? 19 : 22, color: color),
            ),
            const SizedBox(width: 5),
            AnimatedSwitcher(
              duration: Mov.normal,
              child: Text('$total',
                  key: ValueKey(total),
                  style: TextStyle(fontSize: compacto ? 13 : 14.5, fontWeight: FontWeight.w800, color: color)),
            ),
          ]),
        ),
      ),
    );
  }
}

/// Lo que dice y hace el botón de amistad según la relación.
({String texto, IconData icono, bool principal, bool activo}) estiloAmistad(String relacion) => switch (relacion) {
      Relacion.amigo => (texto: 'Escribir', icono: Icons.chat_bubble_rounded, principal: true, activo: true),
      Relacion.enviada => (texto: 'Solicitud enviada', icono: Icons.schedule_send_rounded, principal: false, activo: true),
      Relacion.recibida => (texto: 'Aceptar solicitud', icono: Icons.check_rounded, principal: true, activo: true),
      Relacion.bloqueado => (texto: 'Bloqueado', icono: Icons.block_rounded, principal: false, activo: false),
      Relacion.yo => (texto: 'Tu perfil', icono: Icons.person_rounded, principal: false, activo: false),
      _ => (texto: 'Agregar', icono: Icons.person_add_alt_1_rounded, principal: true, activo: true),
    };

/// El botón de amistad: «Agregar» / «Solicitud enviada» / «Aceptar solicitud»
/// / «Escribir». Mientras trabaja muestra una ruedita.
class BotonAmistad extends StatelessWidget {
  const BotonAmistad({super.key, required this.relacion, required this.alPulsar, this.ocupado = false, this.compacto = false});
  final String relacion;
  final VoidCallback? alPulsar;
  final bool ocupado;
  final bool compacto;

  @override
  Widget build(BuildContext context) {
    final e = estiloAmistad(relacion);
    if (relacion == Relacion.yo) return const SizedBox.shrink();
    final habilitado = e.activo && !ocupado && alPulsar != null;
    final contenido = AnimatedSwitcher(
      duration: Mov.rapido,
      child: ocupado
          ? SizedBox(key: const ValueKey('o'), width: 18, height: 18,
              child: CircularProgressIndicator(strokeWidth: 2, color: e.principal ? C.acentoTexto : C.texto))
          : Row(key: ValueKey(e.texto), mainAxisSize: MainAxisSize.min, children: [
              Icon(e.icono, size: compacto ? 16 : 18),
              const SizedBox(width: 6),
              Text(e.texto),
            ]),
    );
    final forma = const StadiumBorder();
    final relleno = EdgeInsets.symmetric(horizontal: compacto ? 12 : 18, vertical: compacto ? 8 : 12);
    final texto = TextStyle(fontSize: compacto ? 13 : 14.5, fontWeight: FontWeight.w800);
    return e.principal
        ? FilledButton(
            onPressed: habilitado ? alPulsar : null,
            style: FilledButton.styleFrom(
                backgroundColor: C.acento, foregroundColor: C.acentoTexto, shape: forma, padding: relleno, textStyle: texto,
                minimumSize: Size(0, compacto ? 36 : 44)),
            child: contenido)
        : OutlinedButton(
            onPressed: habilitado ? alPulsar : null,
            style: OutlinedButton.styleFrom(
                foregroundColor: C.texto, shape: forma, padding: relleno, textStyle: texto,
                side: BorderSide(color: C.texto3.withValues(alpha: 0.5)), minimumSize: Size(0, compacto ? 36 : 44)),
            child: contenido);
  }
}

// ============================================================ canciones de la comunidad

/// Fila de una canción subida: carátula, título, artista, quién la subió,
/// la nota ARTISTA y el menú (reportar o borrar).
class FilaSubida extends StatelessWidget {
  const FilaSubida({
    super.key,
    required this.subida,
    required this.alReproducir,
    this.sonando = false,
    this.alReportar,
    this.alBorrar,
    this.alAbrirPerfil,
    this.mostrarAutor = true,
  });

  final Subida subida;
  final VoidCallback alReproducir;
  final bool sonando;
  final VoidCallback? alReportar;
  final VoidCallback? alBorrar;
  final VoidCallback? alAbrirPerfil;
  final bool mostrarAutor;

  static String _estado(String e) => switch (e) {
        'revision' => 'En revisión',
        'retirada' => 'Retirada',
        _ => '',
      };

  @override
  Widget build(BuildContext context) {
    final estado = _estado(subida.estado);
    final detalle = [
      if (subida.linea.isNotEmpty) subida.linea,
      if (subida.escuchas > 0) '${subida.escuchas} ${subida.escuchas == 1 ? 'escucha' : 'escuchas'}',
    ].join(' · ');
    return Pulsable(
      escala: 0.985,
      child: InkWell(
        onTap: alReproducir,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: Esp.lado, vertical: 7),
          child: Row(children: [
            Stack(alignment: Alignment.center, children: [
              Portada(url: subida.urlPortada, lado: 56, radio: 8),
              if (sonando)
                Container(
                  width: 56,
                  height: 56,
                  decoration: BoxDecoration(color: Colors.black54, borderRadius: BorderRadius.circular(8)),
                  child: Icon(Icons.graphic_eq_rounded, color: C.acento),
                ),
            ]),
            const SizedBox(width: 12),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(subida.tituloVisible,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: estiloTituloFila.copyWith(color: sonando ? C.acento : C.texto)),
                if (detalle.isNotEmpty)
                  Text(detalle, maxLines: 1, overflow: TextOverflow.ellipsis, style: estiloSubTarjeta),
                const SizedBox(height: 2),
                Row(children: [
                  if (mostrarAutor && subida.usuario.isNotEmpty)
                    Flexible(
                      child: InkWell(
                        onTap: alAbrirPerfil,
                        child: Text('Subida por @${subida.usuario}',
                            maxLines: 1, overflow: TextOverflow.ellipsis, style: estiloDetalle),
                      ),
                    ),
                  if (subida.esArtista) ...[const SizedBox(width: 6), const InsigniaArtista(compacta: true)],
                  if (estado.isNotEmpty) ...[
                    const SizedBox(width: 6),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                      decoration: BoxDecoration(color: C.superficie3, borderRadius: BorderRadius.circular(999)),
                      child: Text(estado, style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w700, color: C.texto2)),
                    ),
                  ],
                ]),
              ]),
            ),
            IconButton(
              tooltip: 'Escuchar ${subida.tituloVisible}',
              icon: Icon(sonando ? Icons.pause_circle_filled_rounded : Icons.play_circle_fill_rounded, size: 34, color: C.acento),
              onPressed: alReproducir,
            ),
            if (alReportar != null || alBorrar != null)
              PopupMenuButton<String>(
                tooltip: 'Más opciones',
                color: C.superficie2,
                icon: const Icon(Icons.more_vert_rounded, color: C.texto2),
                onSelected: (v) => v == 'reportar' ? alReportar?.call() : alBorrar?.call(),
                itemBuilder: (_) => [
                  if (alReportar != null)
                    const PopupMenuItem(value: 'reportar', child: ListTile(
                        dense: true, leading: Icon(Icons.flag_outlined), title: Text('Reportar'))),
                  if (alBorrar != null)
                    const PopupMenuItem(value: 'borrar', child: ListTile(
                        dense: true, leading: Icon(Icons.delete_outline_rounded), title: Text('Borrar mi canción'))),
                ],
              ),
          ]),
        ),
      ),
    );
  }
}

/// Reproduce una canción de la comunidad (con la lista que se está viendo
/// como cola) y cuenta la escucha.
Future<void> reproducirSubida(BuildContext context, Social? social, List<Subida> lista, int indice) async {
  if (indice < 0 || indice >= lista.length) return;
  final s = Caudal.leer(context);
  final elegida = lista[indice];
  // el reproductor solo lee canciones publicadas y que tengan audio
  final pistas = [for (final x in lista) if (x.ruta.isNotEmpty) x.comoPista()];
  final posicion = pistas.indexWhere((p) => p['subida_id'] == elegida.id);
  if (posicion < 0) {
    s.avisar('Esta canción no tiene audio disponible.');
    return;
  }
  try {
    await s.reproducirLista(context, pistas, inicio: posicion,
        contexto: {'tipo': 'comunidad', 'id': 'comunidad', 'titulo': 'Música de la comunidad'});
    social?.contarEscucha(elegida.id);
  } catch (e) {
    s.avisar('No se pudo reproducir. Revisa tu internet y vuelve a probar.');
  }
}

/// ¿Es la canción que suena ahora?
bool suenaSubida(Servicios s, Subida x) => '${s.reproductor.actual?['subida_id'] ?? ''}' == x.id;

/// Pregunta el motivo y manda el reporte. Devuelve true si se envió.
Future<bool> reportarSubidaDialogo(BuildContext context, Social? social, Subida x) async {
  final s = Caudal.leer(context);
  if (social == null) {
    s.avisar('Reportar necesita internet.');
    return false;
  }
  final motivo = await showDialog<String>(
    context: context,
    useRootNavigator: true,
    builder: (ctx) => SimpleDialog(
      backgroundColor: C.superficie2,
      title: const Text('¿Qué pasa con esta canción?'),
      children: [
        for (final m in const [
          'No es de quien la subió (derechos de autor)',
          'Contenido ofensivo o inapropiado',
          'Spam o publicidad',
          'Otro motivo',
        ])
          SimpleDialogOption(onPressed: () => Navigator.pop(ctx, m), child: Text(m)),
        SimpleDialogOption(
          onPressed: () => Navigator.pop(ctx),
          child: const Text('Cancelar', style: TextStyle(color: C.texto3)),
        ),
      ],
    ),
  );
  if (motivo == null) return false;
  try {
    await social.reportarSubida(x.id, motivo);
    s.avisar('Gracias por avisar. Revisaremos esta canción.');
    return true;
  } catch (e) {
    s.avisar(Social.error(e));
    return false;
  }
}

/// Confirma y borra una canción propia. Devuelve true si se borró.
Future<bool> borrarSubidaDialogo(BuildContext context, Social? social, Subida x) async {
  final s = Caudal.leer(context);
  if (social == null) {
    s.avisar('Borrar necesita internet.');
    return false;
  }
  final si = await confirmar(context, '¿Borrar «${x.tituloVisible}»?',
      'Se quitará de la comunidad y se borrarán su audio y su carátula. No se puede deshacer.');
  if (!si) return false;
  try {
    await social.borrarSubida(x.id);
    if (s.reproductor.actual?['subida_id'] == x.id) await s.reproductor.detener();
    s.avisar('Canción borrada.');
    return true;
  } catch (e) {
    s.avisar(Social.error(e));
    return false;
  }
}

/// Aviso de error con botón para reintentar, en lenguaje normal.
Widget errorAmable(Object e, VoidCallback reintentar) => Vacio(
      icono: e is SinConexion ? Icons.wifi_off_rounded : Icons.error_outline_rounded,
      titulo: e is SinConexion ? 'Sin conexión' : 'Algo no salió bien',
      texto: Social.error(e),
      error: true,
      alAccion: reintentar,
    );

/// Atajo para listas de pistas ya convertidas (sin usar en pruebas).
List<Json> pistasDe(List<Subida> l) => [for (final x in l) x.comoPista()];
