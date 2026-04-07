-- =============================================================================
-- RLS 003: Policies atualizadas para Wave 1 (RBAC com is_admin)
-- =============================================================================
-- IMPORTANTE: Service Role bypassa RLS por design. Estas policies protegem
-- acesso DIRETO via Supabase client (frontend/mobile) usando o JWT do usuario.
--
-- Wave 1 introduz is_admin na tabela usuarios. As policies desta tabela agora
-- usam is_admin = true em vez de setor = 'STUDIO' para determinar acesso admin.
-- Policies de outras tabelas permanecem inalteradas (ainda usam setor = 'STUDIO').
-- =============================================================================


-- ─── USUARIOS (substitui policies da RLS 002) ──────────────────────────────

-- SELECT: admin ve todos; nao-admin ve apenas o proprio registro.
DROP POLICY IF EXISTS pol_usuarios_select ON usuarios;
CREATE POLICY pol_usuarios_select ON usuarios
    FOR SELECT
    USING (
        auth_uid = auth.uid()
        OR EXISTS (
            SELECT 1 FROM usuarios u
            WHERE u.auth_uid = auth.uid() AND u.is_admin = true
        )
    );

-- INSERT: apenas admin.
DROP POLICY IF EXISTS pol_usuarios_insert ON usuarios;
CREATE POLICY pol_usuarios_insert ON usuarios
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM usuarios u
            WHERE u.auth_uid = auth.uid() AND u.is_admin = true
        )
    );

-- UPDATE: apenas admin.
DROP POLICY IF EXISTS pol_usuarios_update ON usuarios;
CREATE POLICY pol_usuarios_update ON usuarios
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM usuarios u
            WHERE u.auth_uid = auth.uid() AND u.is_admin = true
        )
    );
