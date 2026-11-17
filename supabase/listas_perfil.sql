-- ================================================================ Caudal: listas públicas o privadas
-- Cada lista tiene dos ajustes que elige su dueño:
--   · publica    → cualquiera con cuenta puede abrirla y escucharla. Privada (por defecto) = solo su dueño
--                  y quienes él mismo invitó con un código (ver listas.sql).
--   · en_perfil  → se muestra en el perfil de su dueño. Solo tiene sentido en una lista pública: si la
--                  lista no es pública, el ajuste se apaga solo (lo hace el servidor, no la app).
--
-- Se pega entero en el SQL Editor de Supabase DESPUÉS de esquema.sql, social.sql y listas.sql.
-- Se puede repetir sin romper nada. Las apps viejas siguen funcionando: no mandan estas columnas y
-- el servidor deja lo que ya había.
--
-- Funciones nuevas (todas solo para quien tiene sesión; la privacidad la hace cumplir el servidor):
--   listas_de_perfil(p_usuario text)  → las listas que se ven en el perfil de esa persona. Si es mi propio
--                                       perfil devuelve TODAS mis listas, con sus ajustes, para que yo vea
--                                       cuáles tengo ocultas.
--   ver_lista_publica(p_lista uuid)   → una lista con todas sus canciones. Solo si es pública (o es mía) y no
--                                       hay bloqueo con su dueño. Si no, devuelve null: no revela que existe.

-- ---------------------------------------------------------------- columnas
alter table public.listas add column if not exists publica   boolean not null default false;
alter table public.listas add column if not exists en_perfil boolean not null default false;

-- «en perfil» nunca puede quedar encendido en una lista privada, mande lo que mande la app
create or replace function public.listas_perfil_coherente()
returns trigger language plpgsql as $$
begin
    new.en_perfil := coalesce(new.en_perfil, false) and coalesce(new.publica, false);
    return new;
end $$;

drop trigger if exists listas_perfil_coherente on public.listas;
create trigger listas_perfil_coherente before insert or update on public.listas
    for each row execute function public.listas_perfil_coherente();

update public.listas set en_perfil = false where en_perfil and not publica;

create index if not exists listas_publicas_por_dueno on public.listas (user_id) where publica;

-- ---------------------------------------------------------------- listas en el perfil
drop function if exists public.listas_de_perfil(text);
create function public.listas_de_perfil(p_usuario text)
returns jsonb language plpgsql stable security definer set search_path = public as $$
declare
    p public.perfiles;
    yo uuid := auth.uid();
    visible boolean;
begin
    if yo is null then return '[]'::jsonb; end if;
    select * into p from public.perfiles where usuario = lower(trim(p_usuario));
    if p.id is null then return '[]'::jsonb; end if;
    if p.id <> yo then
        if coalesce(public.hay_bloqueo(yo, p.id), false) then return '[]'::jsonb; end if;
        -- mismo criterio que ver_perfil: un perfil privado no enseña nada a quien no es su amigo
        visible := public.relacion_con(p.id) = 'amigo' or (p.perfil_publico and public.es_mayor(p.id));
        if not visible then return '[]'::jsonb; end if;
    end if;
    return coalesce((
        select jsonb_agg(jsonb_build_object(
                   'id', l.id, 'nombre', l.nombre, 'descripcion', l.descripcion,
                   'publica', l.publica, 'en_perfil', l.en_perfil, 'fijada', l.fijada,
                   'actualizada', l.actualizada,
                   'total', (select count(*)::int from public.lista_items i where i.lista_id = l.id),
                   'canciones', coalesce((
                       select jsonb_agg(jsonb_build_object(
                                  'titulo', coalesce(q.datos ->> 'titulo', q.datos ->> 'nombre', ''),
                                  'artista', coalesce(q.datos -> 'artistas' -> 0 ->> 'nombre', q.datos ->> 'artista', ''),
                                  'miniatura', coalesce(q.datos ->> 'miniatura', q.datos ->> 'portada', ''))
                                order by q.orden, q.agregada)
                         from (select i.datos, i.orden, i.agregada from public.lista_items i
                                where i.lista_id = l.id order by i.orden, i.agregada limit 4) q), '[]'::jsonb))
                 order by l.fijada desc, l.actualizada desc)
          from (select * from public.listas
                 where user_id = p.id and (p.id = yo or (publica and en_perfil))
                 order by fijada desc, actualizada desc limit 60) l
    ), '[]'::jsonb);
end $$;

-- ---------------------------------------------------------------- abrir una lista pública
drop function if exists public.ver_lista_publica(uuid);
create function public.ver_lista_publica(p_lista uuid)
returns jsonb language plpgsql stable security definer set search_path = public as $$
declare
    yo uuid := auth.uid();
    l public.listas;
    d public.perfiles;
begin
    if yo is null then return null; end if;
    select * into l from public.listas where id = p_lista;
    if l.id is null then return null; end if;
    if l.user_id <> yo then
        if not l.publica then return null; end if;
        if coalesce(public.hay_bloqueo(yo, l.user_id), false) then return null; end if;
    end if;
    select * into d from public.perfiles where id = l.user_id;
    return jsonb_build_object(
        'id', l.id, 'nombre', l.nombre, 'descripcion', l.descripcion,
        'publica', l.publica, 'en_perfil', l.en_perfil,
        'es_mia', l.user_id = yo,
        'dueno', jsonb_build_object('usuario', d.usuario, 'nombre', d.nombre, 'foto_url', d.foto_url),
        'total', (select count(*)::int from public.lista_items where lista_id = l.id),
        'canciones', coalesce((
            select jsonb_agg(jsonb_build_object('clave', q.clave, 'datos', q.datos) order by q.orden, q.agregada)
              from (select clave, datos, orden, agregada from public.lista_items
                     where lista_id = l.id order by orden, agregada limit 2000) q), '[]'::jsonb));
end $$;

-- ---------------------------------------------------------------- permisos
revoke execute on function public.listas_perfil_coherente() from public, anon, authenticated;
revoke execute on function public.listas_de_perfil(text), public.ver_lista_publica(uuid) from public, anon;
grant  execute on function public.listas_de_perfil(text), public.ver_lista_publica(uuid) to authenticated;
