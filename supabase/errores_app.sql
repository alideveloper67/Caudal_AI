-- ---------------------------------------------------------------- Aviso de errores de Caudal
-- Cuando una app (Windows, Android, iPhone o web) se cierra de golpe o tiene un error que nadie
-- atrapó, manda aquí un informe SIN datos personales: plataforma, versión, sistema, la pantalla
-- en la que estaba y la traza (con las rutas de usuario, correos, enlaces y claves ya borrados).
-- No se manda quién es: ni el id de la cuenta ni el usuario.
--
-- Las apps solo pueden ESCRIBIR (nadie lee desde las apps). Se leen con herramientas/ver_errores.py
-- (token de administrador). Cada app tiene una casilla en Ajustes para no mandarlos.
--
-- Freno contra inundaciones: además del límite que ya pone cada app, la base descarta en silencio
-- lo que pase de 30 informes por hora de un mismo error (huella) y de 3000 por hora en total.
-- Se puede ejecutar de nuevo sin romper nada.

create table if not exists public.errores_app (
    id          bigint generated always as identity primary key,
    creado      timestamptz not null default now(),
    plataforma  text not null check (plataforma in ('windows', 'android', 'ios', 'web', 'macos', 'linux', 'otra')),
    version     text not null check (length(version) between 1 and 24),
    sistema     text not null default '' check (length(sistema) <= 120),
    pantalla    text not null default '' check (length(pantalla) <= 80),
    origen      text not null default '' check (length(origen) <= 40),
    tipo        text not null check (length(tipo) between 1 and 160),
    mensaje     text not null default '' check (length(mensaje) <= 600),
    traza       text not null default '' check (length(traza) <= 8000),
    -- la misma huella = el mismo error (tipo + funciones de la traza, sin números de línea)
    huella      text not null check (huella ~ '^[0-9a-f]{16,64}$'),
    -- cuántas veces pasó en ese equipo desde el último informe (la app las junta)
    veces       int not null default 1 check (veces between 1 and 100000),
    primera_vez timestamptz,
    ultima_vez  timestamptz
);

create index if not exists errores_app_huella_idx on public.errores_app (huella, creado desc);
create index if not exists errores_app_creado_idx on public.errores_app (creado desc);

alter table public.errores_app enable row level security;

-- cualquiera (con o sin cuenta) puede mandar un informe; nadie puede leer, cambiar ni borrar
drop policy if exists "errores: mandar informe" on public.errores_app;
create policy "errores: mandar informe" on public.errores_app for insert to anon, authenticated
    with check (true);

revoke all on public.errores_app from anon, authenticated;
grant insert on public.errores_app to anon, authenticated;

-- freno: lo que se pasa del límite no se guarda (y la app no se entera: no reintenta)
create or replace function public.errores_app_freno()
returns trigger language plpgsql security definer set search_path = public as $$
begin
    if (select count(*) from public.errores_app
         where huella = new.huella and creado > now() - interval '1 hour') >= 30 then
        return null;
    end if;
    if (select count(*) from public.errores_app where creado > now() - interval '1 hour') >= 3000 then
        return null;
    end if;
    -- lo que decide el servidor no lo decide la app
    new.creado := now();
    if new.primera_vez is null or new.primera_vez > now() + interval '1 day' then
        new.primera_vez := now();
    end if;
    if new.ultima_vez is null or new.ultima_vez > now() + interval '1 day' then
        new.ultima_vez := now();
    end if;
    return new;
end $$;
revoke execute on function public.errores_app_freno() from public, anon, authenticated;

drop trigger if exists errores_app_freno on public.errores_app;
create trigger errores_app_freno before insert on public.errores_app
    for each row execute function public.errores_app_freno();

-- limpieza: los informes de hace más de 120 días sobran (se llama a mano o con pg_cron)
create or replace function public.errores_app_limpiar()
returns int language sql security definer set search_path = public as $$
    with b as (delete from public.errores_app where creado < now() - interval '120 days' returning 1)
    select count(*)::int from b
$$;
revoke execute on function public.errores_app_limpiar() from public, anon, authenticated;
