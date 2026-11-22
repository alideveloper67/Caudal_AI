-- ================================================================ Caudal: grupos para hablar
-- Grupos abiertos (cualquiera los encuentra y entra) y privados (se entra con un código). Dentro se
-- manda texto, canciones y notas de voz. NO hay imágenes ni videos: los mensajes no tienen dónde
-- llevarlos y el almacén de los audios solo acepta audio.
--
-- Se pega entero en el SQL Editor de Supabase DESPUÉS de esquema.sql y social.sql. Se puede repetir.
--
-- Reglas que pone la base (no dependen de la app):
--   · Solo los miembros leen y escriben; las tablas no se leen directamente, todo pasa por funciones.
--   · Menores de edad: pueden estar en grupos, pero sus datos no salen de lo que ya enseña su perfil
--     (privado), y nadie les puede escribir por privado sin ser su amigo (regla del chat, social.sql).
--   · Freno contra el spam: 8 mensajes por 20 s y 3 grupos nuevos al día por persona.
--   · Un mensaje con 3 reportes de personas distintas se oculta solo hasta que un moderador lo mire.
--   · Quien bloquea a alguien deja de ver sus mensajes; quien fue expulsado no puede volver a entrar.
--   · Avisos al momento por Realtime (tema `grupo-<id>`, evento «nuevo», solo el número de mensaje:
--     el contenido se pide con grupo_mensajes, que comprueba que seas miembro).

-- ---------------------------------------------------------------- tablas
create table if not exists public.grupos (
    id           uuid primary key default gen_random_uuid(),
    nombre       text not null check (length(nombre) between 3 and 50),
    descripcion  text not null default '' check (length(descripcion) <= 300),
    tipo         text not null default 'abierto' check (tipo in ('abierto', 'privado')),
    dueno        uuid references auth.users (id) on delete set null,
    codigo       text unique,                 -- para entrar a uno privado (8 letras), o null
    cerrado      boolean not null default false,  -- lo cerró la moderación de Caudal
    creado       timestamptz not null default now(),
    ultimo       timestamptz not null default now()
);
create index if not exists grupos_abiertos on public.grupos (tipo, ultimo desc) where not cerrado;

create table if not exists public.grupo_miembros (
    grupo        uuid not null references public.grupos (id) on delete cascade,
    user_id      uuid not null references auth.users (id) on delete cascade,
    rol          text not null default 'miembro' check (rol in ('dueno', 'moderador', 'miembro')),
    unido        timestamptz not null default now(),
    leido        timestamptz not null default now(),
    silenciado_hasta timestamptz,
    primary key (grupo, user_id)
);
create index if not exists grupo_miembros_user on public.grupo_miembros (user_id);

create table if not exists public.grupo_expulsados (
    grupo        uuid not null references public.grupos (id) on delete cascade,
    user_id      uuid not null references auth.users (id) on delete cascade,
    por          uuid references auth.users (id) on delete set null,
    creado       timestamptz not null default now(),
    primary key (grupo, user_id)
);

create table if not exists public.grupo_mensajes (
    id           bigint generated always as identity primary key,
    grupo        uuid not null references public.grupos (id) on delete cascade,
    autor        uuid references auth.users (id) on delete cascade,
    texto        text not null default '' check (length(texto) <= 2000),
    pista        jsonb,
    audio        text,                        -- ruta en el almacén «audios-grupos»
    audio_seg    smallint check (audio_seg is null or audio_seg between 1 and 180),
    fijado       boolean not null default false,
    oculto       boolean not null default false,
    creado       timestamptz not null default now(),
    check (length(texto) > 0 or pista is not null or audio is not null)
);
create index if not exists grupo_mensajes_grupo_id on public.grupo_mensajes (grupo, id desc);
create index if not exists grupo_mensajes_autor on public.grupo_mensajes (autor, creado desc);

create table if not exists public.grupo_reportes (
    mensaje      bigint not null references public.grupo_mensajes (id) on delete cascade,
    quien        uuid not null references auth.users (id) on delete cascade,
    motivo       text not null default '' check (length(motivo) <= 300),
    creado       timestamptz not null default now(),
    primary key (mensaje, quien)
);

-- nada se lee ni se escribe directo: solo por las funciones de abajo
alter table public.grupos           enable row level security;
alter table public.grupo_miembros   enable row level security;
alter table public.grupo_expulsados enable row level security;
alter table public.grupo_mensajes   enable row level security;
alter table public.grupo_reportes   enable row level security;
revoke all on public.grupos, public.grupo_miembros, public.grupo_expulsados,
              public.grupo_mensajes, public.grupo_reportes from anon, authenticated;

-- ---------------------------------------------------------------- notas de voz
-- carpeta <grupo>/<persona>/archivo; solo audio, hasta 3 MB (unos 3 minutos); solo la leen los miembros
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('audios-grupos', 'audios-grupos', false, 3145728,
        array['audio/mp4', 'audio/m4a', 'audio/x-m4a', 'audio/aac', 'audio/mpeg', 'audio/ogg', 'audio/webm', 'audio/wav'])
on conflict (id) do update set public = false, file_size_limit = excluded.file_size_limit,
                               allowed_mime_types = excluded.allowed_mime_types;

-- ---------------------------------------------------------------- ayudas
create or replace function public.grupo_rol_de(p_grupo uuid, p_user uuid)
returns text language sql stable security definer set search_path = public as $$
    select rol from public.grupo_miembros where grupo = p_grupo and user_id = p_user;
$$;

create or replace function public.grupo_es_miembro(p_grupo uuid)
returns boolean language sql stable security definer set search_path = public as $$
    select auth.uid() is not null
       and exists (select 1 from public.grupo_miembros where grupo = p_grupo and user_id = auth.uid());
$$;

create or replace function public.grupo_texto(p text, p_largo int)
returns text language sql immutable set search_path = public as $$
    select left(btrim(regexp_replace(coalesce(p, ''), '[[:cntrl:]]+', ' ', 'g')), p_largo);
$$;

-- texto de un mensaje: se conservan los saltos de línea, nada de caracteres de control raros
create or replace function public.grupo_texto_mensaje(p text)
returns text language sql immutable set search_path = public as $$
    select left(btrim(regexp_replace(coalesce(p, ''), '[\x01-\x09\x0B-\x1F\x7F]+', ' ', 'g')), 2000);
$$;

-- una canción compartida: solo lo que hace falta para sonarla; la carátula solo de YouTube/Google
-- (así nadie cuela una imagen cualquiera haciéndola pasar por carátula)
create or replace function public.grupo_pista_limpia(p jsonb)
returns jsonb language plpgsql immutable set search_path = public as $$
declare
    vid text;
    mini text;
begin
    if p is null or jsonb_typeof(p) <> 'object' then
        return null;
    end if;
    vid := coalesce(p ->> 'video_id', '');
    if vid !~ '^[A-Za-z0-9_-]{6,20}$' then
        raise exception 'esa canción no se puede compartir';
    end if;
    mini := coalesce(p ->> 'miniatura', '');
    if mini !~ '^https://(i[0-9]?\.ytimg\.com|lh[0-9]\.googleusercontent\.com|yt[0-9]\.ggpht\.com)/' then
        mini := '';
    end if;
    return jsonb_build_object(
        'video_id', vid,
        'titulo', public.grupo_texto(p ->> 'titulo', 200),
        'artista', public.grupo_texto(p ->> 'artista', 200),
        'miniatura', mini,
        'duracion', case when coalesce(p ->> 'duracion', '') ~ '^[0-9]{1,5}$' then (p ->> 'duracion')::int else 0 end);
end $$;

create or replace function public.grupo_codigo_nuevo()
returns text language plpgsql volatile set search_path = public as $$
declare
    letras constant text := 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
    c text;
begin
    loop
        c := '';
        for i in 1..8 loop
            c := c || substr(letras, 1 + floor(random() * length(letras))::int, 1);
        end loop;
        exit when not exists (select 1 from public.grupos where codigo = c);
    end loop;
    return c;
end $$;

-- avisa por Realtime; nunca hace fallar al que llama (sin Realtime, la app vuelve a mirar sola)
create or replace function public.grupo_avisar(p_grupo uuid, p_evento text, p_datos jsonb)
returns void language plpgsql volatile security definer set search_path = public as $$
begin
    begin
        perform realtime.send(p_datos, p_evento, 'grupo-' || p_grupo::text, false);
    exception when others then
        null;
    end;
end $$;

-- un grupo como lo ve quien pregunta
create or replace function public.grupo_json(g public.grupos)
returns jsonb language sql stable security definer set search_path = public as $$
    select jsonb_build_object(
        'id', g.id, 'nombre', g.nombre, 'descripcion', g.descripcion, 'tipo', g.tipo,
        'creado', g.creado, 'ultimo', g.ultimo, 'cerrado', g.cerrado,
        'miembros', (select count(*)::int from public.grupo_miembros m where m.grupo = g.id),
        'rol', public.grupo_rol_de(g.id, auth.uid()),
        -- el código para invitar solo lo ve quien ya está dentro
        'codigo', case when public.grupo_rol_de(g.id, auth.uid()) is not null then g.codigo end,
        'dueno', (select jsonb_build_object('usuario', p.usuario, 'nombre', p.nombre)
                    from public.perfiles p where p.id = g.dueno));
$$;

create or replace function public.grupo_exigir_rol(p_grupo uuid, p_roles text[])
returns text language plpgsql stable security definer set search_path = public as $$
declare
    r text;
begin
    if auth.uid() is null then
        raise exception 'entra con tu cuenta para usar los grupos';
    end if;
    r := public.grupo_rol_de(p_grupo, auth.uid());
    if r is null then
        raise exception 'no estás en este grupo';
    end if;
    if not (r = any (p_roles)) then
        raise exception 'eso solo lo puede hacer quien modera el grupo';
    end if;
    return r;
end $$;

-- ---------------------------------------------------------------- crear, buscar, entrar y salir
drop function if exists public.grupo_crear(text, text, text);
create function public.grupo_crear(p_nombre text, p_descripcion text default '', p_tipo text default 'abierto')
returns jsonb language plpgsql volatile security definer set search_path = public as $$
declare
    yo uuid := auth.uid();
    v_nombre text := public.grupo_texto(p_nombre, 50);
    g public.grupos;
begin
    if yo is null then
        raise exception 'entra con tu cuenta para crear un grupo';
    end if;
    if length(v_nombre) < 3 then
        raise exception 'el nombre del grupo necesita al menos 3 letras';
    end if;
    if p_tipo not in ('abierto', 'privado') then
        raise exception 'el grupo es abierto o privado';
    end if;
    if (select count(*) from public.grupos where dueno = yo and creado > now() - interval '1 day') >= 3 then
        raise exception 'ya creaste 3 grupos hoy; prueba mañana';
    end if;
    if (select count(*) from public.grupos where dueno = yo) >= 20 then
        raise exception 'ya tienes 20 grupos; borra alguno para crear otro';
    end if;
    insert into public.grupos (nombre, descripcion, tipo, dueno, codigo)
    values (v_nombre, public.grupo_texto(p_descripcion, 300), p_tipo, yo,
            case when p_tipo = 'privado' then public.grupo_codigo_nuevo() end)
    returning * into g;
    insert into public.grupo_miembros (grupo, user_id, rol) values (g.id, yo, 'dueno');
    return public.grupo_json(g);
end $$;

-- grupos abiertos para descubrir (los más activos primero)
drop function if exists public.grupos_explorar(text, int, int);
create function public.grupos_explorar(p_busqueda text default '', p_limite int default 30, p_desde int default 0)
returns setof jsonb language sql stable security definer set search_path = public as $$
    select public.grupo_json(g)
    from public.grupos g
    where auth.uid() is not null
      and g.tipo = 'abierto' and not g.cerrado
      and (coalesce(btrim(p_busqueda), '') = ''
           or g.nombre ilike '%' || replace(replace(btrim(p_busqueda), '%', ''), '_', '') || '%'
           or g.descripcion ilike '%' || replace(replace(btrim(p_busqueda), '%', ''), '_', '') || '%')
    order by (select count(*) from public.grupo_miembros m where m.grupo = g.id) desc, g.ultimo desc
    limit least(greatest(p_limite, 1), 60) offset greatest(p_desde, 0);
$$;

-- mis grupos, con el último mensaje y los que no leí
drop function if exists public.mis_grupos();
create function public.mis_grupos()
returns setof jsonb language sql stable security definer set search_path = public as $$
    select public.grupo_json(g) || jsonb_build_object(
        'sin_leer', (select count(*)::int from public.grupo_mensajes x
                      where x.grupo = g.id and x.creado > m.leido and x.autor is distinct from auth.uid()
                        and not x.oculto and not public.hay_bloqueo(auth.uid(), x.autor)),
        'ultimo_mensaje', (select jsonb_build_object('texto', x.texto, 'pista', x.pista is not null,
                                                     'audio', x.audio is not null, 'creado', x.creado,
                                                     'usuario', p.usuario, 'nombre', p.nombre)
                             from public.grupo_mensajes x left join public.perfiles p on p.id = x.autor
                            where x.grupo = g.id and not x.oculto and not public.hay_bloqueo(auth.uid(), x.autor)
                            order by x.id desc limit 1))
    from public.grupo_miembros m join public.grupos g on g.id = m.grupo
    where m.user_id = auth.uid()
    order by g.ultimo desc;
$$;

-- ver un grupo: uno abierto lo puede ver cualquiera con cuenta; uno privado, solo quien está dentro
drop function if exists public.grupo_ver(uuid);
create function public.grupo_ver(p_grupo uuid)
returns jsonb language plpgsql stable security definer set search_path = public as $$
declare
    g public.grupos;
begin
    if auth.uid() is null then
        raise exception 'entra con tu cuenta para usar los grupos';
    end if;
    select * into g from public.grupos where id = p_grupo;
    if not found or (g.tipo = 'privado' and not public.grupo_es_miembro(p_grupo)) then
        return null;
    end if;
    return public.grupo_json(g);
end $$;

create or replace function public.grupo_meter(g public.grupos)
returns jsonb language plpgsql volatile security definer set search_path = public as $$
begin
    if g.cerrado then
        raise exception 'este grupo está cerrado';
    end if;
    if exists (select 1 from public.grupo_expulsados where grupo = g.id and user_id = auth.uid()) then
        raise exception 'te sacaron de este grupo; no puedes volver a entrar';
    end if;
    if (select count(*) from public.grupo_miembros where grupo = g.id) >= 2000 then
        raise exception 'el grupo está lleno';
    end if;
    if (select count(*) from public.grupo_miembros where user_id = auth.uid()) >= 100 then
        raise exception 'ya estás en 100 grupos; sal de alguno para entrar a otro';
    end if;
    insert into public.grupo_miembros (grupo, user_id) values (g.id, auth.uid())
    on conflict (grupo, user_id) do nothing;
    return public.grupo_json(g);
end $$;

drop function if exists public.grupo_unirse(uuid);
create function public.grupo_unirse(p_grupo uuid)
returns jsonb language plpgsql volatile security definer set search_path = public as $$
declare
    g public.grupos;
begin
    if auth.uid() is null then
        raise exception 'entra con tu cuenta para unirte';
    end if;
    select * into g from public.grupos where id = p_grupo;
    if not found or g.tipo <> 'abierto' then
        raise exception 'ese grupo no existe o es privado (pide su código)';
    end if;
    return public.grupo_meter(g);
end $$;

drop function if exists public.grupo_unirse_codigo(text);
create function public.grupo_unirse_codigo(p_codigo text)
returns jsonb language plpgsql volatile security definer set search_path = public as $$
declare
    g public.grupos;
    c text := upper(regexp_replace(coalesce(p_codigo, ''), '[^A-Za-z0-9]', '', 'g'));
begin
    if auth.uid() is null then
        raise exception 'entra con tu cuenta para unirte';
    end if;
    select * into g from public.grupos where codigo = c;
    if not found then
        raise exception 'no hay ningún grupo con ese código';
    end if;
    return public.grupo_meter(g);
end $$;

-- salir; si sale quien lo creó, pasa a quien modera (o al más antiguo); si no queda nadie, se borra
drop function if exists public.grupo_salir(uuid);
create function public.grupo_salir(p_grupo uuid)
returns void language plpgsql volatile security definer set search_path = public as $$
declare
    r text := public.grupo_rol_de(p_grupo, auth.uid());
    heredero uuid;
begin
    if r is null then
        return;
    end if;
    delete from public.grupo_miembros where grupo = p_grupo and user_id = auth.uid();
    if r = 'dueno' then
        select user_id into heredero from public.grupo_miembros
         where grupo = p_grupo order by (rol = 'moderador') desc, unido limit 1;
        if heredero is null then
            delete from public.grupos where id = p_grupo;
        else
            update public.grupo_miembros set rol = 'dueno' where grupo = p_grupo and user_id = heredero;
            update public.grupos set dueno = heredero where id = p_grupo;
        end if;
    end if;
end $$;

-- ---------------------------------------------------------------- mensajes
create or replace function public.grupo_mensaje_json(x public.grupo_mensajes)
returns jsonb language sql stable security definer set search_path = public as $$
    select jsonb_build_object(
        'id', x.id, 'texto', x.texto, 'pista', x.pista, 'audio', x.audio, 'audio_seg', x.audio_seg,
        'fijado', x.fijado, 'oculto', x.oculto, 'creado', x.creado, 'mio', x.autor = auth.uid(),
        'autor', (select jsonb_build_object('id', p.id, 'usuario', p.usuario, 'nombre', p.nombre,
                                            'foto_url', p.foto_url,
                                            'rol', public.grupo_rol_de(x.grupo, p.id))
                    from public.perfiles p where p.id = x.autor));
$$;

-- los mensajes de un grupo, del más nuevo hacia atrás (p_antes: para seguir cargando)
drop function if exists public.grupo_mensajes(uuid, bigint, int);
create function public.grupo_mensajes(p_grupo uuid, p_antes bigint default null, p_limite int default 50)
returns setof jsonb language plpgsql stable security definer set search_path = public as $$
declare
    r text := public.grupo_rol_de(p_grupo, auth.uid());
begin
    if auth.uid() is null or r is null then
        raise exception 'no estás en este grupo';
    end if;
    return query
        select public.grupo_mensaje_json(x)
        from public.grupo_mensajes x
        where x.grupo = p_grupo
          and (p_antes is null or x.id < p_antes)
          -- lo oculto por reportes solo lo ve quien modera (para decidir) y quien lo escribió
          and (not x.oculto or r in ('dueno', 'moderador') or x.autor = auth.uid())
          and not public.hay_bloqueo(auth.uid(), x.autor)
        order by x.id desc
        limit least(greatest(p_limite, 1), 100);
end $$;

-- los mensajes nuevos desde uno dado (lo que pide la app al oír el aviso de Realtime)
drop function if exists public.grupo_mensajes_desde(uuid, bigint);
create function public.grupo_mensajes_desde(p_grupo uuid, p_desde bigint)
returns setof jsonb language plpgsql stable security definer set search_path = public as $$
declare
    r text := public.grupo_rol_de(p_grupo, auth.uid());
begin
    if auth.uid() is null or r is null then
        raise exception 'no estás en este grupo';
    end if;
    return query
        select public.grupo_mensaje_json(x)
        from public.grupo_mensajes x
        where x.grupo = p_grupo and x.id > coalesce(p_desde, 0)
          and (not x.oculto or r in ('dueno', 'moderador') or x.autor = auth.uid())
          and not public.hay_bloqueo(auth.uid(), x.autor)
        order by x.id
        limit 200;
end $$;

drop function if exists public.grupo_enviar(uuid, text, jsonb, text, int);
create function public.grupo_enviar(p_grupo uuid, p_texto text default '', p_pista jsonb default null,
                                    p_audio text default null, p_audio_seg int default null)
returns jsonb language plpgsql volatile security definer set search_path = public as $$
declare
    yo uuid := auth.uid();
    m public.grupo_miembros;
    g public.grupos;
    v_texto text := public.grupo_texto_mensaje(p_texto);
    v_pista jsonb := public.grupo_pista_limpia(p_pista);
    x public.grupo_mensajes;
begin
    if yo is null then
        raise exception 'entra con tu cuenta para escribir';
    end if;
    select * into m from public.grupo_miembros where grupo = p_grupo and user_id = yo;
    if not found then
        raise exception 'no estás en este grupo';
    end if;
    select * into g from public.grupos where id = p_grupo;
    if g.cerrado then
        raise exception 'este grupo está cerrado';
    end if;
    if m.silenciado_hasta is not null and m.silenciado_hasta > now() then
        raise exception 'quien modera el grupo te silenció un rato; podrás escribir a las %',
            to_char(m.silenciado_hasta at time zone 'America/Lima', 'HH24:MI');
    end if;
    if (select count(*) from public.grupo_mensajes
         where autor = yo and creado > now() - interval '20 seconds') >= 8 then
        raise exception 'vas muy rápido; espera unos segundos';
    end if;
    if p_audio is not null then
        -- la nota de voz tiene que estar ya subida, en la carpeta de este grupo y de quien la manda
        if p_audio !~ ('^' || p_grupo::text || '/' || yo::text || '/[A-Za-z0-9_.-]{1,80}$')
           or not exists (select 1 from storage.objects o where o.bucket_id = 'audios-grupos' and o.name = p_audio) then
            raise exception 'la nota de voz no llegó; vuelve a grabarla';
        end if;
        if p_audio_seg is null or p_audio_seg not between 1 and 180 then
            raise exception 'la nota de voz dura como mucho 3 minutos';
        end if;
    end if;
    if length(v_texto) = 0 and v_pista is null and p_audio is null then
        raise exception 'el mensaje está vacío';
    end if;
    insert into public.grupo_mensajes (grupo, autor, texto, pista, audio, audio_seg)
    values (p_grupo, yo, v_texto, v_pista, p_audio, case when p_audio is not null then p_audio_seg end)
    returning * into x;
    update public.grupos set ultimo = now() where id = p_grupo;
    update public.grupo_miembros set leido = now() where grupo = p_grupo and user_id = yo;
    perform public.grupo_avisar(p_grupo, 'nuevo', jsonb_build_object('id', x.id));
    return public.grupo_mensaje_json(x);
end $$;

drop function if exists public.grupo_leido(uuid);
create function public.grupo_leido(p_grupo uuid)
returns void language sql volatile security definer set search_path = public as $$
    update public.grupo_miembros set leido = now() where grupo = p_grupo and user_id = auth.uid();
$$;

-- reportar un mensaje: con 3 reportes de personas distintas se oculta hasta que lo mire un moderador
drop function if exists public.grupo_reportar(bigint, text);
create function public.grupo_reportar(p_mensaje bigint, p_motivo text default '')
returns void language plpgsql volatile security definer set search_path = public as $$
declare
    x public.grupo_mensajes;
begin
    select * into x from public.grupo_mensajes where id = p_mensaje;
    if not found or not public.grupo_es_miembro(x.grupo) then
        raise exception 'ese mensaje no existe';
    end if;
    if x.autor = auth.uid() then
        raise exception 'no puedes reportar tu propio mensaje';
    end if;
    insert into public.grupo_reportes (mensaje, quien, motivo)
    values (p_mensaje, auth.uid(), public.grupo_texto(p_motivo, 300))
    on conflict (mensaje, quien) do nothing;
    if (select count(*) from public.grupo_reportes where mensaje = p_mensaje) >= 3 and not x.oculto then
        update public.grupo_mensajes set oculto = true where id = p_mensaje;
        perform public.grupo_avisar(x.grupo, 'cambio', jsonb_build_object('id', x.id));
    end if;
end $$;

-- ¿es moderador de Caudal? (los de social.sql: revisan también los grupos abiertos)
create or replace function public.grupo_moderador_caudal()
returns boolean language sql stable security definer set search_path = public as $$
    select exists (select 1 from public.moderadores where user_id = auth.uid());
$$;

-- borrar (quien lo escribió o quien modera), ocultar/mostrar y fijar/desfijar (quien modera)
drop function if exists public.grupo_mensaje_accion(bigint, text);
create function public.grupo_mensaje_accion(p_mensaje bigint, p_accion text)
returns void language plpgsql volatile security definer set search_path = public as $$
declare
    x public.grupo_mensajes;
    r text;
    modera boolean;
begin
    select * into x from public.grupo_mensajes where id = p_mensaje;
    if not found then
        raise exception 'ese mensaje no existe';
    end if;
    r := public.grupo_rol_de(x.grupo, auth.uid());
    modera := r in ('dueno', 'moderador') or public.grupo_moderador_caudal();
    if p_accion = 'borrar' then
        if not (x.autor = auth.uid() or modera) then
            raise exception 'solo quien lo escribió o quien modera puede borrarlo';
        end if;
        if x.audio is not null then
            delete from storage.objects where bucket_id = 'audios-grupos' and name = x.audio;
        end if;
        delete from public.grupo_mensajes where id = p_mensaje;
    elsif p_accion in ('ocultar', 'mostrar', 'fijar', 'desfijar') then
        if not modera then
            raise exception 'eso solo lo puede hacer quien modera el grupo';
        end if;
        if p_accion = 'fijar' and (select count(*) from public.grupo_mensajes where grupo = x.grupo and fijado) >= 5 then
            raise exception 'ya hay 5 mensajes fijados; quita alguno';
        end if;
        update public.grupo_mensajes
           set oculto = case p_accion when 'ocultar' then true when 'mostrar' then false else oculto end,
               fijado = case p_accion when 'fijar' then true when 'desfijar' then false else fijado end
         where id = p_mensaje;
        if p_accion = 'mostrar' then
            delete from public.grupo_reportes where mensaje = p_mensaje;
        end if;
    else
        raise exception 'acción desconocida';
    end if;
    perform public.grupo_avisar(x.grupo, 'cambio', jsonb_build_object('id', x.id));
end $$;

drop function if exists public.grupo_fijados(uuid);
create function public.grupo_fijados(p_grupo uuid)
returns setof jsonb language plpgsql stable security definer set search_path = public as $$
begin
    if not public.grupo_es_miembro(p_grupo) then
        raise exception 'no estás en este grupo';
    end if;
    return query select public.grupo_mensaje_json(x) from public.grupo_mensajes x
                  where x.grupo = p_grupo and x.fijado and not x.oculto order by x.id;
end $$;

-- lo reportado de un grupo (para quien modera)
drop function if exists public.grupo_reportados(uuid);
create function public.grupo_reportados(p_grupo uuid)
returns setof jsonb language plpgsql stable security definer set search_path = public as $$
begin
    perform public.grupo_exigir_rol(p_grupo, array['dueno', 'moderador']);
    return query
        select public.grupo_mensaje_json(x) || jsonb_build_object(
                   'reportes', (select count(*)::int from public.grupo_reportes r where r.mensaje = x.id),
                   'motivos', (select coalesce(jsonb_agg(r.motivo) filter (where r.motivo <> ''), '[]'::jsonb)
                                 from public.grupo_reportes r where r.mensaje = x.id))
        from public.grupo_mensajes x
        where x.grupo = p_grupo and exists (select 1 from public.grupo_reportes r where r.mensaje = x.id)
        order by x.oculto desc, x.id desc limit 100;
end $$;

-- ---------------------------------------------------------------- gente y moderación del grupo
drop function if exists public.grupo_miembros_lista(uuid, int, int);
create function public.grupo_miembros_lista(p_grupo uuid, p_limite int default 100, p_desde int default 0)
returns setof jsonb language plpgsql stable security definer set search_path = public as $$
begin
    if not public.grupo_es_miembro(p_grupo) then
        raise exception 'no estás en este grupo';
    end if;
    return query
        select jsonb_build_object('id', p.id, 'usuario', p.usuario, 'nombre', p.nombre, 'foto_url', p.foto_url,
                                  'rol', m.rol, 'unido', m.unido,
                                  'silenciado_hasta', case when m.silenciado_hasta > now() then m.silenciado_hasta end)
        from public.grupo_miembros m join public.perfiles p on p.id = m.user_id
        where m.grupo = p_grupo and not public.hay_bloqueo(auth.uid(), m.user_id)
        order by case m.rol when 'dueno' then 0 when 'moderador' then 1 else 2 end, m.unido
        limit least(greatest(p_limite, 1), 200) offset greatest(p_desde, 0);
end $$;

-- nombrar o quitar moderadores (solo quien es dueño)
drop function if exists public.grupo_poner_rol(uuid, uuid, text);
create function public.grupo_poner_rol(p_grupo uuid, p_usuario uuid, p_rol text)
returns void language plpgsql volatile security definer set search_path = public as $$
begin
    perform public.grupo_exigir_rol(p_grupo, array['dueno']);
    if p_rol not in ('moderador', 'miembro') then
        raise exception 'el rol es moderador o miembro';
    end if;
    if p_usuario = auth.uid() then
        raise exception 'no puedes cambiar tu propio rol';
    end if;
    update public.grupo_miembros set rol = p_rol where grupo = p_grupo and user_id = p_usuario;
    if not found then
        raise exception 'esa persona no está en el grupo';
    end if;
end $$;

-- pasar el grupo a otra persona del grupo
drop function if exists public.grupo_pasar_dueno(uuid, uuid);
create function public.grupo_pasar_dueno(p_grupo uuid, p_usuario uuid)
returns void language plpgsql volatile security definer set search_path = public as $$
begin
    perform public.grupo_exigir_rol(p_grupo, array['dueno']);
    if public.grupo_rol_de(p_grupo, p_usuario) is null or p_usuario = auth.uid() then
        raise exception 'esa persona no está en el grupo';
    end if;
    update public.grupo_miembros set rol = 'moderador' where grupo = p_grupo and user_id = auth.uid();
    update public.grupo_miembros set rol = 'dueno' where grupo = p_grupo and user_id = p_usuario;
    update public.grupos set dueno = p_usuario where id = p_grupo;
end $$;

-- quien modera no puede tocar a alguien de su mismo rango o más (un moderador no saca al dueño)
create or replace function public.grupo_puede_con(p_grupo uuid, p_usuario uuid)
returns void language plpgsql stable security definer set search_path = public as $$
declare
    yo text := public.grupo_exigir_rol(p_grupo, array['dueno', 'moderador']);
    otro text := public.grupo_rol_de(p_grupo, p_usuario);
begin
    if otro is null then
        raise exception 'esa persona no está en el grupo';
    end if;
    if p_usuario = auth.uid() or otro = 'dueno' or (otro = 'moderador' and yo <> 'dueno') then
        raise exception 'no puedes hacerle eso a esa persona';
    end if;
end $$;

-- silenciar un rato (0 minutos = quitar el silencio)
drop function if exists public.grupo_silenciar(uuid, uuid, int);
create function public.grupo_silenciar(p_grupo uuid, p_usuario uuid, p_minutos int)
returns void language plpgsql volatile security definer set search_path = public as $$
begin
    perform public.grupo_puede_con(p_grupo, p_usuario);
    if p_minutos < 0 or p_minutos > 60 * 24 * 7 then
        raise exception 'se silencia como mucho una semana';
    end if;
    update public.grupo_miembros
       set silenciado_hasta = case when p_minutos = 0 then null else now() + make_interval(mins => p_minutos) end
     where grupo = p_grupo and user_id = p_usuario;
end $$;

-- sacar del grupo (y que no pueda volver a entrar)
drop function if exists public.grupo_expulsar(uuid, uuid);
create function public.grupo_expulsar(p_grupo uuid, p_usuario uuid)
returns void language plpgsql volatile security definer set search_path = public as $$
begin
    perform public.grupo_puede_con(p_grupo, p_usuario);
    delete from public.grupo_miembros where grupo = p_grupo and user_id = p_usuario;
    insert into public.grupo_expulsados (grupo, user_id, por) values (p_grupo, p_usuario, auth.uid())
    on conflict (grupo, user_id) do nothing;
end $$;

drop function if exists public.grupo_readmitir(uuid, uuid);
create function public.grupo_readmitir(p_grupo uuid, p_usuario uuid)
returns void language plpgsql volatile security definer set search_path = public as $$
begin
    perform public.grupo_exigir_rol(p_grupo, array['dueno', 'moderador']);
    delete from public.grupo_expulsados where grupo = p_grupo and user_id = p_usuario;
end $$;

-- cambiar nombre y descripción (quien modera); nuevo código de invitación (dueño)
drop function if exists public.grupo_editar(uuid, text, text);
create function public.grupo_editar(p_grupo uuid, p_nombre text, p_descripcion text)
returns jsonb language plpgsql volatile security definer set search_path = public as $$
declare
    v_nombre text := public.grupo_texto(p_nombre, 50);
    g public.grupos;
begin
    perform public.grupo_exigir_rol(p_grupo, array['dueno', 'moderador']);
    if length(v_nombre) < 3 then
        raise exception 'el nombre del grupo necesita al menos 3 letras';
    end if;
    update public.grupos set nombre = v_nombre, descripcion = public.grupo_texto(p_descripcion, 300)
     where id = p_grupo returning * into g;
    perform public.grupo_avisar(p_grupo, 'grupo', '{}'::jsonb);
    return public.grupo_json(g);
end $$;

drop function if exists public.grupo_cambiar_codigo(uuid);
create function public.grupo_cambiar_codigo(p_grupo uuid)
returns text language plpgsql volatile security definer set search_path = public as $$
declare
    c text;
begin
    perform public.grupo_exigir_rol(p_grupo, array['dueno']);
    if (select tipo from public.grupos where id = p_grupo) <> 'privado' then
        raise exception 'solo los grupos privados tienen código';
    end if;
    c := public.grupo_codigo_nuevo();
    update public.grupos set codigo = c where id = p_grupo;
    return c;
end $$;

drop function if exists public.grupo_borrar(uuid);
create function public.grupo_borrar(p_grupo uuid)
returns void language plpgsql volatile security definer set search_path = public as $$
begin
    perform public.grupo_exigir_rol(p_grupo, array['dueno']);
    delete from storage.objects where bucket_id = 'audios-grupos' and name like p_grupo::text || '/%';
    delete from public.grupos where id = p_grupo;
end $$;

-- la moderación de Caudal cierra (o reabre) un grupo abierto que no cumple las normas
drop function if exists public.grupo_cerrar(uuid, boolean);
create function public.grupo_cerrar(p_grupo uuid, p_cerrar boolean default true)
returns void language plpgsql volatile security definer set search_path = public as $$
begin
    if not public.grupo_moderador_caudal() then
        raise exception 'eso solo lo puede hacer la moderación de Caudal';
    end if;
    update public.grupos set cerrado = p_cerrar where id = p_grupo;
end $$;

-- ---------------------------------------------------------------- almacén de las notas de voz
-- Las políticas se evalúan con los permisos de quien sube, que no puede leer grupo_miembros:
-- preguntan a estas dos funciones (que solo responden sobre quien llama).
create or replace function public.grupo_puedo_subir(p_nombre text)
returns boolean language sql stable security definer set search_path = public as $$
    select auth.uid() is not null
       and (storage.foldername(p_nombre))[2] = auth.uid()::text
       and exists (select 1 from public.grupo_miembros m
                    where m.grupo::text = (storage.foldername(p_nombre))[1]
                      and m.user_id = auth.uid()
                      and (m.silenciado_hasta is null or m.silenciado_hasta <= now()));
$$;

create or replace function public.grupo_puedo_oir(p_nombre text)
returns boolean language sql stable security definer set search_path = public as $$
    select auth.uid() is not null
       and exists (select 1 from public.grupo_miembros m
                    where m.grupo::text = (storage.foldername(p_nombre))[1] and m.user_id = auth.uid());
$$;

drop policy if exists "subo notas de voz a mis grupos" on storage.objects;
create policy "subo notas de voz a mis grupos" on storage.objects for insert to authenticated
    with check (bucket_id = 'audios-grupos' and public.grupo_puedo_subir(name));

drop policy if exists "oigo las notas de voz de mis grupos" on storage.objects;
create policy "oigo las notas de voz de mis grupos" on storage.objects for select to authenticated
    using (bucket_id = 'audios-grupos' and public.grupo_puedo_oir(name));

drop policy if exists "borro mis notas de voz" on storage.objects;
create policy "borro mis notas de voz" on storage.objects for delete to authenticated
    using (bucket_id = 'audios-grupos' and (storage.foldername(name))[2] = auth.uid()::text);

-- ---------------------------------------------------------------- permisos
-- ayudas internas: nadie las llama desde la app
revoke execute on function public.grupo_json(public.grupos), public.grupo_mensaje_json(public.grupo_mensajes),
    public.grupo_meter(public.grupos), public.grupo_avisar(uuid, text, jsonb), public.grupo_codigo_nuevo(),
    public.grupo_exigir_rol(uuid, text[]), public.grupo_puede_con(uuid, uuid), public.grupo_rol_de(uuid, uuid)
    from public, anon, authenticated;
-- las políticas del almacén usan esta: quien sube debe poder ejecutarla
grant execute on function public.grupo_es_miembro(uuid), public.grupo_puedo_subir(text),
    public.grupo_puedo_oir(text) to authenticated;

-- lo que usa la app (solo con cuenta)
revoke execute on function public.grupo_crear(text, text, text), public.grupos_explorar(text, int, int),
    public.mis_grupos(), public.grupo_ver(uuid), public.grupo_unirse(uuid), public.grupo_unirse_codigo(text),
    public.grupo_salir(uuid), public.grupo_mensajes(uuid, bigint, int), public.grupo_mensajes_desde(uuid, bigint),
    public.grupo_enviar(uuid, text, jsonb, text, int), public.grupo_leido(uuid), public.grupo_reportar(bigint, text),
    public.grupo_mensaje_accion(bigint, text), public.grupo_fijados(uuid), public.grupo_reportados(uuid),
    public.grupo_miembros_lista(uuid, int, int), public.grupo_poner_rol(uuid, uuid, text),
    public.grupo_pasar_dueno(uuid, uuid), public.grupo_silenciar(uuid, uuid, int), public.grupo_expulsar(uuid, uuid),
    public.grupo_readmitir(uuid, uuid), public.grupo_editar(uuid, text, text), public.grupo_cambiar_codigo(uuid),
    public.grupo_borrar(uuid), public.grupo_cerrar(uuid, boolean)
    from public, anon;
grant execute on function public.grupo_crear(text, text, text), public.grupos_explorar(text, int, int),
    public.mis_grupos(), public.grupo_ver(uuid), public.grupo_unirse(uuid), public.grupo_unirse_codigo(text),
    public.grupo_salir(uuid), public.grupo_mensajes(uuid, bigint, int), public.grupo_mensajes_desde(uuid, bigint),
    public.grupo_enviar(uuid, text, jsonb, text, int), public.grupo_leido(uuid), public.grupo_reportar(bigint, text),
    public.grupo_mensaje_accion(bigint, text), public.grupo_fijados(uuid), public.grupo_reportados(uuid),
    public.grupo_miembros_lista(uuid, int, int), public.grupo_poner_rol(uuid, uuid, text),
    public.grupo_pasar_dueno(uuid, uuid), public.grupo_silenciar(uuid, uuid, int), public.grupo_expulsar(uuid, uuid),
    public.grupo_readmitir(uuid, uuid), public.grupo_editar(uuid, text, text), public.grupo_cambiar_codigo(uuid),
    public.grupo_borrar(uuid), public.grupo_cerrar(uuid, boolean)
    to authenticated;
