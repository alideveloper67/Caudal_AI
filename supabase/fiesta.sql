-- ================================================================ Caudal: Fiesta por QR
-- El anfitrión abre «Fiesta» en la app (móvil o Windows): sale un QR y un código de 6 letras.
-- Los invitados lo escanean y, desde la página web /fiesta (sin instalar nada ni tener cuenta),
-- buscan canciones, las añaden a la cola del anfitrión, votan las siguientes y ven qué suena.
-- El anfitrión quita canciones, limita cuántas añade cada invitado y cierra la fiesta.
--
-- Se pega entero en el SQL Editor de Supabase (después de esquema.sql). Se puede repetir.
-- No depende de las tablas de listas ni de las sociales.
--
-- Reglas de seguridad (no dependen de la app):
--   · Las tablas no se pueden leer ni escribir desde la API: todo entra por las funciones de abajo.
--   · El anfitrión se identifica con la «clave» secreta que devuelve fiesta_crear (solo se guarda
--     su md5). Sin la clave no se puede quitar, limitar, cerrar ni decir qué suena.
--   · Cada invitado se identifica con un token al azar que guarda su navegador (16-64 caracteres);
--     en la base solo queda su md5 y nunca se devuelve.
--   · Topes: 300 canciones esperando por fiesta, 300 invitados, textos cortos, 300 fiestas nuevas
--     por hora en todo Caudal. Las fiestas sin movimiento en 24 h se borran solas.
--
-- Tiempo real: cada cambio sube `version` y avisa por Realtime Broadcast en el canal público
-- `fiesta-<CODIGO>` (evento «cambio», payload {"version": n}) con realtime.send(). Quien lo oye
-- vuelve a pedir fiesta_ver. Si realtime.send no existe, el cambio se guarda igual (las apps y la
-- web además preguntan cada 20 s).

-- ---------------------------------------------------------------- tablas
create table if not exists public.fiestas (
    codigo      text primary key check (codigo ~ '^[ABCDEFGHJKLMNPQRSTUVWXYZ23456789]{6}$'),
    clave_md5   text not null,
    anfitrion   uuid references auth.users (id) on delete set null,
    nombre      text not null default 'Fiesta' check (length(nombre) between 1 and 60),
    limite      int  not null default 5 check (limite between 0 and 50),   -- 0 = sin límite
    abierta     boolean not null default true,
    sonando     jsonb check (sonando is null or (jsonb_typeof(sonando) = 'object' and pg_column_size(sonando) < 4000)),
    version     bigint not null default 1,
    creada      timestamptz not null default now(),
    actividad   timestamptz not null default now(),
    cerrada     timestamptz
);
create index if not exists fiestas_actividad on public.fiestas (actividad);
create index if not exists fiestas_creada on public.fiestas (creada);

create table if not exists public.fiesta_canciones (
    id          bigint generated always as identity primary key,
    codigo      text not null references public.fiestas (codigo) on delete cascade,
    video_id    text not null check (video_id ~ '^[A-Za-z0-9_-]{11}$'),
    titulo      text not null default '' check (length(titulo) <= 200),
    artista     text not null default '' check (length(artista) <= 200),
    miniatura   text not null default '' check (length(miniatura) <= 500),
    duracion    int  not null default 0 check (duracion between 0 and 86400),
    invitado    text not null,                     -- md5 del token, o 'anfitrion'
    nombre      text not null default '' check (length(nombre) <= 30),
    estado      text not null default 'cola' check (estado in ('cola', 'sonando', 'sonada', 'quitada')),
    votos       int  not null default 0,
    anadida     timestamptz not null default clock_timestamp(),
    cambio      timestamptz not null default clock_timestamp()
);
create index if not exists fiesta_canciones_cola on public.fiesta_canciones (codigo, estado);
create index if not exists fiesta_canciones_invitado on public.fiesta_canciones (codigo, invitado);
-- una canción no puede estar dos veces esperando (o sonando) en la misma fiesta
create unique index if not exists fiesta_canciones_sin_repetir
    on public.fiesta_canciones (codigo, video_id) where estado in ('cola', 'sonando');

create table if not exists public.fiesta_votos (
    cancion     bigint not null references public.fiesta_canciones (id) on delete cascade,
    invitado    text not null,
    primary key (cancion, invitado)
);

create table if not exists public.fiesta_invitados (
    codigo      text not null references public.fiestas (codigo) on delete cascade,
    invitado    text not null,
    nombre      text not null default '' check (length(nombre) <= 30),
    entro       timestamptz not null default now(),
    primary key (codigo, invitado)
);

alter table public.fiestas          enable row level security;
alter table public.fiesta_canciones enable row level security;
alter table public.fiesta_votos     enable row level security;
alter table public.fiesta_invitados enable row level security;
-- sin políticas y sin permisos: solo las funciones de abajo las tocan
revoke all on public.fiestas, public.fiesta_canciones, public.fiesta_votos, public.fiesta_invitados
    from anon, authenticated;

-- ---------------------------------------------------------------- ayudas internas
create or replace function public.fiesta_normalizar(p_codigo text)
returns text language sql immutable set search_path = public as $$
    select upper(regexp_replace(coalesce(p_codigo, ''), '[[:space:]-]', '', 'g'));
$$;

-- 6 caracteres del alfabeto de «Escuchar juntos» (sin 0/O ni 1/I). Son 32 letras: cada byte
-- al azar (de gen_random_uuid, saltando los de versión) da una sin sesgo con «% 32».
create or replace function public.fiesta_nuevo_codigo()
returns text language plpgsql volatile security definer set search_path = public as $$
declare
    alfabeto constant text := 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
    r text := '';
    b bytea;
begin
    b := decode(replace(gen_random_uuid()::text, '-', ''), 'hex');
    for i in 0..15 loop
        continue when i in (6, 8);
        r := r || substr(alfabeto, (get_byte(b, i) % 32) + 1, 1);
        exit when length(r) = 6;
    end loop;
    return r;
end $$;

-- El token del invitado → su huella (md5). Lanza si no tiene la forma esperada.
create or replace function public.fiesta_huella(p_invitado text)
returns text language plpgsql immutable set search_path = public as $$
begin
    if p_invitado is null or p_invitado !~ '^[A-Za-z0-9_-]{16,64}$' then
        raise exception 'No pudimos reconocer tu teléfono. Recarga la página de la fiesta.';
    end if;
    return md5('fiesta:' || p_invitado);
end $$;

create or replace function public.fiesta_texto(p text, p_largo int)
returns text language sql immutable set search_path = public as $$
    select left(btrim(regexp_replace(coalesce(p, ''), '[[:cntrl:]]+', ' ', 'g')), p_largo);
$$;

-- Un número escrito por la app; 0 si no lo es.
create or replace function public.fiesta_numero(p text)
returns numeric language sql immutable set search_path = public as $$
    select case when btrim(coalesce(p, '')) ~ '^[0-9]{1,12}(\.[0-9]+)?$' then btrim(p)::numeric else 0 end;
$$;

-- Avisa por Realtime de que la fiesta cambió. Nunca hace fallar al que llama.
create or replace function public.fiesta_avisar(p_codigo text, p_version bigint)
returns void language plpgsql volatile security definer set search_path = public as $$
begin
    begin
        perform realtime.send(jsonb_build_object('version', p_version), 'cambio', 'fiesta-' || p_codigo, false);
    exception when others then
        null;
    end;
end $$;

-- Sube la versión, apunta actividad y avisa. Devuelve la versión nueva.
create or replace function public.fiesta_tocar(p_codigo text)
returns bigint language plpgsql volatile security definer set search_path = public as $$
declare v bigint;
begin
    update public.fiestas set version = version + 1, actividad = now()
     where codigo = p_codigo returning version into v;
    if v is not null then perform public.fiesta_avisar(p_codigo, v); end if;
    return v;
end $$;

-- La fiesta abierta con ese código (bloqueada para cambiarla), o un error claro.
create or replace function public.fiesta_abierta(p_codigo text)
returns public.fiestas language plpgsql volatile security definer set search_path = public as $$
declare f public.fiestas;
begin
    select * into f from public.fiestas where codigo = public.fiesta_normalizar(p_codigo) for update;
    if not found then raise exception 'Esa fiesta no existe. Revisa el código o vuelve a escanear el QR.'; end if;
    if not f.abierta then raise exception 'Esta fiesta ya terminó: el anfitrión la cerró.'; end if;
    return f;
end $$;

-- La fiesta (abierta o no) si la clave del anfitrión es la buena.
create or replace function public.fiesta_de_anfitrion(p_codigo text, p_clave text)
returns public.fiestas language plpgsql volatile security definer set search_path = public as $$
declare f public.fiestas;
begin
    select * into f from public.fiestas where codigo = public.fiesta_normalizar(p_codigo) for update;
    if not found then raise exception 'Esa fiesta ya no existe.'; end if;
    if p_clave is null or md5(p_clave) <> f.clave_md5 then
        raise exception 'Solo el anfitrión puede hacer eso en esta fiesta.';
    end if;
    return f;
end $$;

-- Una canción como la devuelven las funciones (sin la huella del invitado).
create or replace function public.fiesta_cancion_json(c public.fiesta_canciones, p_huella text)
returns jsonb language sql stable security definer set search_path = public as $$
    select jsonb_build_object(
        'id', c.id, 'video_id', c.video_id, 'titulo', c.titulo, 'artista', c.artista,
        'miniatura', c.miniatura, 'duracion', c.duracion, 'nombre', c.nombre,
        'votos', c.votos, 'estado', c.estado,
        'de_anfitrion', c.invitado = 'anfitrion',
        'mia', p_huella is not null and c.invitado = p_huella,
        'vote', p_huella is not null and exists (
            select 1 from public.fiesta_votos v where v.cancion = c.id and v.invitado = p_huella));
$$;

-- ---------------------------------------------------------------- leer
-- Todo lo que ve un invitado (o el anfitrión, sin token). null si el código no existe.
-- cola: en el orden en que sonarán (más votos primero; a igualdad, la que llegó antes).
create or replace function public.fiesta_ver(p_codigo text, p_invitado text default null)
returns jsonb language plpgsql stable security definer set search_path = public as $$
declare
    f public.fiestas;
    h text := null;
begin
    select * into f from public.fiestas where codigo = public.fiesta_normalizar(p_codigo);
    if not found then return null; end if;
    if p_invitado is not null and p_invitado ~ '^[A-Za-z0-9_-]{16,64}$' then
        h := md5('fiesta:' || p_invitado);
    end if;
    return jsonb_build_object(
        'codigo', f.codigo,
        'nombre', f.nombre,
        'abierta', f.abierta,
        'limite', f.limite,
        'version', f.version,
        'sonando', f.sonando,
        'ahora', (extract(epoch from clock_timestamp()) * 1000)::bigint,
        'invitados', (select count(*) from public.fiesta_invitados i where i.codigo = f.codigo),
        'mias', case when h is null then 0 else
            (select count(*) from public.fiesta_canciones c
              where c.codigo = f.codigo and c.invitado = h and c.estado <> 'quitada') end,
        'cola', coalesce((select jsonb_agg(public.fiesta_cancion_json(c, h) order by c.votos desc, c.anadida, c.id)
                            from public.fiesta_canciones c where c.codigo = f.codigo and c.estado = 'cola'), '[]'::jsonb),
        -- lo último primero (la que suena, si hay, va la primera)
        'sonadas', coalesce((select jsonb_agg(x.j order by x.ahora desc, x.cambio desc, x.id desc) from (
                                select public.fiesta_cancion_json(c, h) as j, c.cambio, c.id, c.estado = 'sonando' as ahora
                                  from public.fiesta_canciones c
                                 where c.codigo = f.codigo and c.estado in ('sonando', 'sonada')
                                 order by c.estado = 'sonando' desc, c.cambio desc, c.id desc limit 15) x), '[]'::jsonb)
    );
end $$;

-- ---------------------------------------------------------------- anfitrión
-- Crea la fiesta. Devuelve {codigo, clave}: la clave es secreta y solo la guarda la app del
-- anfitrión. Con sesión de Caudal se apunta quién la creó; sin sesión también se puede.
drop function if exists public.fiesta_crear(text, int);
create function public.fiesta_crear(p_nombre text default null, p_limite int default 5)
returns jsonb language plpgsql volatile security definer set search_path = public as $$
declare
    cod text;
    clave text := replace(gen_random_uuid()::text, '-', '') || replace(gen_random_uuid()::text, '-', '');
    nombre text := public.fiesta_texto(p_nombre, 60);
    intentos int := 0;
begin
    delete from public.fiestas where actividad < now() - interval '24 hours';
    if (select count(*) from public.fiestas where creada > now() - interval '1 hour') >= 300 then
        raise exception 'Ahora mismo hay demasiadas fiestas nuevas. Prueba de nuevo en unos minutos.';
    end if;
    if p_limite is null or p_limite < 0 or p_limite > 50 then
        raise exception 'El límite por invitado va de 0 (sin límite) a 50 canciones.';
    end if;
    loop
        cod := public.fiesta_nuevo_codigo();
        exit when not exists (select 1 from public.fiestas where codigo = cod);
        intentos := intentos + 1;
        if intentos > 20 then raise exception 'No se pudo crear la fiesta. Vuelve a intentarlo.'; end if;
    end loop;
    insert into public.fiestas (codigo, clave_md5, anfitrion, nombre, limite)
    values (cod, md5(clave), auth.uid(), case when nombre = '' then 'Fiesta' else nombre end, p_limite);
    return jsonb_build_object('codigo', cod, 'clave', clave);
end $$;

-- Quita una canción de la cola (o de lo que ya sonó). Devuelve fiesta_ver.
create or replace function public.fiesta_quitar(p_codigo text, p_clave text, p_cancion bigint)
returns jsonb language plpgsql volatile security definer set search_path = public as $$
declare f public.fiestas;
begin
    f := public.fiesta_de_anfitrion(p_codigo, p_clave);
    update public.fiesta_canciones set estado = 'quitada', cambio = clock_timestamp()
     where id = p_cancion and codigo = f.codigo and estado = 'cola';
    if not found then raise exception 'Esa canción ya no está en la cola.'; end if;
    perform public.fiesta_tocar(f.codigo);
    return public.fiesta_ver(f.codigo);
end $$;

-- Cuántas canciones puede añadir cada invitado (0 = sin límite). No borra las que ya añadieron.
create or replace function public.fiesta_limite(p_codigo text, p_clave text, p_limite int)
returns jsonb language plpgsql volatile security definer set search_path = public as $$
declare f public.fiestas;
begin
    f := public.fiesta_de_anfitrion(p_codigo, p_clave);
    if p_limite is null or p_limite < 0 or p_limite > 50 then
        raise exception 'El límite por invitado va de 0 (sin límite) a 50 canciones.';
    end if;
    update public.fiestas set limite = p_limite where codigo = f.codigo;
    perform public.fiesta_tocar(f.codigo);
    return public.fiesta_ver(f.codigo);
end $$;

-- Cambia el nombre que ven los invitados.
create or replace function public.fiesta_renombrar(p_codigo text, p_clave text, p_nombre text)
returns jsonb language plpgsql volatile security definer set search_path = public as $$
declare f public.fiestas; n text := public.fiesta_texto(p_nombre, 60);
begin
    f := public.fiesta_de_anfitrion(p_codigo, p_clave);
    update public.fiestas set nombre = case when n = '' then 'Fiesta' else n end where codigo = f.codigo;
    perform public.fiesta_tocar(f.codigo);
    return public.fiesta_ver(f.codigo);
end $$;

-- Cierra la fiesta: nadie más puede añadir ni votar. Se puede llamar dos veces.
create or replace function public.fiesta_cerrar(p_codigo text, p_clave text)
returns jsonb language plpgsql volatile security definer set search_path = public as $$
declare f public.fiestas;
begin
    f := public.fiesta_de_anfitrion(p_codigo, p_clave);
    if f.abierta then
        update public.fiestas set abierta = false, cerrada = now(), sonando = null where codigo = f.codigo;
        update public.fiesta_canciones set estado = 'sonada', cambio = clock_timestamp()
         where codigo = f.codigo and estado = 'sonando';
        perform public.fiesta_tocar(f.codigo);
    end if;
    return public.fiesta_ver(f.codigo);
end $$;

-- La siguiente canción: la primera de la cola pasa a «sonando» (la que sonaba, a «sonada»).
-- Devuelve la canción (jsonb) o null si la cola está vacía o la fiesta está cerrada.
create or replace function public.fiesta_tomar(p_codigo text, p_clave text)
returns jsonb language plpgsql volatile security definer set search_path = public as $$
declare
    f public.fiestas;
    c public.fiesta_canciones;
begin
    f := public.fiesta_de_anfitrion(p_codigo, p_clave);
    if not f.abierta then return null; end if;
    select * into c from public.fiesta_canciones
     where codigo = f.codigo and estado = 'cola'
     order by votos desc, anadida, id limit 1 for update;
    if not found then return null; end if;
    update public.fiesta_canciones set estado = 'sonada', cambio = clock_timestamp()
     where codigo = f.codigo and estado = 'sonando';
    update public.fiesta_canciones set estado = 'sonando', cambio = clock_timestamp()
     where id = c.id returning * into c;
    perform public.fiesta_tocar(f.codigo);
    return public.fiesta_cancion_json(c, null);
end $$;

-- Lo que suena en el aparato del anfitrión (null = nada). p_pista: {video_id, titulo, artista,
-- miniatura, duracion (s), pos_ms, pausa, fiesta_id?}. Si la pista está en la cola (por su
-- fiesta_id o su video_id), sale de la cola y queda como «sonando».
create or replace function public.fiesta_sonando(p_codigo text, p_clave text, p_pista jsonb)
returns jsonb language plpgsql volatile security definer set search_path = public as $$
declare
    f public.fiestas;
    s jsonb := null;
    vid text;
    fid bigint;
    ahora bigint := (extract(epoch from clock_timestamp()) * 1000)::bigint;
begin
    f := public.fiesta_de_anfitrion(p_codigo, p_clave);
    if not f.abierta then return public.fiesta_ver(f.codigo); end if;
    if p_pista is not null and jsonb_typeof(p_pista) = 'object' then
        vid := p_pista ->> 'video_id';
        if vid is not null and vid !~ '^[A-Za-z0-9_-]{11}$' then vid := null; end if;
        begin fid := (p_pista ->> 'fiesta_id')::bigint; exception when others then fid := null; end;
        s := jsonb_build_object(
            'video_id', coalesce(vid, ''),
            'titulo', public.fiesta_texto(p_pista ->> 'titulo', 200),
            'artista', public.fiesta_texto(p_pista ->> 'artista', 200),
            'miniatura', case when (p_pista ->> 'miniatura') ~ '^https://[^[:space:]"''<>]+$' and length(p_pista ->> 'miniatura') <= 500
                              then p_pista ->> 'miniatura' else '' end,
            'duracion', least(86400, public.fiesta_numero(p_pista ->> 'duracion'))::int,
            'pos_ms', public.fiesta_numero(p_pista ->> 'pos_ms')::bigint,
            'pausa', (p_pista -> 'pausa') = 'true'::jsonb,
            't', ahora);
        -- de qué canción de la fiesta se trata (si es una)
        if fid is not null and not exists (select 1 from public.fiesta_canciones
                                            where id = fid and codigo = f.codigo and estado in ('cola', 'sonando')) then
            fid := null;
        end if;
        if fid is null and vid is not null then
            select id into fid from public.fiesta_canciones
             where codigo = f.codigo and video_id = vid and estado in ('cola', 'sonando') limit 1;
        end if;
        if fid is not null then
            s := s || jsonb_build_object('fiesta_id', fid,
                'nombre', (select nombre from public.fiesta_canciones where id = fid));
        end if;
    end if;
    update public.fiesta_canciones set estado = 'sonada', cambio = clock_timestamp()
     where codigo = f.codigo and estado = 'sonando' and (fid is null or id <> fid);
    if fid is not null then
        update public.fiesta_canciones set estado = 'sonando', cambio = clock_timestamp()
         where id = fid and estado = 'cola';
    end if;
    update public.fiestas set sonando = s where codigo = f.codigo;
    perform public.fiesta_tocar(f.codigo);
    return public.fiesta_ver(f.codigo);
end $$;

-- ---------------------------------------------------------------- invitados
-- Entrar (o cambiar el nombre). Devuelve fiesta_ver con sus datos.
create or replace function public.fiesta_entrar(p_codigo text, p_invitado text, p_nombre text default null)
returns jsonb language plpgsql volatile security definer set search_path = public as $$
declare
    f public.fiestas;
    h text := public.fiesta_huella(p_invitado);
    n text := public.fiesta_texto(p_nombre, 30);
begin
    f := public.fiesta_abierta(p_codigo);
    if not exists (select 1 from public.fiesta_invitados where codigo = f.codigo and invitado = h) then
        if (select count(*) from public.fiesta_invitados where codigo = f.codigo) >= 300 then
            raise exception 'Esta fiesta ya está llena (300 invitados).';
        end if;
        insert into public.fiesta_invitados (codigo, invitado, nombre) values (f.codigo, h, n);
        perform public.fiesta_tocar(f.codigo);
    elsif n <> '' then
        update public.fiesta_invitados set nombre = n where codigo = f.codigo and invitado = h and nombre <> n;
        if found then perform public.fiesta_tocar(f.codigo); end if;
    end if;
    return public.fiesta_ver(f.codigo, p_invitado);
end $$;

-- Añadir una canción a la cola. p_pista: {video_id, titulo, artista, miniatura, duracion}.
create or replace function public.fiesta_anadir(p_codigo text, p_invitado text, p_pista jsonb, p_nombre text default null)
returns jsonb language plpgsql volatile security definer set search_path = public as $$
declare
    f public.fiestas;
    h text := public.fiesta_huella(p_invitado);
    vid text := p_pista ->> 'video_id';
    n text := public.fiesta_texto(p_nombre, 30);
    mias int;
begin
    f := public.fiesta_abierta(p_codigo);
    if p_pista is null or jsonb_typeof(p_pista) <> 'object' or vid is null or vid !~ '^[A-Za-z0-9_-]{11}$' then
        raise exception 'Esa canción no se puede añadir. Elige otra de la búsqueda.';
    end if;
    if exists (select 1 from public.fiesta_canciones where codigo = f.codigo and video_id = vid and estado = 'cola') then
        raise exception 'Esa canción ya está en la cola: vótala para que suene antes.';
    end if;
    if exists (select 1 from public.fiesta_canciones where codigo = f.codigo and video_id = vid and estado = 'sonando') then
        raise exception 'Esa canción está sonando ahora mismo.';
    end if;
    if f.limite > 0 then
        select count(*) into mias from public.fiesta_canciones
         where codigo = f.codigo and invitado = h and estado <> 'quitada';
        if mias >= f.limite then
            raise exception 'Ya añadiste % %, que es el máximo de esta fiesta.', f.limite,
                case when f.limite = 1 then 'canción' else 'canciones' end;
        end if;
    end if;
    if (select count(*) from public.fiesta_canciones where codigo = f.codigo and estado = 'cola') >= 300 then
        raise exception 'La cola de la fiesta está llena. Espera a que suenen algunas.';
    end if;
    -- quien añade sin haber «entrado» queda apuntado como invitado
    if not exists (select 1 from public.fiesta_invitados where codigo = f.codigo and invitado = h) then
        if (select count(*) from public.fiesta_invitados where codigo = f.codigo) >= 300 then
            raise exception 'Esta fiesta ya está llena (300 invitados).';
        end if;
        insert into public.fiesta_invitados (codigo, invitado, nombre) values (f.codigo, h, n);
    elsif n = '' then
        select nombre into n from public.fiesta_invitados where codigo = f.codigo and invitado = h;
    end if;
    insert into public.fiesta_canciones (codigo, video_id, titulo, artista, miniatura, duracion, invitado, nombre)
    values (f.codigo, vid,
            coalesce(nullif(public.fiesta_texto(p_pista ->> 'titulo', 200), ''), 'Sin título'),
            public.fiesta_texto(p_pista ->> 'artista', 200),
            case when (p_pista ->> 'miniatura') ~ '^https://[^[:space:]"''<>]+$' and length(p_pista ->> 'miniatura') <= 500 then p_pista ->> 'miniatura' else '' end,
            least(86400, public.fiesta_numero(p_pista ->> 'duracion'))::int,
            h, coalesce(n, ''));
    perform public.fiesta_tocar(f.codigo);
    return public.fiesta_ver(f.codigo, p_invitado);
end $$;

-- Votar (p_voto true) o quitar el voto (false) a una canción que espera en la cola.
create or replace function public.fiesta_votar(p_codigo text, p_invitado text, p_cancion bigint, p_voto boolean default true)
returns jsonb language plpgsql volatile security definer set search_path = public as $$
declare
    f public.fiestas;
    h text := public.fiesta_huella(p_invitado);
begin
    f := public.fiesta_abierta(p_codigo);
    perform 1 from public.fiesta_canciones where id = p_cancion and codigo = f.codigo and estado = 'cola' for update;
    if not found then raise exception 'Esa canción ya no está en la cola.'; end if;
    if coalesce(p_voto, true) then
        insert into public.fiesta_votos (cancion, invitado) values (p_cancion, h) on conflict do nothing;
    else
        delete from public.fiesta_votos where cancion = p_cancion and invitado = h;
    end if;
    update public.fiesta_canciones
       set votos = (select count(*) from public.fiesta_votos v where v.cancion = p_cancion)
     where id = p_cancion;
    perform public.fiesta_tocar(f.codigo);
    return public.fiesta_ver(f.codigo, p_invitado);
end $$;

-- ---------------------------------------------------------------- permisos
-- Las ayudas internas no se llaman desde la API.
revoke all on function public.fiesta_nuevo_codigo() from public, anon, authenticated;
revoke all on function public.fiesta_huella(text) from public, anon, authenticated;
revoke all on function public.fiesta_texto(text, int) from public, anon, authenticated;
revoke all on function public.fiesta_avisar(text, bigint) from public, anon, authenticated;
revoke all on function public.fiesta_tocar(text) from public, anon, authenticated;
revoke all on function public.fiesta_abierta(text) from public, anon, authenticated;
revoke all on function public.fiesta_de_anfitrion(text, text) from public, anon, authenticated;
revoke all on function public.fiesta_cancion_json(public.fiesta_canciones, text) from public, anon, authenticated;
revoke all on function public.fiesta_normalizar(text) from public, anon, authenticated;
revoke all on function public.fiesta_numero(text) from public, anon, authenticated;

-- Las que sí: invitados sin cuenta (anon) y apps con o sin sesión.
grant execute on function public.fiesta_ver(text, text) to anon, authenticated;
grant execute on function public.fiesta_crear(text, int) to anon, authenticated;
grant execute on function public.fiesta_quitar(text, text, bigint) to anon, authenticated;
grant execute on function public.fiesta_limite(text, text, int) to anon, authenticated;
grant execute on function public.fiesta_renombrar(text, text, text) to anon, authenticated;
grant execute on function public.fiesta_cerrar(text, text) to anon, authenticated;
grant execute on function public.fiesta_tomar(text, text) to anon, authenticated;
grant execute on function public.fiesta_sonando(text, text, jsonb) to anon, authenticated;
grant execute on function public.fiesta_entrar(text, text, text) to anon, authenticated;
grant execute on function public.fiesta_anadir(text, text, jsonb, text) to anon, authenticated;
grant execute on function public.fiesta_votar(text, text, bigint, boolean) to anon, authenticated;
