// «Supabase falso» para probar los .sql en PGlite: lo mínimo que esquema.sql, social.sql y
// listas.sql esperan encontrar (esquemas auth y storage, roles anon/authenticated, auth.uid()).
// Solo se usa en las pruebas; nada de esto va a la base real.
export const SUPABASE_FALSO = `
create role anon nologin;
create role authenticated nologin;

create schema auth;
create table auth.users (
    id uuid primary key default gen_random_uuid(),
    email text,
    raw_user_meta_data jsonb default '{}'::jsonb
);
-- igual que Supabase: quien llama se lee del token, aquí de un ajuste de la sesión
create function auth.uid() returns uuid language sql stable as $$
    select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid
$$;

create schema storage;
create table storage.buckets (
    id text primary key, name text, public boolean default false,
    file_size_limit bigint, allowed_mime_types text[]
);
create table storage.objects (
    id uuid primary key default gen_random_uuid(),
    bucket_id text, name text
);
alter table storage.objects enable row level security;
create function storage.foldername(name text) returns text[] language sql immutable as $$
    select (string_to_array(name, '/'))[1:array_length(string_to_array(name, '/'), 1) - 1]
$$;

grant usage on schema public, auth, storage to anon, authenticated;
grant execute on function auth.uid() to anon, authenticated;
grant execute on function storage.foldername(text) to anon, authenticated;
-- como en Supabase: las tablas nuevas de public nacen con permisos para las dos funciones
-- (la seguridad la ponen las políticas por filas y las funciones)
alter default privileges in schema public grant all on tables to anon, authenticated;
alter default privileges in schema public grant all on sequences to anon, authenticated;
`;
