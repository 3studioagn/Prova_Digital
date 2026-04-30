-- =============================================================================
-- RLS 010 (Wave 1 v4.0 — Componente 05): Rebase das policies usando helpers
-- =============================================================================
-- IMPORTANTE: Este script e idempotente — DROP IF EXISTS antes de cada CREATE.
--
-- !!! SUPERSEDE POR 012 !!!
--   Esta migration usa public.current_user_* — ver nota em 009. A 012 reaplica
--   as mesmas policies referenciando app_private.current_user_*. Ao aplicar
--   do zero, esta migration eh sobrescrita pela 012 — o estado final e o
--   da 012.
--
-- Objetivo: reescrever as 12 policies existentes usando os helpers
-- introduzidos em 009 (current_user_is_admin / current_user_setor /
-- current_user_id). NO-OP funcional — a semantica de quem ve o que
-- permanece IDENTICA ao estado pos-RLS 005 + 006.
--
-- Por que reaplicar tudo: evita 2 convencoes coexistindo (helper vs
-- subquery EXISTS inline), o que dificultaria manutencao e auditoria.
-- Toda alteracao futura segue um padrao unico.
--
-- O que NAO esta neste arquivo:
--   - pol_etiquetas_select (atualizada em 011 — fecha lacuna L-RLS-1
--     da analysis: motorista + clicheria veem etiqueta de provas
--     no escopo).
--   - REVOKE GRANT-level em audit_logs (RLS 008 — Wave 6, mantido).
--
-- Cobertura: 11 policies reescritas (nao 12 porque etiquetas vai em 011):
--   - usuarios:        select, insert, update                    (3)
--   - provas_digitais: select, insert, update                    (3)
--   - movimentacoes:   select, insert                            (2)
--   - audit_logs:      select                                    (1)
--   - configuracoes:   select, update                            (2)
--                                                          total = 11
--
-- Validacao pos-aplicacao:
--   1. SELECT policyname FROM pg_policies WHERE schemaname='public' deve
--      mostrar 12 policies (mesmas de antes).
--   2. Cada celula da Matriz de Acesso (52 — 12 regras x 4 perfis no JSON
--      shared/access-matrix.json) deve continuar valida.
--   3. scripts/verify_rbac_equivalence.py: 0 desvios apos a aplicacao.
-- =============================================================================


-- ─── USUARIOS (3 policies) ─────────────────────────────────────────────────

-- SELECT: admin ve todos; nao-admin ve apenas o proprio registro.
DROP POLICY IF EXISTS pol_usuarios_select ON public.usuarios;
CREATE POLICY pol_usuarios_select ON public.usuarios
    FOR SELECT
    USING (
        auth_uid = (SELECT auth.uid())
        OR public.current_user_is_admin()
    );

-- INSERT: apenas admin.
DROP POLICY IF EXISTS pol_usuarios_insert ON public.usuarios;
CREATE POLICY pol_usuarios_insert ON public.usuarios
    FOR INSERT
    WITH CHECK ( public.current_user_is_admin() );

-- UPDATE: apenas admin.
DROP POLICY IF EXISTS pol_usuarios_update ON public.usuarios;
CREATE POLICY pol_usuarios_update ON public.usuarios
    FOR UPDATE
    USING ( public.current_user_is_admin() );


-- ─── PROVAS DIGITAIS (3 policies) ──────────────────────────────────────────

-- Admin ve todas. VENDEDOR ve suas. MOTORISTA ve em transito. CLICHERIA
-- ve nos status de clicheria. Mesma semantica da RLS 005/006.
DROP POLICY IF EXISTS pol_provas_select ON public.provas_digitais;
CREATE POLICY pol_provas_select ON public.provas_digitais
    FOR SELECT
    USING (
        public.current_user_is_admin()
        OR vendedor_id = public.current_user_id()
        OR (
            status = 'COM_MOTORISTA'::public.status_prova_enum
            AND public.current_user_setor() = 'MOTORISTA'::public.setor_enum
        )
        OR (
            status = ANY (ARRAY[
                'ENVIADA_PARA_CLICHERIA'::public.status_prova_enum,
                'ENCAMINHADA_A_CLICHERIA'::public.status_prova_enum,
                'RECEBIDA_PELA_CLICHERIA'::public.status_prova_enum
            ])
            AND public.current_user_setor() = 'CLICHERIA'::public.setor_enum
        )
    );

-- INSERT: apenas admin (via Supabase client; backend usa service_role).
DROP POLICY IF EXISTS pol_provas_insert ON public.provas_digitais;
CREATE POLICY pol_provas_insert ON public.provas_digitais
    FOR INSERT
    WITH CHECK ( public.current_user_is_admin() );

-- UPDATE: apenas admin (via Supabase client).
DROP POLICY IF EXISTS pol_provas_update ON public.provas_digitais;
CREATE POLICY pol_provas_update ON public.provas_digitais
    FOR UPDATE
    USING ( public.current_user_is_admin() );


-- ─── MOVIMENTACOES (2 policies) ────────────────────────────────────────────

-- SELECT: admin + vendedor (provas suas) + autor + motorista por status +
-- clicheria por status. Mesma semantica da RLS 006.
DROP POLICY IF EXISTS pol_movimentacoes_select ON public.movimentacoes;
CREATE POLICY pol_movimentacoes_select ON public.movimentacoes
    FOR SELECT
    USING (
        public.current_user_is_admin()
        OR prova_id IN (
            SELECT pd.id FROM public.provas_digitais pd
            WHERE pd.vendedor_id = public.current_user_id()
        )
        OR usuario_id = public.current_user_id()
        OR (
            public.current_user_setor() = 'MOTORISTA'::public.setor_enum
            AND prova_id IN (
                SELECT pd.id FROM public.provas_digitais pd
                WHERE pd.status = 'COM_MOTORISTA'::public.status_prova_enum
            )
        )
        OR (
            public.current_user_setor() = 'CLICHERIA'::public.setor_enum
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

-- INSERT: apenas admin (RLS 006 / ADR-082).
DROP POLICY IF EXISTS pol_movimentacoes_insert ON public.movimentacoes;
CREATE POLICY pol_movimentacoes_insert ON public.movimentacoes
    FOR INSERT
    WITH CHECK ( public.current_user_is_admin() );


-- ─── AUDIT LOGS (1 policy) ─────────────────────────────────────────────────

-- SELECT: apenas admin (RNF-005). REVOKE GRANT-level em INSERT/UPDATE/DELETE
-- e mantido pela RLS 008 (Wave 6) — nao reaplicamos aqui.
DROP POLICY IF EXISTS pol_audit_select ON public.audit_logs;
CREATE POLICY pol_audit_select ON public.audit_logs
    FOR SELECT
    USING ( public.current_user_is_admin() );


-- ─── CONFIGURACOES DO SISTEMA (2 policies) ─────────────────────────────────

DROP POLICY IF EXISTS pol_config_select ON public.configuracoes_sistema;
CREATE POLICY pol_config_select ON public.configuracoes_sistema
    FOR SELECT
    USING ( public.current_user_is_admin() );

DROP POLICY IF EXISTS pol_config_update ON public.configuracoes_sistema;
CREATE POLICY pol_config_update ON public.configuracoes_sistema
    FOR UPDATE
    USING ( public.current_user_is_admin() );
