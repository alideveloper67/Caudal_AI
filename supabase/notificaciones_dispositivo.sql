-- Notificaciones en Android con la app cerrada (mensajes y solicitudes de amistad).
--
-- El teléfono no puede guardar la sesión para usarla en segundo plano (el token de renovación cambia cada vez
-- que se usa). Por eso, al iniciar sesión, la app registra un TOKEN DE DISPOSITIVO aleatorio ligado a la
-- cuenta; el revisor nativo de Android (RevisorNovedades.kt) llama cada ~15 min a `novedades_dispositivo`
-- con ese token, sin sesión, y solo recibe lo justo para avisar: solicitudes pendientes y chats con mensajes
-- sin leer (quién y una vista previa corta). Al cerrar sesión, la app borra el token.

create table if not exists public.dispositivos_aviso (
    token uuid primary key,
    user_id uuid not null references auth.users on delete cascade,
    creado timestamptz not null default now(),
    usado timestamptz
);
create index if not exists dispositivos_aviso_user on public.dispositivos_aviso (user_id);
alter table public.dispositivos_aviso enable row level security;
revoke all on public.dispositivos_aviso from anon, authenticated;

create or replace function public.registrar_dispositivo_aviso(p_token uuid)
returns void language plpgsql security definer set search_path = public as $$
begin
    if auth.uid() is null or p_token is null then
        return;
    end if;
    insert into public.dispositivos_aviso (token, user_id) values (p_token, auth.uid())
        on conflict (token) do update set user_id = excluded.user_id, creado = now();
    -- como mucho 5 dispositivos por cuenta: se van los más viejos
    delete from public.dispositivos_aviso
     where user_id = auth.uid()
       and token not in (select token from public.dispositivos_aviso where user_id = auth.uid()
                         order by creado desc limit 5);
end;
$$;

create or replace function public.borrar_dispositivo_aviso(p_token uuid)
returns void language sql security definer set search_path = public as $$
    delete from public.dispositivos_aviso where token = p_token;
$$;

create or replace function public.novedades_dispositivo(p_token uuid)
returns jsonb language plpgsql security definer set search_path = public as $$
declare
    yo uuid;
begin
    select user_id into yo from public.dispositivos_aviso where token = p_token;
    if yo is null then
        return null;
    end if;
    update public.dispositivos_aviso set usado = now() where token = p_token;
    return jsonb_build_object(
        'solicitudes', coalesce((
            select jsonb_agg(jsonb_build_object('id', s.id, 'nombre', coalesce(nullif(p.nombre, ''), p.usuario)))
            from (select a.id, a.de from public.amistades a
                   where a.para = yo and a.estado = 'pendiente' and not public.hay_bloqueo(yo, a.de)
                   order by a.creado desc limit 5) s
            join public.perfiles p on p.id = s.de), '[]'::jsonb),
        'mensajes', coalesce((
            select jsonb_agg(x) from (
                select jsonb_build_object(
                           'chat', c.id,
                           'ultimo', (select max(n.id) from public.mensajes n where n.chat = c.id and n.autor <> yo),
                           'cuantos', count(*),
                           'nombre', coalesce(nullif(o.nombre, ''), o.usuario),
                           'texto', left(coalesce((select case when n.pista is not null then '♪ ' || coalesce(n.pista->>'titulo', 'Una canción')
                                                              when n.lista is not null then 'Te compartió una lista'
                                                              else n.texto end
                                                   from public.mensajes n where n.chat = c.id and n.autor <> yo
                                                   order by n.id desc limit 1), ''), 90)) x
                from public.chats c
                join public.perfiles o on o.id = case when c.a = yo then c.b else c.a end
                join public.mensajes m on m.chat = c.id and m.autor <> yo
                     and m.creado > case when c.a = yo then c.leido_a else c.leido_b end
                where yo in (c.a, c.b) and not public.hay_bloqueo(c.a, c.b)
                group by c.id, o.nombre, o.usuario
                order by max(m.id) desc limit 5) t), '[]'::jsonb));
end;
$$;

grant execute on function public.registrar_dispositivo_aviso(uuid) to authenticated;
grant execute on function public.borrar_dispositivo_aviso(uuid) to anon, authenticated;
grant execute on function public.novedades_dispositivo(uuid) to anon, authenticated;
revoke execute on function public.registrar_dispositivo_aviso(uuid) from anon;

-- Total de usuarios (para la presentación de agradecimiento al llegar a 100): solo el número, sin datos.
create or replace function public.total_usuarios() returns integer
language sql stable security definer set search_path = public as $$
    select count(*)::int from public.perfiles;
$$;
grant execute on function public.total_usuarios() to anon, authenticated;
