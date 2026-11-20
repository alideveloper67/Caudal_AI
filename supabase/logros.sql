-- ---------------------------------------------------------------- Logros de Caudal
-- Insignias por rachas de escucha, horas, canciones descubiertas, listas, escuchar con amigos...
-- Cada app las calcula y las guarda en el equipo; aquí se guarda una copia para que sean las mismas
-- en el teléfono y en la computadora, y la «vitrina» (hasta 3 logros que se lucen en el perfil).
--
--   logros_guardar(...)  junta lo del equipo con lo de la nube (nunca baja nada) y devuelve el total
--   logros_mios()        lo guardado de la cuenta
--   logros_de(usuario)   la vitrina de otra persona, con las mismas reglas que su perfil
--                        (amigos, o perfil público de mayor de edad; nunca con bloqueo)
--
-- Necesita esquema.sql y social.sql (perfiles, relacion_con, hay_bloqueo, es_mayor).
-- Se puede ejecutar de nuevo sin romper nada.

create table if not exists public.logros (
    user_id       uuid primary key references auth.users (id) on delete cascade,
    -- contadores: {"segundos": 7200, "canciones": 120, ...}; solo números enteros >= 0
    contadores    jsonb not null default '{}'::jsonb,
    -- días con música (aaaa-mm-dd), para las rachas; se guardan los 400 más recientes
    dias          text[] not null default '{}',
    -- dónde se usó Caudal: windows, android, ios, web
    plataformas   text[] not null default '{}',
    -- {"racha_7": 1731000000, ...}: cuándo se consiguió cada uno (segundos desde 1970)
    desbloqueados jsonb not null default '{}'::jsonb,
    vitrina       text[] not null default '{}' check (cardinality(vitrina) <= 3),
    actualizado   timestamptz not null default now()
);

alter table public.logros enable row level security;

-- cada quien lee lo suyo; se escribe solo con logros_guardar (que valida y junta)
drop policy if exists "logros: leer lo mio" on public.logros;
create policy "logros: leer lo mio" on public.logros for select to authenticated
    using (user_id = auth.uid());

revoke all on public.logros from anon, authenticated;
grant select on public.logros to authenticated;

create or replace function public.logros_json(l public.logros)
returns jsonb language sql immutable as $$
    select jsonb_build_object('contadores', coalesce(l.contadores, '{}'::jsonb),
                              'dias', to_jsonb(coalesce(l.dias, '{}'::text[])),
                              'plataformas', to_jsonb(coalesce(l.plataformas, '{}'::text[])),
                              'desbloqueados', coalesce(l.desbloqueados, '{}'::jsonb),
                              'vitrina', to_jsonb(coalesce(l.vitrina, '{}'::text[])),
                              'actualizado', l.actualizado)
$$;

create or replace function public.logros_guardar(p_contadores jsonb default '{}'::jsonb,
                                                 p_dias text[] default '{}',
                                                 p_plataformas text[] default '{}',
                                                 p_desbloqueados jsonb default '{}'::jsonb,
                                                 p_vitrina text[] default null)
returns jsonb language plpgsql security definer set search_path = public as $$
declare
    yo uuid := auth.uid();
    actual public.logros;
    cont jsonb;
    desb jsonb;
    k text;
    v jsonb;
    n bigint;
    dias_n text[];
    plat_n text[];
    vit text[];
begin
    if yo is null then
        raise exception 'Inicia sesión para guardar tus logros.';
    end if;
    p_contadores := coalesce(p_contadores, '{}'::jsonb);
    p_desbloqueados := coalesce(p_desbloqueados, '{}'::jsonb);
    if jsonb_typeof(p_contadores) <> 'object' or jsonb_typeof(p_desbloqueados) <> 'object' then
        raise exception 'Datos de logros no válidos.';
    end if;
    if length(p_contadores::text) > 4000 or length(p_desbloqueados::text) > 8000
       or cardinality(coalesce(p_dias, '{}')) > 1000 then
        raise exception 'Datos de logros demasiado grandes.';
    end if;

    insert into public.logros (user_id) values (yo) on conflict (user_id) do nothing;
    select * into actual from public.logros where user_id = yo for update;

    -- contadores: gana el mayor (nunca se pierde lo conseguido en otro equipo)
    cont := coalesce(actual.contadores, '{}'::jsonb);
    for k, v in select * from jsonb_each(p_contadores) loop
        continue when k !~ '^[a-z0-9_]{1,32}$' or jsonb_typeof(v) <> 'number';
        n := least(greatest(floor((v #>> '{}')::numeric), 0), 1000000000)::bigint;
        if n > coalesce((cont ->> k)::bigint, 0) then
            cont := cont || jsonb_build_object(k, n);
        end if;
    end loop;

    -- desbloqueados: se juntan; si los dos lo tienen, vale la fecha más antigua
    desb := coalesce(actual.desbloqueados, '{}'::jsonb);
    for k, v in select * from jsonb_each(p_desbloqueados) loop
        continue when k !~ '^[a-z0-9_]{1,40}$' or jsonb_typeof(v) <> 'number';
        n := least(greatest(floor((v #>> '{}')::numeric), 0), 4102444800)::bigint;
        if not desb ? k or n < (desb ->> k)::bigint then
            desb := desb || jsonb_build_object(k, n);
        end if;
    end loop;
    if (select count(*) from jsonb_object_keys(desb)) > 200 then
        raise exception 'Demasiados logros.';
    end if;

    -- días: unión de fechas válidas, las 400 más recientes
    select coalesce(array_agg(d order by d desc), '{}') into dias_n from (
        select distinct d from unnest(coalesce(actual.dias, '{}') || coalesce(p_dias, '{}')) d
         where d ~ '^\d{4}-\d{2}-\d{2}$'
         order by d desc limit 400) q;

    select coalesce(array_agg(distinct p order by p), '{}') into plat_n
      from unnest(coalesce(actual.plataformas, '{}') || coalesce(p_plataformas, '{}')) p
     where p in ('windows', 'android', 'ios', 'web', 'macos', 'linux');

    -- vitrina: solo logros conseguidos, sin repetir, como mucho 3 (null = no se toca)
    if p_vitrina is null then
        vit := coalesce(actual.vitrina, '{}');
    else
        select coalesce(array_agg(x order by o), '{}') into vit from (
            select x, min(o) o from unnest(p_vitrina) with ordinality as t(x, o)
             where desb ? x group by x order by min(o) limit 3) q;
    end if;

    update public.logros
       set contadores = cont, desbloqueados = desb, dias = dias_n, plataformas = plat_n,
           vitrina = vit, actualizado = now()
     where user_id = yo
    returning * into actual;
    return public.logros_json(actual);
end $$;

create or replace function public.logros_mios()
returns jsonb language sql stable security definer set search_path = public as $$
    select public.logros_json(l) from public.logros l where l.user_id = auth.uid()
$$;

-- la vitrina de otra persona: con las mismas reglas que ver_perfil
create or replace function public.logros_de(p_usuario text)
returns jsonb language plpgsql stable security definer set search_path = public as $$
declare
    p public.perfiles;
    yo uuid := auth.uid();
    l public.logros;
begin
    select * into p from public.perfiles where usuario = lower(trim(p_usuario));
    if p.id is null or yo is null then return null; end if;
    if public.hay_bloqueo(yo, p.id) then return null; end if;
    if not (p.id = yo or public.relacion_con(p.id) = 'amigo'
            or (p.perfil_publico and public.es_mayor(p.id))) then
        return null;
    end if;
    select * into l from public.logros where user_id = p.id;
    if l.user_id is null then
        return jsonb_build_object('vitrina', '[]'::jsonb, 'total', 0, 'fechas', '{}'::jsonb);
    end if;
    return jsonb_build_object(
        'vitrina', to_jsonb(l.vitrina),
        'total', (select count(*) from jsonb_object_keys(l.desbloqueados)),
        'fechas', coalesce((select jsonb_object_agg(x, l.desbloqueados -> x) from unnest(l.vitrina) x), '{}'::jsonb));
end $$;

revoke execute on function public.logros_guardar(jsonb, text[], text[], jsonb, text[]) from public, anon;
revoke execute on function public.logros_mios() from public, anon;
revoke execute on function public.logros_de(text) from public, anon;
grant execute on function public.logros_guardar(jsonb, text[], text[], jsonb, text[]) to authenticated;
grant execute on function public.logros_mios() to authenticated;
grant execute on function public.logros_de(text) to authenticated;
