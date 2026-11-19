-- ================================================================ Portada del perfil (donadores)
-- Una portada arriba del perfil con la canción del momento, un fragmento de letra y la mascota elegida.
-- La ven la propia persona y sus AMIGOS (nadie más). Solo se puede escribir con premium vigente; si el
-- premium se acaba, lo guardado se conserva pero deja de verse (y vuelve si la persona vuelve a donar).
--
-- Se pega entero en el SQL Editor de Supabase DESPUÉS de esquema.sql, social.sql y premium.sql
-- (usa es_premium, relacion_con y hay_bloqueo). Se puede ejecutar de nuevo sin romper nada.
-- Las pruebas están en supabase/pruebas/perfil_portada.prueba.mjs.

-- ---------------------------------------------------------------- 1. columnas
alter table public.perfiles add column if not exists portada_cancion jsonb;   -- {video_id, titulo, artista, miniatura}
alter table public.perfiles add column if not exists portada_letra text;      -- fragmento de letra (hasta 160 letras)
alter table public.perfiles add column if not exists portada_mascota text;    -- clave de la mascota del catálogo

alter table public.perfiles drop constraint if exists perfil_portada_forma;
alter table public.perfiles add constraint perfil_portada_forma check (
    (portada_letra is null or char_length(portada_letra) <= 160)
    and (portada_mascota is null or portada_mascota ~ '^[a-z0-9_]{1,40}$')
    and (portada_cancion is null
         or (jsonb_typeof(portada_cancion) = 'object' and pg_column_size(portada_cancion) < 2000))
);

-- ---------------------------------------------------------------- 2. el servidor manda
-- Sin premium vigente nada de la portada se escribe (aunque alguien toque la columna a mano): en una
-- fila nueva queda vacía y en una existente se conserva lo de antes. Con premium, se limpia lo escrito:
-- solo las cuatro claves de la canción, con tope de largo, y sin letra ni mascota en blanco.
create or replace function public.perfil_portada_validar()
returns trigger language plpgsql security definer set search_path = public as $$
begin
    if not public.es_premium(new.id) then
        if tg_op = 'UPDATE' then
            new.portada_cancion := old.portada_cancion;
            new.portada_letra := old.portada_letra;
            new.portada_mascota := old.portada_mascota;
        else
            new.portada_cancion := null;
            new.portada_letra := null;
            new.portada_mascota := null;
        end if;
        return new;
    end if;
    if new.portada_cancion is not null then
        if jsonb_typeof(new.portada_cancion) <> 'object'
           or btrim(coalesce(new.portada_cancion ->> 'video_id', '')) = '' then
            new.portada_cancion := null;
        else
            new.portada_cancion := jsonb_build_object(
                'video_id', left(btrim(new.portada_cancion ->> 'video_id'), 32),
                'titulo', left(btrim(coalesce(new.portada_cancion ->> 'titulo', '')), 150),
                'artista', left(btrim(coalesce(new.portada_cancion ->> 'artista', '')), 150),
                'miniatura', left(btrim(coalesce(new.portada_cancion ->> 'miniatura', '')), 300));
        end if;
    end if;
    new.portada_letra := nullif(left(btrim(coalesce(new.portada_letra, '')), 160), '');
    new.portada_mascota := nullif(lower(btrim(coalesce(new.portada_mascota, ''))), '');
    return new;
end $$;
drop trigger if exists perfil_portada_validar on public.perfiles;
create trigger perfil_portada_validar before insert or update on public.perfiles
    for each row execute function public.perfil_portada_validar();

-- ---------------------------------------------------------------- 3. leer la portada de alguien
-- {"cancion": {...}|null, "letra": texto, "mascota": clave|null}; null si no hay nada que ver:
-- sin sesión, sin permiso (ni yo ni amigo), con bloqueo, sin premium vigente o sin portada.
create or replace function public.portada_perfil(p_usuario text)
returns jsonb language plpgsql stable security definer set search_path = public as $$
declare
    p public.perfiles;
    yo uuid := auth.uid();
begin
    if yo is null then return null; end if;
    select * into p from public.perfiles where usuario = lower(btrim(coalesce(p_usuario, '')));
    if p.id is null then return null; end if;
    if p.id <> yo then
        if coalesce(public.hay_bloqueo(yo, p.id), false) then return null; end if;
        if public.relacion_con(p.id) <> 'amigo' then return null; end if;
    end if;
    if not public.es_premium(p.id) then return null; end if;
    if p.portada_cancion is null and coalesce(p.portada_letra, '') = '' and p.portada_mascota is null then
        return null;
    end if;
    return jsonb_build_object('cancion', p.portada_cancion,
                              'letra', coalesce(p.portada_letra, ''),
                              'mascota', p.portada_mascota);
end $$;

-- ---------------------------------------------------------------- 4. permisos
revoke execute on function public.perfil_portada_validar() from public, anon, authenticated;
revoke execute on function public.portada_perfil(text) from public, anon;
grant execute on function public.portada_perfil(text) to authenticated;
