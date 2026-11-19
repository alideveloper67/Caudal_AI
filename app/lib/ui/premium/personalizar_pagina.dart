import 'package:flutter/material.dart';

import '../../nucleo/cosmeticos.dart';
import '../../nucleo/nube.dart';
import '../../nucleo/pases_regalo.dart';
import '../../nucleo/premium.dart';
import '../paginas/donar.dart';
import '../paginas/perfil_comun.dart';
import '../servicios.dart';
import '../tema.dart';
import 'canje_pase.dart';
import 'marcos.dart';
import 'regalo_pases.dart';
import 'temas_premium.dart';

/// «Personalizar»: marco del avatar, efecto del nombre y tema de color, exclusivos de donadores.
///
/// Con los beneficios activos, tocar una opción la aplica y la guarda en el perfil. Sin ellos las
/// mismas opciones se ven con candado y solo cambian la vista previa (para probar antes de donar),
/// con «Donar aquí» y «Tengo un código de prueba» a la mano.
class PersonalizarPagina extends StatefulWidget {
  const PersonalizarPagina({super.key});

  @override
  State<PersonalizarPagina> createState() => _PersonalizarPaginaState();
}

class _PersonalizarPaginaState extends State<PersonalizarPagina> {
  late String _marco = Premium.i.marco;
  late String _efecto = Premium.i.efectoNombre;
  late String _tema = Premium.i.tema;
  String _foto = '';
  bool _guardando = false;

  @override
  void initState() {
    super.initState();
    _cargarFoto();
  }

  Future<void> _cargarFoto() async {
    try {
      final social = socialDe(context);
      if (social == null) return;
      final p = await social.miPerfilEditable();
      if (mounted) setState(() => _foto = p.fotoUrl);
    } catch (_) {}
  }

  String get _nombre {
    final c = Caudal.leer(context).cuenta;
    return c.nombre.trim().isNotEmpty ? c.nombre.trim() : c.usuario;
  }

  void _aviso(String t) => Caudal.leer(context).avisar(t);

  void _bloqueado() => _aviso('Es exclusivo de donadores: dona o canjea un código de prueba para usarlo.');

  Future<void> _elegir({String? marco, String? efecto, String? tema}) async {
    final antes = (_marco, _efecto, _tema);
    setState(() {
      if (marco != null) _marco = marco;
      if (efecto != null) _efecto = efecto;
      if (tema != null) _tema = tema;
    });
    if (!Premium.i.activo) {
      // sin beneficios: solo se mira la vista previa
      if ((marco ?? efecto ?? tema) != Cosmeticos.ninguno) _bloqueado();
      return;
    }
    final social = socialDe(context);
    if (social == null) {
      _volver(antes);
      _aviso(textoSinConexion(context));
      return;
    }
    setState(() => _guardando = true);
    try {
      await Premium.i.guardar(social, marco: marco, efectoNombre: efecto, tema: tema);
    } on ErrorNube catch (e) {
      if (mounted) {
        _volver(antes);
        _aviso(e.mensaje);
      }
    } catch (_) {
      if (mounted) {
        _volver(antes);
        _aviso('No se pudo guardar. Revisa tu internet e inténtalo otra vez.');
      }
    } finally {
      if (mounted) setState(() => _guardando = false);
    }
  }

  void _volver((String, String, String) v) => setState(() {
        _marco = v.$1;
        _efecto = v.$2;
        _tema = v.$3;
      });

  Future<void> _canjear() async {
    final r = await mostrarCanjePase(context);
    if (r == null || !mounted) return;
    setState(() {
      _marco = Premium.i.marco;
      _efecto = Premium.i.efectoNombre;
      _tema = Premium.i.tema;
    });
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: Premium.i,
      builder: (context, _) {
        final activo = Premium.i.activo;
        final e = Premium.i.estado;
        return Scaffold(
          appBar: AppBar(
            backgroundColor: C.fondoVivo,
            surfaceTintColor: Colors.transparent,
            title: const Text('Personalizar', style: estiloTituloBarra),
          ),
          body: ListView(padding: const EdgeInsets.fromLTRB(Esp.lado, 0, Esp.lado, 40), children: [
            _vistaPrevia(),
            const SizedBox(height: Esp.l),
            if (activo && e.esPrueba && e.diasRestantes() != null)
              _banda(Icons.hourglass_bottom_rounded, textoPrueba(e.diasRestantes()!, e.vence))
            else if (activo)
              _banda(Icons.workspace_premium_rounded, 'Tienes los beneficios de donador: todo está desbloqueado.')
            else
              _bloqueo(),
            const AvisoPrueba(margen: EdgeInsets.only(top: Esp.s)),
            const SizedBox(height: Esp.xl),
            _titulo('Marco del avatar'),
            _opciones([for (final c in Cosmeticos.marcos) _tileMarco(c, activo)]),
            const SizedBox(height: Esp.xl),
            _titulo('Efecto del nombre'),
            _opciones([for (final c in Cosmeticos.efectosNombre) _tileEfecto(c, activo)]),
            const SizedBox(height: Esp.xl),
            _titulo('Tema de color'),
            _opciones([for (final c in Cosmeticos.temas) _tileTema(c, activo)]),
            if (PasesRegalo.puedeRegalar(e)) ...[
              const SizedBox(height: Esp.xl),
              const TarjetaRegalo(),
            ],
            if (!activo || e.esPrueba) ...[
              const SizedBox(height: Esp.xl),
              Center(
                child: TextButton.icon(
                  onPressed: _canjear,
                  icon: const Icon(Icons.confirmation_number_outlined, size: 18),
                  label: const Text('Tengo un código de prueba'),
                ),
              ),
            ],
          ]),
        );
      },
    );
  }

  Widget _titulo(String t) => Padding(
        padding: const EdgeInsets.only(bottom: Esp.s),
        child: Text(t, style: estiloTituloSeccion.copyWith(fontSize: 18)),
      );

  Widget _banda(IconData icono, String texto) => Container(
        padding: const EdgeInsets.all(Esp.m),
        decoration: BoxDecoration(
          color: C.superficie2,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: C.acento.withValues(alpha: 0.4)),
        ),
        child: Row(children: [
          Icon(icono, color: C.acento, size: 22),
          const SizedBox(width: 12),
          Expanded(child: Text(texto, style: const TextStyle(fontWeight: FontWeight.w700, height: 1.3))),
        ]),
      );

  Widget _bloqueo() => Container(
        padding: const EdgeInsets.all(Esp.m),
        decoration: BoxDecoration(
          color: C.superficie2,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: C.borde),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Row(children: [
            Icon(Icons.lock_outline_rounded, size: 20, color: Color(0xFFFFC857)),
            SizedBox(width: 10),
            Expanded(
              child: Text('Exclusivo para donadores',
                  style: TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
            ),
          ]),
          const SizedBox(height: 6),
          const Text('Puedes probar cada opción en la vista previa. Para usarla en tu cuenta, dona con Yape o '
              'canjea un código de prueba.', style: estiloSecundario),
          const SizedBox(height: 10),
          Wrap(spacing: 8, runSpacing: 4, children: [
            FilledButton.icon(
              onPressed: () => mostrarDonar(context),
              icon: const Icon(Icons.favorite_rounded, size: 18),
              label: const Text('Donar aquí'),
            ),
            OutlinedButton.icon(
              onPressed: _canjear,
              icon: const Icon(Icons.confirmation_number_outlined, size: 18),
              label: const Text('Tengo un código'),
            ),
          ]),
        ]),
      );

  // ------------------------------------------------------------ vista previa

  Widget _vistaPrevia() {
    final tema = TemasPremium.de(_tema);
    final fondo = tema?.capas[2] ?? C.superficie;
    final acento = tema?.acento ?? C.acento;
    final borde = tema?.capas[5] ?? C.borde;
    return Semantics(
      label: 'Vista previa de tu perfil',
      child: AnimatedContainer(
        duration: Mov.normal,
        padding: const EdgeInsets.symmetric(vertical: Esp.xl, horizontal: Esp.l),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(22),
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [Color.lerp(fondo, acento, 0.22)!, fondo],
          ),
          border: Border.all(color: borde),
        ),
        child: Column(children: [
          AvatarPerfil(nombre: _nombre, fotoUrl: _foto, color: acento, radio: 48, marco: _marco, animar: true),
          const SizedBox(height: 12),
          NombreEfecto(_nombre,
              efecto: _efecto,
              animar: true,
              textAlign: TextAlign.center,
              estilo: const TextStyle(fontSize: 22, fontWeight: FontWeight.w900)),
          const SizedBox(height: 14),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 8),
            decoration: BoxDecoration(color: acento, borderRadius: BorderRadius.circular(20)),
            child: Text(tema == null ? 'Tu tema actual' : 'Tema ${tema.nombre}',
                style: TextStyle(fontWeight: FontWeight.w800, color: TemasPremium.textoSobre(acento))),
          ),
          if (_guardando)
            const Padding(
              padding: EdgeInsets.only(top: 12),
              child: SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)),
            ),
        ]),
      ),
    );
  }

  // ------------------------------------------------------------ opciones

  Widget _opciones(List<Widget> hijos) => Wrap(spacing: 10, runSpacing: 12, children: hijos);

  Widget _tile({
    required String etiqueta,
    required bool seleccionada,
    required bool bloqueada,
    required VoidCallback alTocar,
    required Widget hijo,
    double ancho = 84,
  }) {
    return Semantics(
      button: true,
      selected: seleccionada,
      label: '$etiqueta${bloqueada ? ', bloqueado: exclusivo de donadores' : ''}',
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: alTocar,
        child: SizedBox(
          width: ancho,
          child: Column(children: [
            Stack(clipBehavior: Clip.none, children: [
              Container(
                width: ancho,
                height: 76,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: C.superficie2,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: seleccionada ? C.acento : C.borde, width: seleccionada ? 2 : 1),
                ),
                child: Opacity(opacity: bloqueada ? 0.62 : 1, child: hijo),
              ),
              if (bloqueada)
                const Positioned(
                  right: 5,
                  top: 5,
                  child: Icon(Icons.lock_rounded, size: 15, color: Color(0xFFFFC857)),
                ),
            ]),
            const SizedBox(height: 5),
            Text(etiqueta,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                    fontSize: 12, fontWeight: seleccionada ? FontWeight.w800 : FontWeight.w600,
                    color: seleccionada ? C.texto : C.texto2)),
          ]),
        ),
      ),
    );
  }

  Widget _tileMarco(String clave, bool activo) {
    final e = marcosAvatar[clave];
    return _tile(
      etiqueta: e?.nombre ?? 'Ninguno',
      seleccionada: _marco == clave,
      bloqueada: !activo && clave != Cosmeticos.ninguno,
      alTocar: () => _elegir(marco: clave),
      hijo: AvatarPerfil(nombre: _nombre, fotoUrl: _foto, radio: 26, marco: clave),
    );
  }

  Widget _tileEfecto(String clave, bool activo) {
    return _tile(
      etiqueta: efectosNombreEtiquetas[clave] ?? 'Ninguno',
      seleccionada: _efecto == clave,
      bloqueada: !activo && clave != Cosmeticos.ninguno,
      alTocar: () => _elegir(efecto: clave),
      ancho: 104,
      hijo: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 6),
        child: NombreEfecto('Tu nombre',
            efecto: clave,
            textAlign: TextAlign.center,
            estilo: const TextStyle(fontSize: 15, fontWeight: FontWeight.w900)),
      ),
    );
  }

  Widget _tileTema(String clave, bool activo) {
    final t = TemasPremium.de(clave);
    return _tile(
      etiqueta: t?.nombre ?? 'Normal',
      seleccionada: _tema == clave,
      bloqueada: !activo && clave != Cosmeticos.ninguno,
      alTocar: () => _elegir(tema: clave),
      hijo: t == null
          ? Icon(Icons.palette_outlined, color: C.texto2)
          : Container(
              width: 58,
              height: 52,
              decoration: BoxDecoration(color: t.capas[0], borderRadius: BorderRadius.circular(10), border: Border.all(color: t.capas[5])),
              child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                Container(width: 40, height: 9, decoration: BoxDecoration(color: t.capas[3], borderRadius: BorderRadius.circular(3))),
                const SizedBox(height: 5),
                Container(width: 26, height: 12, decoration: BoxDecoration(color: t.acento, borderRadius: BorderRadius.circular(6))),
              ]),
            ),
    );
  }
}
