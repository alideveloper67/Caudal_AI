-- ================================================================ Caudal listas compartidas
-- Listas que se comparten con un código, listas colaborativas (varias personas añaden
-- música a la misma lista) y listas que viajan por el chat.
--
-- Se pega entero en el SQL Editor de Supabase DESPUÉS de esquema.sql y de social.sql.
-- Se puede repetir sin romper nada. Si algún día se vuelve a ejecutar esquema.sql, hay que
-- volver a ejecutar también este archivo (esquema.sql recrea la política antigua de lista_items).
--
-- Reglas de seguridad que fijan estas tablas (no dependen de la app):
--   · Una lista solo la ve y la cambia su dueño; el resto entra por las funciones de abajo.
--   · El código decide qué permiso recibe quien se une: «colaborador» (puede añadir) u
--     «oyente» (solo escucha). Un bloqueo entre las dos personas corta todo acceso.
--   · Máximo 20 miembros por lista y 2 000 canciones por lista compartida.
--   · lista_miembros y lista_codigos no se pueden tocar desde la API: solo con las funciones.

-- ---------------------------------------------------------------- tablas
create table if not exists public.lista_miembros (
    lista_id  uuid not null references public.listas (id) on delete cascade,
    user_id   uuid not null references auth.users (id) on delete cascade,
    rol       text not null check (rol in ('colaborador', 'oyente')),
    desde     timestamptz not null default now(),
    primary key (lista_id, user_id)
);
create index if not exists lista_miembros_usuario on public.lista_miembros (user_id);

create table if not exists public.lista_codigos (
    codigo    text primary key check (codigo ~ '^[ABCDEFGHJKMNPQRSTUVWXYZ23456789]{8}$'),
    lista_id  uuid not null unique references public.listas (id) on delete cascade,
    rol       text not null default 'colaborador' check (rol in ('colaborador', 'oyente')),
    creado    timestamptz not null default now()
);

alter table public.lista_miembros enable row level security;
alter table public.lista_codigos  enable row level security;
-- sin ninguna política y sin permisos: nadie las lee ni escribe desde la app
revoke all on public.lista_miembros from anon, authenticated;
revoke all on public.lista_codigos  from anon, authenticated;

-- ---------------------------------------------------------------- canciones de la lista
-- Antes cada quien veía solo las filas con su user_id. Ahora el dueño de la lista ve y cambia
-- TODAS las canciones de su lista (también las que añadieron colaboradores).
drop policy if exists "solo lo mio" on public.lista_items;
drop policy if exists "lista_items: dueno de la lista" on public.lista_items;
create policy "lista_items: dueno de la lista" on public.lista_items for all
    using (exists (select 1 from public.listas l where l.id = lista_id and l.user_id = auth.uid()))
    with check (exists (select 1 from public.listas l where l.id = lista_id and l.user_id = auth.uid()));

-- ---------------------------------------------------------------- listas en el chat
alter table public.mensajes add column if not exists lista jsonb;

-- la restricción de antes (texto o pista) se cambia por: texto, pista o lista
do $$
declare r record;
begin
    for r in select conname from pg_constraint
              where conrelid = 'public.mensajes'::regclass and contype = 'c'
                and pg_get_constraintdef(oid) ilike '%pista IS NOT NULL%'
                and conname <> 'mensajes_contenido'
    loop
        execute format('alter table public.mensajes drop constraint %I', r.conname);
    end loop;
end $$;
alter table public.mensajes drop constraint if exists mensajes_contenido;
alter table public.mensajes add constraint mensajes_contenido check (
    (length(texto) > 0 or pista is not null or lista is not null)
    and (lista is null or (jsonb_typeof(lista) = 'object' and lista ? 'codigo'
                           and pg_column_size(lista) < 3000))
);

-- ---------------------------------------------------------------- ayudas internas
-- El código se guarda en mayúsculas y sin guion; al leerlo se quitan espacios y guiones.
create or replace function public.normalizar_codigo(p_codigo text)
returns text language sql immutable set search_path = public as $$
    select upper(regexp_replace(coalesce(p_codigo, ''), '[[:space:]-]', '', 'g'));
$$;

-- 8 caracteres del alfabeto legible (sin I, L, O, 0, 1). La aleatoriedad sale de gen_random_uuid(),
-- que es segura y no depende de ninguna extensión. Los bytes de versión del uuid se saltan y los
-- que sobrarían (>= 248) se descartan para que ningún carácter salga más veces que otro.
create or replace function public.generar_codigo_lista()
returns text language plpgsql volatile security definer set search_path = public as $$
declare
    alfabeto constant text := 'ABCDEFGHJKMNPQRSTUVWXYZ23456789';
    r text := '';
    b bytea;
    v int;
begin
    while length(r) < 8 loop
        b := decode(replace(gen_random_uuid()::text, '-', ''), 'hex');
        for i in 0..15 loop
            continue when i in (6, 8);
            v := get_byte(b, i);
            continue when v >= 248;
            r := r || substr(alfabeto, (v % 31) + 1, 1);
            exit when length(r) = 8;
        end loop;
    end loop;
    return r;
end $$;

-- Qué puede hacer quien llama en una lista: 'dueno', 'colaborador', 'oyente' o null (nada).
-- Un miembro con bloqueo entre él y el dueño queda fuera.
create or replace function public.acceso_lista(p_lista uuid)
returns text language sql stable security definer set search_path = public as $$
    select case
        when l.user_id = auth.uid() then 'dueno'
        else (select m.rol from public.lista_miembros m
               where m.lista_id = l.id and m.user_id = auth.uid()
                 and not coalesce(public.hay_bloqueo(auth.uid(), l.user_id), false))
    end
    from public.listas l where l.id = p_lista;
$$;

-- Las canciones de una petición que de verdad son nuevas: se descartan las que ya están en la
-- lista, las repetidas dentro de la misma petición y las que no traen clave.
create or replace function public.candidatas_lista(p_lista uuid, p_items jsonb)
returns table (n bigint, clave text, datos jsonb)
language sql stable security definer set search_path = public as $$
    select min(q.n), q.clave, (array_agg(q.datos order by q.n))[1]
      from (select t.n, trim(t.e ->> 'clave') as clave,
                   case when jsonb_typeof(t.e -> 'datos') = 'object' then t.e -> 'datos' else '{}'::jsonb end as datos
              from jsonb_array_elements(p_items) with ordinality as t(e, n)
             where jsonb_typeof(t.e) = 'object') q
     where q.clave is not null and q.clave <> ''
       and not exists (select 1 from public.lista_items i where i.lista_id = p_lista and i.clave = q.clave)
     group by q.clave;
$$;

-- ---------------------------------------------------------------- compartir
drop function if exists public.compartir_lista(uuid, text);
create function public.compartir_lista(p_lista uuid, p_rol text default 'colaborador')
returns text language plpgsql security definer set search_path = public as $$
declare
    yo uuid := auth.uid();
    cod text;
    rol_actual text;
begin
    if yo is null then raise exception 'Necesitas iniciar sesión para compartir una lista.'; end if;
    if p_rol is null or p_rol not in ('colaborador', 'oyente') then
        raise exception 'El permiso debe ser «colaborador» (puede añadir canciones) u «oyente» (solo escucha).';
    end if;
    if not exists (select 1 from public.listas where id = p_lista and user_id = yo) then
        raise exception 'Esa lista no existe o no es tuya.';
    end if;
    loop
        select codigo, rol into cod, rol_actual from public.lista_codigos where lista_id = p_lista;
        exit when cod is not null;
        insert into public.lista_codigos (codigo, lista_id, rol)
        values (public.generar_codigo_lista(), p_lista, p_rol)
        on conflict do nothing;
    end loop;
    if rol_actual <> p_rol then
        update public.lista_codigos set rol = p_rol where lista_id = p_lista;
        -- el permiso de la lista vale para todos, también para quien ya estaba dentro
        update public.lista_miembros set rol = p_rol where lista_id = p_lista;
    end if;
    return cod;
end $$;

drop function if exists public.dejar_de_compartir_lista(uuid);
create function public.dejar_de_compartir_lista(p_lista uuid)
returns void language plpgsql security definer set search_path = public as $$
begin
    if auth.uid() is null then raise exception 'Necesitas iniciar sesión.'; end if;
    if not exists (select 1 from public.listas where id = p_lista and user_id = auth.uid()) then
        raise exception 'Esa lista no existe o no es tuya.';
    end if;
    delete from public.lista_codigos  where lista_id = p_lista;
    delete from public.lista_miembros where lista_id = p_lista;
end $$;

-- Vista previa para la página web y para confirmar antes de unirse. La puede llamar cualquiera
-- (también sin cuenta), así que no devuelve ningún identificador interno ni dato privado.
drop function if exists public.ver_lista_codigo(text);
create function public.ver_lista_codigo(p_codigo text)
returns jsonb language plpgsql stable security definer set search_path = public as $$
declare
    c public.lista_codigos;
    l public.listas;
    d public.perfiles;
begin
    select * into c from public.lista_codigos where codigo = public.normalizar_codigo(p_codigo);
    if c.codigo is null then return null; end if;
    select * into l from public.listas where id = c.lista_id;
    if l.id is null then return null; end if;
    select * into d from public.perfiles where id = l.user_id;
    return jsonb_build_object(
        'nombre', l.nombre,
        'descripcion', l.descripcion,
        'total', (select count(*)::int from public.lista_items where lista_id = l.id),
        'rol', c.rol,
        'miembros', (select count(*)::int from public.lista_miembros where lista_id = l.id),
        'dueno', jsonb_build_object('usuario', d.usuario, 'nombre', d.nombre, 'foto_url', d.foto_url),
        'canciones', coalesce((
            select jsonb_agg(jsonb_build_object(
                       'titulo', coalesce(q.datos ->> 'titulo', q.datos ->> 'nombre', ''),
                       'artista', coalesce(q.datos -> 'artistas' -> 0 ->> 'nombre', q.datos ->> 'artista', ''),
                       'miniatura', coalesce(q.datos ->> 'miniatura', q.datos ->> 'portada', ''))
                     order by q.orden, q.agregada)
              from (select datos, orden, agregada from public.lista_items
                     where lista_id = l.id order by orden, agregada limit 6) q), '[]'::jsonb));
end $$;

drop function if exists public.unirse_a_lista(text);
create function public.unirse_a_lista(p_codigo text)
returns jsonb language plpgsql security definer set search_path = public as $$
declare
    yo uuid := auth.uid();
    c public.lista_codigos;
    l public.listas;
    actual text;
begin
    if yo is null then raise exception 'Necesitas iniciar sesión para unirte a una lista.'; end if;
    select * into c from public.lista_codigos where codigo = public.normalizar_codigo(p_codigo);
    if c.codigo is null then
        raise exception 'Ese código no existe o la lista ya no se comparte. Revisa que esté bien escrito.';
    end if;
    -- se bloquea la lista para que dos personas no pasen el tope a la vez
    select * into l from public.listas where id = c.lista_id for update;
    if l.id is null then
        raise exception 'Ese código no existe o la lista ya no se comparte. Revisa que esté bien escrito.';
    end if;
    if l.user_id = yo then
        return jsonb_build_object('lista_id', l.id, 'nombre', l.nombre, 'rol', 'colaborador', 'es_dueno', true);
    end if;
    if coalesce(public.hay_bloqueo(yo, l.user_id), false) then
        raise exception 'No te puedes unir a esta lista.';
    end if;
    select rol into actual from public.lista_miembros where lista_id = l.id and user_id = yo;
    if actual is null then
        if (select count(*) from public.lista_miembros where lista_id = l.id) >= 20 then
            raise exception 'Esta lista ya tiene 20 personas, que es el máximo. Pídele a su dueño que haga lugar.';
        end if;
        insert into public.lista_miembros (lista_id, user_id, rol) values (l.id, yo, c.rol);
        actual := c.rol;
    end if;
    return jsonb_build_object('lista_id', l.id, 'nombre', l.nombre, 'rol', actual, 'es_dueno', false);
end $$;

drop function if exists public.salir_de_lista(uuid);
create function public.salir_de_lista(p_lista uuid)
returns void language plpgsql security definer set search_path = public as $$
begin
    if auth.uid() is null then raise exception 'Necesitas iniciar sesión.'; end if;
    delete from public.lista_miembros where lista_id = p_lista and user_id = auth.uid();
    if not found then raise exception 'No estás en esa lista.'; end if;
end $$;

drop function if exists public.quitar_miembro(uuid, uuid);
create function public.quitar_miembro(p_lista uuid, p_usuario uuid)
returns void language plpgsql security definer set search_path = public as $$
begin
    if auth.uid() is null then raise exception 'Necesitas iniciar sesión.'; end if;
    if not exists (select 1 from public.listas where id = p_lista and user_id = auth.uid()) then
        raise exception 'Solo el dueño de la lista puede quitar a alguien.';
    end if;
    delete from public.lista_miembros where lista_id = p_lista and user_id = p_usuario;
    if not found then raise exception 'Esa persona no está en la lista.'; end if;
end $$;

-- ---------------------------------------------------------------- leer
drop function if exists public.miembros_lista(uuid);
create function public.miembros_lista(p_lista uuid)
returns jsonb language plpgsql stable security definer set search_path = public as $$
begin
    if public.acceso_lista(p_lista) is null then
        raise exception 'No tienes acceso a esa lista.';
    end if;
    return coalesce((
        select jsonb_agg(jsonb_build_object(
                   'id', q.id, 'usuario', q.usuario, 'nombre', q.nombre, 'foto_url', q.foto_url,
                   'rol', q.rol, 'desde', q.desde, 'es_dueno', q.es_dueno)
               order by q.es_dueno desc, q.desde, q.usuario)
          from (select p.id, p.usuario, p.nombre, p.foto_url, 'colaborador'::text as rol,
                       l.creada as desde, true as es_dueno
                  from public.listas l join public.perfiles p on p.id = l.user_id
                 where l.id = p_lista
                union all
                select p.id, p.usuario, p.nombre, p.foto_url, m.rol, m.desde, false
                  from public.lista_miembros m join public.perfiles p on p.id = m.user_id
                 where m.lista_id = p_lista) q), '[]'::jsonb);
end $$;

drop function if exists public.mis_listas_compartidas();
create function public.mis_listas_compartidas()
returns jsonb language sql stable security definer set search_path = public as $$
    select coalesce(jsonb_agg(jsonb_build_object(
               'id', l.id, 'nombre', l.nombre, 'descripcion', l.descripcion, 'rol', m.rol,
               'total', (select count(*)::int from public.lista_items i where i.lista_id = l.id),
               'actualizada', l.actualizada,
               'dueno', jsonb_build_object('id', d.id, 'usuario', d.usuario, 'nombre', d.nombre,
                                           'foto_url', d.foto_url))
               order by l.actualizada desc), '[]'::jsonb)
    from public.lista_miembros m
    join public.listas l on l.id = m.lista_id
    join public.perfiles d on d.id = l.user_id
    where auth.uid() is not null and m.user_id = auth.uid() and l.user_id <> auth.uid()
      and not coalesce(public.hay_bloqueo(auth.uid(), l.user_id), false);
$$;

drop function if exists public.pistas_de_lista(uuid);
create function public.pistas_de_lista(p_lista uuid)
returns jsonb language plpgsql stable security definer set search_path = public as $$
begin
    if public.acceso_lista(p_lista) is null then
        raise exception 'No tienes acceso a esa lista.';
    end if;
    return coalesce((
        select jsonb_agg(jsonb_build_object(
                   'clave', i.clave, 'datos', i.datos, 'orden', i.orden, 'agregada', i.agregada,
                   'agregada_por', jsonb_build_object('id', p.id, 'usuario', p.usuario, 'nombre', p.nombre))
               order by i.orden, i.agregada, i.clave)
          from public.lista_items i left join public.perfiles p on p.id = i.user_id
         where i.lista_id = p_lista), '[]'::jsonb);
end $$;

-- ---------------------------------------------------------------- añadir y quitar canciones
drop function if exists public.agregar_a_lista_compartida(uuid, jsonb);
create function public.agregar_a_lista_compartida(p_lista uuid, p_items jsonb)
returns int language plpgsql security definer set search_path = public as $$
declare
    yo uuid := auth.uid();
    acceso text;
    base double precision;
    existentes int;
    nuevas int;
    entraron int;
begin
    if yo is null then raise exception 'Necesitas iniciar sesión.'; end if;
    acceso := public.acceso_lista(p_lista);
    if acceso is null then raise exception 'No tienes acceso a esa lista.'; end if;
    if acceso = 'oyente' then
        raise exception 'En esta lista solo puedes escuchar: no puedes añadir canciones.';
    end if;
    if p_items is null or jsonb_typeof(p_items) <> 'array' then
        raise exception 'Las canciones no llegaron en el formato esperado.';
    end if;
    -- se bloquea la lista para que dos personas no pasen el tope ni repitan el orden a la vez
    perform 1 from public.listas where id = p_lista for update;

    select count(*) into nuevas from public.candidatas_lista(p_lista, p_items);
    if nuevas = 0 then return 0; end if;
    select count(*) into existentes from public.lista_items where lista_id = p_lista;
    -- sin tope práctico para quien importa listas enormes: solo una guarda de cordura
    if existentes + nuevas > 200000 then
        raise exception 'Una lista compartida admite hasta 200000 canciones y esta ya tiene %.', existentes;
    end if;

    select coalesce(max(orden), 0) into base from public.lista_items where lista_id = p_lista;
    insert into public.lista_items (lista_id, user_id, clave, datos, orden)
    select p_lista, yo, c.clave, c.datos, base + row_number() over (order by c.n)
      from public.candidatas_lista(p_lista, p_items) c
    on conflict (lista_id, clave) do nothing;
    get diagnostics entraron = row_count;
    if entraron > 0 then
        update public.listas set actualizada = now() where id = p_lista;
    end if;
    return entraron;
end $$;

drop function if exists public.quitar_de_lista_compartida(uuid, text);
create function public.quitar_de_lista_compartida(p_lista uuid, p_clave text)
returns void language plpgsql security definer set search_path = public as $$
declare
    acceso text;
    autor uuid;
begin
    if auth.uid() is null then raise exception 'Necesitas iniciar sesión.'; end if;
    acceso := public.acceso_lista(p_lista);
    if acceso is null then raise exception 'No tienes acceso a esa lista.'; end if;
    if acceso = 'oyente' then
        raise exception 'En esta lista solo puedes escuchar: no puedes quitar canciones.';
    end if;
    select user_id into autor from public.lista_items where lista_id = p_lista and clave = p_clave;
    if not found then return; end if;     -- ya no estaba: no hay nada que quitar
    if acceso = 'colaborador' and autor <> auth.uid() then
        raise exception 'Solo puedes quitar las canciones que añadiste tú.';
    end if;
    delete from public.lista_items where lista_id = p_lista and clave = p_clave;
    update public.listas set actualizada = now() where id = p_lista;
end $$;

-- ---------------------------------------------------------------- chat: la tarjeta de lista
drop function if exists public.mis_chats();
create function public.mis_chats()
returns table (id uuid, otro uuid, usuario text, nombre text, ultimo timestamptz,
               ultimo_texto text, ultimo_pista jsonb, ultimo_autor uuid, sin_leer int,
               foto_url text, ultimo_lista jsonb)
language sql stable security definer set search_path = public as $$
    select c.id,
           o.id, o.usuario, o.nombre, c.ultimo,
           m.texto, m.pista, m.autor,
           (select count(*)::int from public.mensajes n
             where n.chat = c.id and n.autor <> auth.uid()
               and n.creado > case when c.a = auth.uid() then c.leido_a else c.leido_b end),
           o.foto_url,
           m.lista
    from public.chats c
    join public.perfiles o on o.id = case when c.a = auth.uid() then c.b else c.a end
    left join lateral (select texto, pista, lista, autor from public.mensajes
                       where chat = c.id order by id desc limit 1) m on true
    where auth.uid() in (c.a, c.b)
      and not public.hay_bloqueo(c.a, c.b)
    order by c.ultimo desc;
$$;

-- ---------------------------------------------------------------- permisos
do $$
declare f text;
begin
    foreach f in array array[
        'compartir_lista(uuid, text)', 'dejar_de_compartir_lista(uuid)', 'ver_lista_codigo(text)',
        'unirse_a_lista(text)', 'salir_de_lista(uuid)', 'quitar_miembro(uuid, uuid)',
        'miembros_lista(uuid)', 'mis_listas_compartidas()', 'pistas_de_lista(uuid)',
        'agregar_a_lista_compartida(uuid, jsonb)', 'quitar_de_lista_compartida(uuid, text)',
        'mis_chats()']
    loop
        execute format('revoke execute on function public.%s from public, anon', f);
        execute format('grant execute on function public.%s to authenticated', f);
    end loop;
end $$;
-- la vista previa también sirve sin cuenta (página web de la lista)
grant execute on function public.ver_lista_codigo(text) to anon;
-- ayudas internas: nadie las llama desde la app
revoke execute on function public.normalizar_codigo(text), public.generar_codigo_lista(),
    public.acceso_lista(uuid), public.candidatas_lista(uuid, jsonb) from public, anon, authenticated;
