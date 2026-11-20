-- ================================================================ Más para donadores
-- Dos cosas nuevas para quien apoya a Caudal:
--   · color del nombre: un color propio (#RRGGBB) para el nombre del perfil, que se ve en el perfil,
--     en los chats y en «Juntos». Igual que el marco y el efecto: solo se escribe con premium vigente y
--     solo se ve mientras siga vigente (lo guardado se conserva y vuelve si la persona vuelve a donar);
--   · pared de agradecimiento: la lista pública de donadores y fundadores que aceptan aparecer
--     (casilla en su perfil, apagada por defecto). La lee la app y también la web, sin sesión.
--
-- Se pega entero en el SQL Editor de Supabase DESPUÉS de esquema.sql, social.sql y premium.sql
-- (usa es_premium, tipo_premium, es_mayor y hay_bloqueo). Se puede ejecutar de nuevo sin romper nada.
-- Las pruebas están en supabase/pruebas/donadores_extra.prueba.mjs.

-- ---------------------------------------------------------------- 1. columnas
alter table public.perfiles add column if not exists color_nombre text;                      -- '#RRGGBB' o null
alter table public.perfiles add column if not exists en_pared boolean not null default false; -- aparece en la pared

alter table public.perfiles drop constraint if exists perfil_color_nombre_forma;
alter table public.perfiles add constraint perfil_color_nombre_forma check (
    color_nombre is null or color_nombre ~ '^#[0-9A-F]{6}$'
);

-- ---------------------------------------------------------------- 2. el servidor manda
-- El color se guarda siempre en mayúsculas («#ff00aa» -> «#FF00AA») y uno mal escrito se descarta
-- (en vez de romper el guardado del resto del perfil). Sin premium vigente el color no se escribe:
-- en una fila nueva queda vacío y en una existente se conserva el de antes (como la portada).
-- La casilla de la pared la puede tocar cualquiera: solo cuenta para donadores y fundadores.
create or replace function public.perfil_donadores_validar()
returns trigger language plpgsql security definer set search_path = public as $$
begin
    if new.color_nombre is not null then
        new.color_nombre := upper(btrim(new.color_nombre));
        if new.color_nombre = '' then
            new.color_nombre := null;
        elsif new.color_nombre !~ '^#[0-9A-F]{6}$' then
            new.color_nombre := case when tg_op = 'UPDATE' then old.color_nombre else null end;
        end if;
    end if;
    if not public.es_premium(new.id) then
        new.color_nombre := case when tg_op = 'UPDATE' then old.color_nombre else null end;
    end if;
    new.en_pared := coalesce(new.en_pared, false);
    return new;
end $$;
drop trigger if exists perfil_donadores_validar on public.perfiles;
create trigger perfil_donadores_validar before insert or update on public.perfiles
    for each row execute function public.perfil_donadores_validar();

-- el color que se ve de alguien: null si no tiene o si ya no tiene premium vigente
create or replace function public.color_nombre_de(p_id uuid)
returns text language sql stable security definer set search_path = public as $$
    select case when public.es_premium(p_id)
                then (select color_nombre from public.perfiles where id = p_id)
                else null end;
$$;

-- ---------------------------------------------------------------- 3. leer colores
-- {"usuario": "#RRGGBB", ...} de los usuarios pedidos que tienen un color vigente (los demás no salen).
-- Una sola llamada para toda una lista (chats, miembros de «Juntos», un perfil). Con bloqueo, no sale.
-- Hasta 200 usuarios por llamada.
create or replace function public.colores_nombre(p_usuarios text[])
returns jsonb language sql stable security definer set search_path = public as $$
    select coalesce(jsonb_object_agg(p.usuario, public.color_nombre_de(p.id)), '{}'::jsonb)
    from public.perfiles p
    where auth.uid() is not null
      and p.usuario = any (
          select lower(btrim(u)) from unnest(coalesce(p_usuarios, '{}'::text[])) with ordinality as x(u, n)
           where n <= 200)
      and public.color_nombre_de(p.id) is not null
      and (p.id = auth.uid() or not coalesce(public.hay_bloqueo(auth.uid(), p.id), false));
$$;

-- ---------------------------------------------------------------- 4. pared de agradecimiento
-- [{"usuario", "nombre", "tipo": "fundador"|"donador", "color": "#RRGGBB"|null, "desde": fecha}, ...]
-- Solo donadores y fundadores vigentes (no las pruebas), que marcaron la casilla y son mayores de edad
-- (la pared es pública: un menor nunca sale, como en el directorio). Primero los fundadores y después
-- por antigüedad. Sin fotos ni nada más del perfil: solo el nombre con el que quieren que se les dé las gracias.
create or replace function public.pared_agradecimiento()
returns jsonb language sql stable security definer set search_path = public as $$
    select coalesce(jsonb_agg(jsonb_build_object(
               'usuario', q.usuario, 'nombre', q.nombre, 'tipo', q.tipo, 'color', q.color, 'desde', q.desde)
               order by (q.tipo = 'fundador') desc, q.desde, q.usuario), '[]'::jsonb)
    from (select p.usuario,
                 left(coalesce(nullif(btrim(p.nombre), ''), p.usuario), 40) as nombre,
                 public.tipo_premium(p.id) as tipo,
                 public.color_nombre_de(p.id) as color,
                 (select min(te.creado) from public.titulos_especiales te
                   where te.user_id = p.id and te.titulo in ('donador_caudal', 'fundador_caudal')) as desde
            from public.perfiles p
           where p.en_pared
             and public.tipo_premium(p.id) in ('donador', 'fundador')
             and public.es_mayor(p.id)
           limit 500) q;
$$;

-- ---------------------------------------------------------------- 5. permisos
revoke execute on function public.perfil_donadores_validar() from public, anon, authenticated;
revoke execute on function public.color_nombre_de(uuid) from public, anon, authenticated;
revoke execute on function public.colores_nombre(text[]) from public, anon;
grant execute on function public.colores_nombre(text[]) to authenticated;
revoke execute on function public.pared_agradecimiento() from public;
grant execute on function public.pared_agradecimiento() to anon, authenticated;
