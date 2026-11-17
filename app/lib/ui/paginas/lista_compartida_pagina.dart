import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../nucleo/vida_app.dart';
import '../../nucleo/coleccion.dart';
import '../../nucleo/listas_compartidas.dart';
import '../comunes.dart';
import '../servicios.dart';
import '../tema.dart';
import 'lista_compartir.dart';
import 'perfil_comun.dart';

/// Las listas de otras personas que ya se vieron en esta sesión (para saber,
/// por ejemplo, si una tarjeta del chat dice «Unirme» o «Abrir»).
class ListasCompartidasVistas {
  ListasCompartidasVistas._();
  static final ValueNotifier<List<ListaCompartida>> lista = ValueNotifier(const []);

  static bool conoceNombre(String nombre) => lista.value.any((l) => l.nombre == nombre);
}

/// Abre una lista de otra persona dentro de la pestaña actual.
Future<void> abrirListaCompartida(BuildContext context, ListaCompartida l) =>
    Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => ListaCompartidaPagina(lista: l)));

/// Abre una lista PROPIA a partir de su identificador en la nube.
Future<void> abrirListaPropiaPorUuid(BuildContext context, String uuid) async {
  final s = Caudal.leer(context);
  final todas = await s.coleccion.listas();
  Json? l;
  for (final x in todas) {
    if ('${x['uuid']}' == uuid) l = x;
  }
  if (!context.mounted) return;
  if (l == null) {
    s.avisar('Esa es tu propia lista. Búscala en tu biblioteca.');
    return;
  }
  s.abrirElemento(context, {'tipo': 'mi_lista', 'id': l['id'], 'titulo': l['nombre']});
}

// ============================================================ «Tengo un código»

/// Pide o recibe un código, enseña la vista previa y se une con «Unirme».
/// [codigoInicial]: un código o un enlace (se prueba solo, sin escribir).
Future<void> hojaTengoCodigo(BuildContext context, {String? codigoInicial}) async {
  final s = Caudal.leer(context);
  if (listasDe(context) == null) {
    s.avisar('Para unirte a una lista hace falta haber entrado con internet.');
    return;
  }
  final nav = Navigator.of(context);
  final r = await showModalBottomSheet<Object>(
    context: context,
    useRootNavigator: true,
    isScrollControlled: true,
    builder: (ctx) => HojaTengoCodigo(codigoInicial: codigoInicial),
  );
  if (r == null || !nav.mounted) return;
  if (r is ListaCompartida) {
    await nav.push(MaterialPageRoute<void>(builder: (_) => ListaCompartidaPagina(lista: r)));
  } else if (r is String && nav.context.mounted) {
    await abrirListaPropiaPorUuid(nav.context, r);
  }
}

class HojaTengoCodigo extends StatefulWidget {
  const HojaTengoCodigo({super.key, this.codigoInicial});
  final String? codigoInicial;

  @override
  State<HojaTengoCodigo> createState() => _HojaTengoCodigoState();
}

class _HojaTengoCodigoState extends State<HojaTengoCodigo> {
  final _campo = TextEditingController();
  VistaPreviaLista? _vista;
  String? _codigo;
  bool _ocupado = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    final c = widget.codigoInicial;
    if (c != null && c.trim().isNotEmpty) {
      final limpio = codigoListaDeTexto(c);
      _campo.text = limpio == null ? c : formatearCodigoLista(limpio);
      if (limpio != null) WidgetsBinding.instance.addPostFrameCallback((_) => _ver());
    }
  }

  @override
  void dispose() {
    _campo.dispose();
    super.dispose();
  }

  Future<void> _pegar() async {
    final d = await Clipboard.getData(Clipboard.kTextPlain);
    final t = d?.text ?? '';
    if (t.isEmpty) return;
    final c = codigoListaDeTexto(t);
    setState(() {
      _campo.text = c == null ? t.trim() : formatearCodigoLista(c);
      _vista = null;
      _error = null;
    });
    if (c != null) _ver();
  }

  Future<void> _ver() async {
    final base = listasDe(context);
    if (base == null || _ocupado) return;
    final c = codigoListaDeTexto(_campo.text);
    if (c == null) {
      setState(() => _error = 'Ese código no es válido: son 8 letras o números, como K7M2-9QXP.');
      return;
    }
    setState(() {
      _ocupado = true;
      _error = null;
      _vista = null;
    });
    try {
      final v = await base.verPorCodigo(c);
      if (!mounted) return;
      setState(() {
        _ocupado = false;
        _codigo = c;
        _vista = v;
        if (v == null) _error = 'Ese código no existe o la lista ya no se comparte. Revisa que esté bien escrito.';
      });
    } catch (e) {
      if (mounted) {
        setState(() {
          _ocupado = false;
          _error = textoErrorLista(e);
        });
      }
    }
  }

  Future<void> _unirme() async {
    final base = listasDe(context);
    final v = _vista;
    final c = _codigo;
    if (base == null || v == null || c == null || _ocupado) return;
    setState(() {
      _ocupado = true;
      _error = null;
    });
    try {
      final r = await base.unirse(c);
      if (!mounted) return;
      if (r.esDueno) {
        Navigator.of(context).pop(r.listaId);
      } else {
        Caudal.leer(context).avisar('Te uniste a «${r.nombre}»');
        Navigator.of(context).pop(ListaCompartida(
            id: r.listaId, nombre: r.nombre, rol: r.rol, total: v.total, dueno: v.dueno));
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _ocupado = false;
          _error = textoErrorLista(e);
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final v = _vista;
    return SafeArea(
      child: SingleChildScrollView(
        padding: EdgeInsets.fromLTRB(20, 4, 20, 16 + MediaQuery.viewInsetsOf(context).bottom),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          const Text('Tengo un código', style: estiloTituloSeccion),
          const SizedBox(height: 4),
          const Text('Escribe o pega el código que te pasaron. También sirve el enlace entero.', style: estiloSecundario),
          const SizedBox(height: 14),
          TextField(
            controller: _campo,
            autofocus: widget.codigoInicial == null,
            textCapitalization: TextCapitalization.characters,
            textInputAction: TextInputAction.search,
            onSubmitted: (_) => _ver(),
            onChanged: (_) {
              if (_vista != null || _error != null) {
                setState(() {
                  _vista = null;
                  _error = null;
                });
              }
            },
            style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w800, letterSpacing: 3),
            decoration: InputDecoration(
              hintText: 'K7M2-9QXP',
              filled: true,
              fillColor: C.superficie2,
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide.none),
              suffixIcon: IconButton(tooltip: 'Pegar', icon: const Icon(Icons.content_paste_rounded), onPressed: _pegar),
            ),
          ),
          const SizedBox(height: 10),
          if (v == null)
            FilledButton(
              onPressed: _ocupado ? null : _ver,
              child: _ocupado
                  ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Text('Ver la lista'),
            )
          else ...[
            _VistaPreviaTarjeta(vista: v),
            const SizedBox(height: 12),
            FilledButton.icon(
              onPressed: _ocupado ? null : _unirme,
              icon: _ocupado
                  ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Icon(Icons.group_add_rounded),
              label: const Text('Unirme'),
            ),
          ],
          if (_error != null)
            Padding(padding: const EdgeInsets.only(top: 10),
                child: Text(_error!, textAlign: TextAlign.center, style: const TextStyle(color: C.error, fontSize: 13.5))),
        ]),
      ),
    );
  }
}

class _VistaPreviaTarjeta extends StatelessWidget {
  const _VistaPreviaTarjeta({required this.vista});
  final VistaPreviaLista vista;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(color: C.superficie2, borderRadius: BorderRadius.circular(16)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(vista.nombre, style: const TextStyle(fontSize: 19, fontWeight: FontWeight.w800)),
          const SizedBox(height: 8),
          Row(children: [
            AvatarPerfil(nombre: vista.dueno.visible, fotoUrl: vista.dueno.fotoUrl, radio: 12),
            const SizedBox(width: 8),
            Expanded(child: Text('De ${vista.dueno.visible}', style: estiloSecundario, maxLines: 1,
                overflow: TextOverflow.ellipsis)),
          ]),
          const SizedBox(height: 6),
          Text('${vista.total == 1 ? '1 canción' : '${vista.total} canciones'} · ${vista.permisoTexto}',
              style: TextStyle(color: C.acento, fontWeight: FontWeight.w700, fontSize: 13)),
          if (vista.canciones.isNotEmpty) ...[
            const SizedBox(height: 10),
            for (final c in vista.canciones)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 3),
                child: Row(children: [
                  Portada(url: c.miniatura, lado: 34, radio: 4),
                  const SizedBox(width: 10),
                  Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(c.titulo, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 13.5)),
                    if (c.artista.isNotEmpty)
                      Text(c.artista, maxLines: 1, overflow: TextOverflow.ellipsis, style: estiloDetalle),
                  ])),
                ]),
              ),
            if (vista.total > vista.canciones.length)
              Padding(padding: const EdgeInsets.only(top: 4),
                  child: Text('y ${vista.total - vista.canciones.length} más…', style: estiloDetalle)),
          ],
        ]),
      );
}

// ================================================= la lista compartida (de otro)

class ListaCompartidaPagina extends StatefulWidget {
  const ListaCompartidaPagina({super.key, required this.lista});
  final ListaCompartida lista;

  @override
  State<ListaCompartidaPagina> createState() => _ListaCompartidaPaginaState();
}

class _ListaCompartidaPaginaState extends State<ListaCompartidaPagina> {
  late ListaCompartida _lista = widget.lista;
  List<PistaCompartida>? _pistas;
  String? _error;
  bool _sinAcceso = false;
  bool _trayendo = false;

  /// Cada cuánto se vuelve a traer mientras está abierta.
  static const cadaCuanto = Duration(seconds: 20);

  /// Solo con la app a la vista y esta pantalla delante; al volver, en el acto.
  late final Sondeo _sondeo = Sondeo(cadaCuanto, () async {
    if (mounted) await _traer(silencioso: true);
  });

  bool get _puedeAnadir => _lista.puedeAnadir;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _traer();
      _sondeo.iniciar();
    });
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _sondeo.seguirPantalla(context);
  }

  @override
  void dispose() {
    _sondeo.detener();
    super.dispose();
  }

  Future<void> _traer({bool silencioso = false}) async {
    final base = listasDe(context);
    if (base == null || _trayendo || !mounted) return;
    _trayendo = true;
    try {
      final r = await Future.wait([base.pistasDeLista(_lista.id), base.misListasCompartidas()]);
      if (!mounted) return;
      final pistas = r[0] as List<PistaCompartida>;
      final mias = r[1] as List<ListaCompartida>;
      ListasCompartidasVistas.lista.value = mias;
      final ahora = mias.where((l) => l.id == _lista.id);
      setState(() {
        _pistas = pistas;
        _error = null;
        if (ahora.isEmpty) {
          _sinAcceso = true; // salió, la quitaron, la dejaron de compartir o hay un bloqueo
        } else {
          _lista = ahora.first;
          _sinAcceso = false;
        }
      });
    } catch (e) {
      final t = textoErrorLista(e);
      if (!mounted) return;
      if (t.contains('Ya no tienes acceso')) {
        setState(() => _sinAcceso = true);
      } else if (!silencioso || _pistas == null) {
        setState(() => _error = t);
      }
    } finally {
      _trayendo = false;
    }
  }

  Json get _contexto => {'tipo': 'lista_compartida', 'id': _lista.id, 'titulo': _lista.nombre,
        'miniatura': _pistas?.isNotEmpty == true ? '${_pistas!.first.pista['miniatura'] ?? ''}' : ''};

  List<Json> get _soloPistas => [for (final p in _pistas ?? const <PistaCompartida>[]) p.pista];

  void _reproducir({bool aleatorio = false, int inicio = 0}) {
    final l = _soloPistas;
    if (l.isEmpty) return;
    Caudal.leer(context).reproducirLista(context, l, inicio: inicio, contexto: _contexto, aleatorio: aleatorio);
  }

  Future<void> _quitar(PistaCompartida p) async {
    final base = listasDe(context);
    final s = Caudal.leer(context);
    if (base == null) return;
    try {
      await base.quitar(_lista.id, p.clave);
      s.avisar('Quitada de «${_lista.nombre}»', deshacer: () async {
        try {
          await base.agregar(_lista.id, [p.pista]);
          _traer();
        } catch (_) {}
      });
      _traer();
    } catch (e) {
      s.avisar(textoErrorLista(e));
    }
  }

  Future<void> _anadir() async {
    final s = Caudal.leer(context);
    final base = listasDe(context);
    if (base == null) return;
    final ya = {for (final p in _pistas ?? const <PistaCompartida>[]) p.clave};
    final gustan = await s.coleccion.listaMeGusta();
    if (!mounted) return;
    final elegidas = await showModalBottomSheet<List<Json>>(
      context: context,
      useRootNavigator: true,
      isScrollControlled: true,
      builder: (ctx) => _ElegirCanciones(opciones: [for (final p in gustan) if (!ya.contains('${p['clave']}')) p]),
    );
    if (elegidas == null || elegidas.isEmpty || !mounted) return;
    try {
      final n = await base.agregar(_lista.id, elegidas);
      s.avisar(n == 0 ? 'Esas canciones ya estaban en la lista.' : n == 1 ? 'Añadiste 1 canción' : 'Añadiste $n canciones');
      _traer();
    } catch (e) {
      s.avisar(textoErrorLista(e));
    }
  }

  Future<void> _miembros() async {
    final base = listasDe(context);
    if (base == null) return;
    await showModalBottomSheet<void>(
      context: context,
      useRootNavigator: true,
      isScrollControlled: true,
      builder: (ctx) => _HojaMiembros(base: base, lista: _lista),
    );
  }

  Future<void> _salir() async {
    final base = listasDe(context);
    final s = Caudal.leer(context);
    if (base == null) return;
    final ok = await confirmar(context, 'Salir de la lista',
        '¿Salir de «${_lista.nombre}»? Podrás volver a unirte con el código mientras ${_lista.dueno.visible} la comparta.',
        si: 'Salir');
    if (!ok || !mounted) return;
    try {
      await base.salir(_lista.id);
      s.avisar('Saliste de «${_lista.nombre}»');
      if (mounted) Navigator.of(context).maybePop();
    } catch (e) {
      s.avisar(textoErrorLista(e));
    }
  }

  @override
  Widget build(BuildContext context) {
    final pistas = _pistas;
    return Scaffold(
      appBar: AppBar(
        title: Text(_lista.nombre, maxLines: 1, overflow: TextOverflow.ellipsis),
        actions: [
          IconButton(tooltip: 'Quién está en la lista', icon: const Icon(Icons.group_outlined), onPressed: _miembros),
          PopupMenuButton<String>(
            onSelected: (v) => v == 'salir' ? _salir() : _traer(),
            itemBuilder: (_) => const [
              PopupMenuItem(value: 'refrescar', child: Text('Actualizar ahora')),
              PopupMenuItem(value: 'salir', child: Text('Salir de la lista')),
            ],
          ),
        ],
      ),
      body: _sinAcceso
          ? Vacio(
              icono: Icons.link_off_rounded,
              titulo: 'Ya no estás en esta lista',
              texto: 'Su dueño dejó de compartirla, te quitó de ella o saliste. Si tienes el código, puedes volver a unirte.',
              textoAccion: 'Volver',
              iconoAccion: Icons.arrow_back_rounded,
              alAccion: () => Navigator.of(context).maybePop(),
            )
          : RefreshIndicator(
              onRefresh: _traer,
              child: ListView(padding: const EdgeInsets.only(bottom: 120), children: [
                _cabecera(pistas),
                if (_error != null && pistas == null)
                  Vacio(icono: Icons.wifi_off_rounded, titulo: 'Sin conexión', texto: _error!, error: true, alAccion: _traer)
                else if (pistas == null)
                  const Esqueleto(filas: true)
                else if (pistas.isEmpty)
                  Padding(
                    padding: const EdgeInsets.all(32),
                    child: Text(_puedeAnadir
                        ? 'Esta lista aún no tiene canciones. ¡Añade la primera!'
                        : 'Esta lista aún no tiene canciones.',
                        textAlign: TextAlign.center, style: estiloSecundario),
                  )
                else
                  for (var i = 0; i < pistas.length; i++) _fila(pistas, i),
              ]),
            ),
    );
  }

  Widget _cabecera(List<PistaCompartida>? pistas) {
    final minis = [for (final p in pistas ?? const <PistaCompartida>[]) '${p.pista['miniatura'] ?? ''}']
        .where((m) => m.isNotEmpty)
        .take(4)
        .toList();
    final total = pistas?.length ?? _lista.total;
    return Padding(
      padding: const EdgeInsets.fromLTRB(Esp.lado, 8, Esp.lado, 12),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(10),
            child: SizedBox(
              width: 96, height: 96,
              child: minis.length == 4
                  ? Wrap(children: [for (final u in minis) Portada(url: u, lado: 48, radio: 0)])
                  : Portada(url: minis.isEmpty ? '' : minis.first, lado: 96, radio: 0, icono: Icons.queue_music_rounded),
            ),
          ),
          const SizedBox(width: 14),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(_lista.nombre, maxLines: 2, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 21, fontWeight: FontWeight.w900, height: 1.15)),
            const SizedBox(height: 6),
            Row(children: [
              AvatarPerfil(nombre: _lista.dueno.visible, fotoUrl: _lista.dueno.fotoUrl, radio: 10),
              const SizedBox(width: 6),
              Expanded(child: Text('Compartida · ${_lista.dueno.visible}', maxLines: 1,
                  overflow: TextOverflow.ellipsis, style: estiloSecundario)),
            ]),
            const SizedBox(height: 4),
            Text('${total == 1 ? '1 canción' : '$total canciones'} · ${textoRolLista(_lista.rol)}',
                style: TextStyle(color: C.acento, fontSize: 12.5, fontWeight: FontWeight.w700)),
          ])),
        ]),
        const SizedBox(height: 14),
        Row(children: [
          Expanded(child: FilledButton.icon(
              onPressed: (pistas?.isEmpty ?? true) ? null : () => _reproducir(),
              icon: const Icon(Icons.play_arrow_rounded), label: const Text('Reproducir'))),
          const SizedBox(width: 8),
          IconButton.outlined(tooltip: 'Al azar', icon: const Icon(Icons.shuffle_rounded),
              onPressed: (pistas?.isEmpty ?? true) ? null : () => _reproducir(aleatorio: true)),
          if (_puedeAnadir) ...[
            const SizedBox(width: 8),
            IconButton.outlined(tooltip: 'Añadir canciones', icon: const Icon(Icons.add_rounded), onPressed: _anadir),
          ],
        ]),
        if (!_puedeAnadir)
          const Padding(padding: EdgeInsets.only(top: 8),
              child: Text('En esta lista solo puedes escuchar.', style: estiloDetalle)),
      ]),
    );
  }

  Widget _fila(List<PistaCompartida> pistas, int i) {
    final p = pistas[i];
    final s = Caudal.leer(context);
    final mia = p.agregadaPor.id == s.cuenta.id;
    final puedeQuitar = _puedeAnadir && mia;
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      FilaPista(
        pista: p.pista,
        alPulsar: () => _reproducir(inicio: i),
        extraMenu: [
          if (puedeQuitar)
            ListTile(
              leading: const Icon(Icons.remove_circle_outline_rounded, color: C.error),
              title: const Text('Quitar de la lista', style: TextStyle(color: C.error)),
              onTap: () {
                Navigator.of(context, rootNavigator: true).pop();
                _quitar(p);
              },
            ),
        ],
      ),
      if (p.textoAutor.isNotEmpty)
        Padding(
          padding: const EdgeInsets.only(left: Esp.lado + 60, bottom: 2),
          child: Text(mia ? 'Añadida por ti' : p.textoAutor, style: estiloDetalle),
        ),
    ]);
  }
}

class _HojaMiembros extends StatefulWidget {
  const _HojaMiembros({required this.base, required this.lista});
  final ListasCompartidas base;
  final ListaCompartida lista;

  @override
  State<_HojaMiembros> createState() => _HojaMiembrosState();
}

class _HojaMiembrosState extends State<_HojaMiembros> {
  List<MiembroLista>? _m;
  String? _error;

  @override
  void initState() {
    super.initState();
    widget.base.miembros(widget.lista.id).then((l) {
      if (mounted) setState(() => _m = l);
    }, onError: (Object e) {
      if (mounted) setState(() => _error = textoErrorLista(e));
    });
  }

  @override
  Widget build(BuildContext context) {
    final m = _m;
    return SafeArea(
      child: ConstrainedBox(
        constraints: BoxConstraints(maxHeight: MediaQuery.sizeOf(context).height * 0.7),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          const Padding(padding: EdgeInsets.fromLTRB(20, 4, 20, 8), child: Text('En esta lista', style: estiloTituloSeccion)),
          if (_error != null)
            Padding(padding: const EdgeInsets.all(20), child: Text(_error!, style: const TextStyle(color: C.error)))
          else if (m == null)
            const Padding(padding: EdgeInsets.all(24), child: Center(child: CircularProgressIndicator()))
          else
            Flexible(
              child: ListView(shrinkWrap: true, children: [
                for (final x in m)
                  ListTile(
                    leading: AvatarPerfil(nombre: x.persona.visible, fotoUrl: x.persona.fotoUrl, radio: 18),
                    title: Text(x.persona.visible),
                    subtitle: Text(x.esDueno ? 'Dueño' : textoRolLista(x.rol), style: estiloDetalle),
                  ),
              ]),
            ),
        ]),
      ),
    );
  }
}

/// Elegir canciones (de tus «me gusta») para añadirlas a la lista compartida.
class _ElegirCanciones extends StatefulWidget {
  const _ElegirCanciones({required this.opciones});
  final List<Json> opciones;

  @override
  State<_ElegirCanciones> createState() => _ElegirCancionesState();
}

class _ElegirCancionesState extends State<_ElegirCanciones> {
  final _marcadas = <String>{};
  String _q = '';

  @override
  Widget build(BuildContext context) {
    final q = _q.trim().toLowerCase();
    final lista = [
      for (final p in widget.opciones)
        if (q.isEmpty || '${p['titulo']} ${p['artista']}'.toLowerCase().contains(q)) p
    ];
    return SafeArea(
      child: ConstrainedBox(
        constraints: BoxConstraints(maxHeight: MediaQuery.sizeOf(context).height * 0.85),
        child: Padding(
          padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(context).bottom),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            const Padding(padding: EdgeInsets.fromLTRB(20, 4, 20, 2), child: Text('Añadir canciones', style: estiloTituloSeccion)),
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: 20),
              child: Text('Elige de tus «me gusta». También puedes añadir desde cualquier canción: '
                  'menú › Añadir a una lista.', style: estiloSecundario),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 10, 20, 6),
              child: TextField(
                onChanged: (t) => setState(() => _q = t),
                decoration: InputDecoration(
                  hintText: 'Buscar en tus me gusta',
                  prefixIcon: const Icon(Icons.search_rounded),
                  isDense: true, filled: true, fillColor: C.superficie2,
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(999), borderSide: BorderSide.none),
                ),
              ),
            ),
            Flexible(
              child: widget.opciones.isEmpty
                  ? const Padding(padding: EdgeInsets.all(28),
                      child: Text('No tienes «me gusta» que falten en esta lista.', textAlign: TextAlign.center,
                          style: estiloSecundario))
                  : ListView.builder(
                      shrinkWrap: true,
                      itemCount: lista.length,
                      itemBuilder: (_, i) {
                        final p = lista[i];
                        final c = '${p['clave']}';
                        return CheckboxListTile(
                          value: _marcadas.contains(c),
                          onChanged: (v) => setState(() => v == true ? _marcadas.add(c) : _marcadas.remove(c)),
                          secondary: Portada(url: '${p['miniatura'] ?? ''}', lado: 44, radio: 4),
                          title: Text('${p['titulo'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis),
                          subtitle: Text('${p['artista'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                              style: estiloDetalle),
                          controlAffinity: ListTileControlAffinity.trailing,
                        );
                      },
                    ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 8, 20, 12),
              child: FilledButton(
                onPressed: _marcadas.isEmpty
                    ? null
                    : () => Navigator.pop(context, [for (final p in widget.opciones) if (_marcadas.contains('${p['clave']}')) p]),
                child: Text(_marcadas.isEmpty ? 'Elige canciones' : 'Añadir (${_marcadas.length})'),
              ),
            ),
          ]),
        ),
      ),
    );
  }
}

// ====================================================== tarjeta de lista en el chat

/// La lista que llegó (o se mandó) por el chat: nombre, canciones, permiso y
/// un botón «Unirme» (o «Abrir» si ya estás dentro).
class TarjetaListaChat extends StatelessWidget {
  const TarjetaListaChat({super.key, required this.tarjeta, required this.mio});
  final TarjetaLista tarjeta;
  final bool mio;

  @override
  Widget build(BuildContext context) {
    final fuerte = mio ? C.acentoTexto : C.texto;
    final suave = mio ? C.acentoTexto.withValues(alpha: 0.75) : C.texto2;
    return ValueListenableBuilder<List<ListaCompartida>>(
      valueListenable: ListasCompartidasVistas.lista,
      builder: (context, _, _) {
        final dentro = mio || ListasCompartidasVistas.conoceNombre(tarjeta.nombre);
        return SizedBox(
          width: 250,
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Portada(url: tarjeta.portada, lado: 54, radio: 6, icono: Icons.queue_music_rounded),
              const SizedBox(width: 10),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(tarjeta.nombre, maxLines: 2, overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontWeight: FontWeight.w800, color: fuerte)),
                Text(tarjeta.textoCanciones, style: TextStyle(fontSize: 12.5, color: suave)),
                Text(textoRolLista(tarjeta.rol), style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: suave)),
              ])),
            ]),
            const SizedBox(height: 8),
            SizedBox(
              width: double.infinity,
              child: FilledButton(
                style: FilledButton.styleFrom(
                  visualDensity: VisualDensity.compact,
                  backgroundColor: mio ? C.acentoTexto : C.acento,
                  foregroundColor: mio ? C.acento : C.acentoTexto,
                ),
                onPressed: () => hojaTengoCodigo(context, codigoInicial: tarjeta.codigo),
                child: Text(dentro ? 'Abrir' : 'Unirme'),
              ),
            ),
          ]),
        );
      },
    );
  }
}
