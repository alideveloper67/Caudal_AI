import AVFoundation
import Flutter
import UIKit

@main
@objc class AppDelegate: FlutterAppDelegate, FlutterImplicitEngineDelegate {
  override func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
  ) -> Bool {
    configurarSesionDeAudio()
    return super.application(application, didFinishLaunchingWithOptions: launchOptions)
  }

  func didInitializeImplicitFlutterEngine(_ engineBridge: FlutterImplicitEngineBridge) {
    GeneratedPluginRegistrant.register(with: engineBridge.pluginRegistry)
    if let registrar = engineBridge.pluginRegistry.registrar(forPlugin: "CaudalNativo") {
      CaudalNativo.register(with: registrar)
    }
    if let registrar = engineBridge.pluginRegistry.registrar(forPlugin: "CaudalSonido") {
      CaudalSonido.register(with: registrar)
    }
  }

  /// Categoria "playback": suena con la pantalla bloqueada y con el interruptor
  /// de silencio puesto. No se activa aqui (eso cortaria la musica de otras apps
  /// solo por abrir Caudal); se activa al empezar a sonar (audio_session/mpv).
  /// El lado Dart vuelve a configurarla con AudioSessionConfiguration.music(),
  /// que en iOS tambien es playback, asi que no se pisan.
  private func configurarSesionDeAudio() {
    do {
      try AVAudioSession.sharedInstance().setCategory(.playback, mode: .default, options: [])
    } catch {
      NSLog("Caudal: no se pudo fijar la categoria de audio: \(error)")
    }
  }
}

/// Canales nativos que la app Android ya usa ("caudal/compartido" y "caudal/pip").
///
/// Se registra como plugin para recibir los eventos de la escena
/// (`scene(_:willConnectTo:options:)`, `scene(_:openURLContexts:)`,
/// `scene(_:continue:)`) que FlutterSceneDelegate reenvia a los plugins con
/// `addSceneDelegate`. Asi no hace falta sobrescribir metodos de
/// FlutterSceneDelegate (no los declara en su cabecera: sobrescribirlos sin
/// poder llamar a super romperia el reenvio de Flutter).
/// Tambien escucha los equivalentes del AppDelegate por si la app corriera sin escenas.
class CaudalNativo: NSObject, FlutterPlugin, FlutterSceneLifeCycleDelegate {
  private var canal: FlutterMethodChannel?
  private var canalPip: FlutterMethodChannel?

  /// Enlace que llego antes de que el lado Dart pidiera `inicial`.
  private var pendiente: String?
  /// true cuando Dart ya pidio `inicial`: a partir de ahi su handler esta puesto.
  private var dartListo = false

  /// PiP: ver la nota en `manejarPip`.
  private var pipPermitido = false

  static func register(with registrar: FlutterPluginRegistrar) {
    let instancia = CaudalNativo()
    let mensajero = registrar.messenger()

    let canal = FlutterMethodChannel(name: "caudal/compartido", binaryMessenger: mensajero)
    canal.setMethodCallHandler { [weak instancia] llamada, resultado in
      guard let instancia = instancia else { return resultado(nil) }
      instancia.manejarCompartido(llamada, resultado)
    }
    instancia.canal = canal

    let canalPip = FlutterMethodChannel(name: "caudal/pip", binaryMessenger: mensajero)
    canalPip.setMethodCallHandler { [weak instancia] llamada, resultado in
      guard let instancia = instancia else { return resultado(nil) }
      instancia.manejarPip(llamada, resultado)
    }
    instancia.canalPip = canalPip

    registrar.addApplicationDelegate(instancia)
    registrar.addSceneDelegate(instancia)  // iOS 13+; el proyecto apunta a 15
    // El registrar guarda los delegados de forma debil: se retiene aqui.
    CaudalNativo.vivas.append(instancia)
  }

  private static var vivas: [CaudalNativo] = []

  // MARK: - caudal/compartido

  private func manejarCompartido(_ llamada: FlutterMethodCall, _ resultado: FlutterResult) {
    if llamada.method == "inicial" {
      dartListo = true
      resultado(pendiente)
      pendiente = nil
    } else {
      resultado(FlutterMethodNotImplemented)
    }
  }

  /// Convierte la URL recibida en el texto que espera Dart (DescargasPagina.pegar):
  /// - caudal://abrir?url=<enlace> (o ?texto=<texto>) -> el enlace/texto decodificado
  /// - http(s), archivos, etc. -> la URL tal cual
  /// - caudal:// sin nada que abrir -> nil (solo abre la app)
  private func textoDe(_ url: URL) -> String? {
    if url.scheme?.lowercased() == "caudal" {
      // caudal://juntos?sala=XXXXXX va entero: Dart lo lleva a "Escuchar juntos"
      if url.host?.lowercased() == "juntos" {
        return url.absoluteString
      }
      let items = URLComponents(url: url, resolvingAgainstBaseURL: false)?.queryItems ?? []
      for nombre in ["url", "texto", "text", "u"] {
        if let valor = items.first(where: { $0.name == nombre })?.value,
          !valor.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
        {
          return valor
        }
      }
      return nil
    }
    return url.absoluteString
  }

  /// Igual que onNewIntent en Android: si Dart ya escucha, se le avisa; si no,
  /// queda pendiente para cuando pida `inicial`.
  @discardableResult
  private func recibir(_ url: URL) -> Bool {
    let esNuestro = url.scheme?.lowercased() == "caudal"
    guard let texto = textoDe(url) else { return esNuestro }
    if dartListo, let canal = canal {
      canal.invokeMethod("compartido", arguments: texto)
    } else {
      pendiente = texto
    }
    return true
  }

  // MARK: - Escena (la app usa UIScene)

  @objc(scene:willConnectToSession:options:)
  func scene(
    _ scene: UIScene,
    willConnectTo session: UISceneSession,
    options connectionOptions: UIScene.ConnectionOptions?
  ) -> Bool {
    guard let opciones = connectionOptions else { return false }
    var manejado = false
    for contexto in opciones.urlContexts {
      if recibir(contexto.url) { manejado = true }
    }
    for actividad in opciones.userActivities {
      if let url = actividad.webpageURL, recibir(url) { manejado = true }
    }
    return manejado
  }

  @objc(scene:openURLContexts:)
  func scene(_ scene: UIScene, openURLContexts URLContexts: Set<UIOpenURLContext>) -> Bool {
    var manejado = false
    for contexto in URLContexts {
      if recibir(contexto.url) { manejado = true }
    }
    return manejado
  }

  @objc(scene:continueUserActivity:)
  func scene(_ scene: UIScene, continue userActivity: NSUserActivity) -> Bool {
    guard let url = userActivity.webpageURL else { return false }
    return recibir(url)
  }

  // MARK: - AppDelegate (respaldo si no hubiera escenas)

  @objc(application:openURL:options:)
  func application(
    _ app: UIApplication,
    open url: URL,
    options: [UIApplication.OpenURLOptionsKey: Any] = [:]
  ) -> Bool {
    return recibir(url)
  }

  @objc(application:continueUserActivity:restorationHandler:)
  func application(
    _ application: UIApplication,
    continue userActivity: NSUserActivity,
    restorationHandler: @escaping ([Any]) -> Void
  ) -> Bool {
    guard let url = userActivity.webpageURL else { return false }
    return recibir(url)
  }

  // MARK: - caudal/pip

  /// En iOS el PiP de AVKit solo funciona con un AVPlayerLayer o con un
  /// AVSampleBufferDisplayLayer alimentado a mano. Aqui el video lo pinta
  /// libmpv (media_kit) en una textura de Flutter: habria que copiar cada
  /// cuadro de esa textura a CMSampleBuffers, sincronizar el audio y conectar
  /// los botones del PiP con mpv. Es mucho codigo nativo fragil que no se
  /// puede compilar ni probar sin Mac, y un fallo ahi cuelga el video.
  ///
  /// Decision: el canal responde (Dart no recibe errores) y nunca emite
  /// `cambio`, asi `Pip.enVentana` se queda en false y la UI sigue igual.
  /// Con UIBackgroundModes=audio el sonido del video sigue al salir de la app.
  private func manejarPip(_ llamada: FlutterMethodCall, _ resultado: FlutterResult) {
    if llamada.method == "permitir" {
      pipPermitido = (llamada.arguments as? Bool) ?? false
      resultado(nil)
    } else {
      resultado(FlutterMethodNotImplemented)
    }
  }
}

/// Por dónde sale el sonido (audífonos, parlante, bluetooth) para el ecualizador avanzado por
/// salida (canal "caudal/sonido", el mismo nombre que en Android). En iPhone no hay sesiones de
/// efectos: "sesion" y "ganancia" no existen aquí y Dart sube el volumen sin limitador.
class CaudalSonido: NSObject, FlutterPlugin {
  private var canal: FlutterMethodChannel?

  static func register(with registrar: FlutterPluginRegistrar) {
    let instancia = CaudalSonido()
    let canal = FlutterMethodChannel(name: "caudal/sonido", binaryMessenger: registrar.messenger())
    instancia.canal = canal
    registrar.addMethodCallDelegate(instancia, channel: canal)
    NotificationCenter.default.addObserver(
      instancia, selector: #selector(CaudalSonido.rutaCambiada(_:)),
      name: AVAudioSession.routeChangeNotification, object: nil)
  }

  func handle(_ call: FlutterMethodCall, result: @escaping FlutterResult) {
    if call.method == "salida" {
      result(CaudalSonido.tipoSalida())
    } else {
      result(FlutterMethodNotImplemented)
    }
  }

  @objc func rutaCambiada(_ aviso: Notification) {
    let tipo = CaudalSonido.tipoSalida()
    DispatchQueue.main.async { [weak self] in
      self?.canal?.invokeMethod("salida", arguments: tipo)
    }
  }

  static func tipoSalida() -> String {
    for puerto in AVAudioSession.sharedInstance().currentRoute.outputs {
      switch puerto.portType {
      case .bluetoothA2DP, .bluetoothLE, .bluetoothHFP, .airPlay:
        return "bluetooth"
      case .headphones, .usbAudio:
        return "audifonos"
      default:
        continue
      }
    }
    return "parlante"
  }
}
