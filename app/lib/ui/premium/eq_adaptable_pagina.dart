import 'package:flutter/material.dart';

import '../../nucleo/eq_adaptable.dart';
import '../../nucleo/mixes.dart' show artistasDe;
import '../../nucleo/premium_letras.dart';
import '../../reproduccion/eq_adaptable_control.dart';
import '../../reproduccion/reproductor.dart' show presetsEq;
import '../plataforma.dart';
import '../tema.dart';
import 'candado_donador.dart';

/// «Ecualizador adaptable» (donadores): un ajuste del ecualizador distinto según la salida
/// (audífonos, bocina o Bluetooth) y otro recordado por género o artista. Si el sistema no deja
/// saber por dónde sale el sonido, se elige el perfil activo a mano.
class EqAdaptablePagina extends StatelessWidget {
  const EqAdaptablePagina({super.key, this.control});

  /// Para pruebas: otro control en vez del de la app.
  final ControlEqAdaptable? control;

  static Future<void> abrir(BuildContext context) =>
      Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => const EqAdaptablePagina()));

  static IconData icono(SalidaAudio s) => switch (s) {
        SalidaAudio.audifonos => Icons.headphones_rounded,
        SalidaAudio.bocina => Icons.speaker_rounded,
        SalidaAudio.bluetooth => Icons.bluetooth_audio_rounded,
      };

  @override
  Widget build(BuildContext context) {
    final c = control ?? ControlEqAdaptable.i;
    return Scaffold(
      appBar: AppBar(title: const Text('Ecualizador adaptable')),
      body: !esPremiumLetras()
          ? const CandadoDonador(
              icono: Icons.equalizer_rounded,
              titulo: 'Ecualizador adaptable',
              texto:
                  'Caudal ajusta el sonido solo: uno para tus audífonos, otro para la bocina y otro para el Bluetooth, y puede recordar uno por género o por artista. Es exclusivo para donadores.')
          : ListenableBuilder(listenable: c, builder: (context, _) => _Cuerpo(c: c)),
    );
  }
}

class _Cuerpo extends StatelessWidget {
  const _Cuerpo({required this.c});
  final ControlEqAdaptable c;

  static List<DropdownMenuItem<String>> _items(String sin) => [
        DropdownMenuItem(value: '', child: Text(sin, maxLines: 1, overflow: TextOverflow.ellipsis)),
        for (final n in presetsEq.keys) DropdownMenuItem(value: n, child: Text(n, maxLines: 1, overflow: TextOverflow.ellipsis)),
      ];

  Widget _selector(String valor, String sin, ValueChanged<String> alCambiar) => DropdownButton<String>(
        isExpanded: true,
        value: presetsEq.containsKey(valor) ? valor : '',
        underline: const SizedBox.shrink(),
        items: _items(sin),
        onChanged: (v) {
          Haptico.seleccion();
          alCambiar(v ?? '');
        },
      );

  Widget _titulo(String t) => Padding(
        padding: const EdgeInsets.fromLTRB(Esp.lado, Esp.xl, Esp.lado, Esp.s),
        child: Text(t, style: estiloTituloSeccion),
      );

  @override
  Widget build(BuildContext context) {
    final p = c.perfiles;
    final pista = c.pistaActual;
    final ahora = c.perfilDeAhora;
    final motivo = c.motivoDeAhora;
    final manual = !p.detectar || !c.puedeDetectar;
    final artista = pista == null ? null : artistasDe(pista).firstOrNull;
    final genero = pista == null ? '' : GeneroEq.de(pista, contexto: c.contextoActual);

    final recordados = <Widget>[
      for (final e in p.artistas.entries)
        _Recordado(
          icono: Icons.person_rounded,
          texto: '${e.value.nombre.isEmpty ? 'Artista' : e.value.nombre}: ${e.value.perfil}',
          alQuitar: () => c.cambiar((x) => x.ponerArtista(e.key, '', null)),
        ),
      for (final e in p.generos.entries)
        _Recordado(
          icono: Icons.category_rounded,
          texto: '${GeneroEq.nombre(e.key)}: ${e.value}',
          alQuitar: () => c.cambiar((x) => x.ponerGenero(e.key, null)),
        ),
    ];

    return ListView(padding: const EdgeInsets.only(bottom: 40), children: [
      // ---- lo que suena ahora
      Padding(
        padding: const EdgeInsets.fromLTRB(Esp.lado, Esp.s, Esp.lado, 0),
        child: DecoratedBox(
          decoration: BoxDecoration(
            color: C.superficie,
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: (ahora == null ? C.borde : C.acento.withValues(alpha: 0.5))),
          ),
          child: Padding(
            padding: const EdgeInsets.all(Esp.l),
            child: Row(children: [
              Icon(ahora == null ? Icons.equalizer_rounded : Icons.auto_awesome_rounded, color: ahora == null ? C.texto3 : C.acento),
              const SizedBox(width: Esp.m),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(ahora == null ? 'Sin cambios ahora' : 'Suena con «$ahora»',
                      style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
                  const SizedBox(height: 2),
                  Text(
                      ahora == null
                          ? (pista == null
                              ? 'Se usa tu ecualizador de siempre. Cuando suene algo con una regla, se ajusta solo.'
                              : 'Ninguna regla aplica a esta canción: se usa tu ecualizador de siempre.')
                          : (motivo ?? ''),
                      style: estiloSecundario),
                ]),
              ),
            ]),
          ),
        ),
      ),

      // ---- la salida
      _titulo('Por dónde sale el sonido'),
      Padding(
        padding: const EdgeInsets.symmetric(horizontal: Esp.lado),
        child: Row(children: [
          Icon(c.detectada == null ? Icons.help_outline_rounded : EqAdaptablePagina.icono(c.detectada!), color: C.texto2),
          const SizedBox(width: Esp.m),
          Expanded(
            child: Text(
                c.puedeDetectar
                    ? 'Ahora: ${c.detectada!.nombre}'
                    : 'Este equipo no dice por dónde sale el sonido. Elige el perfil activo.',
                style: const TextStyle(fontWeight: FontWeight.w700)),
          ),
        ]),
      ),
      if (c.puedeDetectar)
        SwitchListTile(
          title: const Text('Detectar la salida solo'),
          subtitle: const Text('Cambia de perfil al conectar o quitar audífonos o Bluetooth', style: estiloSecundario),
          value: p.detectar,
          onChanged: (v) => c.cambiar((x) => x.detectar = v),
        ),
      if (manual)
        Padding(
          padding: const EdgeInsets.fromLTRB(Esp.lado, Esp.s, Esp.lado, 0),
          child: Wrap(spacing: 8, runSpacing: 8, crossAxisAlignment: WrapCrossAlignment.center, children: [
            const Text('Perfil activo:', style: estiloSecundario),
            for (final s in SalidaAudio.values)
              ChoiceChip(
                avatar: Icon(EqAdaptablePagina.icono(s), size: 18),
                label: Text(s == SalidaAudio.bocina ? 'Bocina' : s.nombre),
                selected: p.manual == s,
                onSelected: (_) {
                  Haptico.seleccion();
                  c.cambiar((x) => x.manual = x.manual == s ? null : s);
                },
              ),
          ]),
        ),

      // ---- un ajuste por salida
      _titulo('Un ajuste para cada salida'),
      for (final s in SalidaAudio.values)
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: Esp.lado, vertical: 2),
          child: Row(children: [
            Icon(EqAdaptablePagina.icono(s), color: c.salidaActual == s ? C.acento : C.texto2),
            const SizedBox(width: Esp.m),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(s.nombre, style: const TextStyle(fontWeight: FontWeight.w700), maxLines: 2, overflow: TextOverflow.ellipsis),
                Text(s.detalle, style: estiloSecundario, maxLines: 2, overflow: TextOverflow.ellipsis),
              ]),
            ),
            const SizedBox(width: Esp.s),
            SizedBox(
              width: 140,
              child: _selector(p.salidas[s.name] ?? '', 'Sin cambios', (v) => c.cambiar((x) => x.ponerSalida(s, v))),
            ),
          ]),
        ),

      // ---- por género o artista
      _titulo('Recordar por género o artista'),
      if (pista == null)
        const Padding(
          padding: EdgeInsets.symmetric(horizontal: Esp.lado),
          child: Text('Pon una canción y aquí podrás guardar un ajuste para su artista o su género.', style: estiloSecundario),
        )
      else ...[
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: Esp.lado),
          child: Text('Suena: ${pista['titulo'] ?? ''} · ${pista['artista'] ?? ''}',
              style: estiloSecundario, maxLines: 2, overflow: TextOverflow.ellipsis),
        ),
        if (artista != null)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: Esp.lado),
            child: Row(children: [
              Expanded(child: Text(artista.nombre, style: const TextStyle(fontWeight: FontWeight.w700), maxLines: 2, overflow: TextOverflow.ellipsis)),
              const SizedBox(width: Esp.s),
              SizedBox(
                width: 140,
                child: _selector(p.artistas[artista.clave]?.perfil ?? '', 'Sin recordar',
                    (v) => c.cambiar((x) => x.ponerArtista(artista.clave, artista.nombre, v))),
              ),
            ]),
          ),
        if (genero.isNotEmpty)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: Esp.lado),
            child: Row(children: [
              Expanded(child: Text(GeneroEq.nombre(genero), style: const TextStyle(fontWeight: FontWeight.w700), maxLines: 2, overflow: TextOverflow.ellipsis)),
              const SizedBox(width: Esp.s),
              SizedBox(
                width: 140,
                child: _selector(p.generos[genero] ?? '', 'Sin recordar', (v) => c.cambiar((x) => x.ponerGenero(genero, v))),
              ),
            ]),
          ),
      ],
      if (recordados.isNotEmpty) ...[
        const SizedBox(height: Esp.m),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: Esp.lado),
          child: Wrap(spacing: 8, runSpacing: 4, children: recordados),
        ),
      ],
      Padding(
        padding: const EdgeInsets.fromLTRB(Esp.lado, Esp.xl, Esp.lado, 0),
        child: Text(
            'Manda lo más específico: el artista, luego el género y luego la salida. Si mueves el ecualizador a mano mientras suena, Caudal respeta lo tuyo.',
            style: estiloSecundario.copyWith(color: C.texto3)),
      ),
    ]);
  }
}

class _Recordado extends StatelessWidget {
  const _Recordado({required this.icono, required this.texto, required this.alQuitar});
  final IconData icono;
  final String texto;
  final VoidCallback alQuitar;

  @override
  Widget build(BuildContext context) => Container(
        constraints: const BoxConstraints(maxWidth: 280),
        padding: const EdgeInsets.only(left: 10),
        decoration: BoxDecoration(
          color: C.superficie2,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: C.borde),
        ),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(icono, size: 16, color: C.texto2),
          const SizedBox(width: 6),
          Flexible(child: Text(texto, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 13.5))),
          IconButton(
            tooltip: 'Quitar',
            visualDensity: VisualDensity.compact,
            icon: const Icon(Icons.close_rounded, size: 18),
            onPressed: alQuitar,
          ),
        ]),
      );
}
