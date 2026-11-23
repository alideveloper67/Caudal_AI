import 'dart:async';

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';

import '../../nucleo/coleccion.dart' show Json;
import '../../nucleo/despertador.dart';
import '../../nucleo/despertador_control.dart';
import '../../nucleo/despertador_nativo.dart';
import '../../nucleo/mixes.dart';
import '../../nucleo/plataforma.dart';
import '../premium/elegir_cancion.dart';
import '../servicios.dart';
import '../tema.dart';

/// «Despertador»: tus alarmas con música. Cada una con su hora, sus días, lo que suena, hasta qué
/// volumen sube y en cuánto tiempo. En Android suenan con la app cerrada y el teléfono bloqueado.
class DespertadorPagina extends StatefulWidget {
  const DespertadorPagina({super.key, this.control});

  /// Para las pruebas; por defecto, el de la app.
  final ControlDespertador? control;

  @override
  State<DespertadorPagina> createState() => _DespertadorPaginaState();
}

class _DespertadorPaginaState extends State<DespertadorPagina> with WidgetsBindingObserver {
  ControlDespertador get _c => widget.control ?? ControlDespertador.i;
  PermisosDespertador _permisos = const PermisosDespertador();
  Timer? _reloj;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _c.addListener(_repintar);
    if (!_c.cargadas) unawaited(_c.cargar());
    unawaited(_leerPermisos());
    // «Suena en 7 h 20 min» se mantiene al día
    _reloj = Timer.periodic(const Duration(seconds: 30), (_) => _repintar());
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _c.removeListener(_repintar);
    _reloj?.cancel();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState estado) {
    if (estado == AppLifecycleState.resumed) unawaited(_leerPermisos()); // al volver del ajuste del sistema
  }

  void _repintar() {
    if (mounted) setState(() {});
  }

  Future<void> _leerPermisos() async {
    final p = await _c.permisos();
    if (mounted) setState(() => _permisos = p);
    // con el permiso nuevo, las alarmas pasan a ser exactas
    if (p.exactas) unawaited(_c.sincronizar());
  }

  Future<void> _editar(Alarma? a) async {
    final nueva = a == null;
    final r = await Navigator.of(context).push<_ResultadoEditor>(MaterialPageRoute(
      builder: (_) => EditorAlarmaPagina(alarma: a ?? Alarma.nueva(), nueva: nueva, control: _c),
    ));
    if (r == null || !mounted) return;
    if (r.borrar) {
      await _c.quitar(r.alarma.id);
      _aviso('Alarma borrada');
      return;
    }
    await _c.poner(r.alarma);
    final p = proximaVez(r.alarma, DateTime.now());
    if (p != null) _aviso(textoFalta(p.difference(DateTime.now())));
  }

  void _aviso(String t) {
    final m = ScaffoldMessenger.maybeOf(context);
    m?.hideCurrentSnackBar();
    m?.showSnackBar(SnackBar(content: Text(t), duration: const Duration(milliseconds: 2400)));
  }

  @override
  Widget build(BuildContext context) {
    final alarmas = [..._c.alarmas]..sort((a, b) => (a.hora * 60 + a.minuto).compareTo(b.hora * 60 + b.minuto));
    final proxima = _c.proxima();
    return Scaffold(
      appBar: AppBar(title: const Text('Despertador')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _editar(null),
        icon: const Icon(Icons.add_alarm_rounded),
        label: const Text('Nueva alarma'),
      ),
      body: ListView(padding: const EdgeInsets.only(bottom: 100), children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(Esp.lado, 8, Esp.lado, 4),
          child: Text(
            proxima == null ? 'Ninguna alarma activa' : textoFalta(proxima.$2.difference(DateTime.now())),
            style: estiloSecundario,
          ),
        ),
        ValueListenableBuilder<bool>(
          valueListenable: _c.preparando,
          builder: (_, si, __) => si
              ? const Padding(
                  padding: EdgeInsets.fromLTRB(Esp.lado, 0, Esp.lado, 4),
                  child: Text('Dejando lista tu música en el teléfono, por si no hay internet al sonar…',
                      style: estiloDetalle),
                )
              : const SizedBox.shrink(),
        ),
        if (Plataforma.esAndroid) _AvisoPermisos(permisos: _permisos, abrir: (c) => _c.abrirAjuste(c)),
        if (!Plataforma.esAndroid)
          const Padding(
            padding: EdgeInsets.fromLTRB(Esp.lado, 4, Esp.lado, 8),
            child: Text(kIsWeb
                ? 'En el navegador suena con esta página abierta y el equipo encendido. Con el teléfono bloqueado '
                    'puede no sonar: para despertarte, mejor la app de Android.'
                : 'En este aparato la alarma suena con Caudal abierto.', style: estiloDetalle),
          ),
        if (alarmas.isEmpty)
          const Padding(
            padding: EdgeInsets.fromLTRB(Esp.lado, 40, Esp.lado, 0),
            child: Column(children: [
              Icon(Icons.alarm_rounded, size: 56, color: C.texto3),
              SizedBox(height: 12),
              Text('Despierta con tu música', style: estiloTituloSeccion, textAlign: TextAlign.center),
              SizedBox(height: 6),
              Text('Una canción, una lista, un mix o tus «me gusta» al azar, empezando bajito.',
                  style: estiloSecundario, textAlign: TextAlign.center),
            ]),
          ),
        for (final a in alarmas) _FilaAlarma(alarma: a, alTocar: () => _editar(a), alCambiar: (v) => _c.activar(a.id, v)),
      ]),
    );
  }
}

class _FilaAlarma extends StatelessWidget {
  const _FilaAlarma({required this.alarma, required this.alTocar, required this.alCambiar});
  final Alarma alarma;
  final VoidCallback alTocar;
  final ValueChanged<bool> alCambiar;

  @override
  Widget build(BuildContext context) {
    final a = alarma;
    final pospuesta = a.pospuestaHasta > DateTime.now().millisecondsSinceEpoch;
    final detalle = [
      if (a.etiqueta.isNotEmpty) a.etiqueta,
      textoDias(a.dias),
      a.fuente.titulo.isEmpty ? a.fuente.tipo.nombre : a.fuente.titulo,
      if (pospuesta) 'pospuesta',
    ].join(' · ');
    return Padding(
      padding: const EdgeInsets.fromLTRB(Esp.lado, 6, Esp.lado, 6),
      child: Material(
        color: C.superficie2,
        borderRadius: BorderRadius.circular(16),
        child: InkWell(
          borderRadius: BorderRadius.circular(16),
          onTap: alTocar,
          child: Padding(
            padding: const EdgeInsets.fromLTRB(18, 12, 10, 12),
            child: Row(children: [
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(a.textoHora,
                      style: TextStyle(fontSize: 38, fontWeight: FontWeight.w900, letterSpacing: -1,
                          color: a.activa ? C.texto : C.texto3)),
                  Text(detalle, style: estiloSecundario, maxLines: 2, overflow: TextOverflow.ellipsis),
                ]),
              ),
              Semantics(
                label: 'Alarma de las ${a.textoHora}',
                child: Switch.adaptive(value: a.activa, onChanged: alCambiar),
              ),
            ]),
          ),
        ),
      ),
    );
  }
}

class _AvisoPermisos extends StatelessWidget {
  const _AvisoPermisos({required this.permisos, required this.abrir});
  final PermisosDespertador permisos;
  final void Function(String) abrir;

  @override
  Widget build(BuildContext context) {
    final faltan = <(String, String, String)>[
      if (!permisos.notificaciones)
        ('notificaciones', 'Permite las notificaciones', 'Sin ellas la alarma no se ve en la pantalla bloqueada.'),
      if (!permisos.exactas)
        ('exactas', 'Permite «Alarmas y recordatorios»', 'Para que suene en el minuto exacto y no unos minutos tarde.'),
      if (!permisos.pantallaCompleta)
        ('pantallaCompleta', 'Permite la pantalla completa', 'Para que la alarma se encienda sobre el bloqueo.'),
      if (!permisos.bateria)
        ('bateria', 'Quita el ahorro de batería a Caudal', 'Algunos teléfonos duermen a las apps y la alarma se retrasa.'),
    ];
    if (faltan.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.fromLTRB(Esp.lado, 8, Esp.lado, 8),
      child: Material(
        color: C.superficie2,
        borderRadius: BorderRadius.circular(14),
        clipBehavior: Clip.antiAlias,
        child: Column(children: [
          for (final (clave, titulo, ayuda) in faltan)
            ListTile(
              leading: Icon(Icons.warning_amber_rounded, color: C.acento),
              title: Text(titulo),
              subtitle: Text(ayuda, style: estiloSecundario),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => abrir(clave),
            ),
        ]),
      ),
    );
  }
}

// ============================================================ editor

class _ResultadoEditor {
  const _ResultadoEditor(this.alarma, {this.borrar = false});
  final Alarma alarma;
  final bool borrar;
}

class EditorAlarmaPagina extends StatefulWidget {
  const EditorAlarmaPagina({super.key, required this.alarma, required this.nueva, required this.control});
  final Alarma alarma;
  final bool nueva;
  final ControlDespertador control;

  @override
  State<EditorAlarmaPagina> createState() => _EditorAlarmaPaginaState();
}

class _EditorAlarmaPaginaState extends State<EditorAlarmaPagina> {
  late Alarma _a = widget.alarma;
  late final _etiqueta = TextEditingController(text: widget.alarma.etiqueta);

  @override
  void dispose() {
    _etiqueta.dispose();
    super.dispose();
  }

  Alarma get _resultado => _a.copia(etiqueta: _etiqueta.text.trim(), activa: true, pospuestaHasta: 0);

  Future<void> _elegirHora() async {
    final t = await showTimePicker(
      context: context,
      initialTime: TimeOfDay(hour: _a.hora, minute: _a.minuto),
      helpText: 'Hora de la alarma',
    );
    if (t != null) setState(() => _a = _a.copia(hora: t.hour, minuto: t.minute));
  }

  void _alternarDia(int d) {
    final dias = {..._a.dias};
    if (!dias.remove(d)) dias.add(d);
    setState(() => _a = _a.copia(dias: dias));
  }

  Future<void> _elegirFuente() async {
    final tipo = await showModalBottomSheet<TipoFuente>(
      context: context,
      useRootNavigator: true,
      builder: (ctx) => SafeArea(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          const Padding(padding: EdgeInsets.fromLTRB(20, 4, 20, 6), child: Text('Qué suena', style: estiloTituloSeccion)),
          for (final t in TipoFuente.values)
            ListTile(
              leading: Icon(_icono(t), color: C.texto2),
              title: Text(t.nombre),
              subtitle: t == TipoFuente.tono
                  ? const Text('Suena siempre, con o sin internet', style: estiloSecundario)
                  : null,
              trailing: t == _a.fuente.tipo ? Icon(Icons.check_rounded, color: C.acento) : null,
              onTap: () => Navigator.pop(ctx, t),
            ),
          const SizedBox(height: 8),
        ]),
      ),
    );
    if (tipo == null || !mounted) return;
    final s = Caudal.leer(context);
    FuenteAlarma? f;
    switch (tipo) {
      case TipoFuente.cancion:
        final p = await elegirCancion(context, titulo: 'Canción para despertar');
        if (p != null) {
          final titulo = ['${p['titulo'] ?? ''}', '${p['artista'] ?? ''}'].where((x) => x.isNotEmpty).join(' · ');
          f = FuenteAlarma(tipo: tipo, id: '${p['clave'] ?? p['video_id'] ?? ''}', titulo: titulo, pista: pistaMinima(p));
        }
      case TipoFuente.lista:
        final listas = await s.coleccion.listas();
        if (!mounted) return;
        final l = await _elegirDe(listas, (x) => '${x['nombre'] ?? ''}', 'Tus listas',
            vacio: 'Aún no tienes listas.');
        if (l != null) f = FuenteAlarma(tipo: tipo, id: '${l['id']}', titulo: '${l['nombre'] ?? ''}');
      case TipoFuente.mix:
        final mixes = await Mixes.delDia(s.coleccion).catchError((_) => <Json>[]);
        if (!mounted) return;
        final m = await _elegirDe(mixes, (x) => '${x['titulo'] ?? ''}', 'Mixes de hoy',
            vacio: 'Escucha un poco más y aquí aparecerán tus mixes.');
        if (m != null) f = FuenteAlarma(tipo: tipo, id: '${m['id']}', titulo: '${m['titulo'] ?? ''}');
      case TipoFuente.meGusta:
        f = FuenteAlarma.meGusta;
      case TipoFuente.tono:
        f = FuenteAlarma.tono;
    }
    if (f != null && mounted) setState(() => _a = _a.copia(fuente: f));
  }

  Future<Json?> _elegirDe(List<Json> opciones, String Function(Json) texto, String titulo, {required String vacio}) =>
      showModalBottomSheet<Json>(
        context: context,
        useRootNavigator: true,
        isScrollControlled: true,
        builder: (ctx) => SafeArea(
          child: ConstrainedBox(
            constraints: BoxConstraints(maxHeight: MediaQuery.of(ctx).size.height * 0.7),
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              Padding(padding: const EdgeInsets.fromLTRB(20, 4, 20, 6), child: Text(titulo, style: estiloTituloSeccion)),
              if (opciones.isEmpty) Padding(padding: const EdgeInsets.all(20), child: Text(vacio, style: estiloSecundario)),
              Flexible(
                child: ListView(shrinkWrap: true, children: [
                  for (final o in opciones) ListTile(title: Text(texto(o)), onTap: () => Navigator.pop(ctx, o)),
                ]),
              ),
            ]),
          ),
        ),
      );

  static IconData _icono(TipoFuente t) => switch (t) {
        TipoFuente.cancion => Icons.music_note_rounded,
        TipoFuente.lista => Icons.queue_music_rounded,
        TipoFuente.mix => Icons.auto_awesome_rounded,
        TipoFuente.meGusta => Icons.favorite_rounded,
        TipoFuente.tono => Icons.notifications_active_rounded,
      };

  String _textoSubida(int s) => s == 0 ? 'De golpe' : (s < 60 ? 'En $s s' : 'En ${s ~/ 60} min${s % 60 == 0 ? '' : ' ${s % 60} s'}');

  @override
  Widget build(BuildContext context) {
    final a = _a;
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.nueva ? 'Nueva alarma' : 'Editar alarma'),
        actions: [
          if (!widget.nueva)
            IconButton(
              tooltip: 'Borrar',
              icon: const Icon(Icons.delete_outline_rounded),
              onPressed: () => Navigator.pop(context, _ResultadoEditor(a, borrar: true)),
            ),
        ],
      ),
      body: ListView(padding: const EdgeInsets.fromLTRB(0, 8, 0, 40), children: [
        Center(
          child: InkWell(
            borderRadius: BorderRadius.circular(16),
            onTap: _elegirHora,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 4),
              child: Semantics(
                button: true,
                label: 'Cambiar la hora, ahora ${a.textoHora}',
                child: Text(a.textoHora, style: const TextStyle(fontSize: 72, fontWeight: FontWeight.w900, letterSpacing: -2)),
              ),
            ),
          ),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: Esp.lado),
          child: Wrap(alignment: WrapAlignment.center, spacing: 6, runSpacing: 6, children: [
            for (final d in const [1, 2, 3, 4, 5, 6, 7])
              Tooltip(
                message: nombresDia[d]!,
                child: FilterChip(
                  label: Text(inicialesDia[d]!),
                  selected: a.dias.contains(d),
                  showCheckmark: false,
                  onSelected: (_) => _alternarDia(d),
                ),
              ),
          ]),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(Esp.lado, 6, Esp.lado, 0),
          child: Text(a.dias.isEmpty ? 'Sin días marcados suena una sola vez.' : textoDias(a.dias),
              textAlign: TextAlign.center, style: estiloDetalle),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(Esp.lado, 14, Esp.lado, 4),
          child: TextField(
            controller: _etiqueta,
            maxLength: 40,
            decoration: const InputDecoration(labelText: 'Nombre (opcional)', hintText: '«Trabajo», «Gimnasio»…'),
          ),
        ),
        ListTile(
          leading: Icon(_icono(a.fuente.tipo), color: C.acento),
          title: const Text('Qué suena'),
          subtitle: Text(a.fuente.titulo.isEmpty ? a.fuente.tipo.nombre : a.fuente.titulo, style: estiloSecundario),
          trailing: const Icon(Icons.chevron_right_rounded),
          onTap: _elegirFuente,
        ),
        const Padding(
          padding: EdgeInsets.fromLTRB(Esp.lado, 0, Esp.lado, 6),
          child: Text('Si al sonar no hay internet, suena una canción descargada o el sonido suave de Caudal.',
              style: estiloDetalle),
        ),
        ListTile(
          title: const Text('Volumen'),
          subtitle: Slider(
            value: a.volumen.toDouble(),
            min: 5,
            max: 100,
            divisions: 19,
            label: '${a.volumen} %',
            onChanged: (v) => setState(() => _a = _a.copia(volumen: v.round())),
          ),
          trailing: Text('${a.volumen} %'),
        ),
        ListTile(
          title: const Text('Sube poco a poco'),
          subtitle: Slider(
            value: a.subida.clamp(0, 300).toDouble(),
            min: 0,
            max: 300,
            divisions: 20,
            label: _textoSubida(a.subida),
            onChanged: (v) => setState(() => _a = _a.copia(subida: v.round())),
          ),
          trailing: Text(_textoSubida(a.subida)),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(Esp.lado, 6, Esp.lado, 0),
          child: Text('Posponer', style: estiloTituloFila),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(Esp.lado, 6, Esp.lado, 6),
          child: Wrap(spacing: 6, children: [
            for (final m in const [5, 9, 10, 15, 20])
              ChoiceChip(
                label: Text('$m min'),
                selected: a.posponer == m,
                onSelected: (_) => setState(() => _a = _a.copia(posponer: m)),
              ),
          ]),
        ),
        if (Plataforma.esAndroid)
          SwitchListTile.adaptive(
            title: const Text('Vibrar'),
            subtitle: const Text('Vibra suave cuando el volumen ya subió', style: estiloSecundario),
            value: a.vibrar,
            onChanged: (v) => setState(() => _a = _a.copia(vibrar: v)),
          ),
        const SizedBox(height: 12),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: Esp.lado),
          child: Row(children: [
            Expanded(
              child: OutlinedButton.icon(
                icon: const Icon(Icons.play_arrow_rounded),
                label: const Text('Probar'),
                onPressed: () => widget.control.probar(_resultado),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: FilledButton(
                onPressed: () {
                  final f = _resultado.fuente;
                  final falta = (f.tipo == TipoFuente.cancion && f.pista == null) ||
                      ((f.tipo == TipoFuente.lista || f.tipo == TipoFuente.mix) && f.id.isEmpty);
                  if (falta) {
                    unawaited(_elegirFuente());
                    return;
                  }
                  Navigator.pop(context, _ResultadoEditor(_resultado));
                },
                child: const Text('Guardar'),
              ),
            ),
          ]),
        ),
      ]),
    );
  }
}
