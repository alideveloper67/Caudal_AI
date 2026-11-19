import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:share_plus/share_plus.dart';

import '../../nucleo/coleccion.dart';
import '../../nucleo/listas_compartidas.dart';
import '../../nucleo/nube.dart';
import '../comunes.dart';
import '../servicios.dart';
import '../tema.dart';
import 'mensajes_pagina.dart';
import 'lista_compartida_pagina.dart';
import 'perfil_comun.dart';

/// La base de listas compartidas de la cuenta (nula si se entró sin internet).
ListasCompartidas? listasDe(BuildContext context) {
  final se = Caudal.leer(context).cuenta.sesion;
  return se == null || se.acceso.isEmpty ? null : ListasCompartidas(se);
}

String textoErrorLista(Object e) =>
    e is ErrorNube ? e.mensaje : 'No se pudo conectar. Revisa tu internet y vuelve a probar.';

/// Comparte una lista propia (si hace falta) y arma su tarjeta. Es lo que usan
/// tanto «Compartir lista › Enviar por el chat» como «Enviar una lista» desde
/// dentro del chat. Falla con un [ErrorNube] legible.
Future<TarjetaLista> prepararTarjetaDeLista(BuildContext context, Json lista, {required String rol}) async {
  final s = Caudal.leer(context);
  final base = listasDe(context);
  if (base == null) throw const ErrorNube('Para compartir listas hace falta haber entrado con internet.');
  final id = Servicios.idLista(lista['id']);
  final uuid = '${lista['uuid'] ?? ''}';
  final recuerdo = await ListasQueComparto.cargar(s.cuenta.id);
  final pistas = id == null ? <Json>[] : await s.coleccion.pistasDeLista(id);
  final mini = pistas.map((p) => '${p['miniatura'] ?? ''}').firstWhere((m) => m.isNotEmpty, orElse: () => '');
  return tarjetaParaEnviar(
    base: base,
    uuid: uuid,
    nombre: '${lista['nombre'] ?? lista['titulo'] ?? 'Mi lista'}',
    canciones: pistas.length,
    rol: rol,
    rolGuardado: recuerdo.rolDe(uuid),
    portada: mini,
    asegurarEnNube: () => enviarPendientesYEsperar(s.coleccion, s.sincronizador),
    alCompartir: recuerdo.marcar,
  );
}

// =============================================================== compartir lista

/// «Compartir lista», desde el menú de una lista propia.
Future<void> hojaCompartirLista(BuildContext context, {required int id}) async {
  final s = Caudal.leer(context);
  final lista = await s.coleccion.lista(id);
  if (lista == null || !context.mounted) return;
  if (listasDe(context) == null) {
    s.avisar('Para compartir listas hace falta haber entrado con internet.');
    return;
  }
  await showModalBottomSheet<void>(
    context: context,
    useRootNavigator: true,
    isScrollControlled: true,
    builder: (ctx) => HojaCompartirLista(lista: lista),
  );
}

class HojaCompartirLista extends StatefulWidget {
  const HojaCompartirLista({super.key, required this.lista});
  final Json lista;

  @override
  State<HojaCompartirLista> createState() => _HojaCompartirListaState();
}

class _HojaCompartirListaState extends State<HojaCompartirLista> {
  ListasQueComparto? _recuerdo;
  String? _codigo;
  bool _colaborativa = true;
  bool _ocupado = true;
  String? _error;
  List<MiembroLista>? _miembros;
  bool _verMiembros = false;

  String get _uuid => '${widget.lista['uuid'] ?? ''}';
  String get _nombre => '${widget.lista['nombre'] ?? 'Mi lista'}';
  String get _rol => _colaborativa ? rolColaborador : rolOyente;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _iniciar());
  }

  Future<void> _iniciar() async {
    final s = Caudal.leer(context);
    final r = await ListasQueComparto.cargar(s.cuenta.id);
    if (!mounted) return;
    _recuerdo = r;
    final rol = r.rolDe(_uuid);
    if (rol == null) {
      setState(() => _ocupado = false);
      return;
    }
    _colaborativa = rol == rolColaborador;
    await _compartir(reutilizar: true);
  }

  /// Crea el código (o recupera el que ya tenía). Con [cambiarPermiso] la base
  /// cambia el permiso de la lista para todos.
  Future<void> _compartir({bool reutilizar = false, bool cambiarPermiso = false}) async {
    final s = Caudal.leer(context);
    final base = listasDe(context);
    if (base == null) return;
    setState(() {
      _ocupado = true;
      _error = null;
    });
    try {
      final c = await base.compartirPropia(_uuid,
          rol: _rol,
          rolGuardado: reutilizar && !cambiarPermiso ? _recuerdo?.rolDe(_uuid) : null,
          asegurarEnNube: reutilizar && !cambiarPermiso
              ? null
              : () => enviarPendientesYEsperar(s.coleccion, s.sincronizador));
      await _recuerdo?.marcar(_uuid, c.rol);
      if (mounted) {
        setState(() {
          _codigo = c.codigo;
          _ocupado = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _ocupado = false;
          _error = textoErrorLista(e);
          if (cambiarPermiso) _colaborativa = !_colaborativa; // vuelve a como estaba
        });
      }
    }
  }

  Future<void> _cambiarPermiso(bool colaborativa) async {
    if (_ocupado) return;
    setState(() => _colaborativa = colaborativa);
    if (_codigo != null) await _compartir(cambiarPermiso: true);
  }

  Future<void> _copiar() async {
    final c = _codigo;
    if (c == null) return;
    await Clipboard.setData(ClipboardData(text: formatearCodigoLista(c)));
    if (mounted) Caudal.leer(context).avisar('Código copiado: ${formatearCodigoLista(c)}');
  }

  Future<void> _compartirSistema() async {
    final c = _codigo;
    if (c == null) return;
    try {
      await SharePlus.instance.share(ShareParams(text: mensajeCompartirLista(_nombre, c)));
    } catch (_) {}
  }

  Future<void> _porChat() async {
    final s = Caudal.leer(context);
    final chat = chatDe(context);
    if (chat == null) {
      s.avisar('Los mensajes necesitan internet.');
      return;
    }
    final destino = await elegirDestinoChat(context);
    if (destino == null || !mounted) return;
    setState(() {
      _ocupado = true;
      _error = null;
    });
    try {
      final tarjeta = await prepararTarjetaDeLista(context, widget.lista, rol: _rol);
      await chat.enviar(destino.id, lista: tarjeta);
      s.avisar('Lista enviada a ${destino.visible}');
      if (mounted) setState(() => _ocupado = false);
    } catch (e) {
      if (mounted) {
        setState(() {
          _ocupado = false;
          _error = textoErrorLista(e);
        });
      }
    }
  }

  Future<void> _dejar() async {
    final ok = await confirmar(context, 'Dejar de compartir',
        'El código dejará de servir y las personas que se unieron saldrán de «$_nombre». '
        'La lista y sus canciones se quedan contigo.', si: 'Dejar de compartir');
    if (!ok || !mounted) return;
    final s = Caudal.leer(context);
    final base = listasDe(context);
    if (base == null) return;
    setState(() => _ocupado = true);
    try {
      await base.dejarDeCompartir(_uuid);
      await _recuerdo?.quitar(_uuid);
      s.avisar('Dejaste de compartir «$_nombre»');
      if (mounted) Navigator.of(context).pop();
    } catch (e) {
      if (mounted) {
        setState(() {
          _ocupado = false;
          _error = textoErrorLista(e);
        });
      }
    }
  }

  Future<void> _cargarMiembros() async {
    final base = listasDe(context);
    if (base == null) return;
    setState(() => _verMiembros = !_verMiembros);
    if (!_verMiembros) return;
    try {
      final m = await base.miembros(_uuid);
      if (mounted) setState(() => _miembros = m);
    } catch (e) {
      if (mounted) setState(() => _error = textoErrorLista(e));
    }
  }

  Future<void> _quitar(MiembroLista m) async {
    final base = listasDe(context);
    if (base == null) return;
    final ok = await confirmar(context, 'Quitar de la lista',
        '¿Quitar a ${m.persona.visible} de «$_nombre»? Podrá volver a unirse con el código.', si: 'Quitar');
    if (!ok || !mounted) return;
    try {
      await base.quitarMiembro(_uuid, m.id);
      final lista = await base.miembros(_uuid);
      if (mounted) setState(() => _miembros = lista);
    } catch (e) {
      if (mounted) setState(() => _error = textoErrorLista(e));
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = _codigo;
    return SafeArea(
      child: SingleChildScrollView(
        padding: EdgeInsets.fromLTRB(20, 4, 20, 16 + MediaQuery.viewInsetsOf(context).bottom),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Text('Compartir «$_nombre»', style: estiloTituloSeccion, maxLines: 2, overflow: TextOverflow.ellipsis),
          const SizedBox(height: 4),
          const Text('Quien tenga el código puede unirse a tu lista desde Caudal.', style: estiloSecundario),
          const SizedBox(height: 14),
          _InterruptorPermiso(colaborativa: _colaborativa, alCambiar: _ocupado ? null : _cambiarPermiso),
          const SizedBox(height: 14),
          if (c == null)
            FilledButton.icon(
              onPressed: _ocupado ? null : () => _compartir(),
              icon: _ocupado
                  ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Icon(Icons.key_rounded),
              label: Text(_ocupado ? 'Preparando el código…' : 'Crear el código'),
            )
          else ...[
            Container(
              padding: const EdgeInsets.symmetric(vertical: 18),
              decoration: BoxDecoration(color: C.superficie2, borderRadius: BorderRadius.circular(16)),
              child: Column(children: [
                const Text('Código de la lista', style: estiloDetalle),
                const SizedBox(height: 6),
                SelectableText(formatearCodigoLista(c), key: const ValueKey('codigo-lista'),
                    style: TextStyle(fontSize: 34, fontWeight: FontWeight.w900, letterSpacing: 4, color: C.acento)),
              ]),
            ),
            const SizedBox(height: 12),
            Row(children: [
              Expanded(child: OutlinedButton.icon(onPressed: _copiar, icon: const Icon(Icons.copy_rounded, size: 18),
                  label: const Text('Copiar código'))),
              const SizedBox(width: 10),
              Expanded(child: FilledButton.icon(onPressed: _compartirSistema,
                  icon: const Icon(Icons.share_rounded, size: 18), label: const Text('Compartir'))),
            ]),
            const SizedBox(height: 8),
            OutlinedButton.icon(onPressed: _ocupado ? null : _porChat,
                icon: const Icon(Icons.send_rounded, size: 18), label: const Text('Enviar por el chat')),
            const SizedBox(height: 4),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.group_outlined, color: C.texto2),
              title: const Text('Ver quién está en la lista'),
              trailing: Icon(_verMiembros ? Icons.expand_less_rounded : Icons.expand_more_rounded, color: C.texto3),
              onTap: _cargarMiembros,
            ),
            if (_verMiembros)
              if (_miembros == null)
                const Padding(padding: EdgeInsets.all(12), child: Center(child: CircularProgressIndicator()))
              else
                for (final m in _miembros!)
                  ListTile(
                    dense: true,
                    contentPadding: EdgeInsets.zero,
                    leading: AvatarPerfil(nombre: m.persona.visible, fotoUrl: m.persona.fotoUrl, marco: m.persona.marco, radio: 18),
                    title: Text(m.esDueno ? '${m.persona.visible} (tú)' : m.persona.visible),
                    subtitle: Text(m.esDueno ? 'Dueño' : textoRolLista(m.rol), style: estiloDetalle),
                    trailing: m.esDueno
                        ? null
                        : IconButton(tooltip: 'Quitar de la lista', icon: const Icon(Icons.person_remove_outlined),
                            onPressed: () => _quitar(m)),
                  ),
            TextButton.icon(
              onPressed: _ocupado ? null : _dejar,
              icon: const Icon(Icons.link_off_rounded, size: 18, color: C.error),
              label: const Text('Dejar de compartir', style: TextStyle(color: C.error)),
            ),
          ],
          if (_error != null)
            Padding(padding: const EdgeInsets.only(top: 8),
                child: Text(_error!, textAlign: TextAlign.center, style: const TextStyle(color: C.error, fontSize: 13))),
        ]),
      ),
    );
  }
}

/// «Pueden añadir canciones» / «Solo escuchar».
class _InterruptorPermiso extends StatelessWidget {
  const _InterruptorPermiso({required this.colaborativa, required this.alCambiar});
  final bool colaborativa;
  final ValueChanged<bool>? alCambiar;

  @override
  Widget build(BuildContext context) => SwitchListTile(
        contentPadding: EdgeInsets.zero,
        value: colaborativa,
        onChanged: alCambiar,
        title: Text(colaborativa ? 'Pueden añadir canciones' : 'Solo escuchar',
            style: const TextStyle(fontWeight: FontWeight.w700)),
        subtitle: Text(
            colaborativa
                ? 'Quien entre podrá poner música en esta lista. Caben hasta $maxMiembrosLista personas, gratis.'
                : 'Quien entre solo podrá escucharla.',
            style: estiloDetalle),
      );
}

// ============================================== «Enviar una lista» dentro del chat

/// Desde dentro de una conversación: elige una de tus listas y devuelve su
/// tarjeta (compartiéndola antes si hacía falta). Nulo si se cancela.
Future<TarjetaLista?> hojaEnviarLista(BuildContext context) async {
  final s = Caudal.leer(context);
  if (listasDe(context) == null) {
    s.avisar('Para enviar listas hace falta haber entrado con internet.');
    return null;
  }
  final listas = s.coleccion.listasEnMemoria ?? await s.coleccion.listas();
  if (!context.mounted) return null;
  final recuerdo = await ListasQueComparto.cargar(s.cuenta.id);
  if (!context.mounted) return null;
  return showModalBottomSheet<TarjetaLista>(
    context: context,
    useRootNavigator: true,
    isScrollControlled: true,
    builder: (ctx) => _HojaEnviarLista(listas: listas, recuerdo: recuerdo),
  );
}

class _HojaEnviarLista extends StatefulWidget {
  const _HojaEnviarLista({required this.listas, required this.recuerdo});
  final List<Json> listas;
  final ListasQueComparto recuerdo;

  @override
  State<_HojaEnviarLista> createState() => _HojaEnviarListaState();
}

class _HojaEnviarListaState extends State<_HojaEnviarLista> {
  bool _colaborativa = true;
  String? _enviando; // uuid de la lista que se está preparando
  String? _error;

  Future<void> _elegir(Json l) async {
    if (_enviando != null) return;
    final uuid = '${l['uuid'] ?? ''}';
    final s = Caudal.leer(context);
    setState(() {
      _enviando = uuid;
      _error = null;
    });
    try {
      final t = await prepararTarjetaDeLista(context, l, rol: _colaborativa ? rolColaborador : rolOyente);
      final nueva = !widget.recuerdo.estaCompartida(uuid);
      if (nueva) {
        s.avisar('Compartí «${t.nombre}» como ${t.colaborativa ? 'lista colaborativa: pueden añadir canciones' : 'lista de solo escuchar'}.');
      }
      if (mounted) Navigator.of(context).pop(t);
    } catch (e) {
      if (mounted) {
        setState(() {
          _enviando = null;
          _error = textoErrorLista(e);
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final alto = MediaQuery.sizeOf(context).height;
    return SafeArea(
      child: ConstrainedBox(
        constraints: BoxConstraints(maxHeight: alto * 0.8),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          const Padding(padding: EdgeInsets.fromLTRB(20, 4, 20, 4), child: Text('Enviar una lista', style: estiloTituloSeccion)),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            child: Text(
                'Si aún no está compartida, se comparte sola. ${_colaborativa ? 'Quien la reciba podrá añadir canciones.' : 'Quien la reciba solo podrá escucharla.'}',
                style: estiloSecundario),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 10, 20, 6),
            child: SegmentedButton<bool>(
              segments: const [
                ButtonSegment(value: true, label: Text('Colaborativa'), icon: Icon(Icons.group_add_rounded, size: 18)),
                ButtonSegment(value: false, label: Text('Solo escuchar'), icon: Icon(Icons.headphones_rounded, size: 18)),
              ],
              selected: {_colaborativa},
              onSelectionChanged: _enviando != null ? null : (v) => setState(() => _colaborativa = v.first),
            ),
          ),
          if (_error != null)
            Padding(padding: const EdgeInsets.fromLTRB(20, 4, 20, 0),
                child: Text(_error!, style: const TextStyle(color: C.error, fontSize: 13))),
          Flexible(
            child: widget.listas.isEmpty
                ? const Padding(
                    padding: EdgeInsets.all(28),
                    child: Text('Todavía no tienes listas. Crea una en tu biblioteca y vuelve a probar.',
                        textAlign: TextAlign.center, style: estiloSecundario))
                : ListView.builder(
                    shrinkWrap: true,
                    itemCount: widget.listas.length,
                    itemBuilder: (_, i) {
                      final l = widget.listas[i];
                      final uuid = '${l['uuid'] ?? ''}';
                      final rol = widget.recuerdo.rolDe(uuid);
                      return ListTile(
                        contentPadding: const EdgeInsets.symmetric(horizontal: 20),
                        leading: CircleAvatar(backgroundColor: C.superficie3,
                            child: Icon(Icons.queue_music_rounded, color: C.acento)),
                        title: Text('${l['nombre']}', maxLines: 1, overflow: TextOverflow.ellipsis),
                        subtitle: Text(
                            '${l['n'] ?? 0} canciones${rol == null ? '' : ' · Compartida · ${textoRolLista(rol)}'}',
                            style: estiloDetalle),
                        trailing: _enviando == uuid
                            ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                            : const Icon(Icons.send_rounded, size: 20, color: C.texto3),
                        onTap: () => _elegir(l),
                      );
                    },
                  ),
          ),
        ]),
      ),
    );
  }
}

// ============================ listas compartidas dentro de «Añadir a una lista»

/// Las listas de otras personas donde puedo añadir canciones, como destinos de
/// la hoja «Añadir a una lista» (se piden en segundo plano). Sin sesión o sin
/// internet devuelve una lista vacía.
Future<List<DestinoLista>> destinosListasCompartidas(Servicios s) async {
  final se = s.cuenta.sesion;
  if (se == null || se.acceso.isEmpty) return const [];
  final base = ListasCompartidas(se);
  try {
    final todas = await base.misListasCompartidas();
    ListasCompartidasVistas.lista.value = todas;
    return [
      for (final l in todas)
        if (l.puedeAnadir)
          DestinoLista(
            id: 'compartida:${l.id}',
            nombre: l.nombre,
            detalle: '${l.total == 1 ? '1 canción' : '${l.total} canciones'} · de ${l.dueno.visible}',
            etiqueta: 'Compartida',
            agregar: (pistas) => agregarYContar(base, l.id, pistas),
            quitar: (claves) async {
              for (final c in claves) {
                await base.quitar(l.id, c);
              }
            },
          ),
    ];
  } catch (_) {
    return const [];
  }
}

/// Añade a una lista compartida y devuelve las claves que de verdad entraron
/// (las que ya estaban no cuentan), para poder deshacer.
Future<List<String>> agregarYContar(ListasCompartidas base, String listaId, List<Json> pistas) async {
  final candidatas = [for (final i in ListasCompartidas.itemsParaNube(pistas)) '${i['clave']}'];
  if (candidatas.isEmpty) return const [];
  final ya = {for (final p in await base.pistasDeLista(listaId)) p.clave};
  final nuevas = [for (final c in candidatas.toSet()) if (!ya.contains(c)) c];
  final n = await base.agregar(listaId, pistas);
  return n >= nuevas.length ? nuevas : nuevas.take(n).toList();
}
