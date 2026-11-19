-- ================================================================ Listas con más gente (GRATIS para todos)
-- Una lista compartida pasa de admitir 20 personas a 50, sin importar si el dueño es donador o no:
-- es una mejora de todos, no un beneficio exclusivo.
--
-- Se pega entero en el SQL Editor de Supabase DESPUÉS de listas.sql (redefine solo `unirse_a_lista`,
-- que en listas.sql tiene el 20 escrito a mano). Se puede ejecutar de nuevo sin romper nada.
-- OJO: si alguien vuelve a ejecutar listas.sql, la función vuelve a 20: ejecuta este archivo otra vez.
-- Las pruebas están en supabase/pruebas/listas_colaboradores.prueba.mjs.

-- El tope vive en UN solo sitio, para cambiarlo sin tocar la función.
create or replace function public.max_miembros_lista()
returns int language sql immutable as $$ select 50 $$;

drop function if exists public.unirse_a_lista(text);
create function public.unirse_a_lista(p_codigo text)
returns jsonb language plpgsql security definer set search_path = public as $$
declare
    yo uuid := auth.uid();
    c public.lista_codigos;
    l public.listas;
    actual text;
    tope int := public.max_miembros_lista();
begin
    if yo is null then raise exception 'Necesitas iniciar sesión para unirte a una lista.'; end if;
    select * into c from public.lista_codigos where codigo = public.normalizar_codigo(p_codigo);
    if c.codigo is null then
        raise exception 'Ese código no existe o la lista ya no se comparte. Revisa que esté bien escrito.';
    end if;
    -- se bloquea la lista para que dos personas no pasen el tope a la vez
    select * into l from public.listas where id = c.lista_id for update;
    if l.id is null then
        raise exception 'Ese código no existe o la lista ya no se comparte. Revisa que esté bien escrito.';
    end if;
    if l.user_id = yo then
        return jsonb_build_object('lista_id', l.id, 'nombre', l.nombre, 'rol', 'colaborador', 'es_dueno', true);
    end if;
    if coalesce(public.hay_bloqueo(yo, l.user_id), false) then
        raise exception 'No te puedes unir a esta lista.';
    end if;
    select rol into actual from public.lista_miembros where lista_id = l.id and user_id = yo;
    if actual is null then
        if (select count(*) from public.lista_miembros where lista_id = l.id) >= tope then
            raise exception 'Esta lista ya tiene % personas, que es el máximo. Pídele a su dueño que haga lugar.', tope;
        end if;
        insert into public.lista_miembros (lista_id, user_id, rol) values (l.id, yo, c.rol);
        actual := c.rol;
    end if;
    return jsonb_build_object('lista_id', l.id, 'nombre', l.nombre, 'rol', actual, 'es_dueno', false);
end $$;

-- permisos: igual que en listas.sql (solo quien tiene sesión)
revoke execute on function public.unirse_a_lista(text) from public, anon;
grant execute on function public.unirse_a_lista(text) to authenticated;
revoke execute on function public.max_miembros_lista() from public, anon, authenticated;
