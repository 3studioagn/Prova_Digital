-- =============================================================================
-- RLS 004: Unifica todas as policies para usar is_admin (substitui setor = 'STUDIO')
-- =============================================================================
-- IMPORTANTE: Este script e idempotente — DROP IF EXISTS antes de cada CREATE.
--
-- Contexto:
--   A RLS 003 atualizou apenas as policies da tabela `usuarios` para usar
--   is_admin = true. As policies de `provas_digitais`, `movimentacoes`,
--   `etiquetas`, `audit_logs` e `configuracoes_sistema` ainda usavam
--   setor = 'STUDIO', criando uma divergencia: um admin com setor != STUDIO
--   conseguiria gerenciar usuarios mas nao veria todas as provas via RLS.
--
-- Decisao (validada com Mario): unificar TUDO em is_admin. A partir desta
-- migration, "admin" e definido exclusivamente pela coluna is_admin = true,
-- independente do setor cadastrado.
--
-- O que MUDA:
--   - Checks de admin trocam `setor = 'STUDIO'` por `is_admin = true`.
--
-- O que NAO muda:
--   - Logica de negocio por setor (VENDEDOR ve suas provas, MOTORISTA ve provas
--     COM_MOTORISTA, CLICHERIA ve provas em status de clicheria) permanece
--     usando setor — sao papeis operacionais, nao permissoes admin.
-- =============================================================================


-- ─── PROVAS DIGITAIS ────────────────────────────────────────────────────────

-- Admin ve todas. VENDEDOR ve suas. MOTORISTA/CLICHERIA veem por status.
DROP POLICY IF EXISTS pol_provas_select ON provas_digitais;
CREATE POLICY pol_provas_select ON provas_digitais
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM usuarios u WHERE u.auth_uid = auth.uid() AND u.is_admin = true
        )
        OR vendedor_id = (
            SELECT u.id FROM usuarios u WHERE u.auth_uid = auth.uid()
        )
        OR (
            status = 'COM_MOTORISTA'
            AND EXISTS (
                SELECT 1 FROM usuarios u WHERE u.auth_uid = auth.uid() AND u.setor = 'MOTORISTA'
            )
        )
        OR (
            status IN ('ENVIADA_PARA_CLICHERIA', 'ENCAMINHADA_A_CLICHERIA', 'RECEBIDA_PELA_CLICHERIA')
            AND EXISTS (
                SELECT 1 FROM usuarios u WHERE u.auth_uid = auth.uid() AND u.setor = 'CLICHERIA'
            )
        )
    );

-- Apenas admin pode criar provas.
DROP POLICY IF EXISTS pol_provas_insert ON provas_digitais;
CREATE POLICY pol_provas_insert ON provas_digitais
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM usuarios u WHERE u.auth_uid = auth.uid() AND u.is_admin = true
        )
    );

-- Apenas admin pode atualizar provas (UPDATE direto via Supabase client).
DROP POLICY IF EXISTS pol_provas_update ON provas_digitais;
CREATE POLICY pol_provas_update ON provas_digitais
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM usuarios u WHERE u.auth_uid = auth.uid() AND u.is_admin = true
        )
    );


-- ─── MOVIMENTACOES ──────────────────────────────────────────────────────────

-- Admin ve todas. VENDEDOR ve movimentacoes das suas provas. Demais veem as proprias.
DROP POLICY IF EXISTS pol_movimentacoes_select ON movimentacoes;
CREATE POLICY pol_movimentacoes_select ON movimentacoes
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM usuarios u WHERE u.auth_uid = auth.uid() AND u.is_admin = true
        )
        OR prova_id IN (
            SELECT pd.id FROM provas_digitais pd
            WHERE pd.vendedor_id = (
                SELECT u.id FROM usuarios u WHERE u.auth_uid = auth.uid()
            )
        )
        OR usuario_id = (
            SELECT u.id FROM usuarios u WHERE u.auth_uid = auth.uid()
        )
    );


-- ─── ETIQUETAS ──────────────────────────────────────────────────────────────

-- Admin ve todas. Vendedor ve etiquetas de suas provas.
DROP POLICY IF EXISTS pol_etiquetas_select ON etiquetas;
CREATE POLICY pol_etiquetas_select ON etiquetas
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM usuarios u WHERE u.auth_uid = auth.uid() AND u.is_admin = true
        )
        OR prova_id IN (
            SELECT pd.id FROM provas_digitais pd
            WHERE pd.vendedor_id = (
                SELECT u.id FROM usuarios u WHERE u.auth_uid = auth.uid()
            )
        )
    );


-- ─── AUDIT LOGS ─────────────────────────────────────────────────────────────

-- Apenas admin pode ler audit logs (RNF-005).
DROP POLICY IF EXISTS pol_audit_select ON audit_logs;
CREATE POLICY pol_audit_select ON audit_logs
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM usuarios u WHERE u.auth_uid = auth.uid() AND u.is_admin = true
        )
    );


-- ─── CONFIGURACOES DO SISTEMA ───────────────────────────────────────────────

-- Apenas admin pode ler/alterar configuracoes (RF-021).
DROP POLICY IF EXISTS pol_config_select ON configuracoes_sistema;
CREATE POLICY pol_config_select ON configuracoes_sistema
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM usuarios u WHERE u.auth_uid = auth.uid() AND u.is_admin = true
        )
    );

DROP POLICY IF EXISTS pol_config_update ON configuracoes_sistema;
CREATE POLICY pol_config_update ON configuracoes_sistema
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM usuarios u WHERE u.auth_uid = auth.uid() AND u.is_admin = true
        )
    );
