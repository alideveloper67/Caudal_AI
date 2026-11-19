-- «Feliz cumpleaños»: qué amigos cumplen años hoy, SIN revelar nunca la fecha de nacimiento.
-- Se ejecuta DESPUÉS de esquema.sql y social.sql (usa perfiles.fecha_nacimiento y amistades). Se puede repetir.
--
--   · amigos_cumplen_hoy()   solo los ids de tus amigos que cumplen hoy (día de Lima). Ni fecha, ni edad.
--
-- Regla del 29 de febrero: en un año que no es bisiesto se celebra el 28 de febrero (igual que en la app).
-- Quien tiene un bloqueo con la otra persona (en cualquier sentido) no aparece.

-- ayuda interna con la fecha como parámetro (para poder probarla); nadie la llama desde la app
create or replace function public.amigos_cumplen_el(p_dia date)
returns setof uuid language sql stable security definer set search_path = public as $$
    select p.id
      from public.amistades a
      join public.perfiles p on p.id = case when a.de = auth.uid() then a.para else a.de end
     where auth.uid() is not null
       and a.estado = 'aceptada' and auth.uid() in (a.de, a.para)
       and p.fecha_nacimiento is not null
       and not exists (select 1 from public.bloqueos b
                        where (b.quien = auth.uid() and b.a = p.id) or (b.quien = p.id and b.a = auth.uid()))
       and (   (extract(month from p.fecha_nacimiento) = extract(month from p_dia)
                and extract(day from p.fecha_nacimiento) = extract(day from p_dia))
            or (extract(month from p.fecha_nacimiento) = 2 and extract(day from p.fecha_nacimiento) = 29
                and extract(month from p_dia) = 2 and extract(day from p_dia) = 28
                and not (   (extract(year from p_dia)::int % 4 = 0 and extract(year from p_dia)::int % 100 <> 0)
                         or extract(year from p_dia)::int % 400 = 0)))
     order by p.id;
$$;

drop function if exists public.amigos_cumplen_hoy();
create function public.amigos_cumplen_hoy()
returns setof uuid language sql stable security definer set search_path = public as $$
    select public.amigos_cumplen_el((now() at time zone 'America/Lima')::date);
$$;

revoke execute on function public.amigos_cumplen_el(date) from public, anon, authenticated;
revoke execute on function public.amigos_cumplen_hoy() from public, anon;
grant execute on function public.amigos_cumplen_hoy() to authenticated;
