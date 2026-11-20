import 'dart:async';

import 'package:flutter/foundation.dart';

import 'coleccion.dart';
import 'importar.dart';

/// Una importación grande en marcha (lista nueva o «me gusta»), que sigue aunque se
/// salga de la pantalla y se puede reanudar si se cierra la app.
///
/// Va de lote en lote: después de cada lote guarda lo encontrado (en la lista o en
/// tus Me gusta) y apunta por dónde va. Las canciones se apuntan una sola vez
/// (`importacion_canciones`); el avance, que es pequeño, después de cada lote
/// (`importacion_pendiente`).
class TrabajoImportacion extends ChangeNotifier {
  TrabajoImportacion._();
  static final i = TrabajoImportacion._();

  static const clavePendiente = 'importacion_pendiente';
  static const claveCanciones = 'importacion_canciones';
  static const claveFuentes = 'fuentes_me_gusta';

  /// Para las pruebas: la búsqueda de cada canción.
  Future<Map<String, dynamic>?> Function(CancionExterna c)? buscarPista;

  bool enMarcha = false;
  bool terminado = false;
  bool _parar = false;
  String titulo = '';
  String plataforma = '';
  bool aMeGusta = false;
  int? listaId;
  int hechas = 0;
  int total = 0;
  int encontradas = 0;
  int anadidas = 0;
  int repetidas = 0;
  List<String> noEncontradas = [];
  String aviso = '';
  String? error;

  Map<String, dynamic> _avance() => {
        'titulo': titulo,
        'plataforma': plataforma,
        'me_gusta': aMeGusta,
        'lista_id': listaId,
        'hechas': hechas,
        'total': total,
        'encontradas': encontradas,
        'anadidas': anadidas,
        'repetidas': repetidas,
        'no_encontradas': noEncontradas,
        'aviso': aviso,
        'enlace': _enlace,
      };
  String _enlace = '';

  /// Lo que quedó a medias la última vez (o null).
  static Future<Map<String, dynamic>?> pendiente(Coleccion c) async {
    final p = await c.estado(clavePendiente);
    if (p is! Map) return null;
    final m = Map<String, dynamic>.from(p);
    if (((m['hechas'] as num?) ?? 0) >= ((m['total'] as num?) ?? 0)) return null;
    return m;
  }

  /// Empieza a pasar [l] a una lista nueva o a tus Me gusta.
  Future<void> empezar(Coleccion c, ListaExterna l, {required bool meGusta, String enlace = ''}) async {
    if (enMarcha) throw const ErrorImportar('Ya se están pasando canciones: espera a que termine o páusalo.');
    _reiniciar();
    titulo = l.titulo;
    plataforma = l.plataforma;
    aMeGusta = meGusta;
    aviso = l.aviso;
    _enlace = enlace;
    total = l.canciones.length;
    if (!meGusta) {
      var nombre = l.titulo.trim().isEmpty ? 'Lista traída' : l.titulo.trim();
      try {
        listaId = await c.crearLista(nombre, descripcion: 'Traída de ${l.plataforma}');
      } on FormatException {
        // ya hay una lista con ese nombre: "Nombre n.º 2"...
        nombre = await c.nombreLibre(nombre);
        listaId = await c.crearLista(nombre, descripcion: 'Traída de ${l.plataforma}');
      }
      titulo = nombre;
    }
    await c.guardarEstado(claveCanciones, [for (final x in l.canciones) x.aJson()]);
    await c.guardarEstado(clavePendiente, _avance());
    unawaited(_correr(c, l.canciones));
  }

  /// Sigue la que quedó a medias.
  Future<void> reanudar(Coleccion c) async {
    if (enMarcha) return;
    final p = await pendiente(c);
    final lista = await c.estado(claveCanciones);
    if (p == null || lista is! List) throw const ErrorImportar('No hay nada a medias que seguir.');
    _reiniciar();
    titulo = '${p['titulo'] ?? ''}';
    plataforma = '${p['plataforma'] ?? ''}';
    aMeGusta = p['me_gusta'] == true;
    listaId = (p['lista_id'] as num?)?.toInt();
    hechas = (p['hechas'] as num?)?.toInt() ?? 0;
    total = lista.length;
    encontradas = (p['encontradas'] as num?)?.toInt() ?? 0;
    anadidas = (p['anadidas'] as num?)?.toInt() ?? 0;
    repetidas = (p['repetidas'] as num?)?.toInt() ?? 0;
    noEncontradas = [for (final x in (p['no_encontradas'] as List? ?? const [])) '$x'];
    aviso = '${p['aviso'] ?? ''}';
    _enlace = '${p['enlace'] ?? ''}';
    if (!aMeGusta && (listaId == null || await c.lista(listaId!) == null)) {
      await descartar(c);
      throw const ErrorImportar('La lista donde se estaban guardando ya no existe.');
    }
    final canciones = [for (final x in lista.whereType<Map>()) CancionExterna.deJson(x)];
    unawaited(_correr(c, canciones));
  }

  /// Se detiene después del lote que va: lo encontrado queda guardado.
  void pausar() {
    _parar = true;
    notifyListeners();
  }

  bool get pausando => _parar && enMarcha;

  Future<void> descartar(Coleccion c) async {
    await c.guardarEstado(clavePendiente, null);
    await c.guardarEstado(claveCanciones, null);
    if (!enMarcha) {
      _reiniciar();
      notifyListeners();
    }
  }

  void _reiniciar() {
    enMarcha = false;
    terminado = false;
    _parar = false;
    listaId = null;
    hechas = 0;
    total = 0;
    encontradas = 0;
    anadidas = 0;
    repetidas = 0;
    noEncontradas = [];
    aviso = '';
    error = null;
  }

  /// Lo que terminó, ya mostrado: la pantalla vuelve a su estado normal.
  void olvidarTerminado() {
    if (enMarcha) return;
    _reiniciar();
    notifyListeners();
  }

  Future<void> _correr(Coleccion c, List<CancionExterna> canciones) async {
    enMarcha = true;
    notifyListeners();
    var ultimoAviso = DateTime(2000);
    try {
      final r = await Importar.emparejar(canciones,
          desde: hechas,
          buscarPista: buscarPista,
          cancelado: () => _parar,
          alAvanzar: (h, t) {
            hechas = h;
            // la pantalla se repinta como mucho 8 veces por segundo
            final ahora = DateTime.now();
            if (ahora.difference(ultimoAviso).inMilliseconds > 120) {
              ultimoAviso = ahora;
              notifyListeners();
            }
          },
          alLote: (fin, pistas, sin) async {
            if (pistas.isNotEmpty) {
              if (aMeGusta) {
                final (a, rep) = await c.agregarMeGustaVarios(pistas);
                anadidas += a;
                repetidas += rep;
              } else if (listaId != null) {
                anadidas += await c.agregarALista(listaId!, pistas);
              }
            }
            encontradas += pistas.length;
            noEncontradas = [...noEncontradas, ...sin];
            hechas = fin;
            await c.guardarEstado(clavePendiente, _avance());
            notifyListeners();
          });
      if (!r.cancelado) {
        terminado = true;
        await c.guardarEstado(clavePendiente, null);
        await c.guardarEstado(claveCanciones, null);
        if (aMeGusta) {
          await anotarFuente(c, plataforma, _enlace, titulo, anadidas, noEncontradas.length);
        }
      }
    } catch (e) {
      error = 'Se detuvo: ${e is ErrorImportar ? e.mensaje : 'revisa tu internet y vuelve a seguir.'}';
    } finally {
      enMarcha = false;
      _parar = false;
      notifyListeners();
    }
  }

  /// El resumen para el aviso final.
  String resumen() {
    final faltan = noEncontradas.length;
    var t = aMeGusta
        ? 'Se añadieron ${miles(anadidas)} canciones a tus Me gusta${repetidas > 0 ? ' (${miles(repetidas)} ya estaban)' : ''}'
        : 'Lista «$titulo» creada con ${miles(anadidas)} canciones';
    t += faltan > 0 ? '. ${miles(faltan)} no se encontraron.' : '.';
    return t;
  }

  /// Recuerda de dónde se trajeron me gusta, para «Volver a sincronizar».
  static Future<void> anotarFuente(Coleccion c, String servicio, String enlace, String titulo, int anadidas,
      int noEncontradas) async {
    final antes = await c.estado(claveFuentes);
    final fuentes = [
      for (final f in (antes is List ? antes : const []).whereType<Map>())
        if (f['enlace'] != enlace) Map<String, dynamic>.from(f)
    ];
    fuentes.insert(0, {
      'servicio': servicio,
      'enlace': enlace,
      'titulo': titulo,
      'cuando': DateTime.now().millisecondsSinceEpoch ~/ 1000,
      'anadidas': anadidas,
      'no_encontradas': noEncontradas,
    });
    await c.guardarEstado(claveFuentes, fuentes.take(12).toList());
  }

  static Future<List<Map<String, dynamic>>> fuentes(Coleccion c) async {
    final f = await c.estado(claveFuentes);
    return [for (final x in (f is List ? f : const []).whereType<Map>()) Map<String, dynamic>.from(x)];
  }
}
