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

-- se crea solo al registrarse (los datos vienen en raw_user_meta_data)
create or replace function public.crear_perfil()
returns trigger language plpgsql security definer set search_path = public as $$
begin
    insert into public.perfiles (id, usuario, nombre)
    values (new.id,
            lower(coalesce(new.raw_user_meta_data ->> 'usuario', split_part(new.email, '@', 1))),
            coalesce(new.raw_user_meta_data ->> 'nombre', ''))
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
