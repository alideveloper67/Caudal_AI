# -*- coding: utf-8 -*-
"""Un solo punto para conectar las pantallas sociales a la navegación de la ventana.

En `Ventana._fabricar` basta con:

    from .paginas.perfil_rutas import fabricar
    w = fabricar(self.ctx, destino)      # None si el destino no es social

Destinos (los que se pasan a ctx.navegar):
    {"pagina": "perfil", "usuario": "ana"}      # sin "usuario" -> mi perfil
    {"pagina": "directorio"}
    {"pagina": "amigos", "pestana": "solicitudes" | "amigos" | "bloqueados"}
    {"pagina": "subir_musica"}
    {"pagina": "comunidad"}
Para abrir un chat con un amigo desde cualquier sitio: `ctx.chat_pendiente = {"id", "usuario",
"nombre", "visible"}` y navegar a {"pagina": "mensajes"} (Mensajes lo recoge al abrirse).
"""

PAGINAS_SOCIALES = ("perfil", "directorio", "amigos", "subir_musica", "comunidad")


def fabricar(ctx, destino):
    pag = (destino or {}).get("pagina")
    if pag == "perfil":
        from .perfil import PaginaPerfil
        return PaginaPerfil(ctx, destino.get("usuario"))
    if pag == "directorio":
        from .directorio import PaginaDirectorio
        return PaginaDirectorio(ctx)
    if pag == "amigos":
        from .amigos import PaginaAmigos
        return PaginaAmigos(ctx, destino.get("pestana") or "solicitudes")
    if pag == "subir_musica":
        from .subir_musica import PaginaSubirMusica
        return PaginaSubirMusica(ctx)
    if pag == "comunidad":
        from .comunidad import PaginaComunidad
        return PaginaComunidad(ctx)
    return None
