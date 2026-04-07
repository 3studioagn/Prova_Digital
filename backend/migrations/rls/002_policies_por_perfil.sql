-- =============================================================================
-- RLS 002: Policies por perfil e localizacao (RN-004, RN-007)
-- =============================================================================
-- IMPORTANTE: Este script e idempotente — DROP IF EXISTS antes de cada CREATE.
--
-- Estrategia de acesso:
--   O backend FastAPI usa a service_role_key (bypassa RLS).
--   Estas policies protegem acesso DIRETO via Supabase client (frontend/mobile).
--
-- O JWT do Supabase Auth contem:
--   - sub: auth.users.id (UUID)
--   - role: 'authenticated'
--
-- Para resolver o setor/localizacao do usuario, as policies fazem lookup na
-- tabela usuarios usando auth.uid() = usuarios.auth_uid.
--
-- Perfis e permissoes (derivados da Secao 2 dos Requisitos):
--   STUDIO:    acesso total (admin)
--   VENDEDOR:  ve suas proprias provas + provas em status relevante ao seu fluxo
--   MOTORISTA: ve provas com status COM_MOTORISTA
--   CLICHERIA: ve provas com status ENVIADA/ENCAMINHADA_A_CLICHERIA
-- =============================================================================


-- ─── USUARIOS ───────────────────────────────────────────────────────────────

-- Todos autenticados podem ler seu proprio perfil.
-- STUDIO pode ler todos (para gestao de usuarios).
DROP POLICY IF EXISTS pol_usuarios_select ON usuarios;
CREATE POLICY pol_usuarios_select ON usuarios
    FOR SELECT
    USING (
        auth_uid = auth.uid()
        OR EXISTS (
            SELECT 1 FROM usuarios u
            WHERE u.auth_uid = auth.uid() AND u.setor = 'STUDIO'
        )
    );

-- Apenas STUDIO pode inserir/atualizar usuarios.
DROP POLICY IF EXISTS pol_usuarios_insert ON usuarios;
CREATE POLICY pol_usuarios_insert ON usuarios
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM usuarios u
            WHERE u.auth_uid = auth.uid() AND u.setor = 'STUDIO'
        )
    );

DROP POLICY IF EXISTS pol_usuarios_update ON usuarios;
CREATE POLICY pol_usuarios_update ON usuarios
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM usuarios u
            WHERE u.auth_uid = auth.uid() AND u.setor = 'STUDIO'
        )
    );


-- ─── PROVAS DIGITAIS ────────────────────────────────────────────────────────

-- STUDIO: ve todas as provas.
-- VENDEDOR: ve provas onde e o vendedor responsavel.
-- MOTORISTA: ve provas com status COM_MOTORISTA.
-- CLICHERIA: ve provas com status ENVIADA_PARA_CLICHERIA ou ENCAMINHADA_A_CLICHERIA.
DROP POLICY IF EXISTS pol_provas_select ON provas_digitais;
CREATE POLICY pol_provas_select ON provas_digitais
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM usuarios u WHERE u.auth_uid = auth.uid() AND u.setor = 'STUDIO'
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
            status IN ('ENVIADA_PARA_CLICHERIA', 'ENCAMINHADA_A_CLICHERIA')
            AND EXISTS (
                SELECT 1 FROM usuarios u WHERE u.auth_uid = auth.uid() AND u.setor = 'CLICHERIA'
            )
        )
    );

-- Apenas STUDIO pode criar provas.
DROP POLICY IF EXISTS pol_provas_insert ON provas_digitais;
CREATE POLICY pol_provas_insert ON provas_digitais
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM usuarios u WHERE u.auth_uid = auth.uid() AND u.setor = 'STUDIO'
        )
    );

-- Updates sao feitos pelo backend (service_role), mas como seguranca adicional:
DROP POLICY IF EXISTS pol_provas_update ON provas_digitais;
CREATE POLICY pol_provas_update ON provas_digitais
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM usuarios u WHERE u.auth_uid = auth.uid() AND u.setor = 'STUDIO'
        )
    );


-- ─── MOVIMENTACOES ──────────────────────────────────────────────────────────

-- Todos autenticados podem ver movimentacoes das provas que podem ver.
-- INSERT e feito exclusivamente pelo backend (service_role).
-- UPDATE/DELETE bloqueados pelo trigger de imutabilidade.
DROP POLICY IF EXISTS pol_movimentacoes_select ON movimentacoes;
CREATE POLICY pol_movimentacoes_select ON movimentacoes
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM usuarios u WHERE u.auth_uid = auth.uid() AND u.setor = 'STUDIO'
        )
        OR usuario_id = (
            SELECT u.id FROM usuarios u WHERE u.auth_uid = auth.uid()
        )
    );


-- ─── ETIQUETAS ──────────────────────────────────────────────────────────────

-- STUDIO pode ver todas. Vendedor ve etiquetas de suas provas.
DROP POLICY IF EXISTS pol_etiquetas_select ON etiquetas;
CREATE POLICY pol_etiquetas_select ON etiquetas
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM usuarios u WHERE u.auth_uid = auth.uid() AND u.setor = 'STUDIO'
        )
        OR prova_id IN (
            SELECT pd.id FROM provas_digitais pd
            WHERE pd.vendedor_id = (
                SELECT u.id FROM usuarios u WHERE u.auth_uid = auth.uid()
            )
        )
    );


-- ─── AUDIT LOGS ─────────────────────────────────────────────────────────────

-- Apenas STUDIO pode ver audit logs (RNF-005).
DROP POLICY IF EXISTS pol_audit_select ON audit_logs;
CREATE POLICY pol_audit_select ON audit_logs
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM usuarios u WHERE u.auth_uid = auth.uid() AND u.setor = 'STUDIO'
        )
    );


-- ─── CONFIGURACOES DO SISTEMA ───────────────────────────────────────────────

-- Apenas STUDIO pode ler e alterar configuracoes (RF-021).
DROP POLICY IF EXISTS pol_config_select ON configuracoes_sistema;
CREATE POLICY pol_config_select ON configuracoes_sistema
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM usuarios u WHERE u.auth_uid = auth.uid() AND u.setor = 'STUDIO'
        )
    );

DROP POLICY IF EXISTS pol_config_update ON configuracoes_sistema;
CREATE POLICY pol_config_update ON configuracoes_sistema
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM usuarios u WHERE u.auth_uid = auth.uid() AND u.setor = 'STUDIO'
        )
    );
