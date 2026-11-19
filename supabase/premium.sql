-- ================================================================ Caudal premium (donadores)
-- Lo que se desbloquea con ser Donador (o Fundador, o con un pase de prueba):
--   · «premium vigente»: títulos con fecha de vencimiento, para que un pase de prueba acabe solo;
--   · cosméticos del perfil: marco del avatar, efecto del nombre y tema de colores;
--   · pases de prueba: códigos que dan unos días de beneficios a quien los canjea (una vez por cuenta).
--
-- Se pega entero en el SQL Editor de Supabase DESPUÉS de esquema.sql, social.sql, listas.sql y
-- listas_perfil.sql (redefine varias de sus funciones). Se puede ejecutar de nuevo sin romper nada.
-- Los códigos se crean con herramientas/pase_prueba.py.

-- ---------------------------------------------------------------- 1. títulos con vencimiento
-- vence null = permanente (como todos los títulos de hasta ahora).
alter table public.titulos_especiales add column if not exists vence timestamptz;

-- ¿esta persona tiene beneficios ahora mismo? Donador y Fundador valen mientras no venzan (hasta
-- hoy ninguno vence); el invitado de prueba SIEMPRE necesita una fecha futura.
create or replace function public.es_premium(p_id uuid)
returns boolean language sql stable security definer set search_path = public as $$
    select exists (select 1 from public.titulos_especiales te
                    where te.user_id = p_id
                      and ((te.titulo in ('donador_caudal', 'fundador_caudal') and (te.vence is null or te.vence > now()))
                           or (te.titulo = 'invitado_caudal' and te.vence > now())));
$$;

-- el tipo, de mayor a menor: fundador, donador, prueba (null si no tiene nada vigente)
create or replace function public.tipo_premium(p_id uuid)
returns text language sql stable security definer set search_path = public as $$
    select case
        when exists (select 1 from public.titulos_especiales te where te.user_id = p_id
                      and te.titulo = 'fundador_caudal' and (te.vence is null or te.vence > now())) then 'fundador'
        when exists (select 1 from public.titulos_especiales te where te.user_id = p_id
                      and te.titulo = 'donador_caudal' and (te.vence is null or te.vence > now())) then 'donador'
        when exists (select 1 from public.titulos_especiales te where te.user_id = p_id
                      and te.titulo = 'invitado_caudal' and te.vence > now()) then 'prueba'
        else null end;
$$;

-- lo que llama la app: {"premium": bool, "tipo": "donador"|"fundador"|"prueba"|null, "vence": fecha|null}
-- (vence es null si es permanente o si no hay premium)
create or replace function public.mi_premium()
returns jsonb language sql stable security definer set search_path = public as $$
    select jsonb_build_object(
        'premium', public.tipo_premium(auth.uid()) is not null,
        'tipo', public.tipo_premium(auth.uid()),
        'vence', (select max(te.vence) from public.titulos_especiales te
                   where te.user_id = auth.uid() and te.titulo = 'invitado_caudal' and te.vence > now()
                     and public.tipo_premium(auth.uid()) = 'prueba'));
$$;

-- los títulos que se enseñan de alguien: los vencidos no salen
create or replace function public.titulos_vigentes(p_id uuid)
returns jsonb language sql stable security definer set search_path = public as $$
    select coalesce(jsonb_agg(jsonb_build_object('clave', te.titulo, 'nombre', te.nombre) order by te.creado),
                    '[]'::jsonb)
    from public.titulos_especiales te
    where te.user_id = p_id and (te.vence is null or te.vence > now());
$$;

-- fondo y GIF del perfil: ahora también para quien tiene un pase de prueba vigente
create or replace function public.puede_tener_fondo(p_id uuid)
returns boolean language sql stable security definer set search_path = public as $$
    select public.es_premium(p_id);
$$;

-- ---------------------------------------------------------------- 2. cosméticos del perfil
alter table public.perfiles add column if not exists marco text not null default 'ninguno';
alter table public.perfiles add column if not exists efecto_nombre text not null default 'ninguno';
alter table public.perfiles add column if not exists tema_premium text not null default 'ninguno';

alter table public.perfiles drop constraint if exists perfil_cosmeticos;
alter table public.perfiles add constraint perfil_cosmeticos check (
    marco in ('ninguno', 'aurora', 'fuego', 'oro', 'neon', 'hielo', 'arcoiris', 'galaxia')
    and efecto_nombre in ('ninguno', 'brillo', 'degradado', 'arcoiris', 'neon')
    and tema_premium in ('ninguno', 'atardecer', 'bosque', 'sakura', 'oceano', 'medianoche', 'ambar')
);

-- lo que se ve de otra persona: su marco y su efecto solo cuentan mientras tenga premium vigente
create or replace function public.marco_de(p_id uuid)
returns text language sql stable security definer set search_path = public as $$
    select case when public.es_premium(p_id) then coalesce((select marco from public.perfiles where id = p_id), 'ninguno')
                else 'ninguno' end;
$$;
create or replace function public.efecto_de(p_id uuid)
returns text language sql stable security definer set search_path = public as $$
    select case when public.es_premium(p_id) then coalesce((select efecto_nombre from public.perfiles where id = p_id), 'ninguno')
                else 'ninguno' end;
$$;

-- el servidor manda: lo de siempre (perfil público solo de mayores, fondo y GIF solo premium) y,
-- sin premium vigente, ningún cosmético se guarda, aunque alguien escriba la columna a mano
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
        new.marco := 'ninguno';
        new.efecto_nombre := 'ninguno';
        new.tema_premium := 'ninguno';
    end if;
    return new;
end $$;
drop trigger if exists perfil_validar on public.perfiles;
create trigger perfil_validar before insert or update on public.perfiles
    for each row execute function public.perfil_validar();

-- ---------------------------------------------------------------- 3. pases de prueba
-- Sin políticas: desde la app nadie los lee ni los escribe, solo quien administra la base
-- (herramientas/pase_prueba.py) y la función canjear_pase de abajo.
create table if not exists public.pases_prueba (
    codigo    text primary key check (codigo ~ '^[A-Z0-9]{4}-[A-Z0-9]{4}$'),
    dias      int not null default 7 check (dias between 1 and 30),
    usos_max  int not null default 1 check (usos_max >= 1),
    usos      int not null default 0 check (usos >= 0),
    caduca    timestamptz,
    creado    timestamptz not null default now()
);
alter table public.pases_prueba enable row level security;

-- una sola prueba por cuenta, de por vida
create table if not exists public.pases_canjeados (
    user_id   uuid primary key references auth.users (id) on delete cascade,
    codigo    text not null,
    canjeado  timestamptz not null default now()
);
alter table public.pases_canjeados enable row level security;

-- intentos fallidos, para que nadie pueda adivinar códigos a fuerza bruta
create table if not exists public.pases_intentos (
    user_id   uuid not null references auth.users (id) on delete cascade,
    momento   timestamptz not null default now()
);
create index if not exists pases_intentos_quien on public.pases_intentos (user_id, momento);
alter table public.pases_intentos enable row level security;

-- canjear un código: {"ok": bool, "mensaje": texto, "dias": n, "vence": fecha}
-- (siempre contesta con un mensaje claro; no lanza errores, así los intentos fallidos se quedan anotados)
drop function if exists public.canjear_pase(text);
create function public.canjear_pase(p_codigo text)
returns jsonb language plpgsql security definer set search_path = public as $$
declare
    yo uuid := auth.uid();
    limpio text;
    cod text;
    p public.pases_prueba;
    fin timestamptz;
    fallos int;
begin
    if yo is null then
        return jsonb_build_object('ok', false, 'mensaje', 'Necesitas iniciar sesión para canjear un código.');
    end if;
    delete from public.pases_intentos where momento < now() - interval '1 day';
    select count(*)::int into fallos from public.pases_intentos
     where user_id = yo and momento > now() - interval '1 hour';
    if fallos >= 10 then
        return jsonb_build_object('ok', false,
            'mensaje', 'Probaste demasiados códigos seguidos. Espera una hora y vuelve a intentarlo.');
    end if;
    -- quien ya es donador (o fundador) no necesita una prueba
    if exists (select 1 from public.titulos_especiales te where te.user_id = yo
                and te.titulo in ('donador_caudal', 'fundador_caudal') and (te.vence is null or te.vence > now())) then
        return jsonb_build_object('ok', false,
            'mensaje', 'Ya eres donador de Caudal: no necesitas un código de prueba. ¡Gracias por apoyar!');
    end if;
    -- una sola prueba por cuenta
    if exists (select 1 from public.pases_canjeados where user_id = yo)
       or exists (select 1 from public.titulos_especiales te where te.user_id = yo and te.titulo = 'invitado_caudal') then
        return jsonb_build_object('ok', false,
            'mensaje', 'Ya usaste tu prueba gratis. Cada cuenta puede probarla una sola vez.');
    end if;
    -- el código, sin importar mayúsculas, espacios ni guiones de más
    limpio := upper(regexp_replace(coalesce(p_codigo, ''), '[^A-Za-z0-9]', '', 'g'));
    if length(limpio) <> 8 then
        insert into public.pases_intentos (user_id) values (yo);
        return jsonb_build_object('ok', false, 'mensaje', 'Ese código no existe. Revisa que esté bien escrito.');
    end if;
    cod := substr(limpio, 1, 4) || '-' || substr(limpio, 5, 4);
    select * into p from public.pases_prueba where codigo = cod for update;
    if p.codigo is null then
        insert into public.pases_intentos (user_id) values (yo);
        return jsonb_build_object('ok', false, 'mensaje', 'Ese código no existe. Revisa que esté bien escrito.');
    end if;
    if p.caduca is not null and p.caduca <= now() then
        return jsonb_build_object('ok', false, 'mensaje', 'Ese código ya caducó.');
    end if;
    if p.usos >= p.usos_max then
        return jsonb_build_object('ok', false, 'mensaje', 'Ese código ya se usó el máximo de veces.');
    end if;
    fin := now() + make_interval(days => p.dias);
    insert into public.titulos_especiales (user_id, titulo, nombre, vence)
    values (yo, 'invitado_caudal', 'Donador de prueba', fin)
    on conflict (user_id, titulo) do update set vence = excluded.vence;
    insert into public.pases_canjeados (user_id, codigo) values (yo, cod);
    update public.pases_prueba set usos = usos + 1 where codigo = cod;
    return jsonb_build_object('ok', true,
        'mensaje', '¡Listo! Tienes ' || p.dias || case when p.dias = 1 then ' día' else ' días' end
                   || ' de beneficios de donador.',
        'dias', p.dias, 'vence', fin);
end $$;

-- ---------------------------------------------------------------- 4. permisos
-- las ayudas internas no las llama nadie desde la app (por dentro responden con el rol del dueño)
revoke execute on function public.es_premium(uuid), public.tipo_premium(uuid), public.titulos_vigentes(uuid),
    public.marco_de(uuid), public.efecto_de(uuid) from public, anon, authenticated;
revoke execute on function public.mi_premium(), public.canjear_pase(text) from public, anon;
grant execute on function public.mi_premium(), public.canjear_pase(text) to authenticated;
revoke execute on function public.puede_tener_fondo(uuid) from public, anon;
grant execute on function public.puede_tener_fondo(uuid) to authenticated;

-- ---------------------------------------------------------------- 5. RPC existentes, ahora con marco y efecto
-- Son las definiciones vigentes de social.sql, listas.sql y listas_perfil.sql con DOS campos más
-- (`marco` y `efecto_nombre`, ya filtrados: 'ninguno' si esa persona no es premium vigente) y con los
-- títulos vencidos fuera de `titulos`. Por eso este archivo se ejecuta SIEMPRE DESPUÉS de esos tres.

drop function if exists public.mis_bloqueados();
create function public.mis_bloqueados()
returns table (id uuid, usuario text, nombre text, foto_url text, marco text, efecto_nombre text)
language sql stable security definer set search_path = public as $$
    select p.id, p.usuario, p.nombre, p.foto_url, public.marco_de(p.id), public.efecto_de(p.id)
    from public.bloqueos b
    join public.perfiles p on p.id = b.a where b.quien = auth.uid() order by b.creado desc;
$$;

drop function if exists public.mis_solicitudes();
create function public.mis_solicitudes()
returns table (id bigint, de uuid, usuario text, nombre text, foto_url text, marco text, efecto_nombre text,
               creado timestamptz)
language sql stable security definer set search_path = public as $$
    select a.id, p.id, p.usuario, p.nombre, p.foto_url, public.marco_de(p.id), public.efecto_de(p.id), a.creado
    from public.amistades a join public.perfiles p on p.id = a.de
    where a.para = auth.uid() and a.estado = 'pendiente'
      and not public.hay_bloqueo(auth.uid(), a.de)
    order by a.creado desc;
$$;

drop function if exists public.mis_enviadas();
create function public.mis_enviadas()
returns table (id bigint, para uuid, usuario text, nombre text, foto_url text, marco text, efecto_nombre text,
               creado timestamptz)
language sql stable security definer set search_path = public as $$
    select a.id, p.id, p.usuario, p.nombre, p.foto_url, public.marco_de(p.id), public.efecto_de(p.id), a.creado
    from public.amistades a join public.perfiles p on p.id = a.para
    where a.de = auth.uid() and a.estado = 'pendiente' order by a.creado desc;
$$;

drop function if exists public.mis_amigos();
create function public.mis_amigos()
returns table (id uuid, usuario text, nombre text, foto_url text, marco text, efecto_nombre text, desde timestamptz)
language sql stable security definer set search_path = public as $$
    select p.id, p.usuario, p.nombre, p.foto_url, public.marco_de(p.id), public.efecto_de(p.id), a.respondido
    from public.amistades a
    join public.perfiles p on p.id = case when a.de = auth.uid() then a.para else a.de end
    where a.estado = 'aceptada' and auth.uid() in (a.de, a.para)
    order by lower(p.nombre), p.usuario;
$$;

drop function if exists public.buscar_persona(text);
create function public.buscar_persona(p_usuario text)
returns table (id uuid, usuario text, nombre text, foto_url text, marco text, efecto_nombre text, relacion text)
language sql stable security definer set search_path = public as $$
    select p.id, p.usuario, p.nombre, p.foto_url, public.marco_de(p.id), public.efecto_de(p.id),
           public.relacion_con(p.id)
    from public.perfiles p
    where p.usuario = lower(trim(p_usuario)) and p.id <> auth.uid()
      and not public.hay_bloqueo(auth.uid(), p.id);
$$;

drop function if exists public.mis_chats();
create function public.mis_chats()
returns table (id uuid, otro uuid, usuario text, nombre text, ultimo timestamptz,
               ultimo_texto text, ultimo_pista jsonb, ultimo_autor uuid, sin_leer int,
               foto_url text, ultimo_lista jsonb, marco text, efecto_nombre text)
language sql stable security definer set search_path = public as $$
    select c.id,
           o.id, o.usuario, o.nombre, c.ultimo,
           m.texto, m.pista, m.autor,
           (select count(*)::int from public.mensajes n
             where n.chat = c.id and n.autor <> auth.uid()
               and n.creado > case when c.a = auth.uid() then c.leido_a else c.leido_b end),
           o.foto_url,
           m.lista,
           public.marco_de(o.id), public.efecto_de(o.id)
    from public.chats c
    join public.perfiles o on o.id = case when c.a = auth.uid() then c.b else c.a end
    left join lateral (select texto, pista, lista, autor from public.mensajes
                       where chat = c.id order by id desc limit 1) m on true
    where auth.uid() in (c.a, c.b)
      and not public.hay_bloqueo(c.a, c.b)
    order by c.ultimo desc;
$$;

drop function if exists public.explorar_perfiles(text, int, int);
create function public.explorar_perfiles(p_busqueda text default '', p_limite int default 30,
                                         p_desde int default 0)
returns table (id uuid, usuario text, nombre text, foto_url text, bio text,
               cancion_fav jsonb, color_perfil text, relacion text, likes int, di_like boolean,
               num_subidas int, es_artista boolean, fundador boolean, fundador_caudal boolean, titulos jsonb, banner_url text,
               marco text, efecto_nombre text)
language sql stable security definer set search_path = public as $$
    select p.id, p.usuario, p.nombre, p.foto_url, p.bio, p.cancion_fav, p.color_perfil,
           public.relacion_con(p.id),
           (select count(*)::int from public.likes_perfil l where l.a = p.id),
           exists (select 1 from public.likes_perfil l where l.a = p.id and l.quien = auth.uid()),
           (select count(*)::int from public.canciones_subidas s where s.user_id = p.id and s.estado = 'publicada'),
           (select count(*) from public.likes_perfil l where l.a = p.id) >= 200,
           coalesce(p.numero <= 100, false),
           exists (select 1 from public.titulos_especiales te where te.user_id = p.id and te.titulo = 'fundador_caudal'),
           public.titulos_vigentes(p.id),
           p.banner_url,
           public.marco_de(p.id), public.efecto_de(p.id)
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
                                  'marco', public.marco_de(p.id), 'efecto_nombre', public.efecto_de(p.id),
                                  'fundador', coalesce(p.numero <= 100, false), 'numero', p.numero,
                                  'fundador_caudal', exists (select 1 from public.titulos_especiales te
                                      where te.user_id = p.id and te.titulo = 'fundador_caudal'),
                                  'titulos', public.titulos_vigentes(p.id),
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
        'marco', public.marco_de(p.id), 'efecto_nombre', public.efecto_de(p.id),
        'bio', p.bio, 'cancion_fav', p.cancion_fav, 'artista_fav', p.artista_fav,
        'generos', to_jsonb(p.generos), 'frase', p.frase, 'color_perfil', p.color_perfil,
        'creado', p.creado, 'relacion', rel, 'es_mio', p.id = yo,
        'publico', p.perfil_publico, 'mostrar_top', p.mostrar_top,
        'top_artistas', top_art, 'top_canciones', top_can, 'insignias', insig,
        'afinidad', case when p.id = yo then null else public.afinidad_entre(yo, p.id) end,
        'fundador', coalesce(p.numero <= 100, false), 'numero', p.numero,
        'fundador_caudal', exists (select 1 from public.titulos_especiales te
                                    where te.user_id = p.id and te.titulo = 'fundador_caudal'),
        'titulos', public.titulos_vigentes(p.id),
        'likes', n_likes, 'es_artista', n_likes >= 200,
        'subidas', subidas, 'num_subidas', jsonb_array_length(subidas),
        'di_like', exists (select 1 from public.likes_perfil l where l.a = p.id and l.quien = yo));
end $$;

drop function if exists public.explorar_subidas(text, int, int);
create function public.explorar_subidas(p_busqueda text default '', p_limite int default 40,
                                        p_desde int default 0)
returns table (id uuid, user_id uuid, usuario text, titulo text, artista text, album text,
               duracion int, ruta text, portada text, escuchas int, creado timestamptz, es_artista boolean,
               marco text, efecto_nombre text)
language sql stable security definer set search_path = public as $$
    select s.id, s.user_id, p.usuario, s.titulo, s.artista, s.album, s.duracion, s.ruta, s.portada,
           s.escuchas, s.creado,
           (select count(*) from public.likes_perfil l where l.a = s.user_id) >= 200,
           public.marco_de(p.id), public.efecto_de(p.id)
    from public.canciones_subidas s join public.perfiles p on p.id = s.user_id
    where auth.uid() is not null and s.estado = 'publicada'
      and not public.hay_bloqueo(auth.uid(), s.user_id)
      and (coalesce(trim(p_busqueda), '') = ''
           or s.titulo ilike '%' || replace(replace(trim(p_busqueda), '%', ''), '_', '') || '%'
           or s.artista ilike '%' || replace(replace(trim(p_busqueda), '%', ''), '_', '') || '%')
    order by s.creado desc
    limit least(greatest(p_limite, 1), 100) offset greatest(p_desde, 0);
$$;

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
        'dueno', jsonb_build_object('usuario', d.usuario, 'nombre', d.nombre, 'foto_url', d.foto_url,
                                    'marco', public.marco_de(d.id), 'efecto_nombre', public.efecto_de(d.id)),
        'canciones', coalesce((
            select jsonb_agg(jsonb_build_object(
                       'titulo', coalesce(q.datos ->> 'titulo', q.datos ->> 'nombre', ''),
                       'artista', coalesce(q.datos -> 'artistas' -> 0 ->> 'nombre', q.datos ->> 'artista', ''),
                       'miniatura', coalesce(q.datos ->> 'miniatura', q.datos ->> 'portada', ''))
                     order by q.orden, q.agregada)
              from (select datos, orden, agregada from public.lista_items
                     where lista_id = l.id order by orden, agregada limit 6) q), '[]'::jsonb));
end $$;

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
                   'marco', public.marco_de(q.id), 'efecto_nombre', public.efecto_de(q.id),
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
                                           'foto_url', d.foto_url,
                                           'marco', public.marco_de(d.id),
                                           'efecto_nombre', public.efecto_de(d.id)))
               order by l.actualizada desc), '[]'::jsonb)
    from public.lista_miembros m
    join public.listas l on l.id = m.lista_id
    join public.perfiles d on d.id = l.user_id
    where auth.uid() is not null and m.user_id = auth.uid() and l.user_id <> auth.uid()
      and not coalesce(public.hay_bloqueo(auth.uid(), l.user_id), false);
$$;

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
        'dueno', jsonb_build_object('usuario', d.usuario, 'nombre', d.nombre, 'foto_url', d.foto_url,
                                    'marco', public.marco_de(d.id), 'efecto_nombre', public.efecto_de(d.id)),
        'total', (select count(*)::int from public.lista_items where lista_id = l.id),
        'canciones', coalesce((
            select jsonb_agg(jsonb_build_object('clave', q.clave, 'datos', q.datos) order by q.orden, q.agregada)
              from (select clave, datos, orden, agregada from public.lista_items
                     where lista_id = l.id order by orden, agregada limit 2000) q), '[]'::jsonb));
end $$;

-- permisos (el mismo reparto que tenían)
revoke execute on function public.mis_bloqueados() from public, anon;
grant execute on function public.mis_bloqueados() to authenticated;
revoke execute on function public.mis_solicitudes() from public, anon;
grant execute on function public.mis_solicitudes() to authenticated;
revoke execute on function public.mis_enviadas() from public, anon;
grant execute on function public.mis_enviadas() to authenticated;
revoke execute on function public.mis_amigos() from public, anon;
grant execute on function public.mis_amigos() to authenticated;
revoke execute on function public.buscar_persona(text) from public, anon;
grant execute on function public.buscar_persona(text) to authenticated;
revoke execute on function public.mis_chats() from public, anon;
grant execute on function public.mis_chats() to authenticated;
revoke execute on function public.explorar_perfiles(text, int, int) from public, anon;
grant execute on function public.explorar_perfiles(text, int, int) to authenticated;
revoke execute on function public.ver_perfil(text) from public, anon;
grant execute on function public.ver_perfil(text) to authenticated;
revoke execute on function public.explorar_subidas(text, int, int) from public, anon;
grant execute on function public.explorar_subidas(text, int, int) to authenticated;
revoke execute on function public.ver_lista_codigo(text) from public;
grant execute on function public.ver_lista_codigo(text) to anon, authenticated;
revoke execute on function public.miembros_lista(uuid) from public, anon;
grant execute on function public.miembros_lista(uuid) to authenticated;
revoke execute on function public.mis_listas_compartidas() from public, anon;
grant execute on function public.mis_listas_compartidas() to authenticated;
revoke execute on function public.ver_lista_publica(uuid) from public, anon;
grant execute on function public.ver_lista_publica(uuid) to authenticated;
