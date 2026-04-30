-- =============================================================================
-- RLS 012 (Wave 1 v4.0 — Componente 05): mover helpers SECURITY DEFINER
--                                          para schema `app_private`
-- =============================================================================
-- IMPORTANTE: Este script e idempotente — usa CREATE SCHEMA IF NOT EXISTS,
-- CREATE OR REPLACE FUNCTION e DROP POLICY IF EXISTS.
--
-- Contexto (auditoria pos-aplicacao do 009/010/011):
--   O Supabase database advisor reportou 6 WARN apos aplicar a 009:
--     - 3x anon_security_definer_function_executable
--     - 3x authenticated_security_definer_function_executable
--   Causa: `public` e schema EXPOSTO via PostgREST (default
--   `db-schemas = public`). Qualquer FUNCTION em `public` com GRANT EXECUTE
--   para `anon`/`authenticated` fica callable por `/rest/v1/rpc/<nome>`.
--   Como current_user_is_admin/setor/id sao SECURITY DEFINER, isso bypassa
--   RLS de `usuarios`. Apesar de retornarem apenas info do proprio usuario
--   (nao vazam dados de terceiros), o advisor recomenda moverem-se para
--   um schema NAO exposto.
--
-- Solucao:
--   1. Criar schema `app_private` (nao listado em db-schemas do PostgREST).
--   2. Recriar as 3 funcoes em `app_private` com mesma assinatura/semantica.
--   3. Reaplicar as 12 policies referenciando `app_private.current_user_*`.
--   4. DROP das funcoes antigas em `public`.
--
-- Por que 012 e nao "fixar" 009: as migrations 009/010/011 ja foram
-- aplicadas em producao via apply_migration. Reverter seria mais arriscado
-- do que adicionar 012 que estabiliza o estado final. As migrations 009-011
-- ficam no historico do `supabase_migrations.schema_migrations` como
-- registro do que foi feito.
--
-- O backend FastAPI nao chama essas funcoes diretamente (usa SQLAlchemy
-- + service_role que bypassa RLS). Apenas as policies SQL referenciam.
-- Logo, mover de schema NAO afeta codigo Python.
--
-- Validacao pos-aplicacao:
--   1. SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
--      WHERE n.nspname='public' AND p.proname IN ('current_user_is_admin',
--      'current_user_setor', 'current_user_id')  -> deve retornar 0.
--   2. SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
--      WHERE n.nspname='app_private' AND p.proname IN (...)  -> 3.
--   3. get_advisors security: 0 WARN do tipo *_security_definer_function_executable.
--   4. scripts smoke (RLS): mesmo comportamento de antes (pol_provas_select
--      com motorista=COM_MOTORISTA, clicheria=clicheria-states, etc.)
-- =============================================================================


-- ─── 1. Schema privado fora do API ─────────────────────────────────────────
CREATE SCHEMA IF NOT EXISTS app_private;
COMMENT ON SCHEMA app_private IS
'Helpers SECURITY DEFINER usados por policies RLS. Nao exposto via PostgREST '
'(`db-schemas` no painel do Supabase mantem apenas `public`).';


-- ─── 2. Recriar as 3 funcoes em app_private ────────────────────────────────

CREATE OR REPLACE FUNCTION app_private.current_user_is_admin()
    RETURNS boolean
    LANGUAGE sql
    STABLE
    SECURITY DEFINER
    SET search_path = ''
AS $$
    SELECT COALESCE((
        SELECT u.is_admin
        FROM public.usuarios u
        WHERE u.auth_uid = (SELECT auth.uid())
    ), false);
$$;

CREATE OR REPLACE FUNCTION app_private.current_user_setor()
    RETURNS public.setor_enum
    LANGUAGE sql
    STABLE
    SECURITY DEFINER
    SET search_path = ''
AS $$
    SELECT u.setor
    FROM public.usuarios u
    WHERE u.auth_uid = (SELECT auth.uid());
$$;

CREATE OR REPLACE FUNCTION app_private.current_user_id()
    RETURNS uuid
    LANGUAGE sql
    STABLE
    SECURITY DEFINER
    SET search_path = ''
AS $$
    SELECT u.id
    FROM public.usuarios u
    WHERE u.auth_uid = (SELECT auth.uid());
$$;


-- ─── 3. Permissoes ────────────────────────────────────────────────────────
-- REVOKE PUBLIC e GRANT apenas authenticated/service_role. Como o schema
-- nao esta no db-schemas do PostgREST, anon nao tem rota REST para chamar
-- mesmo se tivesse GRANT.
REVOKE ALL ON SCHEMA app_private FROM PUBLIC;
GRANT USAGE ON SCHEMA app_private TO authenticated, service_role;

REVOKE EXECUTE ON FUNCTION app_private.current_user_is_admin() FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION app_private.current_user_setor()    FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION app_private.current_user_id()       FROM PUBLIC;

GRANT EXECUTE ON FUNCTION app_private.current_user_is_admin() TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION app_private.current_user_setor()    TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION app_private.current_user_id()       TO authenticated, service_role;


-- ─── 4. Reaplicar as 12 policies referenciando app_private.* ──────────────

-- usuarios
DROP POLICY IF EXISTS pol_usuarios_select ON public.usuarios;
CREATE POLICY pol_usuarios_select ON public.usuarios
    FOR SELECT
    USING (
        auth_uid = (SELECT auth.uid())
        OR app_private.current_user_is_admin()
    );

DROP POLICY IF EXISTS pol_usuarios_insert ON public.usuarios;
CREATE POLICY pol_usuarios_insert ON public.usuarios
    FOR INSERT
    WITH CHECK ( app_private.current_user_is_admin() );

DROP POLICY IF EXISTS pol_usuarios_update ON public.usuarios;
CREATE POLICY pol_usuarios_update ON public.usuarios
    FOR UPDATE
    USING ( app_private.current_user_is_admin() );

-- provas_digitais
DROP POLICY IF EXISTS pol_provas_select ON public.provas_digitais;
CREATE POLICY pol_provas_select ON public.provas_digitais
    FOR SELECT
    USING (
        app_private.current_user_is_admin()
        OR vendedor_id = app_private.current_user_id()
        OR (
            status = 'COM_MOTORISTA'::public.status_prova_enum
            AND app_private.current_user_setor() = 'MOTORISTA'::public.setor_enum
        )
        OR (
            status = ANY (ARRAY[
                'ENVIADA_PARA_CLICHERIA'::public.status_prova_enum,
                'ENCAMINHADA_A_CLICHERIA'::public.status_prova_enum,
                'RECEBIDA_PELA_CLICHERIA'::public.status_prova_enum
            ])
            AND app_private.current_user_setor() = 'CLICHERIA'::public.setor_enum
        )
    );

DROP POLICY IF EXISTS pol_provas_insert ON public.provas_digitais;
CREATE POLICY pol_provas_insert ON public.provas_digitais
    FOR INSERT
    WITH CHECK ( app_private.current_user_is_admin() );

DROP POLICY IF EXISTS pol_provas_update ON public.provas_digitais;
CREATE POLICY pol_provas_update ON public.provas_digitais
    FOR UPDATE
    USING ( app_private.current_user_is_admin() );

-- movimentacoes
DROP POLICY IF EXISTS pol_movimentacoes_select ON public.movimentacoes;
CREATE POLICY pol_movimentacoes_select ON public.movimentacoes
    FOR SELECT
    USING (
        app_private.current_user_is_admin()
        OR prova_id IN (
            SELECT pd.id FROM public.provas_digitais pd
            WHERE pd.vendedor_id = app_private.current_user_id()
        )
        OR usuario_id = app_private.current_user_id()
        OR (
            app_private.current_user_setor() = 'MOTORISTA'::public.setor_enum
            AND prova_id IN (
                SELECT pd.id FROM public.provas_digitais pd
                WHERE pd.status = 'COM_MOTORISTA'::public.status_prova_enum
            )
        )
        OR (
            app_private.current_user_setor() = 'CLICHERIA'::public.setor_enum
            AND prova_id IN (
                SELECT pd.id FROM public.provas_digitais pd
                WHERE pd.status = ANY (ARRAY[
                    'ENVIADA_PARA_CLICHERIA'::public.status_prova_enum,
                    'ENCAMINHADA_A_CLICHERIA'::public.status_prova_enum,
                    'RECEBIDA_PELA_CLICHERIA'::public.status_prova_enum
                ])
            )
        )
    );

DROP POLICY IF EXISTS pol_movimentacoes_insert ON public.movimentacoes;
CREATE POLICY pol_movimentacoes_insert ON public.movimentacoes
    FOR INSERT
    WITH CHECK ( app_private.current_user_is_admin() );

-- etiquetas (espelha 011 — ja com motorista + clicheria)
DROP POLICY IF EXISTS pol_etiquetas_select ON public.etiquetas;
CREATE POLICY pol_etiquetas_select ON public.etiquetas
    FOR SELECT
    USING (
        app_private.current_user_is_admin()
        OR EXISTS (
            SELECT 1 FROM public.provas_digitais pd
            WHERE pd.id = etiquetas.prova_id
              AND (
                  pd.vendedor_id = app_private.current_user_id()
                  OR (
                      app_private.current_user_setor() = 'MOTORISTA'::public.setor_enum
                      AND pd.status = 'COM_MOTORISTA'::public.status_prova_enum
                  )
                  OR (
                      app_private.current_user_setor() = 'CLICHERIA'::public.setor_enum
                      AND pd.status = ANY (ARRAY[
                          'ENVIADA_PARA_CLICHERIA'::public.status_prova_enum,
                          'ENCAMINHADA_A_CLICHERIA'::public.status_prova_enum,
                          'RECEBIDA_PELA_CLICHERIA'::public.status_prova_enum
                      ])
                  )
              )
        )
    );

-- audit_logs
DROP POLICY IF EXISTS pol_audit_select ON public.audit_logs;
CREATE POLICY pol_audit_select ON public.audit_logs
    FOR SELECT
    USING ( app_private.current_user_is_admin() );

-- configuracoes_sistema
DROP POLICY IF EXISTS pol_config_select ON public.configuracoes_sistema;
CREATE POLICY pol_config_select ON public.configuracoes_sistema
    FOR SELECT
    USING ( app_private.current_user_is_admin() );

DROP POLICY IF EXISTS pol_config_update ON public.configuracoes_sistema;
CREATE POLICY pol_config_update ON public.configuracoes_sistema
    FOR UPDATE
    USING ( app_private.current_user_is_admin() );


-- ─── 5. Remover as funcoes antigas de public ──────────────────────────────
-- IF EXISTS evita erro caso a 012 seja reaplicada apos cleanup completo.
DROP FUNCTION IF EXISTS public.current_user_is_admin();
DROP FUNCTION IF EXISTS public.current_user_setor();
DROP FUNCTION IF EXISTS public.current_user_id();
