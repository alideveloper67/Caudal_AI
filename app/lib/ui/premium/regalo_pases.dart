import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:share_plus/share_plus.dart';

import '../../nucleo/pases_regalo.dart';
import '../../nucleo/premium.dart';
import '../paginas/perfil_comun.dart' show socialDe, textoSinConexion;
import '../servicios.dart';
import '../tema.dart';
import 'canje_pase.dart' show fechaLarga;

/// Cómo se manda el texto del regalo (se cambia en las pruebas para no abrir la hoja del sistema).
typedef Compartidor = Future<void> Function(String texto);

Future<void> _compartirDeVerdad(String texto) => SharePlus.instance.share(ShareParams(text: texto));

const _verde = Color(0xFF5BD68A);

/// «Regala una prueba a tus amigos»: crea, copia, comparte y anula códigos de prueba. Solo se ve
/// para donadores y fundadores (una prueba no puede regalar pruebas); para el resto no ocupa nada.
class TarjetaRegalo extends StatefulWidget {
  const TarjetaRegalo({super.key, this.compartir = _compartirDeVerdad});

  final Compartidor compartir;

  @override
  State<TarjetaRegalo> createState() => _TarjetaRegaloState();
}

class _TarjetaRegaloState extends State<TarjetaRegalo> {
  List<PaseRegalo> _pases = const [];
  bool _cargando = false;
  bool _creando = false;
  bool _pedido = false;
  String? _errorLista;
  String? _mensaje;
  bool _mensajeEsError = false;
  final _anulando = <String>{};
  int _tanda = 0;

  void _aviso(String t) => Caudal.leer(context).avisar(t);

  Future<void> _cargar({bool silencioso = false}) async {
    final social = socialDe(context);
    if (social == null) {
      if (!silencioso) setState(() => _errorLista = textoSinConexion(context));
      return;
    }
    final mia = ++_tanda;
    if (!silencioso) {
      setState(() {
        _cargando = true;
        _errorLista = null;
      });
    }
    try {
      final l = await PasesRegalo.listar(social);
      if (!mounted || mia != _tanda) return;
      setState(() {
        _pases = l;
        _cargando = false;
        _errorLista = null;
      });
    } catch (e) {
      if (!mounted || mia != _tanda) return;
      setState(() {
        _cargando = false;
        if (!silencioso) _errorLista = 'No se pudieron cargar tus códigos. Revisa tu internet.';
      });
    }
  }

  Future<void> _crear() async {
    if (_creando) return;
    final social = socialDe(context);
    if (social == null) {
      setState(() {
        _mensaje = textoSinConexion(context);
        _mensajeEsError = true;
      });
      return;
    }
    setState(() {
      _creando = true;
      _mensaje = null;
    });
    final r = await PasesRegalo.crear(social);
    if (!mounted) return;
    setState(() {
      _creando = false;
      if (r.ok && r.pase != null) {
        _pases = [r.pase!, ..._pases.where((p) => p.codigo != r.pase!.codigo)];
        _mensaje = null;
      } else {
        _mensaje = r.mensaje;
        _mensajeEsError = true;
      }
    });
    if (r.ok) _cargar(silencioso: true);
  }

  Future<void> _copiar(PaseRegalo p) async {
    try {
      await Clipboard.setData(ClipboardData(text: p.codigo));
      if (mounted) _aviso('Código ${p.codigo} copiado.');
    } catch (_) {
      if (mounted) _aviso('No se pudo copiar el código.');
    }
  }

  Future<void> _compartir(PaseRegalo p) async {
    try {
      await widget.compartir(PasesRegalo.textoCompartir(p.codigo, dias: p.dias));
    } catch (_) {
      if (mounted) _aviso('No se pudo abrir el menú de compartir.');
    }
  }

  Future<void> _anular(PaseRegalo p) async {
    if (_anulando.contains(p.codigo)) return;
    final seguro = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: C.panel,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20), side: BorderSide(color: C.borde)),
        title: const Text('¿Anular este código?'),
        content: Text('${p.codigo} dejará de funcionar. Podrás crear otro.', style: estiloSecundario),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancelar')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Anular')),
        ],
      ),
    );
    if (seguro != true || !mounted) return;
    final social = socialDe(context);
    if (social == null) {
      _aviso(textoSinConexion(context));
      return;
    }
    setState(() => _anulando.add(p.codigo));
    final r = await PasesRegalo.anular(social, p.codigo);
    if (!mounted) return;
    setState(() {
      _anulando.remove(p.codigo);
      if (r.ok) _pases = [for (final x in _pases) if (x.codigo != p.codigo) x];
    });
    _aviso(r.mensaje);
    // si el servidor dijo que ya no se podía, la lista se pone al día
    if (!r.ok) _cargar(silencioso: true);
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: Premium.i,
      builder: (context, _) {
        if (!PasesRegalo.puedeRegalar(Premium.i.estado)) return const SizedBox.shrink();
        if (!_pedido) {
          _pedido = true;
          WidgetsBinding.instance.addPostFrameCallback((_) {
            if (mounted) _cargar();
          });
        }
        return _tarjeta();
      },
    );
  }

  Widget _tarjeta() {
    final sinUsar = PasesRegalo.sinUsar(_pases);
    return Semantics(
      container: true,
      label: 'Regala una prueba a tus amigos',
      child: Container(
        padding: const EdgeInsets.all(Esp.l),
        decoration: BoxDecoration(
          color: C.superficie2,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: C.acento.withValues(alpha: 0.4)),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(color: C.acento.withValues(alpha: 0.16), shape: BoxShape.circle),
              child: Icon(Icons.card_giftcard_rounded, color: C.acento, size: 22),
            ),
            const SizedBox(width: 12),
            const Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('Regala una prueba a tus amigos',
                    style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16, height: 1.25)),
                SizedBox(height: 4),
                Text('Cada código le da a un amigo 7 días de beneficios de donador. Puedes tener hasta '
                    '${PasesRegalo.maxSinUsar} sin usar a la vez.',
                    style: estiloSecundario),
              ]),
            ),
          ]),
          const SizedBox(height: Esp.m),
          Align(
            alignment: Alignment.centerLeft,
            child: FilledButton.icon(
              onPressed: _creando ? null : _crear,
              icon: _creando
                  ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Icon(Icons.add_rounded, size: 20),
              label: const Text('Crear código'),
            ),
          ),
          if (_mensaje != null) ...[
            const SizedBox(height: Esp.s),
            Semantics(
              liveRegion: true,
              child: Text(_mensaje!,
                  style: TextStyle(color: _mensajeEsError ? C.error : C.texto2, height: 1.35, fontSize: 13.5)),
            ),
          ],
          if (_cargando && _pases.isEmpty)
            const Padding(
              padding: EdgeInsets.only(top: Esp.l),
              child: Center(child: SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))),
            )
          else if (_errorLista != null && _pases.isEmpty)
            Padding(
              padding: const EdgeInsets.only(top: Esp.m),
              child: Row(children: [
                Expanded(child: Text(_errorLista!, style: const TextStyle(color: C.error, fontSize: 13.5, height: 1.35))),
                TextButton(onPressed: _cargar, child: const Text('Reintentar')),
              ]),
            )
          else if (_pases.isNotEmpty) ...[
            const SizedBox(height: Esp.m),
            Text('Tus códigos · $sinUsar sin usar',
                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13, color: C.texto2)),
            const SizedBox(height: Esp.s),
            for (final p in _pases) _fila(p),
          ],
        ]),
      ),
    );
  }

  Widget _fila(PaseRegalo p) {
    final e = p.estado;
    final activo = e == EstadoPase.sinUsar;
    final color = switch (e) {
      EstadoPase.sinUsar => C.acento,
      EstadoPase.usado => _verde,
      EstadoPase.caducado => C.texto3,
    };
    final ocupado = _anulando.contains(p.codigo);
    final detalle = switch (e) {
      EstadoPase.sinUsar => p.caduca == null ? null : 'Canjéalo antes del ${fechaLarga(p.caduca!)}',
      EstadoPase.usado => 'Tu amigo ya lo canjeó',
      EstadoPase.caducado => 'Ya no se puede canjear',
    };
    return Container(
      key: ValueKey('pase-${p.codigo}'),
      margin: const EdgeInsets.only(bottom: Esp.s),
      padding: const EdgeInsets.fromLTRB(12, 8, 4, 8),
      decoration: BoxDecoration(
        color: C.panel,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: C.borde),
      ),
      child: Row(children: [
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Wrap(spacing: 8, runSpacing: 4, crossAxisAlignment: WrapCrossAlignment.center, children: [
              Text(p.codigo,
                    maxLines: 1,
                    softWrap: false,
                    style: TextStyle(
                      fontSize: 17,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 1.8,
                      color: activo ? C.texto : C.texto3,
                      decoration: e == EstadoPase.caducado ? TextDecoration.lineThrough : null,
                    )),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.16),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Text(e.etiqueta, style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800, color: color)),
              ),
            ]),
            if (detalle != null) ...[
              const SizedBox(height: 2),
              Text(detalle, style: estiloSecundario.copyWith(fontSize: 12)),
            ],
          ]),
        ),
        if (activo) ...[
          _icono(Icons.copy_rounded, 'Copiar código ${p.codigo}', () => _copiar(p)),
          _icono(Icons.ios_share_rounded, 'Compartir código ${p.codigo}', () => _compartir(p)),
        ],
        if (p.sePuedeAnular)
          ocupado
              ? const SizedBox(
                  width: 40,
                  height: 40,
                  child: Center(child: SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))))
              : _icono(Icons.delete_outline_rounded, 'Anular código ${p.codigo}', () => _anular(p)),
      ]),
    );
  }

  Widget _icono(IconData i, String tip, VoidCallback f) => IconButton(
        onPressed: f,
        tooltip: tip,
        icon: Icon(i, size: 20),
        color: C.texto2,
        visualDensity: VisualDensity.compact,
        constraints: const BoxConstraints(minWidth: 40, minHeight: 40),
        padding: EdgeInsets.zero,
      );
}

/// La hoja de una sola vez: «Ahora puedes regalar códigos de prueba a tus amigos». Devuelve true si
/// tocó «Ver mis códigos».
Future<bool> mostrarAvisoPasesRegalo(BuildContext context) async {
  final r = await showModalBottomSheet<bool>(
    context: context,
    useRootNavigator: true,
    isScrollControlled: true,
    backgroundColor: C.panel,
    showDragHandle: true,
    shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
    builder: (_) => const _HojaAvisoRegalo(),
  );
  return r == true;
}

class _HojaAvisoRegalo extends StatelessWidget {
  const _HojaAvisoRegalo();

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(Esp.xl, 0, Esp.xl, Esp.xl),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Container(
            width: 72,
            height: 72,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [C.acento.withValues(alpha: 0.35), C.acento.withValues(alpha: 0.10)],
              ),
              border: Border.all(color: C.acento.withValues(alpha: 0.5)),
            ),
            child: Icon(Icons.card_giftcard_rounded, size: 36, color: C.acento),
          ),
          const SizedBox(height: Esp.l),
          const Text('Ahora puedes regalar códigos de prueba a tus amigos',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.w900, height: 1.25, letterSpacing: -0.2)),
          const SizedBox(height: Esp.s),
          Text('Por ser donador, puedes crear códigos que dan 7 días de beneficios de donador a quien los canjee. '
              'Los encuentras en Personalizar.',
              textAlign: TextAlign.center,
              style: estiloSecundario.copyWith(fontSize: 14.5, height: 1.45)),
          const SizedBox(height: Esp.xl),
          SizedBox(
            width: double.infinity,
            child: FilledButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: const Text('Ver mis códigos'),
            ),
          ),
          const SizedBox(height: Esp.xs),
          TextButton(onPressed: () => Navigator.of(context).pop(false), child: const Text('Ahora no')),
        ]),
      ),
    );
  }
}
