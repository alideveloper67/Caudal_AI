import 'dart:async';

import 'package:flutter/material.dart';

import '../../nucleo/letras_cache.dart';
import '../../nucleo/mixes.dart';
import '../../nucleo/premium.dart';
import '../../nucleo/premium_letras.dart';
import '../comunes.dart';
import '../servicios.dart';
import '../tema.dart';
import 'candado_donador.dart';

const _mesesCortos = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
const _diasCortos = ['lun', 'mar', 'mié', 'jue', 'vie', 'sáb', 'dom'];

/// «el mar 17 nov, 9:05 p. m.»
String textoCuando(DateTime f, {DateTime? ahora}) {
  final hoy = ahora ?? DateTime.now();
  final d0 = DateTime(hoy.year, hoy.month, hoy.day);
  final d = DateTime(f.year, f.month, f.day);
  final h = f.hour % 12 == 0 ? 12 : f.hour % 12;
  final hora = '$h:${f.minute.toString().padLeft(2, '0')} ${f.hour < 12 ? 'a. m.' : 'p. m.'}';
  final dif = d0.difference(d).inDays;
  final dia = dif == 0
      ? 'hoy'
      : dif == 1
          ? 'ayer'
          : '${_diasCortos[f.weekday - 1]} ${f.day} ${_mesesCortos[f.month - 1]}${f.year != hoy.year ? ' ${f.year}' : ''}';
  return '$dia, $hora';
}

/// «¿Qué canción era?» (donadores): escribes lo que recuerdas («el martes», «ayer Rosalía»,
/// «decía quiero bailar») y aparece lo que escuchaste. Busca en el historial del teléfono por
/// fecha, por título o artista y por letra (solo de las canciones cuya letra ya se vio).
class QueCancionEraPagina extends StatefulWidget {
  const QueCancionEraPagina({super.key, this.historial, this.letras, this.ahora});

  /// Para pruebas: si se da, no se lee la colección.
  final List<Escucha>? historial;
  final Map<String, Map<String, dynamic>>? letras;
  final DateTime? ahora;

  static Future<void> abrir(BuildContext context) =>
      Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => const QueCancionEraPagina()));

  @override
  State<QueCancionEraPagina> createState() => _QueCancionEraPaginaState();
}

class _QueCancionEraPaginaState extends State<QueCancionEraPagina> {
  final _campo = TextEditingController();
  Timer? _espera;
  List<Escucha>? _historial;
  Map<String, Map<String, dynamic>> _letras = const {};
  String? _error;
  ResultadoHistorial? _resultado;

  static const _atajos = [
    ('Ayer', 'ayer'),
    ('Anoche', 'anoche'),
    ('Esta semana', 'esta semana'),
    ('La semana pasada', 'la semana pasada'),
    ('El mes pasado', 'el mes pasado'),
  ];

  DateTime get _hoy => widget.ahora ?? DateTime.now();

  @override
  void initState() {
    super.initState();
    if (widget.historial != null) {
      _historial = widget.historial;
      _letras = widget.letras ?? const {};
    } else {
      WidgetsBinding.instance.addPostFrameCallback((_) => _cargar());
    }
  }

  @override
  void dispose() {
    _espera?.cancel();
    _campo.dispose();
    super.dispose();
  }

  Future<void> _cargar() async {
    try {
      final col = Caudal.leer(context).coleccion;
      LetrasCache.i.vincular(col);
      final h = await Historial.leer(col);
      await LetrasCache.i.listo();
      if (!mounted) return;
      setState(() {
        _historial = h;
        _letras = widget.letras ?? LetrasCache.i.todas;
      });
      _buscar(_campo.text);
    } catch (_) {
      if (mounted) setState(() => _error = 'No se pudo leer tu historial. Inténtalo otra vez.');
    }
  }

  void _alEscribir(String t) {
    _espera?.cancel();
    // se espera un momento a que termine de escribir: no se busca letra por letra
    _espera = Timer(const Duration(milliseconds: 250), () => _buscar(t));
    setState(() {}); // para el botón de borrar
  }

  void _buscar(String t) {
    if (!mounted) return;
    final h = _historial;
    if (h == null) return;
    setState(() {
      _resultado = t.trim().isEmpty ? null : QueCancionEra.buscar(h, t, ahora: _hoy, letras: _letras);
    });
  }

  void _poner(String texto) {
    _campo.text = texto;
    _campo.selection = TextSelection.collapsed(offset: texto.length);
    _espera?.cancel();
    _buscar(texto);
  }

  String _resumen(ConsultaHistorial q) {
    final partes = <String>[
      if (q.tieneFecha) q.etiqueta,
      if (q.franja != null) const ['por la mañana', 'por la tarde', 'por la noche', 'de madrugada'][q.franja!.clamp(0, 3)],
      if (q.terminos.isNotEmpty) '«${q.terminos.join(' ')}»',
      if (q.frase.isNotEmpty) 'letra «${q.frase}»',
    ];
    return partes.join(' · ');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('¿Qué canción era?')),
      body: !esPremiumLetras()
          ? const CandadoDonador(
              icono: Icons.manage_search_rounded,
              titulo: '¿Qué canción era?',
              texto:
                  'Encuentra esa canción que escuchaste buscando por el día («el martes», «ayer»), por el título o el artista, o por lo que decía la letra. Es exclusivo para donadores.')
          : Column(children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(Esp.lado, Esp.s, Esp.lado, Esp.s),
                child: TextField(
                  controller: _campo,
                  onChanged: _alEscribir,
                  onSubmitted: (t) {
                    _espera?.cancel();
                    _buscar(t);
                  },
                  textInputAction: TextInputAction.search,
                  decoration: InputDecoration(
                    hintText: 'El martes, ayer Rosalía, decía «quiero bailar»…',
                    prefixIcon: const Icon(Icons.search_rounded),
                    suffixIcon: _campo.text.isEmpty
                        ? null
                        : IconButton(
                            tooltip: 'Borrar',
                            icon: const Icon(Icons.close_rounded),
                            onPressed: () {
                              _campo.clear();
                              _alEscribir('');
                            },
                          ),
                  ),
                ),
              ),
              SizedBox(
                height: 44,
                child: ListView.separated(
                  scrollDirection: Axis.horizontal,
                  padding: const EdgeInsets.symmetric(horizontal: Esp.lado),
                  itemCount: _atajos.length,
                  separatorBuilder: (_, _) => const SizedBox(width: 8),
                  itemBuilder: (_, i) => ActionChip(label: Text(_atajos[i].$1), onPressed: () => _poner(_atajos[i].$2)),
                ),
              ),
              Expanded(child: _cuerpo()),
            ]),
    );
  }

  Widget _cuerpo() {
    if (_error != null) {
      return Vacio(icono: Icons.error_outline_rounded, titulo: 'Algo salió mal', texto: _error!, error: true, alAccion: _cargar);
    }
    if (_historial == null) return const Center(child: CircularProgressIndicator.adaptive());
    final r = _resultado;
    if (r == null) {
      return ListView(padding: const EdgeInsets.all(Esp.xl), children: const [
        Icon(Icons.history_rounded, size: 44, color: C.texto3),
        SizedBox(height: Esp.m),
        Text('Escribe lo que recuerdas', textAlign: TextAlign.center, style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
        SizedBox(height: Esp.s),
        Text(
          'Puedes combinar: el día («el martes», «hace 3 días», «del 3 al 5 de noviembre»), '
          'una palabra del título o del artista, o lo que decía la letra («decía quiero bailar»). '
          'La búsqueda por letra funciona con las canciones cuya letra ya abriste.',
          textAlign: TextAlign.center,
          style: estiloSecundario,
        ),
      ]);
    }
    if (r.resultados.isEmpty) {
      return Vacio(
          icono: Icons.search_off_rounded,
          titulo: 'No encontré nada',
          texto: r.consulta.tieneFecha
              ? 'No hay escuchas que coincidan con ${_resumen(r.consulta)}. Prueba con otro día o con menos palabras.'
              : 'Prueba con otra palabra del título o del artista, o agrega el día en que la escuchaste.');
    }
    final s = Caudal.leer(context);
    return ListView.builder(
      padding: const EdgeInsets.only(bottom: 32),
      itemCount: r.resultados.length + 1,
      itemBuilder: (_, i) {
        if (i == 0) {
          return Padding(
            padding: const EdgeInsets.fromLTRB(Esp.lado, Esp.s, Esp.lado, Esp.s),
            child: Text('${r.resultados.length} ${r.resultados.length == 1 ? 'canción' : 'canciones'} · ${_resumen(r.consulta)}',
                style: estiloSecundario, maxLines: 2, overflow: TextOverflow.ellipsis),
          );
        }
        final h = r.resultados[i - 1];
        final p = h.pista;
        return ListTile(
          leading: Portada(url: '${p['miniatura'] ?? ''}', lado: 48, radio: 6),
          title: Text('${p['titulo'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis),
          subtitle: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(
                '${p['artista'] ?? ''} · ${textoCuando(h.ultima, ahora: _hoy)}${h.veces > 1 ? ' · ${h.veces} veces' : ''}',
                maxLines: 1,
                overflow: TextOverflow.ellipsis),
            if (h.fragmento.isNotEmpty)
              Text('Letra: «${h.fragmento}»',
                  maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(color: C.acento, fontSize: 12.5)),
          ]),
          trailing: IconButton(
            tooltip: 'Reproducir ${p['titulo'] ?? ''}',
            icon: const Icon(Icons.play_circle_fill_rounded, size: 32),
            onPressed: () => s.reproducirPista(context, p),
          ),
          onTap: () => s.reproducirPista(context, p),
        );
      },
    );
  }
}
