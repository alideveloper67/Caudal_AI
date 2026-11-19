-- Pases de regalo: cada donador (o fundador) puede crear códigos para que sus amigos prueben los
-- beneficios de donador unos días. Se ejecuta DESPUÉS de premium.sql (usa sus tablas y funciones).
--
--   · crear_pase_regalo()      crea un código de un solo uso (7 días de prueba, vale 30 días para canjearlo)
--   · mis_pases_regalo()       los códigos que creó, con su estado
--   · anular_pase_regalo(cod)  borra uno que nadie ha usado todavía
--
-- Quien lo canjea usa la función de siempre (canjear_pase): una sola prueba por cuenta, con su límite
-- de intentos. Cada donador puede tener 3 códigos sin usar a la vez, para que no se regalen sin freno.

alter table public.pases_prueba add column if not exists regala uuid references auth.users (id) on delete cascade;
create index if not exists pases_prueba_regala on public.pases_prueba (regala) where regala is not null;

-- ¿esta persona es donadora o fundadora de verdad? (la prueba no puede regalar pruebas)
create or replace function public.es_donador_de_verdad(p_id uuid)
returns boolean language sql stable security definer set search_path = public as $$
    select coalesce(public.tipo_premium(p_id) in ('donador', 'fundador'), false);
$$;

drop function if exists public.crear_pase_regalo();
create function public.crear_pase_regalo()
returns jsonb language plpgsql security definer set search_path = public as $$
declare
    yo uuid := auth.uid();
    letras constant text := 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';   -- sin 0, O, 1, I: no se confunden al dictarlos
    cod text;
    intento int := 0;
    vigentes int;
begin
    if yo is null then
        return jsonb_build_object('ok', false, 'mensaje', 'Necesitas iniciar sesión.');
    end if;
    if not public.es_donador_de_verdad(yo) then
        return jsonb_build_object('ok', false, 'mensaje', 'Los códigos de regalo son para donadores y fundadores de Caudal.');
    end if;
    -- serializa a esta persona: dos toques seguidos no se saltan el tope
    perform pg_advisory_xact_lock(hashtextextended('regalo' || yo::text, 0));
    select count(*)::int into vigentes from public.pases_prueba
     where regala = yo and usos < usos_max and (caduca is null or caduca > now());
    if vigentes >= 3 then
        return jsonb_build_object('ok', false,
            'mensaje', 'Ya tienes 3 códigos sin usar. Cuando un amigo canjee uno, puedes crear otro.');
    end if;
    loop
        intento := intento + 1;
        cod := '';
        for i in 1..8 loop
            cod := cod || substr(letras, 1 + floor(random() * length(letras))::int, 1);
            if i = 4 then cod := cod || '-'; end if;
        end loop;
        begin
            insert into public.pases_prueba (codigo, dias, usos_max, caduca, regala)
            values (cod, 7, 1, now() + interval '30 days', yo);
            exit;
        exception when unique_violation then
            if intento >= 20 then
                return jsonb_build_object('ok', false, 'mensaje', 'No se pudo crear el código. Inténtalo otra vez.');
            end if;
        end;
    end loop;
    return jsonb_build_object('ok', true, 'codigo', cod, 'dias', 7, 'caduca', now() + interval '30 days');
end $$;

-- {codigo, dias, usado, caduca, vigente}: los últimos 20, los más nuevos primero
drop function if exists public.mis_pases_regalo();
create function public.mis_pases_regalo()
returns jsonb language sql stable security definer set search_path = public as $$
    select coalesce(jsonb_agg(jsonb_build_object(
               'codigo', x.codigo, 'dias', x.dias, 'usado', x.usos >= x.usos_max,
               'caduca', x.caduca, 'vigente', x.usos < x.usos_max and (x.caduca is null or x.caduca > now()))
           order by x.creado desc), '[]'::jsonb)
    from (select * from public.pases_prueba where regala = auth.uid() order by creado desc limit 20) x;
$$;

drop function if exists public.anular_pase_regalo(text);
create function public.anular_pase_regalo(p_codigo text)
returns boolean language plpgsql security definer set search_path = public as $$
declare borradas int;
begin
    if auth.uid() is null then return false; end if;
    delete from public.pases_prueba
     where codigo = upper(coalesce(p_codigo, '')) and regala = auth.uid() and usos = 0;
    get diagnostics borradas = row_count;
    return borradas > 0;
end $$;

revoke execute on function public.es_donador_de_verdad(uuid) from public, anon, authenticated;
revoke execute on function public.crear_pase_regalo(), public.mis_pases_regalo(), public.anular_pase_regalo(text)
    from public, anon;
grant execute on function public.crear_pase_regalo(), public.mis_pases_regalo(), public.anular_pase_regalo(text)
    to authenticated;
