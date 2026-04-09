-- =============================================================================
-- RLS 005: Otimizacao initplan — substitui auth.uid() por (SELECT auth.uid())
-- =============================================================================
-- IMPORTANTE: Este script e idempotente — DROP IF EXISTS antes de cada CREATE.
--
-- Contexto (ADR-029):
--   O performance advisor do Supabase reporta 11x WARN `auth_rls_initplan`
--   em todas as policies que chamam `auth.uid()` diretamente em USING/WITH
--   CHECK. O Postgres re-avalia a expressao por LINHA em vez de uma vez por
--   query — penaliza SELECTs com muitas linhas.
--
--   A correcao oficial e envolver a chamada em `(SELECT auth.uid())`. O
--   planner detecta que a subquery e estavel no escopo da query e a promove
--   a um InitPlan executado UMA UNICA VEZ. Lean fix, zero mudanca semantica.
--
-- O que muda em relacao a RLS 002 + 003 + 004:
--   - Cada ocorrencia de `auth.uid()` vira `(SELECT auth.uid())`.
--   - Nenhuma mudanca em logica de negocio, campos, filtros ou roles.
--
-- Aplicacao na Wave 2:
--   - W2-T0 (primeira tarefa da Wave 2, conforme ADR-029).
--   - Aplicavel isoladamente via `execute_sql` ou como parte do run completo
--     do `apply_rls.py` (ambos sao idempotentes).
--
-- Validacao pos-aplicacao:
--   1. Supabase advisor (performance): os 11 WARN `auth_rls_initplan` devem
--      sumir.
--   2. `EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM provas_digitais LIMIT 50`
--      como authenticated role: plano deve mostrar `InitPlan` (nao SubPlan
--      re-avaliado por linha).
-- =============================================================================


-- ─── USUARIOS (3 policies) ─────────────────────────────────────────────────

-- SELECT: admin ve todos; nao-admin ve apenas o proprio registro.
DROP POLICY IF EXISTS pol_usuarios_select ON usuarios;
CREATE POLICY pol_usuarios_select ON usuarios
    FOR SELECT
    USING (
        auth_uid = (SELECT auth.uid())
        OR EXISTS (
            SELECT 1 FROM usuarios u
            WHERE u.auth_uid = (SELECT auth.uid()) AND u.is_admin = true
        )
    );

-- INSERT: apenas admin.
DROP POLICY IF EXISTS pol_usuarios_insert ON usuarios;
CREATE POLICY pol_usuarios_insert ON usuarios
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM usuarios u
            WHERE u.auth_uid = (SELECT auth.uid()) AND u.is_admin = true
        )
    );

-- UPDATE: apenas admin.
DROP POLICY IF EXISTS pol_usuarios_update ON usuarios;
CREATE POLICY pol_usuarios_update ON usuarios
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM usuarios u
            WHERE u.auth_uid = (SELECT auth.uid()) AND u.is_admin = true
        )
    );


-- ─── PROVAS DIGITAIS (3 policies) ──────────────────────────────────────────

-- Admin ve todas. VENDEDOR ve suas. MOTORISTA/CLICHERIA veem por status.
DROP POLICY IF EXISTS pol_provas_select ON provas_digitais;
CREATE POLICY pol_provas_select ON provas_digitais
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM usuarios u
            WHERE u.auth_uid = (SELECT auth.uid()) AND u.is_admin = true
        )
        OR vendedor_id = (
            SELECT u.id FROM usuarios u WHERE u.auth_uid = (SELECT auth.uid())
        )
        OR (
            status = 'COM_MOTORISTA'
            AND EXISTS (
                SELECT 1 FROM usuarios u
                WHERE u.auth_uid = (SELECT auth.uid()) AND u.setor = 'MOTORISTA'
            )
        )
        OR (
            status IN ('ENVIADA_PARA_CLICHERIA', 'ENCAMINHADA_A_CLICHERIA', 'RECEBIDA_PELA_CLICHERIA')
            AND EXISTS (
                SELECT 1 FROM usuarios u
                WHERE u.auth_uid = (SELECT auth.uid()) AND u.setor = 'CLICHERIA'
            )
        )
    );

-- Apenas admin pode criar provas (via Supabase client; backend usa service_role).
DROP POLICY IF EXISTS pol_provas_insert ON provas_digitais;
CREATE POLICY pol_provas_insert ON provas_digitais
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM usuarios u
            WHERE u.auth_uid = (SELECT auth.uid()) AND u.is_admin = true
        )
    );

-- Apenas admin pode atualizar provas (via Supabase client).
DROP POLICY IF EXISTS pol_provas_update ON provas_digitais;
CREATE POLICY pol_provas_update ON provas_digitais
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM usuarios u
            WHERE u.auth_uid = (SELECT auth.uid()) AND u.is_admin = true
        )
    );


-- ─── MOVIMENTACOES (1 policy) ──────────────────────────────────────────────

-- Admin ve todas. VENDEDOR ve movimentacoes das suas provas. Demais veem as proprias.
-- INSERT e feito exclusivamente pelo backend via service_role (bypassa RLS).
-- UPDATE/DELETE bloqueados pelo trigger trg_movimentacoes_imutavel.
DROP POLICY IF EXISTS pol_movimentacoes_select ON movimentacoes;
CREATE POLICY pol_movimentacoes_select ON movimentacoes
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM usuarios u
            WHERE u.auth_uid = (SELECT auth.uid()) AND u.is_admin = true
        )
        OR prova_id IN (
            SELECT pd.id FROM provas_digitais pd
            WHERE pd.vendedor_id = (
                SELECT u.id FROM usuarios u WHERE u.auth_uid = (SELECT auth.uid())
            )
        )
        OR usuario_id = (
            SELECT u.id FROM usuarios u WHERE u.auth_uid = (SELECT auth.uid())
        )
    );


-- ─── ETIQUETAS (1 policy) ──────────────────────────────────────────────────

-- Admin ve todas. Vendedor ve etiquetas de suas provas.
DROP POLICY IF EXISTS pol_etiquetas_select ON etiquetas;
CREATE POLICY pol_etiquetas_select ON etiquetas
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM usuarios u
            WHERE u.auth_uid = (SELECT auth.uid()) AND u.is_admin = true
        )
        OR prova_id IN (
            SELECT pd.id FROM provas_digitais pd
            WHERE pd.vendedor_id = (
                SELECT u.id FROM usuarios u WHERE u.auth_uid = (SELECT auth.uid())
            )
        )
    );


-- ─── AUDIT LOGS (1 policy) ─────────────────────────────────────────────────

-- Apenas admin pode ler audit logs (RNF-005).
DROP POLICY IF EXISTS pol_audit_select ON audit_logs;
CREATE POLICY pol_audit_select ON audit_logs
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM usuarios u
            WHERE u.auth_uid = (SELECT auth.uid()) AND u.is_admin = true
        )
    );


-- ─── CONFIGURACOES DO SISTEMA (2 policies) ─────────────────────────────────

-- Apenas admin pode ler configuracoes (RF-021).
DROP POLICY IF EXISTS pol_config_select ON configuracoes_sistema;
CREATE POLICY pol_config_select ON configuracoes_sistema
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM usuarios u
            WHERE u.auth_uid = (SELECT auth.uid()) AND u.is_admin = true
        )
    );

-- Apenas admin pode alterar configuracoes (RF-021).
DROP POLICY IF EXISTS pol_config_update ON configuracoes_sistema;
CREATE POLICY pol_config_update ON configuracoes_sistema
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM usuarios u
            WHERE u.auth_uid = (SELECT auth.uid()) AND u.is_admin = true
        )
    );
