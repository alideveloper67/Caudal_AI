import 'dart:async';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;
import 'package:just_audio/just_audio.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../nucleo/coleccion.dart' show Json;
import '../../nucleo/grupos.dart';
import '../../nucleo/nube.dart';
import '../../nucleo/vida_app.dart';
import '../comunes.dart';
import '../emojis.dart';
import '../servicios.dart';
import '../tema.dart';
import 'perfil_comun.dart';

/// Grupos para hablar: la pestaña «Grupos» de Mensajes, explorar, crear, entrar con código, la
/// conversación (texto, canciones y notas de voz; sin imágenes ni videos) y la moderación.

Grupos? gruposDe(BuildContext context) {
  final s = Caudal.leer(context).cuenta.sesion;
  return s == null || s.acceso.isEmpty ? null : Grupos(s);
}

String _error(Object e) =>
    e is ErrorNube ? e.mensaje : 'No se pudo conectar. Revisa tu internet y vuelve a probar.';

String _hora(DateTime t) {
  final ahora = DateTime.now();
  final hh = '${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}';
  if (ahora.difference(t).inHours < 20 && ahora.day == t.day) return hh;
  if (ahora.difference(t).inDays < 7) return const ['lun', 'mar', 'mié', 'jue', 'vie', 'sáb', 'dom'][t.weekday - 1];
  return '${t.day}/${t.month}';
}

String duracionNota(int seg) => '${seg ~/ 60}:${(seg % 60).toString().padLeft(2, '0')}';

Widget _avatarGrupo(Grupo g, {double radio = 24}) => CircleAvatar(
      radius: radio,
      backgroundColor: g.privado ? C.superficie3 : C.acento.withValues(alpha: 0.22),
      child: Text(g.inicial, style: TextStyle(fontWeight: FontWeight.w900, fontSize: radio * 0.8, color: C.texto)),
    );

// ============================================================ pestaña «Grupos»

class GruposVista extends StatefulWidget {
  const GruposVista({super.key});

  @override
  State<GruposVista> createState() => _GruposVistaState();
}

class _GruposVistaState extends State<GruposVista> {
  List<Grupo>? _grupos;
  String? _fallo;

  /// Una sola vez, a quien ya tenía cuenta y su perfil privado: «hazlo público para que te encuentren».
  bool _ofrecerPublico = false;
  static const _clavePregunta = 'pregunta_perfil_publico_vista';

  late final Sondeo _sondeo = Sondeo(const Duration(seconds: 10), () async {
    if (mounted) await _cargar();
  });

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _cargar();
      _mirarPerfil();
    });
    _sondeo.iniciar();
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

  Future<void> _mirarPerfil() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      if (prefs.getBool(_clavePregunta) == true || !mounted) return;
      final social = socialDe(context);
      if (social == null) return;
      final p = await social.miPerfilEditable();
      // a un menor no se le ofrece (no puede) y sin fecha de nacimiento la base no lo dejaría
      if (!mounted || p.perfilPublico || p.esMenor || p.fechaNacimiento == null) return;
      setState(() => _ofrecerPublico = true);
    } catch (_) {}
  }

  Future<void> _responderPublico(bool si) async {
    final s = Caudal.leer(context);
    final social = socialDe(context);
    setState(() => _ofrecerPublico = false);
    try {
      (await SharedPreferences.getInstance()).setBool(_clavePregunta, true);
    } catch (_) {}
    if (!si || social == null) return;
    try {
      final p = await social.miPerfilEditable();
      final quedo = await social.guardarPerfil(p.copiar(perfilPublico: true));
      s.avisar(quedo.perfilPublico
          ? 'Listo: tu perfil es público. Puedes cerrarlo cuando quieras en Editar perfil › Privacidad.'
          : 'Tu perfil sigue privado: los perfiles públicos son solo para mayores de 18 años.');
    } catch (e) {
      s.avisar(_error(e));
    }
  }

  Future<void> _cargar() async {
    final g = gruposDe(context);
    if (g == null) {
      if (mounted) setState(() => _fallo = 'Los grupos necesitan tu cuenta y conexión a internet.');
      return;
    }
    try {
      final l = await g.misGrupos();
      if (mounted) setState(() {
        _grupos = l;
        _fallo = null;
      });
    } catch (e) {
      if (mounted && _grupos == null) setState(() => _fallo = _error(e));
    }
  }

  Future<void> _abrir(Grupo g) async {
    await Navigator.of(context).push(MaterialPageRoute(builder: (_) => GrupoPagina(grupo: g)));
    _cargar();
  }

  Future<void> _crear() async {
    final g = await hojaCrearGrupo(context);
    if (g != null && mounted) _abrir(g);
  }

  Future<void> _codigo() async {
    final g = await hojaUnirseConCodigo(context);
    if (g != null && mounted) _abrir(g);
  }

  Future<void> _explorar() async {
    await Navigator.of(context).push(MaterialPageRoute(builder: (_) => const ExplorarGruposPagina()));
    _cargar();
  }

  @override
  Widget build(BuildContext context) {
    final botones = Padding(
      padding: const EdgeInsets.fromLTRB(Esp.m, Esp.m, Esp.m, Esp.s),
      child: Wrap(spacing: 8, runSpacing: 8, children: [
        FilledButton.icon(onPressed: _crear, icon: const Icon(Icons.add_rounded), label: const Text('Crear grupo')),
        OutlinedButton.icon(onPressed: _explorar, icon: const Icon(Icons.travel_explore_rounded), label: const Text('Explorar')),
        OutlinedButton.icon(onPressed: _codigo, icon: const Icon(Icons.key_rounded), label: const Text('Tengo un código')),
      ]),
    );
    final pregunta = !_ofrecerPublico
        ? const SizedBox.shrink()
        : Card(
            margin: const EdgeInsets.fromLTRB(Esp.m, Esp.s, Esp.m, 0),
            child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 14, 16, 8),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                const Text('¿Hacemos público tu perfil?', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
                const SizedBox(height: 4),
                const Text('Así la gente de los grupos puede ver tu perfil y tu música. Ahora los perfiles nuevos vienen '
                    'públicos; el tuyo sigue privado hasta que digas.', style: estiloSecundario),
                const SizedBox(height: 6),
                // en pantallas angostas los botones bajan de línea en vez de salirse
                Wrap(alignment: WrapAlignment.end, spacing: 8, runSpacing: 4, children: [
                  TextButton(onPressed: () => _responderPublico(false), child: const Text('Dejarlo privado')),
                  FilledButton(onPressed: () => _responderPublico(true), child: const Text('Hacerlo público')),
                ]),
              ]),
            ),
          );
    final l = _grupos;
    if (l == null) {
      return ListView(children: [
        pregunta,
        botones,
        Padding(
          padding: const EdgeInsets.all(32),
          child: _fallo == null
              ? const Center(child: CircularProgressIndicator())
              : Text(_fallo!, textAlign: TextAlign.center, style: estiloSecundario),
        ),
      ]);
    }
    return RefreshIndicator(
      onRefresh: _cargar,
      child: ListView(children: [
        pregunta,
        botones,
        if (l.isEmpty)
          const Padding(
            padding: EdgeInsets.all(32),
            child: Text('Aún no estás en ningún grupo.\nExplora los grupos abiertos o crea el tuyo para hablar de música.',
                textAlign: TextAlign.center, style: estiloSecundario),
          ),
        for (final g in l)
          ListTile(
            leading: _avatarGrupo(g),
            title: Row(children: [
              Flexible(child: Text(g.nombre, maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontWeight: FontWeight.w800))),
              if (g.privado) ...[const SizedBox(width: 4), Icon(Icons.lock_rounded, size: 14, color: C.texto3)],
            ]),
            subtitle: Text(g.ultimoTexto.isEmpty ? '${g.miembros} ${g.miembros == 1 ? 'persona' : 'personas'}' : g.ultimoTexto,
                maxLines: 1, overflow: TextOverflow.ellipsis, style: estiloSecundario),
            trailing: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.end, children: [
              if (g.ultimo != null) Text(_hora(g.ultimo!), style: estiloDetalle),
              if (g.sinLeer > 0)
                Container(
                  margin: const EdgeInsets.only(top: 4),
                  padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                  decoration: BoxDecoration(color: C.acento, borderRadius: BorderRadius.circular(10)),
                  child: Text(g.sinLeer > 99 ? '99+' : '${g.sinLeer}',
                      style: TextStyle(color: C.acentoTexto, fontSize: 11.5, fontWeight: FontWeight.w800)),
                ),
            ]),
            onTap: () => _abrir(g),
          ),
        const SizedBox(height: 90),
      ]),
    );
  }
}

// ============================================================ crear y entrar con código

Future<Grupo?> hojaCrearGrupo(BuildContext context) async {
  final grupos = gruposDe(context);
  final s = Caudal.leer(context);
  if (grupos == null) {
    s.avisar('Para crear un grupo necesitas tu cuenta y conexión a internet.');
    return null;
  }
  final nombre = TextEditingController();
  final descripcion = TextEditingController();
  var privado = false;
  String? fallo;
  var creando = false;
  return showModalBottomSheet<Grupo>(
    context: context,
    isScrollControlled: true,
    useRootNavigator: true,
    builder: (ctx) => StatefulBuilder(
      builder: (ctx, poner) => Padding(
        padding: EdgeInsets.fromLTRB(20, 18, 20, MediaQuery.viewInsetsOf(ctx).bottom + 20),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          const Text('Crear un grupo', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w900)),
          const SizedBox(height: 12),
          TextField(
            controller: nombre,
            maxLength: 50,
            autofocus: true,
            textCapitalization: TextCapitalization.sentences,
            decoration: const InputDecoration(labelText: 'Nombre', hintText: 'Ej.: Reggaetón de Lima'),
          ),
          TextField(
            controller: descripcion,
            maxLength: 300,
            maxLines: 3,
            minLines: 1,
            textCapitalization: TextCapitalization.sentences,
            decoration: const InputDecoration(labelText: 'De qué va (opcional)'),
          ),
          const SizedBox(height: 4),
          SegmentedButton<bool>(
            segments: const [
              ButtonSegment(value: false, icon: Icon(Icons.public_rounded), label: Text('Abierto')),
              ButtonSegment(value: true, icon: Icon(Icons.lock_rounded), label: Text('Privado')),
            ],
            selected: {privado},
            onSelectionChanged: (v) => poner(() => privado = v.first),
          ),
          const SizedBox(height: 8),
          Text(
            privado
                ? 'Solo entra quien tenga el código del grupo. Te lo damos al crearlo para que lo compartas.'
                : 'Cualquiera con cuenta en Caudal lo encuentra en «Explorar» y puede entrar.',
            style: estiloSecundario,
          ),
          const SizedBox(height: 6),
          Text('En los grupos se comparten mensajes, canciones y notas de voz. No se pueden enviar imágenes ni videos.',
              style: estiloDetalle),
          if (fallo != null) ...[
            const SizedBox(height: 8),
            Text(fallo!, style: TextStyle(color: Colors.red.shade300, fontWeight: FontWeight.w700)),
          ],
          const SizedBox(height: 14),
          FilledButton(
            onPressed: creando
                ? null
                : () async {
                    poner(() {
                      creando = true;
                      fallo = null;
                    });
                    try {
                      final g = await grupos.crear(nombre.text, descripcion: descripcion.text, privado: privado);
                      if (ctx.mounted) Navigator.of(ctx).pop(g);
                    } catch (e) {
                      poner(() {
                        creando = false;
                        fallo = _error(e);
                      });
                    }
                  },
            child: Text(creando ? 'Creando…' : 'Crear'),
          ),
        ]),
      ),
    ),
  );
}

Future<Grupo?> hojaUnirseConCodigo(BuildContext context) async {
  final grupos = gruposDe(context);
  final s = Caudal.leer(context);
  if (grupos == null) {
    s.avisar('Para entrar a un grupo necesitas tu cuenta y conexión a internet.');
    return null;
  }
  final campo = TextEditingController();
  String? fallo;
  var entrando = false;
  return showModalBottomSheet<Grupo>(
    context: context,
    isScrollControlled: true,
    useRootNavigator: true,
    builder: (ctx) => StatefulBuilder(
      builder: (ctx, poner) => Padding(
        padding: EdgeInsets.fromLTRB(20, 18, 20, MediaQuery.viewInsetsOf(ctx).bottom + 20),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          const Text('Entrar con un código', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w900)),
          const SizedBox(height: 6),
          const Text('Pídele el código del grupo privado a alguien que ya esté dentro.', style: estiloSecundario),
          const SizedBox(height: 10),
          TextField(
            controller: campo,
            autofocus: true,
            textCapitalization: TextCapitalization.characters,
            decoration: const InputDecoration(labelText: 'Código', hintText: 'ABCD-2345'),
          ),
          if (fallo != null) ...[
            const SizedBox(height: 8),
            Text(fallo!, style: TextStyle(color: Colors.red.shade300, fontWeight: FontWeight.w700)),
          ],
          const SizedBox(height: 14),
          FilledButton(
            onPressed: entrando
                ? null
                : () async {
                    if (Grupos.limpiarCodigo(campo.text).length < 6) {
                      poner(() => fallo = 'Escribe el código completo (8 letras y números).');
                      return;
                    }
                    poner(() {
                      entrando = true;
                      fallo = null;
                    });
                    try {
                      final g = await grupos.unirseConCodigo(campo.text);
                      if (ctx.mounted) Navigator.of(ctx).pop(g);
                    } catch (e) {
                      poner(() {
                        entrando = false;
                        fallo = _error(e);
                      });
                    }
                  },
            child: Text(entrando ? 'Entrando…' : 'Entrar'),
          ),
        ]),
      ),
    ),
  );
}

// ============================================================ explorar

class ExplorarGruposPagina extends StatefulWidget {
  const ExplorarGruposPagina({super.key});

  @override
  State<ExplorarGruposPagina> createState() => _ExplorarGruposPaginaState();
}

class _ExplorarGruposPaginaState extends State<ExplorarGruposPagina> {
  final _busqueda = TextEditingController();
  List<Grupo>? _grupos;
  String? _fallo;
  Timer? _espera;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _buscar());
  }

  @override
  void dispose() {
    _espera?.cancel();
    _busqueda.dispose();
    super.dispose();
  }

  Future<void> _buscar() async {
    final g = gruposDe(context);
    if (g == null) {
      setState(() => _fallo = 'Explorar grupos necesita tu cuenta y conexión a internet.');
      return;
    }
    try {
      final l = await g.explorar(busqueda: _busqueda.text);
      if (mounted) setState(() {
        _grupos = l;
        _fallo = null;
      });
    } catch (e) {
      if (mounted) setState(() => _fallo = _error(e));
    }
  }

  Future<void> _entrar(Grupo g) async {
    final grupos = gruposDe(context);
    final s = Caudal.leer(context);
    if (grupos == null) return;
    var abierto = g;
    if (!g.dentro) {
      try {
        abierto = await grupos.unirse(g.id);
      } catch (e) {
        s.avisar(_error(e));
        return;
      }
    }
    if (!mounted) return;
    await Navigator.of(context).pushReplacement(MaterialPageRoute(builder: (_) => GrupoPagina(grupo: abierto)));
  }

  @override
  Widget build(BuildContext context) {
    final l = _grupos;
    return Scaffold(
      appBar: AppBar(title: const Text('Explorar grupos', style: estiloTituloBarra)),
      body: Column(children: [
        Padding(
          padding: const EdgeInsets.all(Esp.m),
          child: TextField(
            controller: _busqueda,
            decoration: InputDecoration(
              hintText: 'Busca por artista, género, ciudad…',
              prefixIcon: const Icon(Icons.search_rounded),
              filled: true,
              fillColor: C.superficie2,
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(22), borderSide: BorderSide.none),
            ),
            onChanged: (_) {
              _espera?.cancel();
              _espera = Timer(const Duration(milliseconds: 350), _buscar);
            },
          ),
        ),
        Expanded(
          child: l == null
              ? Center(
                  child: _fallo == null
                      ? const CircularProgressIndicator()
                      : Padding(padding: const EdgeInsets.all(32), child: Text(_fallo!, textAlign: TextAlign.center, style: estiloSecundario)))
              : l.isEmpty
                  ? Center(
                      child: Padding(
                        padding: const EdgeInsets.all(32),
                        child: Text(
                            _busqueda.text.trim().isEmpty
                                ? 'Todavía no hay grupos abiertos. ¡Crea el primero!'
                                : 'No hay grupos con «${_busqueda.text.trim()}». Puedes crearlo tú.',
                            textAlign: TextAlign.center,
                            style: estiloSecundario),
                      ),
                    )
                  : ListView.builder(
                      itemCount: l.length,
                      itemBuilder: (_, i) {
                        final g = l[i];
                        return ListTile(
                          leading: _avatarGrupo(g),
                          title: Text(g.nombre, style: const TextStyle(fontWeight: FontWeight.w800)),
                          subtitle: Text(
                              [
                                '${g.miembros} ${g.miembros == 1 ? 'persona' : 'personas'}',
                                if (g.descripcion.isNotEmpty) g.descripcion,
                              ].join(' · '),
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                              style: estiloSecundario),
                          trailing: g.dentro
                              ? const Text('Ya estás', style: estiloDetalle)
                              : FilledButton.tonal(onPressed: () => _entrar(g), child: const Text('Unirme')),
                          onTap: () => _entrar(g),
                        );
                      },
                    ),
        ),
      ]),
    );
  }
}

// ============================================================ la conversación

/// Graba notas de voz: AAC en el teléfono, Opus en el navegador.
class GrabadorNota {
  final _rec = AudioRecorder();
  String? _ruta;
  DateTime? _desde;

  Future<bool> permiso() => _rec.hasPermission();

  Future<void> empezar() async {
    var ruta = '';
    if (!kIsWeb) {
      final dir = await getTemporaryDirectory();
      ruta = p.join(dir.path, 'nota_${DateTime.now().millisecondsSinceEpoch}.m4a');
    }
    _ruta = ruta;
    _desde = DateTime.now();
    await _rec.start(
      kIsWeb
          ? const RecordConfig(encoder: AudioEncoder.opus, numChannels: 1)
          : const RecordConfig(encoder: AudioEncoder.aacLc, bitRate: 64000, sampleRate: 44100, numChannels: 1),
      path: ruta,
    );
  }

  int get segundos => _desde == null ? 0 : DateTime.now().difference(_desde!).inSeconds;

  /// (bytes, tipo, segundos) o null si no se grabó nada.
  Future<(Uint8List, String, int)?> parar() async {
    final seg = segundos;
    final salida = await _rec.stop();
    _desde = null;
    if (salida == null || salida.isEmpty) return null;
    if (kIsWeb) {
      final r = await http.get(Uri.parse(salida));
      return r.bodyBytes.isEmpty ? null : (r.bodyBytes, 'audio/webm', seg);
    }
    final f = File(salida);
    if (!await f.exists()) return null;
    final bytes = await f.readAsBytes();
    try {
      await f.delete();
    } catch (_) {}
    return bytes.isEmpty ? null : (bytes, 'audio/mp4', seg);
  }

  Future<void> cancelar() async {
    try {
      if (await _rec.isRecording()) await _rec.stop();
    } catch (_) {}
    _desde = null;
    final r = _ruta;
    if (r != null && r.isNotEmpty && !kIsWeb) {
      try {
        final f = File(r);
        if (await f.exists()) await f.delete();
      } catch (_) {}
    }
  }

  Future<void> soltar() async {
    await cancelar();
    await _rec.dispose();
  }
}

class _Pendiente {
  _Pendiente(this.clave, {this.texto = '', this.pista, this.bytes, this.tipo = '', this.segundos = 0});
  final int clave;
  final String texto;
  final Json? pista;
  final Uint8List? bytes; // nota de voz por subir
  final String tipo;
  final int segundos;
  String? rutaSubida;
  final DateTime creado = DateTime.now();
  String? fallo;
}

class GrupoPagina extends StatefulWidget {
  const GrupoPagina({super.key, required this.grupo});
  final Grupo grupo;

  @override
  State<GrupoPagina> createState() => _GrupoPaginaState();
}

class _GrupoPaginaState extends State<GrupoPagina> {
  final _campo = TextEditingController();
  final _scroll = ScrollController();
  late Grupo _grupo = widget.grupo;
  List<MensajeGrupo> _mensajes = [];
  List<MensajeGrupo> _fijados = [];
  final List<_Pendiente> _pendientes = [];
  int _siguiente = 0;
  int _enCamino = 0;
  bool _cargado = false;
  bool _hayMasViejos = true;
  bool _cargandoViejos = false;
  String? _errorCarga;
  Grupos? _api;
  GrabadorNota? _grabador;
  Timer? _relojGrabacion;
  bool _grabando = false;

  late final Sondeo _sondeo = Sondeo(const Duration(seconds: 3), () async {
    if (mounted && _api != null) await _nuevos();
  });

  @override
  void initState() {
    super.initState();
    _campo.addListener(() => setState(() {}));
    _scroll.addListener(() {
      if (_scroll.hasClients && _scroll.position.pixels > _scroll.position.maxScrollExtent - 300) _viejos();
    });
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _api = gruposDe(context);
      _cargar();
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
    _relojGrabacion?.cancel();
    _grabador?.soltar();
    _campo.dispose();
    _scroll.dispose();
    super.dispose();
  }

  void _sumar(Iterable<MensajeGrupo> llegan) {
    final porId = {for (final m in _mensajes) m.id: m};
    for (final m in llegan) {
      porId[m.id] = m;
    }
    _mensajes = porId.values.toList()..sort((a, b) => a.id.compareTo(b.id));
  }

  Future<void> _cargar() async {
    final api = _api;
    if (api == null) {
      setState(() {
        _cargado = true;
        _errorCarga = 'El grupo necesita tu cuenta y conexión a internet.';
      });
      return;
    }
    setState(() => _errorCarga = null);
    try {
      final l = await api.mensajes(_grupo.id);
      final fij = await api.fijados(_grupo.id).catchError((_) => <MensajeGrupo>[]);
      if (!mounted) return;
      setState(() {
        _mensajes = [];
        _sumar(l);
        _fijados = fij;
        _hayMasViejos = l.length >= 50;
        _cargado = true;
      });
      api.leido(_grupo.id);
    } catch (e) {
      if (mounted) {
        setState(() {
          _cargado = true;
          _errorCarga = _error(e);
        });
      }
    }
  }

  Future<void> _viejos() async {
    final api = _api;
    if (api == null || !_hayMasViejos || _cargandoViejos || _mensajes.isEmpty) return;
    _cargandoViejos = true;
    try {
      final l = await api.mensajes(_grupo.id, antes: _mensajes.first.id);
      if (mounted) setState(() {
        _sumar(l);
        _hayMasViejos = l.length >= 50;
      });
    } catch (_) {
    } finally {
      _cargandoViejos = false;
    }
  }

  Future<void> _nuevos() async {
    final api = _api;
    if (api == null || !_cargado || _enCamino > 0) return;
    if (_errorCarga != null) return _cargar();
    try {
      final desde = _mensajes.isEmpty ? 0 : _mensajes.last.id;
      final l = await api.nuevos(_grupo.id, desde);
      if (!mounted || l.isEmpty) return;
      setState(() => _sumar(l));
      api.leido(_grupo.id);
    } catch (_) {}
  }

  void _enviar({Json? pista}) {
    final texto = pista == null ? _campo.text.trim() : '';
    if (_api == null || (texto.isEmpty && pista == null)) return;
    if (pista == null) _campo.clear();
    _poner(_Pendiente(++_siguiente, texto: texto, pista: pista));
  }

  void _poner(_Pendiente p) {
    setState(() => _pendientes.add(p));
    if (_scroll.hasClients) _scroll.animateTo(0, duration: const Duration(milliseconds: 200), curve: Curves.easeOut);
    _mandar(p);
  }

  Future<void> _mandar(_Pendiente p) async {
    final api = _api;
    if (api == null) return;
    setState(() => p.fallo = null);
    _enCamino++;
    try {
      if (p.bytes != null && p.rutaSubida == null) {
        p.rutaSubida = await api.subirAudio(_grupo.id, p.bytes!, p.tipo);
      }
      final m = await api.enviar(_grupo.id,
          texto: p.texto, pista: p.pista, audio: p.rutaSubida, audioSeg: p.segundos);
      if (!mounted) return;
      setState(() {
        _pendientes.remove(p);
        _sumar([m]);
      });
    } catch (e) {
      if (mounted) setState(() => p.fallo = _error(e));
    } finally {
      _enCamino = (_enCamino - 1).clamp(0, 1 << 30);
    }
  }

  void _enviarLoQueSuena() {
    final s = Caudal.leer(context);
    final pista = s.reproductor.actual;
    if (pista == null) {
      s.avisar('Ahora no suena nada. Pon una canción y vuelve a tocar 🎵');
      return;
    }
    if ('${pista['video_id'] ?? ''}'.isEmpty) {
      s.avisar('Esa canción es un archivo del teléfono: solo se pueden enviar canciones de YouTube Music.');
      return;
    }
    _enviar(pista: pista);
  }

  // ---------------------------------------------------------------- notas de voz
  Future<void> _empezarGrabar() async {
    final s = Caudal.leer(context);
    final g = _grabador ??= GrabadorNota();
    if (!await g.permiso()) {
      s.avisar('Para grabar notas de voz, Caudal necesita permiso para usar el micrófono.');
      return;
    }
    try {
      await g.empezar();
    } catch (_) {
      s.avisar('No se pudo usar el micrófono.');
      return;
    }
    if (!mounted) return;
    setState(() => _grabando = true);
    _relojGrabacion = Timer.periodic(const Duration(milliseconds: 500), (_) {
      if (!mounted) return;
      if (g.segundos >= Grupos.maxSegundosAudio) {
        _terminarGrabar();
      } else {
        setState(() {});
      }
    });
  }

  Future<void> _terminarGrabar({bool cancelar = false}) async {
    _relojGrabacion?.cancel();
    final g = _grabador;
    if (g == null) return;
    setState(() => _grabando = false);
    if (cancelar) {
      await g.cancelar();
      return;
    }
    final r = await g.parar();
    if (r == null || !mounted) return;
    final (bytes, tipo, seg) = r;
    if (seg < 1) {
      Caudal.leer(context).avisar('Mantén pulsado un poco más para grabar.');
      return;
    }
    _poner(_Pendiente(++_siguiente, bytes: bytes, tipo: tipo, segundos: seg.clamp(1, Grupos.maxSegundosAudio)));
  }

  // ---------------------------------------------------------------- acciones sobre un mensaje
  Future<void> _opciones(MensajeGrupo m) async {
    final api = _api;
    final s = Caudal.leer(context);
    if (api == null) return;
    final modero = _grupo.modero;
    final accion = await showModalBottomSheet<String>(
      context: context,
      useRootNavigator: true,
      builder: (ctx) => SafeArea(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          if (m.texto.isNotEmpty)
            ListTile(leading: const Icon(Icons.copy_rounded), title: const Text('Copiar texto'),
                onTap: () => Navigator.of(ctx).pop('copiar')),
          if (m.autor.usuario.isNotEmpty)
            ListTile(leading: const Icon(Icons.person_rounded), title: Text('Ver perfil de ${m.autor.visible}'),
                onTap: () => Navigator.of(ctx).pop('perfil')),
          if (modero)
            ListTile(
                leading: Icon(m.fijado ? Icons.push_pin_outlined : Icons.push_pin_rounded),
                title: Text(m.fijado ? 'Quitar de fijados' : 'Fijar arriba'),
                onTap: () => Navigator.of(ctx).pop(m.fijado ? 'desfijar' : 'fijar')),
          if (modero && !m.mio)
            ListTile(
                leading: Icon(m.oculto ? Icons.visibility_rounded : Icons.visibility_off_rounded),
                title: Text(m.oculto ? 'Volver a mostrar' : 'Ocultar'),
                onTap: () => Navigator.of(ctx).pop(m.oculto ? 'mostrar' : 'ocultar')),
          if (!m.mio)
            ListTile(leading: const Icon(Icons.flag_rounded), title: const Text('Reportar'),
                onTap: () => Navigator.of(ctx).pop('reportar')),
          if (m.mio || modero)
            ListTile(
                leading: Icon(Icons.delete_outline_rounded, color: Colors.red.shade300),
                title: Text('Borrar', style: TextStyle(color: Colors.red.shade300)),
                onTap: () => Navigator.of(ctx).pop('borrar')),
        ]),
      ),
    );
    if (accion == null || !mounted) return;
    try {
      switch (accion) {
        case 'copiar':
          await Clipboard.setData(ClipboardData(text: m.texto));
          s.avisar('Texto copiado');
        case 'perfil':
          await abrirPerfil(context, m.autor.usuario);
        case 'reportar':
          final motivo = await _pedirMotivo();
          if (motivo == null) return;
          await api.reportar(m.id, motivo: motivo);
          s.avisar('Gracias. Quien modera el grupo lo revisará; con varios reportes se oculta solo.');
        case 'borrar':
          await api.accion(m.id, 'borrar');
          setState(() => _mensajes.removeWhere((x) => x.id == m.id));
        default:
          await api.accion(m.id, accion);
          await _cargar();
      }
    } catch (e) {
      s.avisar(_error(e));
    }
  }

  Future<String?> _pedirMotivo() async {
    return showModalBottomSheet<String>(
      context: context,
      useRootNavigator: true,
      builder: (ctx) => SafeArea(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          const Padding(
            padding: EdgeInsets.fromLTRB(20, 16, 20, 6),
            child: Text('¿Por qué lo reportas?', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
          ),
          for (final m in const ['Insulta o acosa', 'Contenido sexual', 'Spam o estafa', 'Pone en peligro a un menor', 'Otra cosa'])
            ListTile(title: Text(m), onTap: () => Navigator.of(ctx).pop(m)),
        ]),
      ),
    );
  }

  Future<void> _info() async {
    final r = await Navigator.of(context).push<Grupo?>(MaterialPageRoute(builder: (_) => GrupoInfoPagina(grupo: _grupo)));
    if (!mounted) return;
    if (r == null) {
      // se salió o lo borró
      final sigue = await _api?.ver(_grupo.id).catchError((_) => null);
      if (!mounted) return;
      if (sigue == null || !sigue.dentro) {
        Navigator.of(context).pop();
        return;
      }
      setState(() => _grupo = sigue);
    } else {
      setState(() => _grupo = r);
    }
    _cargar();
  }

  @override
  Widget build(BuildContext context) {
    final s = Caudal.of(context);
    final total = _pendientes.length + _mensajes.length;
    Widget lista;
    if (!_cargado) {
      lista = const Center(child: CircularProgressIndicator());
    } else if (total == 0 && _errorCarga != null) {
      lista = Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Text(_errorCarga!, textAlign: TextAlign.center, style: estiloSecundario),
            const SizedBox(height: 12),
            OutlinedButton.icon(onPressed: _cargar, icon: const Icon(Icons.refresh_rounded), label: const Text('Reintentar')),
          ]),
        ),
      );
    } else if (total == 0) {
      lista = Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Text('Aquí empieza «${_grupo.nombre}».\nSaluda, comparte lo que estás escuchando 🎵 o manda una nota de voz 🎤',
              textAlign: TextAlign.center, style: estiloSecundario),
        ),
      );
    } else {
      lista = ListView.builder(
        controller: _scroll,
        reverse: true,
        padding: const EdgeInsets.symmetric(horizontal: Esp.m, vertical: Esp.m),
        itemCount: total,
        itemBuilder: (_, i) {
          if (i < _pendientes.length) {
            final p = _pendientes[_pendientes.length - 1 - i];
            return _BurbujaGrupo(
              mensaje: MensajeGrupo(id: -p.clave, autor: const Autor('', '', 'Tú'), texto: p.texto, pista: p.pista,
                  audio: p.bytes != null ? '' : null, audioSeg: p.segundos, mio: true, creado: p.creado),
              api: _api,
              estado: p.fallo == null ? 'Enviando…' : '⚠ ${p.fallo} · Toca para reintentar',
              alTocarEstado: p.fallo == null ? null : () => _mandar(p),
            );
          }
          final idx = _mensajes.length - 1 - (i - _pendientes.length);
          final m = _mensajes[idx];
          // el nombre solo cuando cambia quien escribe
          final anterior = idx > 0 ? _mensajes[idx - 1] : null;
          final conNombre = !m.mio && (anterior == null || anterior.autor.id != m.autor.id);
          return _BurbujaGrupo(mensaje: m, api: _api, conNombre: conNombre, alMantener: () => _opciones(m));
        },
      );
    }
    final g = _grabador;
    return Scaffold(
      appBar: AppBar(
        titleSpacing: 0,
        title: InkWell(
          onTap: _info,
          child: Row(children: [
            _avatarGrupo(_grupo, radio: 17),
            const SizedBox(width: 10),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(_grupo.nombre, maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800)),
                Text('${_grupo.privado ? 'Privado' : 'Abierto'} · ${_grupo.miembros} ${_grupo.miembros == 1 ? 'persona' : 'personas'}',
                    style: estiloDetalle),
              ]),
            ),
          ]),
        ),
        actions: [IconButton(tooltip: 'Info del grupo', icon: const Icon(Icons.info_outline_rounded), onPressed: _info)],
      ),
      body: Column(children: [
        if (_fijados.isNotEmpty)
          Material(
            color: C.superficie2,
            child: InkWell(
              onTap: () => _opciones(_fijados.last),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: Esp.m, vertical: 8),
                child: Row(children: [
                  Icon(Icons.push_pin_rounded, size: 16, color: C.acento),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                        _fijados.last.texto.isNotEmpty
                            ? _fijados.last.texto
                            : _fijados.last.pista != null
                                ? '♪ ${_fijados.last.pista!['titulo'] ?? 'Una canción'}'
                                : '🎤 Nota de voz',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontWeight: FontWeight.w700)),
                  ),
                  if (_fijados.length > 1) Text('+${_fijados.length - 1}', style: estiloDetalle),
                ]),
              ),
            ),
          ),
        Expanded(child: lista),
        ListenableBuilder(
          listenable: s.reproductor,
          builder: (context, _) {
            final sonando = s.reproductor.actual;
            final enviable = sonando != null && '${sonando['video_id'] ?? ''}'.isNotEmpty;
            final hayTexto = _campo.text.trim().isNotEmpty;
            if (_grupo.cerrado) {
              return SafeArea(
                top: false,
                child: Padding(
                  padding: const EdgeInsets.all(Esp.m),
                  child: Text('La moderación de Caudal cerró este grupo. Ya no se puede escribir.',
                      textAlign: TextAlign.center, style: estiloSecundario),
                ),
              );
            }
            return SafeArea(
              top: false,
              child: Container(
                margin: EdgeInsets.only(bottom: sonando != null ? 74 : 0),
                padding: const EdgeInsets.all(Esp.s),
                decoration: BoxDecoration(color: C.panel, border: Border(top: BorderSide(color: C.borde))),
                child: _grabando
                    ? Row(children: [
                        IconButton(
                          tooltip: 'Cancelar',
                          icon: Icon(Icons.delete_outline_rounded, color: Colors.red.shade300),
                          onPressed: () => _terminarGrabar(cancelar: true),
                        ),
                        const SizedBox(width: 6),
                        Icon(Icons.fiber_manual_record_rounded, color: Colors.red.shade400, size: 14),
                        const SizedBox(width: 6),
                        Expanded(
                          child: Text(
                              'Grabando ${duracionNota(g?.segundos ?? 0)} · máx. ${duracionNota(Grupos.maxSegundosAudio)}',
                              style: const TextStyle(fontWeight: FontWeight.w700)),
                        ),
                        IconButton.filled(
                          tooltip: 'Enviar nota de voz',
                          style: IconButton.styleFrom(backgroundColor: C.acento, foregroundColor: C.acentoTexto),
                          onPressed: () => _terminarGrabar(),
                          icon: const Icon(Icons.send_rounded),
                        ),
                      ])
                    : Row(children: [
                        IconButton(
                          tooltip: enviable ? 'Enviar «${sonando['titulo'] ?? 'lo que suena'}»' : 'Enviar la canción que suena',
                          icon: Icon(Icons.music_note_rounded, color: enviable ? C.acento : C.texto3),
                          onPressed: _enviarLoQueSuena,
                        ),
                        IconButton(
                          tooltip: 'Emojis',
                          visualDensity: VisualDensity.compact,
                          icon: const Icon(Icons.emoji_emotions_outlined),
                          onPressed: () => elegirEmoji(context, (e) => insertarEnCampo(_campo, e)),
                        ),
                        Expanded(
                          child: TextField(
                            controller: _campo,
                            minLines: 1,
                            maxLines: 4,
                            maxLength: 2000,
                            textCapitalization: TextCapitalization.sentences,
                            textInputAction: TextInputAction.send,
                            decoration: InputDecoration(
                              hintText: 'Escribe al grupo',
                              counterText: '',
                              filled: true,
                              fillColor: C.superficie2,
                              isDense: true,
                              contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                              border: OutlineInputBorder(borderRadius: BorderRadius.circular(22), borderSide: BorderSide.none),
                            ),
                            onSubmitted: (_) => _enviar(),
                          ),
                        ),
                        const SizedBox(width: 6),
                        if (hayTexto)
                          IconButton.filled(
                            tooltip: 'Enviar',
                            style: IconButton.styleFrom(backgroundColor: C.acento, foregroundColor: C.acentoTexto),
                            onPressed: () => _enviar(),
                            icon: const Icon(Icons.send_rounded),
                          )
                        else
                          IconButton.filled(
                            tooltip: 'Grabar una nota de voz',
                            style: IconButton.styleFrom(backgroundColor: C.acento, foregroundColor: C.acentoTexto),
                            onPressed: _empezarGrabar,
                            icon: const Icon(Icons.mic_rounded),
                          ),
                      ]),
              ),
            );
          },
        ),
      ]),
    );
  }
}

class _BurbujaGrupo extends StatelessWidget {
  const _BurbujaGrupo({required this.mensaje, this.api, this.conNombre = false, this.estado, this.alTocarEstado, this.alMantener});
  final MensajeGrupo mensaje;
  final Grupos? api;
  final bool conNombre;
  final String? estado;
  final VoidCallback? alTocarEstado;
  final VoidCallback? alMantener;

  @override
  Widget build(BuildContext context) {
    final s = Caudal.of(context);
    final m = mensaje;
    final mio = m.mio;
    final pista = m.pista;
    final ancho = MediaQuery.sizeOf(context).width * 0.78;
    final colorTexto = mio ? C.acentoTexto : C.texto;
    Widget contenido;
    if (m.audio != null) {
      contenido = NotaDeVoz(ruta: m.audio!, segundos: m.audioSeg, api: api, color: colorTexto);
    } else if (pista != null) {
      contenido = GestureDetector(
        onTap: () => s.reproducirPista(context, pista),
        child: SizedBox(
          width: 250,
          child: Row(children: [
            Portada(url: '${pista['miniatura'] ?? ''}', lado: 54, radio: 6),
            const SizedBox(width: 10),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${pista['titulo'] ?? ''}', maxLines: 2, overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontWeight: FontWeight.w800, color: colorTexto)),
                Text('${pista['artista'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontSize: 12.5, color: colorTexto.withValues(alpha: 0.75))),
              ]),
            ),
            Icon(Icons.play_circle_fill_rounded, size: 30, color: mio ? C.acentoTexto : C.acento),
          ]),
        ),
      );
    } else {
      contenido = Text(m.texto, style: TextStyle(fontSize: 15.5, color: colorTexto, height: 1.3));
    }
    final pie = Text(
      estado ?? [if (m.fijado) '📌', if (m.oculto) 'Oculto por reportes ·', _hora(m.creado)].join(' '),
      textAlign: TextAlign.right,
      style: TextStyle(fontSize: 10.5, color: mio ? C.acentoTexto.withValues(alpha: 0.7) : C.texto3,
          fontWeight: alTocarEstado != null ? FontWeight.w700 : FontWeight.w400),
    );
    final burbuja = Container(
      constraints: BoxConstraints(maxWidth: ancho),
      margin: const EdgeInsets.symmetric(vertical: 2),
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 6),
      decoration: BoxDecoration(
        color: mio ? C.acento : C.superficie2,
        borderRadius: BorderRadius.only(
          topLeft: const Radius.circular(18),
          topRight: const Radius.circular(18),
          bottomLeft: Radius.circular(mio ? 18 : 4),
          bottomRight: Radius.circular(mio ? 4 : 18),
        ),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
        if (conNombre)
          Padding(
            padding: const EdgeInsets.only(bottom: 2),
            child: Text(
              m.autor.visible + (m.autor.rol == RolGrupo.dueno ? ' · dueño' : m.autor.rol == RolGrupo.moderador ? ' · modera' : ''),
              style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w800, color: C.acento),
            ),
          ),
        contenido,
        const SizedBox(height: 2),
        Align(
          alignment: Alignment.centerRight,
          child: alTocarEstado != null
              ? InkWell(onTap: alTocarEstado, child: Padding(padding: const EdgeInsets.symmetric(vertical: 2), child: pie))
              : pie,
        ),
      ]),
    );
    return Opacity(
      opacity: (estado != null && alTocarEstado == null) || m.oculto ? 0.6 : 1,
      child: GestureDetector(
        onLongPress: alMantener,
        child: Row(
          mainAxisAlignment: mio ? MainAxisAlignment.end : MainAxisAlignment.start,
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            if (!mio)
              Padding(
                padding: const EdgeInsets.only(right: 6, bottom: 2),
                child: conNombre
                    ? InkWell(
                        borderRadius: BorderRadius.circular(999),
                        onTap: m.autor.usuario.isEmpty ? null : () => abrirPerfil(context, m.autor.usuario),
                        child: AvatarPerfil(nombre: m.autor.visible, fotoUrl: m.autor.fotoUrl, radio: 14),
                      )
                    : const SizedBox(width: 28),
              ),
            Flexible(child: burbuja),
          ],
        ),
      ),
    );
  }
}

/// Una nota de voz: se pide su dirección firmada al tocar (el almacén es privado) y suena con el
/// reproductor del sistema; la música se pausa mientras tanto.
class NotaDeVoz extends StatefulWidget {
  const NotaDeVoz({super.key, required this.ruta, required this.segundos, this.api, this.color});
  final String ruta; // vacía: todavía se está subiendo
  final int segundos;
  final Grupos? api;
  final Color? color;

  @override
  State<NotaDeVoz> createState() => _NotaDeVozState();
}

class _NotaDeVozState extends State<NotaDeVoz> {
  AudioPlayer? _jugador;
  bool _cargando = false;
  bool _sonando = false;
  Duration _pos = Duration.zero;
  final List<StreamSubscription> _subs = [];

  @override
  void dispose() {
    for (final s in _subs) {
      s.cancel();
    }
    _jugador?.dispose();
    super.dispose();
  }

  Future<void> _tocar() async {
    final s = Caudal.leer(context);
    if (widget.ruta.isEmpty || widget.api == null) return;
    var j = _jugador;
    if (j != null) {
      if (_sonando) {
        await j.pause();
      } else {
        if (j.processingState == ProcessingState.completed) await j.seek(Duration.zero);
        await s.reproductor.pausar();
        await j.play();
      }
      return;
    }
    setState(() => _cargando = true);
    try {
      final url = await widget.api!.urlAudio(widget.ruta);
      j = AudioPlayer(handleInterruptions: false, handleAudioSessionActivation: false);
      _subs.add(j.playerStateStream.listen((e) {
        if (!mounted) return;
        setState(() => _sonando = e.playing && e.processingState != ProcessingState.completed);
      }));
      _subs.add(j.positionStream.listen((p) {
        if (mounted) setState(() => _pos = p);
      }));
      await j.setUrl(url);
      _jugador = j;
      await s.reproductor.pausar();
      await j.play();
    } catch (e) {
      s.avisar(e is ErrorNube ? e.mensaje : 'No se pudo oír la nota de voz.');
      await j?.dispose();
    } finally {
      if (mounted) setState(() => _cargando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final color = widget.color ?? C.texto;
    final total = widget.segundos <= 0 ? 1 : widget.segundos;
    final avance = (_pos.inMilliseconds / (total * 1000)).clamp(0.0, 1.0);
    return SizedBox(
      width: 220,
      child: Row(children: [
        SizedBox(
          width: 40,
          height: 40,
          child: _cargando || widget.ruta.isEmpty
              ? Padding(padding: const EdgeInsets.all(10), child: CircularProgressIndicator(strokeWidth: 2.4, color: color))
              : IconButton(
                  padding: EdgeInsets.zero,
                  tooltip: _sonando ? 'Pausar' : 'Oír',
                  icon: Icon(_sonando ? Icons.pause_circle_filled_rounded : Icons.play_circle_fill_rounded, size: 36, color: color),
                  onPressed: _tocar,
                ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(3),
              child: LinearProgressIndicator(value: avance, minHeight: 4,
                  backgroundColor: color.withValues(alpha: 0.25), color: color),
            ),
            const SizedBox(height: 4),
            Text('🎤 ${duracionNota(_sonando || _pos > Duration.zero ? _pos.inSeconds : widget.segundos)}',
                style: TextStyle(fontSize: 12, color: color.withValues(alpha: 0.85))),
          ]),
        ),
      ]),
    );
  }
}

// ============================================================ info del grupo, gente y moderación

class GrupoInfoPagina extends StatefulWidget {
  const GrupoInfoPagina({super.key, required this.grupo});
  final Grupo grupo;

  @override
  State<GrupoInfoPagina> createState() => _GrupoInfoPaginaState();
}

class _GrupoInfoPaginaState extends State<GrupoInfoPagina> {
  late Grupo _grupo = widget.grupo;
  List<MiembroGrupo>? _gente;
  List<(MensajeGrupo, int, List<String>)> _reportados = [];
  Grupos? _api;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _api = gruposDe(context);
      _cargar();
    });
  }

  Future<void> _cargar() async {
    final api = _api;
    if (api == null) return;
    try {
      final g = await api.ver(_grupo.id);
      final gente = await api.miembros(_grupo.id);
      final rep = g != null && g.modero ? await api.reportados(_grupo.id) : <(MensajeGrupo, int, List<String>)>[];
      if (!mounted) return;
      setState(() {
        if (g != null) _grupo = g;
        _gente = gente;
        _reportados = rep;
      });
    } catch (e) {
      if (mounted) Caudal.leer(context).avisar(_error(e));
    }
  }

  Future<void> _hacer(Future<void> Function() f, String hecho) async {
    final s = Caudal.leer(context);
    try {
      await f();
      s.avisar(hecho);
      await _cargar();
    } catch (e) {
      s.avisar(_error(e));
    }
  }

  Future<bool> _confirmar(String titulo, String texto, String si) async =>
      await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: Text(titulo),
          content: Text(texto),
          actions: [
            TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Cancelar')),
            FilledButton(onPressed: () => Navigator.of(ctx).pop(true), child: Text(si)),
          ],
        ),
      ) ??
      false;

  Future<void> _sobrePersona(MiembroGrupo m) async {
    final api = _api;
    if (api == null) return;
    final yo = Caudal.leer(context).cuenta.id;
    final esDueno = _grupo.rol == RolGrupo.dueno;
    final puedo = m.autor.id != yo &&
        m.autor.rol != RolGrupo.dueno &&
        (esDueno || (_grupo.rol == RolGrupo.moderador && m.autor.rol == RolGrupo.miembro));
    final accion = await showModalBottomSheet<String>(
      context: context,
      useRootNavigator: true,
      builder: (ctx) => SafeArea(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          ListTile(leading: const Icon(Icons.person_rounded), title: const Text('Ver perfil'),
              onTap: () => Navigator.of(ctx).pop('perfil')),
          if (esDueno && m.autor.id != yo)
            ListTile(
                leading: const Icon(Icons.shield_rounded),
                title: Text(m.autor.rol == RolGrupo.moderador ? 'Quitar de moderadores' : 'Hacer moderador'),
                onTap: () => Navigator.of(ctx).pop(m.autor.rol == RolGrupo.moderador ? 'quitar_mod' : 'mod')),
          if (esDueno && m.autor.id != yo)
            ListTile(leading: const Icon(Icons.workspace_premium_rounded), title: const Text('Pasarle el grupo'),
                onTap: () => Navigator.of(ctx).pop('dueno')),
          if (puedo && !m.silenciado) ...[
            ListTile(leading: const Icon(Icons.volume_off_rounded), title: const Text('Silenciar 1 hora'),
                onTap: () => Navigator.of(ctx).pop('sil60')),
            ListTile(leading: const Icon(Icons.volume_off_rounded), title: const Text('Silenciar 1 día'),
                onTap: () => Navigator.of(ctx).pop('sil1440')),
          ],
          if (puedo && m.silenciado)
            ListTile(leading: const Icon(Icons.volume_up_rounded), title: const Text('Quitar el silencio'),
                onTap: () => Navigator.of(ctx).pop('sil0')),
          if (puedo)
            ListTile(
                leading: Icon(Icons.person_remove_rounded, color: Colors.red.shade300),
                title: Text('Sacar del grupo', style: TextStyle(color: Colors.red.shade300)),
                onTap: () => Navigator.of(ctx).pop('expulsar')),
        ]),
      ),
    );
    if (accion == null || !mounted) return;
    final g = _grupo.id, u = m.autor.id, n = m.autor.visible;
    switch (accion) {
      case 'perfil':
        await abrirPerfil(context, m.autor.usuario);
      case 'mod':
        await _hacer(() => api.ponerRol(g, u, moderador: true), '$n ahora modera el grupo');
      case 'quitar_mod':
        await _hacer(() => api.ponerRol(g, u, moderador: false), '$n ya no modera el grupo');
      case 'dueno':
        if (await _confirmar('¿Pasarle el grupo a $n?', '$n será quien lo administre. Tú quedarás como moderador.', 'Pasar')) {
          await _hacer(() => api.pasarDueno(g, u), 'Ahora el grupo es de $n');
        }
      case 'expulsar':
        if (await _confirmar('¿Sacar a $n?', '$n saldrá del grupo y no podrá volver a entrar.', 'Sacar')) {
          await _hacer(() => api.expulsar(g, u), '$n ya no está en el grupo');
        }
      default:
        final min = int.parse(accion.substring(3));
        await _hacer(() => api.silenciar(g, u, min), min == 0 ? '$n puede volver a escribir' : '$n no podrá escribir por un rato');
    }
  }

  Future<void> _editar() async {
    final api = _api;
    if (api == null) return;
    final nombre = TextEditingController(text: _grupo.nombre);
    final desc = TextEditingController(text: _grupo.descripcion);
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Editar el grupo'),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          TextField(controller: nombre, maxLength: 50, decoration: const InputDecoration(labelText: 'Nombre')),
          TextField(controller: desc, maxLength: 300, maxLines: 3, minLines: 1,
              decoration: const InputDecoration(labelText: 'De qué va')),
        ]),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Cancelar')),
          FilledButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Guardar')),
        ],
      ),
    );
    if (ok == true) await _hacer(() => api.editar(_grupo.id, nombre.text, desc.text), 'Grupo actualizado');
  }

  @override
  Widget build(BuildContext context) {
    final api = _api;
    final gente = _gente;
    final esDueno = _grupo.rol == RolGrupo.dueno;
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (hecho, _) {
        if (!hecho) Navigator.of(context).pop(_grupo);
      },
      child: Scaffold(
        appBar: AppBar(title: const Text('Info del grupo', style: estiloTituloBarra)),
        body: RefreshIndicator(
          onRefresh: _cargar,
          child: ListView(padding: const EdgeInsets.only(bottom: 100), children: [
            const SizedBox(height: 16),
            Center(child: _avatarGrupo(_grupo, radio: 40)),
            const SizedBox(height: 10),
            Text(_grupo.nombre, textAlign: TextAlign.center, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w900)),
            Text('${_grupo.privado ? 'Grupo privado' : 'Grupo abierto'} · ${_grupo.miembros} ${_grupo.miembros == 1 ? 'persona' : 'personas'}',
                textAlign: TextAlign.center, style: estiloSecundario),
            if (_grupo.descripcion.isNotEmpty)
              Padding(
                padding: const EdgeInsets.fromLTRB(24, 10, 24, 0),
                child: Text(_grupo.descripcion, textAlign: TextAlign.center),
              ),
            if (_grupo.privado && _grupo.codigo != null)
              Card(
                margin: const EdgeInsets.fromLTRB(Esp.m, 16, Esp.m, 0),
                child: ListTile(
                  leading: const Icon(Icons.key_rounded),
                  title: Text(_grupo.codigo!, style: const TextStyle(fontWeight: FontWeight.w900, letterSpacing: 2, fontSize: 18)),
                  subtitle: const Text('Comparte este código para invitar', style: estiloSecundario),
                  trailing: Row(mainAxisSize: MainAxisSize.min, children: [
                    IconButton(
                      tooltip: 'Copiar',
                      icon: const Icon(Icons.copy_rounded),
                      onPressed: () async {
                        await Clipboard.setData(ClipboardData(text: _grupo.codigo!));
                        if (context.mounted) Caudal.leer(context).avisar('Código copiado');
                      },
                    ),
                    if (esDueno && api != null)
                      IconButton(
                        tooltip: 'Cambiar el código (el anterior deja de servir)',
                        icon: const Icon(Icons.autorenew_rounded),
                        onPressed: () => _hacer(() => api.cambiarCodigo(_grupo.id), 'Código nuevo listo'),
                      ),
                  ]),
                ),
              ),
            if (_grupo.modero)
              ListTile(leading: const Icon(Icons.edit_rounded), title: const Text('Editar nombre y descripción'), onTap: _editar),
            if (_grupo.modero && _reportados.isNotEmpty) ...[
              Padding(
                padding: const EdgeInsets.fromLTRB(Esp.m, 16, Esp.m, 4),
                child: Text('Reportado (${_reportados.length})', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
              ),
              for (final (m, n, motivos) in _reportados)
                ListTile(
                  leading: Icon(m.oculto ? Icons.visibility_off_rounded : Icons.flag_rounded, color: Colors.orange.shade300),
                  title: Text(
                      m.texto.isNotEmpty ? m.texto : m.audio != null ? '🎤 Nota de voz' : '♪ ${m.pista?['titulo'] ?? 'Una canción'}',
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis),
                  subtitle: Text('${m.autor.visible} · $n ${n == 1 ? 'reporte' : 'reportes'}'
                      '${motivos.isEmpty ? '' : ' · ${motivos.toSet().join(', ')}'}', style: estiloSecundario),
                  trailing: PopupMenuButton<String>(
                    onSelected: (a) => _hacer(() => api!.accion(m.id, a),
                        a == 'mostrar' ? 'Vuelve a verse' : a == 'ocultar' ? 'Mensaje oculto' : 'Mensaje borrado'),
                    itemBuilder: (_) => [
                      if (m.oculto) const PopupMenuItem(value: 'mostrar', child: Text('Está bien: mostrar')),
                      if (!m.oculto) const PopupMenuItem(value: 'ocultar', child: Text('Ocultar')),
                      const PopupMenuItem(value: 'borrar', child: Text('Borrar')),
                    ],
                  ),
                ),
            ],
            Padding(
              padding: const EdgeInsets.fromLTRB(Esp.m, 16, Esp.m, 4),
              child: Text('Personas', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
            ),
            if (gente == null)
              const Padding(padding: EdgeInsets.all(24), child: Center(child: CircularProgressIndicator()))
            else
              for (final m in gente)
                ListTile(
                  leading: AvatarPerfil(nombre: m.autor.visible, fotoUrl: m.autor.fotoUrl, radio: 20),
                  title: Text(m.autor.visible, style: const TextStyle(fontWeight: FontWeight.w700)),
                  subtitle: Text(
                      [
                        '@${m.autor.usuario}',
                        if (m.autor.rol == RolGrupo.dueno) 'dueño',
                        if (m.autor.rol == RolGrupo.moderador) 'modera',
                        if (m.silenciado) 'silenciado',
                      ].join(' · '),
                      style: estiloSecundario),
                  onTap: () => _sobrePersona(m),
                ),
            const Divider(height: 32),
            ListTile(
              leading: Icon(Icons.logout_rounded, color: Colors.red.shade300),
              title: Text('Salir del grupo', style: TextStyle(color: Colors.red.shade300)),
              subtitle: esDueno ? const Text('El grupo pasará a quien modera (o a quien lleve más tiempo).', style: estiloSecundario) : null,
              onTap: api == null
                  ? null
                  : () async {
                      if (!await _confirmar('¿Salir de «${_grupo.nombre}»?', 'Dejarás de ver sus mensajes.', 'Salir')) return;
                      try {
                        await api.salir(_grupo.id);
                        if (context.mounted) Navigator.of(context).pop(null);
                      } catch (e) {
                        if (context.mounted) Caudal.leer(context).avisar(_error(e));
                      }
                    },
            ),
            if (esDueno)
              ListTile(
                leading: Icon(Icons.delete_forever_rounded, color: Colors.red.shade300),
                title: Text('Borrar el grupo', style: TextStyle(color: Colors.red.shade300)),
                subtitle: const Text('Se borran todos sus mensajes y notas de voz, para todos.', style: estiloSecundario),
                onTap: api == null
                    ? null
                    : () async {
                        if (!await _confirmar('¿Borrar «${_grupo.nombre}»?', 'Esto no se puede deshacer.', 'Borrar')) return;
                        try {
                          await api.borrar(_grupo.id);
                          if (context.mounted) Navigator.of(context).pop(null);
                        } catch (e) {
                          if (context.mounted) Caudal.leer(context).avisar(_error(e));
                        }
                      },
              ),
          ]),
        ),
      ),
    );
  }
}
