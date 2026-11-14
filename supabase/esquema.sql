-- =====================================================================
--  Caudal: cuentas y biblioteca compartidas entre Android, Windows e iOS
--
--  Pegar entero en Supabase -> SQL Editor -> New query -> Run.
--  Se puede ejecutar varias veces sin romper nada.
--
--  Las canciones descargadas NO se suben: viven en cada dispositivo.
--  Aqui solo va lo que debe verse igual en todos: perfil, me gusta,
--  listas, albumes/artistas guardados, escuchas recientes y ajustes.
--
--  Cada fila lleva user_id y la seguridad por filas (RLS) hace que cada
--  usuario solo pueda leer y escribir lo suyo, aunque la clave publica
--  (anon key) vaya dentro de las apps.
-- =====================================================================

-- ---------- perfil: el nombre de usuario con el que se entra
create table if not exists public.perfiles (
    id         uuid primary key references auth.users (id) on delete cascade,
    usuario    text not null unique check (usuario ~ '^[a-z0-9._-]{3,30}$'),
    nombre     text not null default '',
    creado     timestamptz not null default now()
);

-- se crea solo al registrarse (los datos vienen en raw_user_meta_data).
-- Con Google no hay "usuario": se toma lo de antes de la @ del correo y, si
-- ya existe, se le pone un numero (luis, luis2, luis3...).
create or replace function public.crear_perfil()
returns trigger language plpgsql security definer set search_path = public as $$
declare
    base text;
    candidato text;
    n int := 1;
begin
    -- con usuario y contraseña viene "usuario"; con Google, el correo real
    base := lower(coalesce(new.raw_user_meta_data ->> 'usuario', split_part(new.email, '@', 1)));
    base := regexp_replace(base, '[^a-z0-9._-]', '', 'g');
    if length(base) < 3 then base := base || 'caudal'; end if;
    base := left(base, 26);
    candidato := base;
    while exists (select 1 from public.perfiles p where p.usuario = candidato) loop
        n := n + 1;
        candidato := base || n::text;
    end loop;
    insert into public.perfiles (id, usuario, nombre)
    values (new.id, candidato,
            coalesce(nullif(new.raw_user_meta_data ->> 'nombre', ''),
                     nullif(new.raw_user_meta_data ->> 'full_name', ''),
                     nullif(new.raw_user_meta_data ->> 'name', ''), ''))
    on conflict (id) do nothing;
    return new;
end $$;

drop trigger if exists al_crear_usuario on auth.users;
create trigger al_crear_usuario after insert on auth.users
    for each row execute function public.crear_perfil();

-- ---------- me gusta
create table if not exists public.me_gusta (
    user_id    uuid not null references auth.users (id) on delete cascade default auth.uid(),
    clave      text not null,               -- "yt:<videoId>"
    datos      jsonb not null default '{}', -- titulo, artistas, album, portada, duracion
    fecha      timestamptz not null default now(),
    primary key (user_id, clave)
);

-- ---------- listas propias
create table if not exists public.listas (
    id          uuid primary key default gen_random_uuid(),
    user_id     uuid not null references auth.users (id) on delete cascade default auth.uid(),
    nombre      text not null,
    descripcion text not null default '',
    fijada      boolean not null default false,
    creada      timestamptz not null default now(),
    actualizada timestamptz not null default now()
);

create table if not exists public.lista_items (
    lista_id   uuid not null references public.listas (id) on delete cascade,
    user_id    uuid not null references auth.users (id) on delete cascade default auth.uid(),
    clave      text not null,
    datos      jsonb not null default '{}',
    orden      double precision not null default 0,
    agregada   timestamptz not null default now(),
    primary key (lista_id, clave)
);

-- ---------- albumes, listas de YouTube y artistas guardados
create table if not exists public.guardados (
    user_id    uuid not null references auth.users (id) on delete cascade default auth.uid(),
    tipo       text not null check (tipo in ('album', 'lista', 'artista')),
    id         text not null,
    datos      jsonb not null default '{}',
    fecha      timestamptz not null default now(),
    primary key (user_id, tipo, id)
);

-- ---------- escuchas (para "Volver a escuchar" y los mixes)
create table if not exists public.escuchas (
    id         bigint generated always as identity primary key,
    user_id    uuid not null references auth.users (id) on delete cascade default auth.uid(),
    clave      text not null,
    datos      jsonb not null default '{}',
    contexto   jsonb,
    fecha      timestamptz not null default now()
);
create index if not exists escuchas_usuario_fecha on public.escuchas (user_id, fecha desc);

-- ---------- ajustes que conviene compartir (calidad, ecualizador, region...)
create table if not exists public.ajustes (
    user_id     uuid primary key references auth.users (id) on delete cascade default auth.uid(),
    datos       jsonb not null default '{}',
    actualizado timestamptz not null default now()
);

-- ---------- seguridad: cada uno solo ve y toca lo suyo
alter table public.perfiles    enable row level security;
alter table public.me_gusta    enable row level security;
alter table public.listas      enable row level security;
alter table public.lista_items enable row level security;
alter table public.guardados   enable row level security;
alter table public.escuchas    enable row level security;
alter table public.ajustes     enable row level security;

do $$
declare t text;
begin
    foreach t in array array['me_gusta', 'listas', 'lista_items', 'guardados', 'escuchas', 'ajustes']
    loop
        execute format('drop policy if exists "solo lo mio" on public.%I', t);
        execute format('create policy "solo lo mio" on public.%I for all '
                       'using (user_id = auth.uid()) with check (user_id = auth.uid())', t);
    end loop;
end $$;

drop policy if exists "mi perfil" on public.perfiles;
create policy "mi perfil" on public.perfiles for all
    using (id = auth.uid()) with check (id = auth.uid());

-- comprobar si un usuario esta libre antes de registrarse (sin exponer nada mas)
drop function if exists public.usuario_libre(text);
create function public.usuario_libre(p_usuario text)
returns boolean language sql security definer set search_path = public as $$
    select not exists (select 1 from public.perfiles p where p.usuario = lower(p_usuario));
$$;
grant execute on function public.usuario_libre(text) to anon, authenticated;

-- las escuchas viejas se recortan solas: se guardan las 2000 ultimas por usuario
create or replace function public.recortar_escuchas()
returns trigger language plpgsql security definer set search_path = public as $$
begin
    delete from public.escuchas
    where user_id = new.user_id
      and id not in (select id from public.escuchas where user_id = new.user_id
                     order by fecha desc limit 2000);
    return null;
end $$;
drop trigger if exists al_escuchar on public.escuchas;
create trigger al_escuchar after insert on public.escuchas
    for each row execute function public.recortar_escuchas();
-- ================================================================ chat
-- Conversaciones de dos personas (como los mensajes de Spotify): texto y
-- canciones compartidas. Solo las dos personas del chat lo ven.

create table if not exists public.chats (
    id        uuid primary key default gen_random_uuid(),
    a         uuid not null references auth.users (id) on delete cascade,
    b         uuid not null references auth.users (id) on delete cascade,
    creado    timestamptz not null default now(),
    ultimo    timestamptz not null default now(),
    leido_a   timestamptz not null default now(),
    leido_b   timestamptz not null default now(),
    unique (a, b),
    check (a < b)
);

create table if not exists public.mensajes (
    id        bigint generated always as identity primary key,
    chat      uuid not null references public.chats (id) on delete cascade,
    autor     uuid not null references auth.users (id) on delete cascade default auth.uid(),
    texto     text not null default '' check (length(texto) <= 2000),
    pista     jsonb,
    creado    timestamptz not null default now(),
    check (length(texto) > 0 or pista is not null)
);
create index if not exists mensajes_chat_id on public.mensajes (chat, id);

alter table public.chats    enable row level security;
alter table public.mensajes enable row level security;

drop policy if exists "mis chats" on public.chats;
create policy "mis chats" on public.chats for select
    using (auth.uid() in (a, b));

drop policy if exists "mensajes de mis chats" on public.mensajes;
create policy "mensajes de mis chats" on public.mensajes for select
    using (exists (select 1 from public.chats c where c.id = chat and auth.uid() in (c.a, c.b)));

drop policy if exists "escribo en mis chats" on public.mensajes;
create policy "escribo en mis chats" on public.mensajes for insert
    with check (autor = auth.uid()
                and exists (select 1 from public.chats c where c.id = chat and auth.uid() in (c.a, c.b)));

-- al llegar un mensaje, el chat sube y quien escribe ya lo tiene leido
create or replace function public.al_mensaje()
returns trigger language plpgsql security definer set search_path = public as $$
begin
    update public.chats set ultimo = new.creado,
        leido_a = case when a = new.autor then new.creado else leido_a end,
        leido_b = case when b = new.autor then new.creado else leido_b end
    where id = new.chat;
    return new;
end $$;
drop trigger if exists al_mensaje on public.mensajes;
create trigger al_mensaje after insert on public.mensajes
    for each row execute function public.al_mensaje();

-- buscar a alguien por su usuario EXACTO (no se puede listar a nadie)
drop function if exists public.buscar_persona(text);
create function public.buscar_persona(p_usuario text)
returns table (id uuid, usuario text, nombre text)
language sql stable security definer set search_path = public as $$
    select p.id, p.usuario, p.nombre from public.perfiles p
    where p.usuario = lower(trim(p_usuario)) and p.id <> auth.uid();
$$;

drop function if exists public.abrir_chat(uuid);
create function public.abrir_chat(p_otro uuid)
returns uuid language plpgsql security definer set search_path = public as $$
declare
    yo uuid := auth.uid();
    x uuid; y uuid; r uuid;
begin
    if yo is null or p_otro is null or p_otro = yo then
        raise exception 'chat no valido';
    end if;
    if not exists (select 1 from public.perfiles where id = p_otro) then
        raise exception 'esa persona no existe';
    end if;
    x := least(yo, p_otro); y := greatest(yo, p_otro);
    insert into public.chats (a, b) values (x, y) on conflict (a, b) do nothing;
    select id into r from public.chats where a = x and b = y;
    return r;
end $$;

drop function if exists public.mis_chats();
create function public.mis_chats()
returns table (id uuid, otro uuid, usuario text, nombre text, ultimo timestamptz,
               ultimo_texto text, ultimo_pista jsonb, ultimo_autor uuid, sin_leer int)
language sql stable security definer set search_path = public as $$
    select c.id,
           o.id, o.usuario, o.nombre, c.ultimo,
           m.texto, m.pista, m.autor,
           (select count(*)::int from public.mensajes n
             where n.chat = c.id and n.autor <> auth.uid()
               and n.creado > case when c.a = auth.uid() then c.leido_a else c.leido_b end)
    from public.chats c
    join public.perfiles o on o.id = case when c.a = auth.uid() then c.b else c.a end
    left join lateral (select texto, pista, autor from public.mensajes
                       where chat = c.id order by id desc limit 1) m on true
    where auth.uid() in (c.a, c.b)
    order by c.ultimo desc;
$$;

drop function if exists public.marcar_leido(uuid);
create function public.marcar_leido(p_chat uuid)
returns void language sql security definer set search_path = public as $$
    update public.chats set
        leido_a = case when a = auth.uid() then now() else leido_a end,
        leido_b = case when b = auth.uid() then now() else leido_b end
    where id = p_chat and auth.uid() in (a, b);
$$;

-- ================================================================ mezcla
-- "Mezcla con un amigo": junta lo que mas escuchan las dos personas de un chat
-- (ultimos 120 dias y sus me gusta) y dice cuanto se parecen sus gustos.
-- Solo funciona entre las dos personas del chat.
drop function if exists public.mezcla(uuid);
create function public.mezcla(p_chat uuid)
returns jsonb language plpgsql stable security definer set search_path = public as $$
declare
    c public.chats;
    resultado jsonb;
begin
    select * into c from public.chats where id = p_chat and auth.uid() in (a, b);
    if c.id is null then
        raise exception 'no es tu chat';
    end if;
    with puntos as (
        select user_id, clave, max(datos::text)::jsonb as datos, count(*)::float as n
        from public.escuchas
        where user_id in (c.a, c.b) and fecha > now() - interval '120 days' and clave like 'yt:%'
        group by user_id, clave
        union all
        select user_id, clave, datos, 3.0 from public.me_gusta
        where user_id in (c.a, c.b) and clave like 'yt:%'
    ), por_persona as (
        select user_id, clave, max(datos::text)::jsonb as datos, sum(n) as n
        from puntos group by user_id, clave
    ), ranking as (
        select *, row_number() over (partition by user_id order by n desc) as pos
        from por_persona
    ), artistas as (
        select user_id, lower(coalesce(datos->'artistas'->0->>'nombre', datos->>'artista', '')) as artista,
               sum(n) as n
        from por_persona group by 1, 2
    ), afinidad as (
        select coalesce(sum(least(x.n, y.n)) / nullif(greatest(
                   (select sum(n) from artistas where user_id = c.a),
                   (select sum(n) from artistas where user_id = c.b)), 0), 0) as v
        from artistas x join artistas y on x.artista = y.artista and x.artista <> ''
        where x.user_id = c.a and y.user_id = c.b
    ), comunes as (
        select x.clave, x.datos, x.n + y.n as n from ranking x join ranking y on x.clave = y.clave
        where x.user_id = c.a and y.user_id = c.b
    ), alternas as (
        select r.clave, r.datos, r.pos, r.user_id from ranking r
        where r.pos <= 25 and r.clave not in (select clave from comunes)
    )
    select jsonb_build_object(
        'afinidad', round((least(1.0, (select v from afinidad) * 1.6) * 100)::numeric),
        'comunes', coalesce((select jsonb_agg(datos order by n desc) from (select * from comunes order by n desc limit 15) q), '[]'),
        'mezcla', coalesce((select jsonb_agg(datos order by pos, user_id) from alternas), '[]'),
        'artistas_comunes', coalesce((select jsonb_agg(nombre) from (
            select initcap(x.artista) as nombre from artistas x join artistas y on x.artista = y.artista
            where x.user_id = c.a and y.user_id = c.b and x.artista <> ''
            order by least(x.n, y.n) desc limit 5) q), '[]')
    ) into resultado;
    return resultado;
end $$;

grant execute on function public.buscar_persona(text) to authenticated;
grant execute on function public.abrir_chat(uuid) to authenticated;
grant execute on function public.mis_chats() to authenticated;
grant execute on function public.marcar_leido(uuid) to authenticated;
grant execute on function public.mezcla(uuid) to authenticated;
revoke execute on function public.buscar_persona(text) from anon;
revoke execute on function public.abrir_chat(uuid) from anon;
revoke execute on function public.mis_chats() from anon;
revoke execute on function public.marcar_leido(uuid) from anon;
revoke execute on function public.mezcla(uuid) from anon;
-- ================================================================ terminos y datos
-- Constancia de que cada persona acepto los terminos (version y fecha) y de si
-- quiere compartir sus datos de uso anonimos (opcional, se puede retirar).
alter table public.perfiles add column if not exists terminos_version text;
alter table public.perfiles add column if not exists terminos_fecha timestamptz;
alter table public.perfiles add column if not exists comparte_datos boolean not null default false;
alter table public.perfiles add column if not exists comparte_fecha timestamptz;

-- al registrarse, la aceptacion llega en los datos de la cuenta
create or replace function public.crear_perfil()
returns trigger language plpgsql security definer set search_path = public as $$
declare
    base text;
    candidato text;
    n int := 1;
    comparte boolean := coalesce((new.raw_user_meta_data ->> 'comparte_datos')::boolean, false);
begin
    base := lower(coalesce(new.raw_user_meta_data ->> 'usuario', split_part(new.email, '@', 1)));
    base := regexp_replace(base, '[^a-z0-9._-]', '', 'g');
    if length(base) < 3 then base := base || 'caudal'; end if;
    base := left(base, 26);
    candidato := base;
    while exists (select 1 from public.perfiles p where p.usuario = candidato) loop
        n := n + 1;
        candidato := base || n::text;
    end loop;
    insert into public.perfiles (id, usuario, nombre, terminos_version, terminos_fecha,
                                 comparte_datos, comparte_fecha)
    values (new.id, candidato,
            coalesce(nullif(new.raw_user_meta_data ->> 'nombre', ''),
                     nullif(new.raw_user_meta_data ->> 'full_name', ''),
                     nullif(new.raw_user_meta_data ->> 'name', ''), ''),
            nullif(new.raw_user_meta_data ->> 'terminos', ''),
            case when nullif(new.raw_user_meta_data ->> 'terminos', '') is not null then now() end,
            comparte, case when comparte then now() end)
    on conflict (id) do nothing;
    return new;
end $$;

-- aceptar (o volver a aceptar tras un cambio) y elegir si se comparte
drop function if exists public.aceptar_terminos(text, boolean);
create function public.aceptar_terminos(p_version text, p_comparte boolean)
returns void language sql security definer set search_path = public as $$
    update public.perfiles set
        terminos_version = p_version, terminos_fecha = now(),
        comparte_datos = p_comparte,
        comparte_fecha = case when p_comparte <> comparte_datos or comparte_fecha is null then now() else comparte_fecha end
    where id = auth.uid();
$$;

drop function if exists public.compartir_datos(boolean);
create function public.compartir_datos(p_comparte boolean)
returns void language sql security definer set search_path = public as $$
    update public.perfiles set comparte_datos = p_comparte, comparte_fecha = now() where id = auth.uid();
$$;

-- borrar la cuenta y TODO lo suyo (lo exige Google Play)
drop function if exists public.eliminar_mi_cuenta();
create function public.eliminar_mi_cuenta()
returns void language plpgsql security definer set search_path = public, auth as $$
begin
    if auth.uid() is null then
        raise exception 'sin sesion';
    end if;
    delete from auth.users where id = auth.uid();
end $$;

grant execute on function public.aceptar_terminos(text, boolean) to authenticated;
grant execute on function public.compartir_datos(boolean) to authenticated;
grant execute on function public.eliminar_mi_cuenta() to authenticated;
revoke execute on function public.aceptar_terminos(text, boolean) from anon;
revoke execute on function public.compartir_datos(boolean) from anon;
revoke execute on function public.eliminar_mi_cuenta() from anon;

-- Lo UNICO que se puede compartir con terceros: totales anonimos de quienes
-- dieron permiso, sin id, usuario, nombre ni correo, y solo grupos de al
-- menos 10 personas (para que nadie se pueda reconocer). Solo lo lee el
-- dueno del proyecto (service_role), nunca la app.
create or replace view public.datos_anonimos
with (security_invoker = true) as
select
    date_trunc('week', e.fecha)::date as semana,
    extract(hour from e.fecha at time zone 'America/Lima')::int as hora,
    coalesce(e.datos -> 'artistas' -> 0 ->> 'nombre', e.datos ->> 'artista', 'desconocido') as artista,
    count(*) as escuchas,
    count(distinct e.user_id) as personas,
    round(sum(least(coalesce((e.datos ->> 'duracion')::numeric, 210), 900)) / 60) as minutos
from public.escuchas e
join public.perfiles p on p.id = e.user_id and p.comparte_datos
group by 1, 2, 3
having count(distinct e.user_id) >= 10;

revoke all on public.datos_anonimos from anon, authenticated;
-- ================================================================ datos basicos del perfil
-- Fecha de nacimiento (para comprobar la edad), pais y genero (opcional).
alter table public.perfiles add column if not exists fecha_nacimiento date;
alter table public.perfiles add column if not exists pais text;
alter table public.perfiles add column if not exists genero text
    check (genero is null or genero in ('mujer', 'hombre', 'otro', 'no_decir'));
alter table public.perfiles add column if not exists permiso_tutor boolean not null default false;

create or replace function public.crear_perfil()
returns trigger language plpgsql security definer set search_path = public as $$
declare
    base text;
    candidato text;
    n int := 1;
    m jsonb := coalesce(new.raw_user_meta_data, '{}'::jsonb);
    comparte boolean := coalesce((m ->> 'comparte_datos')::boolean, false);
begin
    base := lower(coalesce(m ->> 'usuario', split_part(new.email, '@', 1)));
    base := regexp_replace(base, '[^a-z0-9._-]', '', 'g');
    if length(base) < 3 then base := base || 'caudal'; end if;
    base := left(base, 26);
    candidato := base;
    while exists (select 1 from public.perfiles p where p.usuario = candidato) loop
        n := n + 1;
        candidato := base || n::text;
    end loop;
    insert into public.perfiles (id, usuario, nombre, terminos_version, terminos_fecha,
                                 comparte_datos, comparte_fecha, fecha_nacimiento, pais, genero, permiso_tutor)
    values (new.id, candidato,
            coalesce(nullif(m ->> 'nombre', ''), nullif(m ->> 'full_name', ''), nullif(m ->> 'name', ''), ''),
            nullif(m ->> 'terminos', ''),
            case when nullif(m ->> 'terminos', '') is not null then now() end,
            comparte, case when comparte then now() end,
            nullif(m ->> 'fecha_nacimiento', '')::date,
            nullif(m ->> 'pais', ''),
            nullif(m ->> 'genero', ''),
            coalesce((m ->> 'permiso_tutor')::boolean, false))
    on conflict (id) do nothing;
    return new;
end $$;

-- completar o corregir los datos basicos (cuentas de antes de pedirlos)
drop function if exists public.completar_perfil(text, date, text, text, boolean);
create function public.completar_perfil(p_nombre text, p_nacimiento date, p_pais text,
                                        p_genero text, p_permiso_tutor boolean)
returns void language plpgsql security definer set search_path = public as $$
begin
    if p_nacimiento is null or p_nacimiento > current_date or p_nacimiento < date '1900-01-01' then
        raise exception 'fecha de nacimiento no valida';
    end if;
    if age(p_nacimiento) < interval '14 years' and not coalesce(p_permiso_tutor, false) then
        raise exception 'menor sin permiso';
    end if;
    update public.perfiles set
        nombre = coalesce(nullif(trim(p_nombre), ''), nombre),
        fecha_nacimiento = p_nacimiento,
        pais = nullif(trim(p_pais), ''),
        genero = nullif(p_genero, ''),
        permiso_tutor = coalesce(p_permiso_tutor, false)
    where id = auth.uid();
end $$;
grant execute on function public.completar_perfil(text, date, text, text, boolean) to authenticated;
revoke execute on function public.completar_perfil(text, date, text, text, boolean) from anon;

-- las estadisticas anonimas pueden ir por rango de edad, pais y genero
-- (siempre grupos de 10 personas o mas, y solo de quienes dieron permiso)
drop view if exists public.datos_anonimos;
create view public.datos_anonimos
with (security_invoker = true) as
select
    date_trunc('week', e.fecha)::date as semana,
    extract(hour from e.fecha at time zone 'America/Lima')::int as hora,
    coalesce(e.datos -> 'artistas' -> 0 ->> 'nombre', e.datos ->> 'artista', 'desconocido') as artista,
    coalesce(p.pais, 'desconocido') as pais,
    case
        when p.fecha_nacimiento is null then 'desconocido'
        when age(p.fecha_nacimiento) < interval '18 years' then 'menos de 18'
        when age(p.fecha_nacimiento) < interval '25 years' then '18-24'
        when age(p.fecha_nacimiento) < interval '35 years' then '25-34'
        when age(p.fecha_nacimiento) < interval '45 years' then '35-44'
        when age(p.fecha_nacimiento) < interval '55 years' then '45-54'
        else '55 o mas'
    end as edad,
    coalesce(p.genero, 'no_decir') as genero,
    count(*) as escuchas,
    count(distinct e.user_id) as personas,
    round(sum(least(coalesce((e.datos ->> 'duracion')::numeric, 210), 900)) / 60) as minutos
from public.escuchas e
join public.perfiles p on p.id = e.user_id and p.comparte_datos
    and (p.fecha_nacimiento is null or age(p.fecha_nacimiento) >= interval '18 years')
group by 1, 2, 3, 4, 5, 6
having count(distinct e.user_id) >= 10;
revoke all on public.datos_anonimos from anon, authenticated;
