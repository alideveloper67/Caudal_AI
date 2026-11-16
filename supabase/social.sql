-- ================================================================ Caudal social
-- Perfiles con foto y descripción, solicitudes de amistad, bloqueos, directorio
-- de perfiles públicos y música subida por la gente.
--
-- Se pega entero en el SQL Editor de Supabase DESPUÉS de esquema.sql. Se puede
-- repetir sin romper nada.
--
-- Reglas de seguridad que fijan estas tablas (no dependen de la app):
--   · Solo se puede escribir a un AMIGO (solicitud aceptada).
--   · Los perfiles son privados hasta que la persona los hace públicos, y los
--     menores de 18 años nunca aparecen en el directorio.
--   · Cada quien solo escribe en su carpeta de fotos y de música.

-- ---------------------------------------------------------------- ayudas
create or replace function public.es_mayor(p_id uuid)
returns boolean language sql stable security definer set search_path = public as $$
    select coalesce((select age(fecha_nacimiento) >= interval '18 years'
                       from public.perfiles where id = p_id), false);
$$;

-- ---------------------------------------------------------------- perfil
alter table public.perfiles add column if not exists bio text not null default '';
alter table public.perfiles add column if not exists foto_url text;
alter table public.perfiles add column if not exists cancion_fav jsonb;
alter table public.perfiles add column if not exists artista_fav text not null default '';
alter table public.perfiles add column if not exists generos text[] not null default '{}';
alter table public.perfiles add column if not exists frase text not null default '';
alter table public.perfiles add column if not exists color_perfil text;
alter table public.perfiles add column if not exists perfil_publico boolean not null default false;
alter table public.perfiles add column if not exists mostrar_top boolean not null default true;
alter table public.perfiles add column if not exists banner_url text;   -- imagen de fondo: <mi id>/banner.jpg

alter table public.perfiles drop constraint if exists perfil_limites;
alter table public.perfiles add constraint perfil_limites check (
    length(bio) <= 300
    and length(frase) <= 80
    and length(artista_fav) <= 80
    and coalesce(array_length(generos, 1), 0) <= 5
    and (color_perfil is null or color_perfil ~ '^#[0-9A-Fa-f]{6}$')
    and (cancion_fav is null or pg_column_size(cancion_fav) < 3000)
    and (foto_url is null or foto_url like id::text || '/%')
    and (banner_url is null or banner_url like id::text || '/%')
);

-- Número de usuario: el orden de llegada, que nunca se reutiliza ni cambia aunque alguien borre su cuenta.
-- Las 100 primeras personas son «Usuario fundador» (se muestra con una estrella).
create sequence if not exists public.perfiles_numero_seq;
alter table public.perfiles add column if not exists numero int;
with orden as (
    select id, row_number() over (order by creado, id)
               + coalesce((select max(numero) from public.perfiles), 0) as n
    from public.perfiles where numero is null)
update public.perfiles p set numero = o.n from orden o where p.id = o.id;
select setval('public.perfiles_numero_seq',
              coalesce((select max(numero) from public.perfiles), 0) + 1, false);
alter table public.perfiles alter column numero set default nextval('public.perfiles_numero_seq');
create unique index if not exists perfiles_numero on public.perfiles (numero);

-- Títulos especiales («Fundador de Caudal», «Rey de la música»...): los asigna solo quien administra
-- la base. La tabla no tiene ninguna política, así que desde la app nadie puede leerla ni escribirla.
create table if not exists public.titulos_especiales (
    user_id  uuid not null references auth.users (id) on delete cascade,
    titulo   text not null check (titulo ~ '^[a-z_]{3,30}$'),      -- clave: fundador_caudal
    nombre   text not null check (length(nombre) between 2 and 40), -- lo que se ve: Fundador de Caudal
    creado   timestamptz not null default now(),
    primary key (user_id, titulo)
);
alter table public.titulos_especiales enable row level security;
insert into public.titulos_especiales (user_id, titulo, nombre)
select id, 'fundador_caudal', 'Fundador de Caudal' from public.perfiles where usuario in ('aliceo', 'aliceoapp')
on conflict do nothing;
insert into public.titulos_especiales (user_id, titulo, nombre)
select id, 'rey_de_la_musica', 'Rey de la música' from public.perfiles where usuario = 'cochayuyo'
on conflict do nothing;

-- un menor de 18 años no puede tener el perfil público
create or replace function public.perfil_validar()
returns trigger language plpgsql security definer set search_path = public as $$
begin
    if new.perfil_publico and not (new.fecha_nacimiento is not null
                                   and age(new.fecha_nacimiento) >= interval '18 years') then
        new.perfil_publico := false;
    end if;
    return new;
end $$;
drop trigger if exists perfil_validar on public.perfiles;
create trigger perfil_validar before insert or update on public.perfiles
    for each row execute function public.perfil_validar();

-- fotos de perfil: carpeta propia, imágenes de hasta 2 MB
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('avatares', 'avatares', true, 2097152, array['image/jpeg', 'image/png', 'image/webp'])
on conflict (id) do update set public = true, file_size_limit = 2097152,
    allowed_mime_types = array['image/jpeg', 'image/png', 'image/webp'];

drop policy if exists "avatar: subir el mio" on storage.objects;
create policy "avatar: subir el mio" on storage.objects for insert to authenticated
    with check (bucket_id = 'avatares' and (storage.foldername(name))[1] = auth.uid()::text);
drop policy if exists "avatar: cambiar el mio" on storage.objects;
create policy "avatar: cambiar el mio" on storage.objects for update to authenticated
    using (bucket_id = 'avatares' and (storage.foldername(name))[1] = auth.uid()::text);
-- Sin esta política la subida falla con «no tienes permiso»: el almacén lee la fila al guardarla.
drop policy if exists "avatar: ver el mio" on storage.objects;
create policy "avatar: ver el mio" on storage.objects for select to authenticated
    using (bucket_id = 'avatares' and (storage.foldername(name))[1] = auth.uid()::text);
drop policy if exists "avatar: borrar el mio" on storage.objects;
create policy "avatar: borrar el mio" on storage.objects for delete to authenticated
    using (bucket_id = 'avatares' and (storage.foldername(name))[1] = auth.uid()::text);

-- ---------------------------------------------------------------- amistades
create table if not exists public.amistades (
    id         bigint generated always as identity primary key,
    de         uuid not null references auth.users (id) on delete cascade,
    para       uuid not null references auth.users (id) on delete cascade,
    estado     text not null default 'pendiente' check (estado in ('pendiente', 'aceptada', 'rechazada')),
    creado     timestamptz not null default now(),
    respondido timestamptz,
    check (de <> para)
);
create unique index if not exists amistades_par on public.amistades (least(de, para), greatest(de, para));
create index if not exists amistades_para on public.amistades (para, estado);

create table if not exists public.bloqueos (
    quien   uuid not null references auth.users (id) on delete cascade,
    a       uuid not null references auth.users (id) on delete cascade,
    creado  timestamptz not null default now(),
    primary key (quien, a),
    check (quien <> a)
);

alter table public.amistades enable row level security;
alter table public.bloqueos  enable row level security;
-- solo se lee lo propio; escribir se hace únicamente con las funciones de abajo
drop policy if exists "mis amistades" on public.amistades;
create policy "mis amistades" on public.amistades for select using (auth.uid() in (de, para));
drop policy if exists "mis bloqueos" on public.bloqueos;
create policy "mis bloqueos" on public.bloqueos for select using (quien = auth.uid());

create or replace function public.son_amigos(p_x uuid, p_y uuid)
returns boolean language sql stable security definer set search_path = public as $$
    select auth.uid() in (p_x, p_y)
       and exists (select 1 from public.amistades
                    where estado = 'aceptada'
                      and ((de = p_x and para = p_y) or (de = p_y and para = p_x)));
$$;

create or replace function public.hay_bloqueo(p_x uuid, p_y uuid)
returns boolean language sql stable security definer set search_path = public as $$
    select auth.uid() in (p_x, p_y)
       and exists (select 1 from public.bloqueos
                    where (quien = p_x and a = p_y) or (quien = p_y and a = p_x));
$$;

-- las personas que ya conversaban en los dos sentidos siguen siendo amigas
insert into public.amistades (de, para, estado, respondido)
select c.a, c.b, 'aceptada', now() from public.chats c
where exists (select 1 from public.mensajes m where m.chat = c.id and m.autor = c.a)
  and exists (select 1 from public.mensajes m where m.chat = c.id and m.autor = c.b)
on conflict do nothing;

-- enviar una solicitud (si la otra persona ya te había enviado una, se aceptan)
drop function if exists public.enviar_solicitud(uuid);
create function public.enviar_solicitud(p_otro uuid)
returns text language plpgsql security definer set search_path = public as $$
declare
    yo uuid := auth.uid();
    a public.amistades;
begin
    if yo is null or p_otro is null or p_otro = yo then raise exception 'solicitud no valida'; end if;
    if not exists (select 1 from public.perfiles where id = p_otro) then
        raise exception 'esa persona no existe';
    end if;
    if public.hay_bloqueo(yo, p_otro) then raise exception 'no se puede enviar'; end if;
    select * into a from public.amistades
     where least(de, para) = least(yo, p_otro) and greatest(de, para) = greatest(yo, p_otro);
    if a.id is not null then
        if a.estado = 'aceptada' then return 'ya_amigos'; end if;
        if a.estado = 'pendiente' and a.de = yo then return 'ya_enviada'; end if;
        if a.estado = 'pendiente' and a.para = yo then
            update public.amistades set estado = 'aceptada', respondido = now() where id = a.id;
            return 'aceptada';
        end if;
        -- rechazada: quien la envió puede volver a intentarlo pasados 30 días
        if a.de = yo and a.respondido > now() - interval '30 days' then
            raise exception 'espera unos dias para volver a enviarla';
        end if;
        update public.amistades set de = yo, para = p_otro, estado = 'pendiente',
               creado = now(), respondido = null where id = a.id;
        return 'enviada';
    end if;
    if (select count(*) from public.amistades where de = yo and estado = 'pendiente') >= 30 then
        raise exception 'tienes demasiadas solicitudes pendientes';
    end if;
    insert into public.amistades (de, para) values (yo, p_otro);
    return 'enviada';
end $$;

drop function if exists public.responder_solicitud(bigint, boolean);
create function public.responder_solicitud(p_id bigint, p_acepta boolean)
returns void language plpgsql security definer set search_path = public as $$
begin
    update public.amistades set estado = case when p_acepta then 'aceptada' else 'rechazada' end,
           respondido = now()
     where id = p_id and para = auth.uid() and estado = 'pendiente';
    if not found then raise exception 'solicitud no encontrada'; end if;
end $$;

drop function if exists public.cancelar_solicitud(uuid);
create function public.cancelar_solicitud(p_otro uuid)
returns void language sql security definer set search_path = public as $$
    delete from public.amistades where de = auth.uid() and para = p_otro and estado = 'pendiente';
$$;

drop function if exists public.quitar_amigo(uuid);
create function public.quitar_amigo(p_otro uuid)
returns void language sql security definer set search_path = public as $$
    delete from public.amistades
     where estado = 'aceptada'
       and ((de = auth.uid() and para = p_otro) or (de = p_otro and para = auth.uid()));
$$;

drop function if exists public.bloquear(uuid);
create function public.bloquear(p_otro uuid)
returns void language plpgsql security definer set search_path = public as $$
begin
    if auth.uid() is null or p_otro is null or p_otro = auth.uid() then
        raise exception 'bloqueo no valido';
    end if;
    insert into public.bloqueos (quien, a) values (auth.uid(), p_otro) on conflict do nothing;
    delete from public.amistades
     where (de = auth.uid() and para = p_otro) or (de = p_otro and para = auth.uid());
end $$;

drop function if exists public.desbloquear(uuid);
create function public.desbloquear(p_otro uuid)
returns void language sql security definer set search_path = public as $$
    delete from public.bloqueos where quien = auth.uid() and a = p_otro;
$$;

drop function if exists public.mis_bloqueados();
create function public.mis_bloqueados()
returns table (id uuid, usuario text, nombre text, foto_url text)
language sql stable security definer set search_path = public as $$
    select p.id, p.usuario, p.nombre, p.foto_url from public.bloqueos b
    join public.perfiles p on p.id = b.a where b.quien = auth.uid() order by b.creado desc;
$$;

drop function if exists public.mis_solicitudes();
create function public.mis_solicitudes()
returns table (id bigint, de uuid, usuario text, nombre text, foto_url text, creado timestamptz)
language sql stable security definer set search_path = public as $$
    select a.id, p.id, p.usuario, p.nombre, p.foto_url, a.creado
    from public.amistades a join public.perfiles p on p.id = a.de
    where a.para = auth.uid() and a.estado = 'pendiente'
      and not public.hay_bloqueo(auth.uid(), a.de)
    order by a.creado desc;
$$;

drop function if exists public.mis_enviadas();
create function public.mis_enviadas()
returns table (id bigint, para uuid, usuario text, nombre text, foto_url text, creado timestamptz)
language sql stable security definer set search_path = public as $$
    select a.id, p.id, p.usuario, p.nombre, p.foto_url, a.creado
    from public.amistades a join public.perfiles p on p.id = a.para
    where a.de = auth.uid() and a.estado = 'pendiente' order by a.creado desc;
$$;

drop function if exists public.mis_amigos();
create function public.mis_amigos()
returns table (id uuid, usuario text, nombre text, foto_url text, desde timestamptz)
language sql stable security definer set search_path = public as $$
    select p.id, p.usuario, p.nombre, p.foto_url, a.respondido
    from public.amistades a
    join public.perfiles p on p.id = case when a.de = auth.uid() then a.para else a.de end
    where a.estado = 'aceptada' and auth.uid() in (a.de, a.para)
    order by lower(p.nombre), p.usuario;
$$;

-- la relación de quien mira con otra persona
create or replace function public.relacion_con(p_otro uuid)
returns text language sql stable security definer set search_path = public as $$
    select case
        when p_otro = auth.uid() then 'yo'
        when public.hay_bloqueo(auth.uid(), p_otro) then 'bloqueado'
        else coalesce((select case when estado = 'aceptada' then 'amigo'
                                   when estado = 'pendiente' and de = auth.uid() then 'enviada'
                                   when estado = 'pendiente' then 'recibida'
                                   else 'ninguna' end
                         from public.amistades
                        where least(de, para) = least(auth.uid(), p_otro)
                          and greatest(de, para) = greatest(auth.uid(), p_otro)), 'ninguna')
    end;
$$;

-- buscar a alguien por su usuario EXACTO (ahora dice también la relación y la foto)
drop function if exists public.buscar_persona(text);
create function public.buscar_persona(p_usuario text)
returns table (id uuid, usuario text, nombre text, foto_url text, relacion text)
language sql stable security definer set search_path = public as $$
    select p.id, p.usuario, p.nombre, p.foto_url, public.relacion_con(p.id)
    from public.perfiles p
    where p.usuario = lower(trim(p_usuario)) and p.id <> auth.uid()
      and not public.hay_bloqueo(auth.uid(), p.id);
$$;

-- el chat solo se abre entre amigos
create or replace function public.abrir_chat(p_otro uuid)
returns uuid language plpgsql security definer set search_path = public as $$
declare
    yo uuid := auth.uid();
    x uuid; y uuid; r uuid;
begin
    if yo is null or p_otro is null or p_otro = yo then raise exception 'chat no valido'; end if;
    if not exists (select 1 from public.perfiles where id = p_otro) then
        raise exception 'esa persona no existe';
    end if;
    if not public.son_amigos(yo, p_otro) then raise exception 'primero deben ser amigos'; end if;
    x := least(yo, p_otro); y := greatest(yo, p_otro);
    insert into public.chats (a, b) values (x, y) on conflict (a, b) do nothing;
    select id into r from public.chats where a = x and b = y;
    return r;
end $$;

-- y solo se escribe a un amigo (aunque alguien llame a la API a mano)
drop policy if exists "escribo en mis chats" on public.mensajes;
create policy "escribo en mis chats" on public.mensajes for insert
    with check (autor = auth.uid()
                and exists (select 1 from public.chats c
                             where c.id = chat and auth.uid() in (c.a, c.b)
                               and public.son_amigos(c.a, c.b)
                               and not public.hay_bloqueo(c.a, c.b)));

drop function if exists public.mis_chats();
create function public.mis_chats()
returns table (id uuid, otro uuid, usuario text, nombre text, ultimo timestamptz,
               ultimo_texto text, ultimo_pista jsonb, ultimo_autor uuid, sin_leer int,
               foto_url text)
language sql stable security definer set search_path = public as $$
    select c.id,
           o.id, o.usuario, o.nombre, c.ultimo,
           m.texto, m.pista, m.autor,
           (select count(*)::int from public.mensajes n
             where n.chat = c.id and n.autor <> auth.uid()
               and n.creado > case when c.a = auth.uid() then c.leido_a else c.leido_b end),
           o.foto_url
    from public.chats c
    join public.perfiles o on o.id = case when c.a = auth.uid() then c.b else c.a end
    left join lateral (select texto, pista, autor from public.mensajes
                       where chat = c.id order by id desc limit 1) m on true
    where auth.uid() in (c.a, c.b)
      and not public.hay_bloqueo(c.a, c.b)
    order by c.ultimo desc;
$$;

-- tabla de la música subida (se crea aquí porque el directorio y los perfiles la consultan)
create table if not exists public.canciones_subidas (
    id        uuid primary key default gen_random_uuid(),
    user_id   uuid not null references auth.users (id) on delete cascade,
    titulo    text not null check (length(trim(titulo)) between 1 and 120),
    artista   text not null default '' check (length(artista) <= 120),
    album     text not null default '' check (length(album) <= 120),
    duracion  int not null default 0 check (duracion between 0 and 7200),
    ruta      text not null,              -- "<usuario>/<archivo>" en el bucket musica
    portada   text not null,              -- ruta de la carátula: es obligatoria
    tamano    bigint not null default 0,
    estado    text not null default 'pendiente' check (estado in ('pendiente', 'publicada', 'revision', 'retirada')),
    nota      text not null default '',   -- motivo si se rechaza
    escuchas  int not null default 0,
    creado    timestamptz not null default now(),
    check (ruta like user_id::text || '/%'),
    check (portada like user_id::text || '/%')
);
-- (si la tabla ya existía con los tres estados de antes)
alter table public.canciones_subidas drop constraint if exists canciones_subidas_estado_check;
alter table public.canciones_subidas add constraint canciones_subidas_estado_check
    check (estado in ('pendiente', 'publicada', 'revision', 'retirada'));
alter table public.canciones_subidas add column if not exists nota text not null default '';
create index if not exists subidas_usuario on public.canciones_subidas (user_id, estado, creado desc);
create index if not exists subidas_creado on public.canciones_subidas (estado, creado desc);

-- Quien revisa la música que sube la gente. Solo se añaden desde la base: ninguna política, nadie la lee desde la app.
create table if not exists public.moderadores (
    user_id  uuid primary key references auth.users (id) on delete cascade,
    creado   timestamptz not null default now()
);
alter table public.moderadores enable row level security;

create or replace function public.puede_publicar(p_id uuid)
returns boolean language sql stable security definer set search_path = public as $$
    select exists (select 1 from public.moderadores where user_id = p_id)
        or exists (select 1 from public.titulos_especiales where user_id = p_id and titulo = 'fundador_caudal');
$$;

-- ---------------------------------------------------------------- me gusta a perfiles
create table if not exists public.likes_perfil (
    quien   uuid not null references auth.users (id) on delete cascade,
    a       uuid not null references auth.users (id) on delete cascade,
    creado  timestamptz not null default now(),
    primary key (quien, a),
    check (quien <> a)
);
create index if not exists likes_perfil_a on public.likes_perfil (a);
alter table public.likes_perfil enable row level security;
drop policy if exists "mis likes" on public.likes_perfil;
create policy "mis likes" on public.likes_perfil for select using (quien = auth.uid());

-- se puede dar me gusta a un perfil que se puede ver (público, amigo)
drop function if exists public.dar_like(uuid);
create function public.dar_like(p_otro uuid)
returns int language plpgsql security definer set search_path = public as $$
declare yo uuid := auth.uid();
begin
    if yo is null or p_otro is null or p_otro = yo then raise exception 'like no valido'; end if;
    if public.hay_bloqueo(yo, p_otro) then raise exception 'no se puede'; end if;
    if not (public.son_amigos(yo, p_otro)
            or exists (select 1 from public.perfiles where id = p_otro and perfil_publico
                       and public.es_mayor(id))) then
        raise exception 'ese perfil no es publico';
    end if;
    insert into public.likes_perfil (quien, a) values (yo, p_otro) on conflict do nothing;
    return (select count(*)::int from public.likes_perfil where a = p_otro);
end $$;

drop function if exists public.quitar_like(uuid);
create function public.quitar_like(p_otro uuid)
returns int language plpgsql security definer set search_path = public as $$
begin
    delete from public.likes_perfil where quien = auth.uid() and a = p_otro;
    return (select count(*)::int from public.likes_perfil where a = p_otro);
end $$;

-- ---------------------------------------------------------------- perfiles de Caudal
-- Directorio: solo perfiles hechos públicos por su dueño y de mayores de 18 años.
drop function if exists public.explorar_perfiles(text, int, int);
create function public.explorar_perfiles(p_busqueda text default '', p_limite int default 30,
                                         p_desde int default 0)
returns table (id uuid, usuario text, nombre text, foto_url text, bio text,
               cancion_fav jsonb, color_perfil text, relacion text, likes int, di_like boolean,
               num_subidas int, es_artista boolean, fundador boolean, fundador_caudal boolean, titulos jsonb, banner_url text)
language sql stable security definer set search_path = public as $$
    select p.id, p.usuario, p.nombre, p.foto_url, p.bio, p.cancion_fav, p.color_perfil,
           public.relacion_con(p.id),
           (select count(*)::int from public.likes_perfil l where l.a = p.id),
           exists (select 1 from public.likes_perfil l where l.a = p.id and l.quien = auth.uid()),
           (select count(*)::int from public.canciones_subidas s where s.user_id = p.id and s.estado = 'publicada'),
           (select count(*) from public.likes_perfil l where l.a = p.id) >= 200,
           coalesce(p.numero <= 100, false),
           exists (select 1 from public.titulos_especiales te where te.user_id = p.id and te.titulo = 'fundador_caudal'),
           coalesce((select jsonb_agg(jsonb_build_object('clave', te.titulo, 'nombre', te.nombre) order by te.creado)
                       from public.titulos_especiales te where te.user_id = p.id), '[]'::jsonb),
           p.banner_url
    from public.perfiles p
    where auth.uid() is not null
      and p.id <> auth.uid()
      and p.perfil_publico
      and public.es_mayor(p.id)
      and not public.hay_bloqueo(auth.uid(), p.id)
      and (coalesce(trim(p_busqueda), '') = ''
           or p.usuario ilike '%' || replace(replace(trim(p_busqueda), '%', ''), '_', '') || '%'
           or p.nombre  ilike '%' || replace(replace(trim(p_busqueda), '%', ''), '_', '') || '%')
    order by (p.foto_url is not null) desc, (p.cancion_fav is not null) desc, p.creado desc
    limit least(greatest(p_limite, 1), 60) offset greatest(p_desde, 0);
$$;

-- cuánto se parecen los gustos de dos personas (0 a 100), por artistas escuchados
create or replace function public.afinidad_entre(p_x uuid, p_y uuid)
returns int language sql stable security definer set search_path = public as $$
    with puntos as (
        select user_id, lower(coalesce(datos -> 'artistas' -> 0 ->> 'nombre', datos ->> 'artista', '')) as artista,
               count(*)::float as n
        from public.escuchas
        where user_id in (p_x, p_y) and fecha > now() - interval '120 days'
        group by 1, 2
    ), comunes as (
        select coalesce(sum(least(x.n, y.n)), 0) as c
        from puntos x join puntos y on x.artista = y.artista and x.artista <> ''
        where x.user_id = p_x and y.user_id = p_y
    )
    select round(least(1.0, coalesce((select c from comunes) / nullif(greatest(
               (select sum(n) from puntos where user_id = p_x),
               (select sum(n) from puntos where user_id = p_y)), 0), 0) * 1.6) * 100)::int;
$$;

-- el perfil completo de alguien (si es público, amigo o es el tuyo)
drop function if exists public.ver_perfil(text);
create function public.ver_perfil(p_usuario text)
returns jsonb language plpgsql stable security definer set search_path = public as $$
declare
    p public.perfiles;
    yo uuid := auth.uid();
    rel text;
    visible boolean;
    top_art jsonb := '[]'; top_can jsonb := '[]'; insig jsonb := '[]'; subidas jsonb := '[]';
    n_likes int; dias int; artistas int; gustos int; n_sem int;
begin
    select * into p from public.perfiles where usuario = lower(trim(p_usuario));
    if p.id is null or yo is null then return null; end if;
    if public.hay_bloqueo(yo, p.id) then return null; end if;
    rel := public.relacion_con(p.id);
    visible := p.id = yo or rel = 'amigo' or (p.perfil_publico and public.es_mayor(p.id));
    if not visible then
        return jsonb_build_object('id', p.id, 'usuario', p.usuario, 'nombre', p.nombre,
                                  'foto_url', p.foto_url, 'banner_url', p.banner_url, 'relacion', rel, 'privado', true,
                                  'fundador', coalesce(p.numero <= 100, false), 'numero', p.numero,
                                  'fundador_caudal', exists (select 1 from public.titulos_especiales te
                                      where te.user_id = p.id and te.titulo = 'fundador_caudal'),
                                  'titulos', coalesce((select jsonb_agg(jsonb_build_object('clave', te.titulo, 'nombre', te.nombre)
                                      order by te.creado) from public.titulos_especiales te where te.user_id = p.id), '[]'::jsonb),
                                  'likes', 0, 'di_like', false, 'es_artista', false,
                                  'subidas', '[]'::jsonb, 'num_subidas', 0);
    end if;
    select count(*)::int into n_likes from public.likes_perfil where a = p.id;
    select coalesce(jsonb_agg(jsonb_build_object(
               'id', s.id, 'titulo', s.titulo, 'artista', s.artista, 'album', s.album,
               'duracion', s.duracion, 'ruta', s.ruta, 'portada', s.portada,
               'escuchas', s.escuchas, 'estado', s.estado, 'nota', s.nota, 'creado', s.creado)
               order by s.creado desc), '[]') into subidas
      from (select * from public.canciones_subidas
             where user_id = p.id and (estado = 'publicada' or p.id = yo)
             order by creado desc limit 60) s;
    if p.mostrar_top or p.id = yo then
        select coalesce(jsonb_agg(jsonb_build_object('nombre', initcap(a), 'portada', portada, 'veces', n)
                                  order by n desc), '[]') into top_art
        from (select lower(coalesce(datos -> 'artistas' -> 0 ->> 'nombre', datos ->> 'artista', '')) as a,
                     max(coalesce(datos ->> 'portada', datos ->> 'miniatura', '')) as portada,
                     count(*) as n
                from public.escuchas where user_id = p.id and fecha > now() - interval '30 days'
               group by 1 having lower(coalesce(datos -> 'artistas' -> 0 ->> 'nombre', datos ->> 'artista', '')) <> ''
               order by n desc limit 5) q;
        select coalesce(jsonb_agg(datos || jsonb_build_object('veces', n) order by n desc), '[]') into top_can
        from (select clave, max(datos::text)::jsonb as datos, count(*) as n
                from public.escuchas where user_id = p.id and fecha > now() - interval '30 days'
               group by clave order by n desc limit 5) q;
        select count(distinct (fecha at time zone 'America/Lima')::date) into dias
          from public.escuchas where user_id = p.id and fecha > now() - interval '60 days';
        select count(distinct lower(coalesce(datos -> 'artistas' -> 0 ->> 'nombre', datos ->> 'artista', '')))
          into artistas from public.escuchas where user_id = p.id and fecha > now() - interval '120 days';
        select count(*) into gustos from public.me_gusta where user_id = p.id;
        select coalesce(max(c), 0) into n_sem from (select count(*) c from public.escuchas
               where user_id = p.id group by date_trunc('week', fecha)) q;
        if p.creado < now() - interval '90 days' then
            insig := insig || jsonb_build_array(jsonb_build_object('clave', 'veterano', 'titulo', 'Veterano', 'detalle', 'Más de 3 meses en Caudal'));
        end if;
        if dias >= 30 then
            insig := insig || jsonb_build_array(jsonb_build_object('clave', 'fiel', 'titulo', 'Oyente fiel', 'detalle', dias || ' días con música en 2 meses'));
        end if;
        if artistas >= 50 then
            insig := insig || jsonb_build_array(jsonb_build_object('clave', 'explorador', 'titulo', 'Explorador', 'detalle', artistas || ' artistas distintos'));
        end if;
        if jsonb_array_length(subidas) > 0 then
            insig := insig || jsonb_build_array(jsonb_build_object('clave', 'creador', 'titulo', 'Creador', 'detalle', 'Sube su propia música'));
        end if;
        if gustos >= 100 then
            insig := insig || jsonb_build_array(jsonb_build_object('clave', 'coleccionista', 'titulo', 'Coleccionista', 'detalle', gustos || ' canciones favoritas'));
        end if;
        if n_sem >= 100 then
            insig := insig || jsonb_build_array(jsonb_build_object('clave', 'maratonista', 'titulo', 'Maratonista', 'detalle', n_sem || ' canciones en una semana'));
        end if;
    end if;
    return jsonb_build_object(
        'id', p.id, 'usuario', p.usuario, 'nombre', p.nombre, 'foto_url', p.foto_url,
        'banner_url', p.banner_url,
        'bio', p.bio, 'cancion_fav', p.cancion_fav, 'artista_fav', p.artista_fav,
        'generos', to_jsonb(p.generos), 'frase', p.frase, 'color_perfil', p.color_perfil,
        'creado', p.creado, 'relacion', rel, 'es_mio', p.id = yo,
        'publico', p.perfil_publico, 'mostrar_top', p.mostrar_top,
        'top_artistas', top_art, 'top_canciones', top_can, 'insignias', insig,
        'afinidad', case when p.id = yo then null else public.afinidad_entre(yo, p.id) end,
        'fundador', coalesce(p.numero <= 100, false), 'numero', p.numero,
        'fundador_caudal', exists (select 1 from public.titulos_especiales te
                                    where te.user_id = p.id and te.titulo = 'fundador_caudal'),
        'titulos', coalesce((select jsonb_agg(jsonb_build_object('clave', te.titulo, 'nombre', te.nombre)
                                order by te.creado) from public.titulos_especiales te
                              where te.user_id = p.id), '[]'::jsonb),
        'likes', n_likes, 'es_artista', n_likes >= 200,
        'subidas', subidas, 'num_subidas', jsonb_array_length(subidas),
        'di_like', exists (select 1 from public.likes_perfil l where l.a = p.id and l.quien = yo));
end $$;

-- ---------------------------------------------------------------- música de la gente
-- Canciones que sube la gente: una carpeta por persona, audio de hasta 15 MB.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('musica', 'musica', true, 15728640,
        array['audio/mpeg', 'audio/mp4', 'audio/x-m4a', 'audio/aac', 'audio/flac', 'audio/ogg',
              'audio/wav', 'audio/x-wav', 'audio/webm', 'image/jpeg', 'image/png', 'image/webp'])
on conflict (id) do update set public = true, file_size_limit = 15728640,
    allowed_mime_types = array['audio/mpeg', 'audio/mp4', 'audio/x-m4a', 'audio/aac', 'audio/flac',
        'audio/ogg', 'audio/wav', 'audio/x-wav', 'audio/webm', 'image/jpeg', 'image/png', 'image/webp'];

drop policy if exists "musica: subir la mia" on storage.objects;
create policy "musica: subir la mia" on storage.objects for insert to authenticated
    with check (bucket_id = 'musica' and (storage.foldername(name))[1] = auth.uid()::text);
drop policy if exists "musica: ver la mia" on storage.objects;
create policy "musica: ver la mia" on storage.objects for select to authenticated
    using (bucket_id = 'musica' and (storage.foldername(name))[1] = auth.uid()::text);
drop policy if exists "musica: borrar la mia" on storage.objects;
create policy "musica: borrar la mia" on storage.objects for delete to authenticated
    using (bucket_id = 'musica' and (storage.foldername(name))[1] = auth.uid()::text);


create table if not exists public.reportes_subidas (
    cancion  uuid not null references public.canciones_subidas (id) on delete cascade,
    quien    uuid not null references auth.users (id) on delete cascade,
    motivo   text not null default '' check (length(motivo) <= 300),
    creado   timestamptz not null default now(),
    primary key (cancion, quien)
);

alter table public.canciones_subidas enable row level security;
alter table public.reportes_subidas  enable row level security;
drop policy if exists "ver subidas" on public.canciones_subidas;
create policy "ver subidas" on public.canciones_subidas for select to authenticated
    using (estado = 'publicada' or user_id = auth.uid());
drop policy if exists "mis reportes" on public.reportes_subidas;
create policy "mis reportes" on public.reportes_subidas for select using (quien = auth.uid());

drop function if exists public.registrar_subida(text, text, int, text, text, bigint);
drop function if exists public.registrar_subida(text, text, text, int, text, text, bigint);
create function public.registrar_subida(p_titulo text, p_artista text, p_album text, p_duracion int,
                                        p_ruta text, p_portada text, p_tamano bigint)
returns uuid language plpgsql security definer set search_path = public as $$
declare yo uuid := auth.uid(); nuevo uuid;
begin
    if yo is null then raise exception 'sin sesion'; end if;
    if p_ruta not like yo::text || '/%' then raise exception 'ruta no valida'; end if;
    if p_portada is null or trim(p_portada) = '' then
        raise exception 'la cancion necesita una portada';
    end if;
    if p_portada not like yo::text || '/%' then raise exception 'ruta no valida'; end if;
    if (select count(*) from public.canciones_subidas where user_id = yo and estado <> 'retirada') >= 30 then
        raise exception 'ya subiste 30 canciones: borra alguna para subir otra';
    end if;
    if (select count(*) from public.canciones_subidas
         where user_id = yo and creado > now() - interval '1 day') >= 10 then
        raise exception 'hoy ya subiste 10 canciones: sigue manana';
    end if;
    insert into public.canciones_subidas (user_id, titulo, artista, album, duracion, ruta, portada, tamano, estado)
    values (yo, trim(p_titulo), coalesce(trim(p_artista), ''), coalesce(trim(p_album), ''),
            greatest(coalesce(p_duracion, 0), 0), p_ruta, p_portada, coalesce(p_tamano, 0),
            case when public.puede_publicar(yo) then 'publicada' else 'pendiente' end)
    returning id into nuevo;
    return nuevo;
end $$;

drop function if exists public.borrar_subida(uuid);
create function public.borrar_subida(p_id uuid)
returns void language sql security definer set search_path = public as $$
    delete from public.canciones_subidas where id = p_id and user_id = auth.uid();
$$;

drop function if exists public.explorar_subidas(text, int, int);
create function public.explorar_subidas(p_busqueda text default '', p_limite int default 40,
                                        p_desde int default 0)
returns table (id uuid, user_id uuid, usuario text, titulo text, artista text, album text,
               duracion int, ruta text, portada text, escuchas int, creado timestamptz, es_artista boolean)
language sql stable security definer set search_path = public as $$
    select s.id, s.user_id, p.usuario, s.titulo, s.artista, s.album, s.duracion, s.ruta, s.portada,
           s.escuchas, s.creado,
           (select count(*) from public.likes_perfil l where l.a = s.user_id) >= 200
    from public.canciones_subidas s join public.perfiles p on p.id = s.user_id
    where auth.uid() is not null and s.estado = 'publicada'
      and not public.hay_bloqueo(auth.uid(), s.user_id)
      and (coalesce(trim(p_busqueda), '') = ''
           or s.titulo ilike '%' || replace(replace(trim(p_busqueda), '%', ''), '_', '') || '%'
           or s.artista ilike '%' || replace(replace(trim(p_busqueda), '%', ''), '_', '') || '%')
    order by s.creado desc
    limit least(greatest(p_limite, 1), 100) offset greatest(p_desde, 0);
$$;

drop function if exists public.contar_escucha_subida(uuid);
create function public.contar_escucha_subida(p_id uuid)
returns void language sql security definer set search_path = public as $$
    update public.canciones_subidas set escuchas = escuchas + 1
     where id = p_id and estado = 'publicada' and auth.uid() is not null;
$$;

-- con 3 reportes de personas distintas, la canción se oculta hasta revisarla
drop function if exists public.reportar_subida(uuid, text);
create function public.reportar_subida(p_id uuid, p_motivo text)
returns void language plpgsql security definer set search_path = public as $$
begin
    if auth.uid() is null then raise exception 'sin sesion'; end if;
    insert into public.reportes_subidas (cancion, quien, motivo)
    values (p_id, auth.uid(), left(coalesce(p_motivo, ''), 300)) on conflict do nothing;
    update public.canciones_subidas set estado = 'revision'
     where id = p_id and estado = 'publicada'
       and (select count(*) from public.reportes_subidas where cancion = p_id) >= 3;
end $$;

-- ---------------------------------------------------------------- revisión de la música
-- ¿publica sin revisión? (fundadores de Caudal y moderadores) y ¿soy moderador?
drop function if exists public.publica_directo();
create function public.publica_directo()
returns boolean language sql stable security definer set search_path = public as $$
    select auth.uid() is not null and public.puede_publicar(auth.uid());
$$;

drop function if exists public.soy_moderador();
create function public.soy_moderador()
returns boolean language sql stable security definer set search_path = public as $$
    select exists (select 1 from public.moderadores where user_id = auth.uid());
$$;

-- lo que espera revisión: canciones nuevas y las que la gente reportó
drop function if exists public.revision_pendientes(int);
create function public.revision_pendientes(p_limite int default 60)
returns table (id uuid, user_id uuid, usuario text, nombre text, titulo text, artista text, album text,
               duracion int, ruta text, portada text, tamano bigint, estado text, reportes int,
               motivos jsonb, creado timestamptz)
language sql stable security definer set search_path = public as $$
    select s.id, s.user_id, p.usuario, p.nombre, s.titulo, s.artista, s.album, s.duracion, s.ruta,
           s.portada, s.tamano, s.estado,
           (select count(*)::int from public.reportes_subidas r where r.cancion = s.id),
           coalesce((select jsonb_agg(r.motivo) from public.reportes_subidas r
                      where r.cancion = s.id and r.motivo <> ''), '[]'::jsonb),
           s.creado
    from public.canciones_subidas s join public.perfiles p on p.id = s.user_id
    where public.soy_moderador() and s.estado in ('pendiente', 'revision')
    order by s.creado
    limit least(greatest(p_limite, 1), 200);
$$;

drop function if exists public.revision_contar();
create function public.revision_contar()
returns int language sql stable security definer set search_path = public as $$
    select case when public.soy_moderador()
                then (select count(*)::int from public.canciones_subidas where estado in ('pendiente', 'revision'))
                else 0 end;
$$;

-- aprobar (se publica) o rechazar (se retira, con el motivo que verá quien la subió)
drop function if exists public.revision_resolver(uuid, boolean, text);
create function public.revision_resolver(p_id uuid, p_aprobar boolean, p_nota text default '')
returns void language plpgsql security definer set search_path = public as $$
begin
    if not public.soy_moderador() then raise exception 'no tienes permiso para revisar'; end if;
    update public.canciones_subidas
       set estado = case when p_aprobar then 'publicada' else 'retirada' end,
           nota = case when p_aprobar then '' else left(coalesce(trim(p_nota), ''), 300) end
     where id = p_id and estado in ('pendiente', 'revision');
    if not found then raise exception 'esa cancion ya no esta pendiente'; end if;
    if p_aprobar then delete from public.reportes_subidas where cancion = p_id; end if;
end $$;

-- ---------------------------------------------------------------- borrar la cuenta
-- Al borrar la cuenta desaparece TODO lo suyo: filas (en cascada) y también las fotos y la
-- música que subió (lo exige Google Play).
drop function if exists public.eliminar_mi_cuenta();
create function public.eliminar_mi_cuenta()
returns void language plpgsql security definer set search_path = public, auth, storage as $$
begin
    if auth.uid() is null then
        raise exception 'sin sesion';
    end if;
    delete from storage.objects
     where bucket_id in ('avatares', 'musica')
       and (storage.foldername(name))[1] = auth.uid()::text;
    delete from auth.users where id = auth.uid();
end $$;
grant execute on function public.eliminar_mi_cuenta() to authenticated;
revoke execute on function public.eliminar_mi_cuenta() from anon;

-- ---------------------------------------------------------------- permisos
do $$
declare f text;
begin
    foreach f in array array[
        'enviar_solicitud(uuid)', 'responder_solicitud(bigint, boolean)', 'cancelar_solicitud(uuid)',
        'quitar_amigo(uuid)', 'bloquear(uuid)', 'desbloquear(uuid)', 'mis_bloqueados()',
        'mis_solicitudes()', 'mis_enviadas()', 'mis_amigos()', 'buscar_persona(text)',
        'abrir_chat(uuid)', 'mis_chats()', 'explorar_perfiles(text, int, int)', 'ver_perfil(text)',
        'dar_like(uuid)', 'quitar_like(uuid)', 'publica_directo()', 'soy_moderador()',
        'revision_pendientes(int)', 'revision_contar()', 'revision_resolver(uuid, boolean, text)', 'registrar_subida(text, text, text, int, text, text, bigint)', 'borrar_subida(uuid)',
        'explorar_subidas(text, int, int)', 'contar_escucha_subida(uuid)', 'reportar_subida(uuid, text)']
    loop
        execute format('revoke execute on function public.%s from public, anon', f);
        execute format('grant execute on function public.%s to authenticated', f);
    end loop;
end $$;
-- ayudas internas: nadie las llama desde la app
revoke execute on function public.es_mayor(uuid), public.relacion_con(uuid),
    public.afinidad_entre(uuid, uuid), public.puede_publicar(uuid) from public, anon, authenticated;
-- estas dos las usan las políticas de seguridad, así que quien escribe debe poder ejecutarlas
-- (por dentro solo responden sobre quien las llama)
revoke execute on function public.son_amigos(uuid, uuid), public.hay_bloqueo(uuid, uuid) from public, anon;
grant execute on function public.son_amigos(uuid, uuid), public.hay_bloqueo(uuid, uuid) to authenticated;


-- ---------------------------------------------------------------- Donadores y fondo de Caudal
-- «Donador de Caudal» lo asigna solo quien administra la base (igual que los demás títulos).
-- Quien lo tiene, y las dos cuentas fundadoras, pueden poner una imagen de fondo en toda la app.
alter table public.perfiles add column if not exists fondo_url text;                       -- <mi id>/fondo.jpg
alter table public.perfiles add column if not exists fondo_visible smallint not null default 22;   -- % de imagen que se ve
alter table public.perfiles add column if not exists fondo_desenfoque smallint not null default 0; -- 0 a 20

alter table public.perfiles drop constraint if exists perfil_limites;
alter table public.perfiles add constraint perfil_limites check (
    length(bio) <= 300
    and length(frase) <= 80
    and length(artista_fav) <= 80
    and coalesce(array_length(generos, 1), 0) <= 5
    and (color_perfil is null or color_perfil ~ '^#[0-9A-Fa-f]{6}$')
    and (cancion_fav is null or pg_column_size(cancion_fav) < 3000)
    and (foto_url is null or foto_url like id::text || '/%')
    and (banner_url is null or banner_url like id::text || '/%')
    and (fondo_url is null or fondo_url like id::text || '/%')
    and fondo_visible between 5 and 60
    and fondo_desenfoque between 0 and 20
);

insert into public.titulos_especiales (user_id, titulo, nombre)
select id, 'donador_caudal', 'Donador de Caudal' from public.perfiles
where usuario in ('arkhux', 'ibxo', 'marieliuwu', 'franzz')
on conflict do nothing;

-- ¿esta persona puede tener fondo? (donadores y fundadores)
create or replace function public.puede_tener_fondo(p_id uuid)
returns boolean language sql stable security definer set search_path = public as $$
    select exists (select 1 from public.titulos_especiales
                   where user_id = p_id and titulo in ('donador_caudal', 'fundador_caudal'));
$$;

-- lo que llama la app para saber si muestra la opción (solo responde sobre quien pregunta)
create or replace function public.puede_poner_fondo()
returns boolean language sql stable security definer set search_path = public as $$
    select auth.uid() is not null and public.puede_tener_fondo(auth.uid());
$$;

-- el servidor manda: sin título no se guarda ningún fondo, aunque alguien escriba la columna a mano
create or replace function public.perfil_validar()
returns trigger language plpgsql security definer set search_path = public as $$
begin
    if new.perfil_publico and not (new.fecha_nacimiento is not null
                                   and age(new.fecha_nacimiento) >= interval '18 years') then
        new.perfil_publico := false;
    end if;
    if new.fondo_url is not null and not public.puede_tener_fondo(new.id) then
        new.fondo_url := null;
    end if;
    return new;
end $$;

-- y el almacén: solo quien puede tener fondo sube el archivo «fondo.*» de su carpeta
drop policy if exists "avatar: subir el mio" on storage.objects;
create policy "avatar: subir el mio" on storage.objects for insert to authenticated
    with check (bucket_id = 'avatares' and (storage.foldername(name))[1] = auth.uid()::text
                and (name not like '%/fondo.%' or public.puede_tener_fondo(auth.uid())));
drop policy if exists "avatar: cambiar el mio" on storage.objects;
create policy "avatar: cambiar el mio" on storage.objects for update to authenticated
    using (bucket_id = 'avatares' and (storage.foldername(name))[1] = auth.uid()::text)
    with check (bucket_id = 'avatares' and (storage.foldername(name))[1] = auth.uid()::text
                and (name not like '%/fondo.%' or public.puede_tener_fondo(auth.uid())));

-- el fondo pesa más que una foto de perfil: el cubo admite hasta 5 MB
update storage.buckets set file_size_limit = 5242880 where id = 'avatares';

revoke execute on function public.puede_tener_fondo(uuid) from public, anon;
grant execute on function public.puede_tener_fondo(uuid) to authenticated;
revoke execute on function public.puede_poner_fondo() from public, anon;
grant execute on function public.puede_poner_fondo() to authenticated;

-- ---------------------------------------------------------------- Artistas favoritos (gustos)
-- Al crear la cuenta la persona puede elegir sus artistas (o saltarlo). Sirven para recomendar.
-- gustos: [{"nombre": "...", "id": "<id de artista en el catálogo>", "portada": "<url>"}], hasta 30.
alter table public.perfiles add column if not exists gustos jsonb not null default '[]'::jsonb;
do $$
begin
    -- las cuentas que ya existían no vuelven a ver la pantalla de elegir artistas
    if not exists (select 1 from information_schema.columns
                   where table_schema = 'public' and table_name = 'perfiles' and column_name = 'gustos_elegidos') then
        alter table public.perfiles add column gustos_elegidos boolean not null default false;
        update public.perfiles set gustos_elegidos = true;
    end if;
end $$;
alter table public.perfiles add column if not exists gustos_elegidos boolean not null default false;
alter table public.perfiles drop constraint if exists perfil_gustos_limites;
alter table public.perfiles add constraint perfil_gustos_limites check (
    jsonb_typeof(gustos) = 'array' and jsonb_array_length(gustos) <= 30 and pg_column_size(gustos) < 24000
);

-- ---------------------------------------------------------------- GIF en la foto y el fondo del perfil (donadores y fundadores)
update storage.buckets set allowed_mime_types = array['image/jpeg', 'image/png', 'image/webp', 'image/gif'] where id = 'avatares';

-- el servidor manda: un GIF en la foto o en el fondo del perfil solo lo guarda quien puede
create or replace function public.perfil_validar()
returns trigger language plpgsql security definer set search_path = public as $$
begin
    if new.perfil_publico and not (new.fecha_nacimiento is not null
                                   and age(new.fecha_nacimiento) >= interval '18 years') then
        new.perfil_publico := false;
    end if;
    if new.fondo_url is not null and not public.puede_tener_fondo(new.id) then
        new.fondo_url := null;
    end if;
    if not public.puede_tener_fondo(new.id) then
        if new.foto_url ~* '\.gif$' then
            new.foto_url := case when tg_op = 'UPDATE' and old.foto_url !~* '\.gif$' then old.foto_url else null end;
        end if;
        if new.banner_url ~* '\.gif$' then
            new.banner_url := case when tg_op = 'UPDATE' and old.banner_url !~* '\.gif$' then old.banner_url else null end;
        end if;
    end if;
    return new;
end $$;

-- y el almacén: los archivos .gif de la carpeta propia solo los sube quien puede
drop policy if exists "avatar: subir el mio" on storage.objects;
create policy "avatar: subir el mio" on storage.objects for insert to authenticated
    with check (bucket_id = 'avatares' and (storage.foldername(name))[1] = auth.uid()::text
                and ((name not like '%/fondo.%' and name not ilike '%.gif') or public.puede_tener_fondo(auth.uid())));
drop policy if exists "avatar: cambiar el mio" on storage.objects;
create policy "avatar: cambiar el mio" on storage.objects for update to authenticated
    using (bucket_id = 'avatares' and (storage.foldername(name))[1] = auth.uid()::text)
    with check (bucket_id = 'avatares' and (storage.foldername(name))[1] = auth.uid()::text
                and ((name not like '%/fondo.%' and name not ilike '%.gif') or public.puede_tener_fondo(auth.uid())));
