-- ================================================================ Caudal: perfiles públicos por defecto
-- Desde el 21/11/2026 el perfil de una persona MAYOR DE EDAD es público salvo que ella lo cierre.
-- Se pega en el SQL Editor DESPUÉS de social.sql. Se puede repetir.
--
--   · Cuentas nuevas: en cuanto se sabe que la persona tiene 18 años o más (fecha de nacimiento), el
--     perfil queda público. Si ella lo cambia (a público o a privado), manda lo suyo para siempre.
--   · Cuentas que ya existían: NO se tocan (cuentan como «ya eligió»); la app les pregunta una vez.
--   · Menores de 18: nunca públicos. Lo sigue imponiendo perfil_validar (social.sql), que corre
--     después que este disparador y lo vuelve a poner en privado.

do $$
begin
    if not exists (select 1 from information_schema.columns
                    where table_schema = 'public' and table_name = 'perfiles' and column_name = 'publico_elegido') then
        -- las que ya existen quedan como «ya eligió» (true); las nuevas nacen sin elegir (false)
        alter table public.perfiles add column publico_elegido boolean not null default true;
        alter table public.perfiles alter column publico_elegido set default false;
    end if;
end $$;

create or replace function public.perfil_publico_defecto()
returns trigger language plpgsql security definer set search_path = public as $$
begin
    -- tocar el interruptor (a público o a privado) es elegir: desde ahí manda la persona
    if tg_op = 'UPDATE' and new.perfil_publico is distinct from old.perfil_publico then
        new.publico_elegido := true;
    end if;
    if tg_op = 'UPDATE' and old.publico_elegido and not new.publico_elegido then
        new.publico_elegido := true;           -- desde la app no se puede «des-elegir»
    end if;
    if not new.publico_elegido and new.fecha_nacimiento is not null
       and age(new.fecha_nacimiento) >= interval '18 years' then
        new.perfil_publico := true;
    end if;
    return new;
end $$;

-- el nombre importa: Postgres corre los disparadores por orden alfabético y este debe ir ANTES de
-- perfil_validar (que deja en privado a quien no es mayor de edad)
drop trigger if exists perfil_publico_defecto on public.perfiles;
create trigger perfil_publico_defecto before insert or update on public.perfiles
    for each row execute function public.perfil_publico_defecto();

revoke execute on function public.perfil_publico_defecto() from public, anon, authenticated;
