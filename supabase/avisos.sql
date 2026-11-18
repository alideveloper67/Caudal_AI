-- ---------------------------------------------------------------- Avisos de Caudal
-- Mensajes que quien administra manda a todas las apps (web, Android, Windows, iPhone) sin sacar
-- una versión nueva. Cada app los lee al abrirse y muestra cada aviso UNA sola vez por dispositivo.
-- Se envían con herramientas/enviar_aviso.py (o con un insert desde el SQL Editor).
-- Se puede ejecutar de nuevo sin romper nada.
create table if not exists public.avisos (
    id             bigint generated always as identity primary key,
    titulo         text not null check (length(titulo) between 1 and 80),
    texto          text not null check (length(texto) between 1 and 600),
    -- a quién le sale: 'todas' o una lista de 'web', 'android', 'windows', 'ios'
    plataformas    text[] not null default array['todas'],
    enlace         text check (enlace is null or enlace ~ '^https://'),
    etiqueta_enlace text check (etiqueta_enlace is null or length(etiqueta_enlace) <= 30),
    activo         boolean not null default true,
    caduca         timestamptz,
    creado         timestamptz not null default now()
);

alter table public.avisos enable row level security;

-- cualquiera (con o sin cuenta) puede LEER los avisos vigentes; nadie escribe desde las apps
drop policy if exists "avisos: leer los vigentes" on public.avisos;
create policy "avisos: leer los vigentes" on public.avisos for select to anon, authenticated
    using (activo and (caduca is null or caduca > now()));

revoke insert, update, delete on public.avisos from anon, authenticated;
grant select on public.avisos to anon, authenticated;
