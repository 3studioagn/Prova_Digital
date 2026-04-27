-- =============================================================================
-- SNAPSHOT DO SCHEMA ATUAL — Rastreio de Provas Digitais
-- Atualizado em: 2026-04-27 (Wave 5 Bloco 5.0, alembic_version = 011)
-- =============================================================================
-- Este arquivo e referencia rapida. A fonte de verdade sao as migrations Alembic
-- em backend/migrations/versions/ e os .sql em backend/migrations/rls/.
--
-- Estado apos Wave 5 Bloco 5.0 (recovery + clarify):
--   - 6 tabelas de dominio + alembic_version (todas RLS on)
--   - 12 policies RLS, todas usando `is_admin=true` com `(SELECT auth.uid())`
--   - 32 indexes cobrindo queries de filtro/paginacao/scoping/relatorios
--   - 6 triggers (3 imutabilidade + 3 updated_at) com search_path=''
--   - Seeds: tempo_atraso_horas_uteis (texto atualizado para 'horas corridas',
--            ADR-099) + template_etiqueta (JSONB estruturado)
--
-- Migrations Alembic aplicadas (1-11):
--   001  create_enums_tables_triggers_indexes
--   002  seed_configuracoes_iniciais
--   003  fix_constraints_indexes_trigger
--   004  add_is_admin_created_by_to_usuarios
--   005  add_index_on_usuarios_created_by (ADR-023)
--   006  set_search_path_on_trigger_functions (ADR-024)
--   007  enable_rls_on_alembic_version (ADR-025)
--   008  add_index_on_configuracoes_sistema_updated_by (ADR-026)
--   009  evolve_template_etiqueta_schema (ADR-036)
--   010  add_indexes_for_wave5_reports (ADR-095 — recovery + Wave 5)
--   011  clarify_tempo_atraso_descricao (ADR-099 — RN-008 desvio Wave 5)
--
-- NOTA SOBRE 010 e 011 (drift detectado e reconciliado em 2026-04-27):
--   - 010 ja estava aplicada em producao desde 2026-04-15 via commit 5db44bb
--     (Wave 5 anterior, revertida no repo mas nao no banco). Recovery 1:1.
--   - 011 e nova; cosmetica (apenas texto da `descricao`). Aplicacao em
--     producao planejada para o Bloco 5.6 (closeout da Wave 5).
--
-- Policies RLS em producao:
--   001_enable_rls.sql                         (RLS ligado nas 6 tabelas)
--   002_policies_por_perfil.sql                (legacy — substituida pela 004)
--   003_policies_wave1_usuarios.sql            (is_admin-based em usuarios)
--   004_unify_rls_is_admin.sql                 (ADR-018 — is_admin em todas)
--   005_initplan_optimization.sql              (ADR-029 — (SELECT auth.uid()))
--   006_movimentacoes_insert_and_expand_select.sql
--                                              (ADR-082 — Wave 3 A.2; adiciona
--                                               pol_movimentacoes_insert +
--                                               expande SELECT para MOTORISTA/
--                                               CLICHERIA, resolve F03 Sessao 22)
--   007_enable_realtime_provas.sql             (Wave 4 — provas_digitais na
--                                               publicacao supabase_realtime)
-- =============================================================================


-- 1. ENUMS

CREATE TYPE setor_enum AS ENUM ('STUDIO', 'VENDEDOR', 'MOTORISTA', 'CLICHERIA');

CREATE TYPE localizacao_enum AS ENUM ('MATRIZ', 'FILIAL');

CREATE TYPE status_prova_enum AS ENUM (
    'CRIADA',
    'RETIRADA_PELO_VENDEDOR',
    'APROVADA_PELO_VENDEDOR',
    'DE_VOLTA_3STUDIO',
    'COM_MOTORISTA',
    'ENVIADA_PARA_CLICHERIA',
    'ENCAMINHADA_A_CLICHERIA',
    'RECEBIDA_PELA_CLICHERIA',
    'REPROVADA_PELO_VENDEDOR',
    'CANCELADA'
);

CREATE TYPE rota_enum AS ENUM ('PADRAO', 'DIRETA');


-- 2. TABELAS

CREATE TABLE usuarios (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    auth_uid    UUID UNIQUE NOT NULL,
    nome        VARCHAR(150) NOT NULL,
    email       VARCHAR(255) UNIQUE NOT NULL,
    setor       setor_enum NOT NULL,
    localizacao localizacao_enum,
    is_admin    BOOLEAN NOT NULL DEFAULT false,
    ativo       BOOLEAN NOT NULL DEFAULT true,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by  UUID REFERENCES usuarios(id),
    CONSTRAINT chk_vendedor_localizacao CHECK (
        (setor = 'VENDEDOR' AND localizacao IS NOT NULL)
        OR
        (setor != 'VENDEDOR' AND localizacao IS NULL)
    )
);

CREATE TABLE provas_digitais (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome                 VARCHAR(200) NOT NULL,
    nro_requerimento     VARCHAR(50) UNIQUE NOT NULL,
    cliente              VARCHAR(200) NOT NULL,
    vendedor_id          UUID NOT NULL REFERENCES usuarios(id),
    imagem_url           TEXT NOT NULL,
    qr_code_hash         VARCHAR(64) UNIQUE NOT NULL,
    status               status_prova_enum NOT NULL DEFAULT 'CRIADA',
    rota                 rota_enum,
    ciclo_atual          INTEGER NOT NULL DEFAULT 1,
    motivo_cancelamento  TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_ciclo_atual_positivo CHECK (ciclo_atual >= 1)
);

CREATE TABLE movimentacoes (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prova_id           UUID NOT NULL REFERENCES provas_digitais(id),
    usuario_id         UUID NOT NULL REFERENCES usuarios(id),
    status_anterior    status_prova_enum NOT NULL,
    status_novo        status_prova_enum NOT NULL,
    assinatura_digital BYTEA NOT NULL,
    motivo_reprovacao  TEXT,
    ciclo              INTEGER NOT NULL,
    rota_no_momento    rota_enum,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_status_diferente CHECK (status_anterior != status_novo),
    CONSTRAINT chk_ciclo_positivo CHECK (ciclo >= 1)
);

CREATE TABLE etiquetas (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prova_id         UUID NOT NULL REFERENCES provas_digitais(id),
    nome_prova       VARCHAR(200) NOT NULL,
    nro_requerimento VARCHAR(50) NOT NULL,
    vendedor_nome    VARCHAR(150) NOT NULL,
    qr_code_image    BYTEA NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE audit_logs (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prova_id      UUID REFERENCES provas_digitais(id),
    usuario_id    UUID NOT NULL REFERENCES usuarios(id),
    acao          VARCHAR(100) NOT NULL,
    detalhes_json JSONB,
    ip_address    INET,
    user_agent    TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE configuracoes_sistema (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chave       VARCHAR(100) UNIQUE NOT NULL,
    valor       JSONB NOT NULL,
    descricao   TEXT,
    updated_by  UUID REFERENCES usuarios(id),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- 3. FUNCOES

CREATE OR REPLACE FUNCTION fn_bloquear_alteracao()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Operacao % nao permitida na tabela %. Registros sao imutaveis (RNF-005).',
        TG_OP, TG_TABLE_NAME;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_atualizar_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- 4. TRIGGERS

-- Imutabilidade (RNF-005)
CREATE TRIGGER trg_movimentacoes_imutavel
    BEFORE UPDATE OR DELETE ON movimentacoes
    FOR EACH ROW EXECUTE FUNCTION fn_bloquear_alteracao();

CREATE TRIGGER trg_audit_logs_imutavel
    BEFORE UPDATE OR DELETE ON audit_logs
    FOR EACH ROW EXECUTE FUNCTION fn_bloquear_alteracao();

CREATE TRIGGER trg_etiquetas_imutavel
    BEFORE UPDATE OR DELETE ON etiquetas
    FOR EACH ROW EXECUTE FUNCTION fn_bloquear_alteracao();

-- updated_at automatico
CREATE TRIGGER trg_usuarios_updated_at
    BEFORE UPDATE ON usuarios
    FOR EACH ROW EXECUTE FUNCTION fn_atualizar_updated_at();

CREATE TRIGGER trg_provas_updated_at
    BEFORE UPDATE ON provas_digitais
    FOR EACH ROW EXECUTE FUNCTION fn_atualizar_updated_at();

CREATE TRIGGER trg_configuracoes_updated_at
    BEFORE UPDATE ON configuracoes_sistema
    FOR EACH ROW EXECUTE FUNCTION fn_atualizar_updated_at();


-- 5. INDICES
--
-- NOTA: primary keys e UNIQUE constraints geram indexes automaticamente
-- (usuarios_pkey, usuarios_auth_uid_key, usuarios_email_key, provas_digitais_pkey,
-- provas_digitais_nro_requerimento_key, provas_digitais_qr_code_hash_key, etc).
-- Esses nao estao listados abaixo — so os indexes criados EXPLICITAMENTE.

-- usuarios
CREATE INDEX idx_usuarios_setor ON usuarios (setor);
CREATE INDEX idx_usuarios_ativo ON usuarios (ativo) WHERE ativo = true;
CREATE INDEX idx_usuarios_created_by ON usuarios (created_by);  -- migration 005

-- provas_digitais
CREATE INDEX idx_provas_status ON provas_digitais (status);
CREATE INDEX idx_provas_vendedor ON provas_digitais (vendedor_id);
CREATE INDEX idx_provas_created_at ON provas_digitais (created_at);
CREATE INDEX idx_provas_status_created ON provas_digitais (status, created_at);
CREATE INDEX idx_provas_vendedor_status ON provas_digitais (vendedor_id, status);  -- migration 010 (Wave 5 — breakdown por vendedor)

-- movimentacoes
CREATE INDEX idx_movimentacoes_prova ON movimentacoes (prova_id);
CREATE INDEX idx_movimentacoes_usuario ON movimentacoes (usuario_id);
CREATE INDEX idx_movimentacoes_prova_ciclo ON movimentacoes (prova_id, ciclo);
CREATE INDEX idx_movimentacoes_created_at ON movimentacoes (created_at);  -- migration 003
CREATE INDEX idx_movimentacoes_prova_data ON movimentacoes (prova_id, created_at DESC);  -- migration 003
CREATE INDEX idx_movimentacoes_status_novo_created_at ON movimentacoes (status_novo, created_at DESC);  -- migration 010 (Wave 5 — tempo medio aprovacao + taxa reprovacao)

-- etiquetas
CREATE INDEX idx_etiquetas_prova ON etiquetas (prova_id);

-- audit_logs
CREATE INDEX idx_audit_prova ON audit_logs (prova_id);
CREATE INDEX idx_audit_usuario ON audit_logs (usuario_id);
CREATE INDEX idx_audit_acao ON audit_logs (acao);
CREATE INDEX idx_audit_created_at ON audit_logs (created_at);

-- configuracoes_sistema
CREATE INDEX idx_configuracoes_sistema_updated_by ON configuracoes_sistema (updated_by);  -- migration 008


-- 6. ROW LEVEL SECURITY

ALTER TABLE usuarios ENABLE ROW LEVEL SECURITY;
ALTER TABLE provas_digitais ENABLE ROW LEVEL SECURITY;
ALTER TABLE movimentacoes ENABLE ROW LEVEL SECURITY;
ALTER TABLE etiquetas ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE configuracoes_sistema ENABLE ROW LEVEL SECURITY;
ALTER TABLE alembic_version ENABLE ROW LEVEL SECURITY;  -- migration 007 (ADR-025)

-- Policies pos Wave 3 Lote A sub-bloco A.2 (apos RLS 004, 005 e 006):
-- 12 policies no schema public, todas com `(SELECT auth.uid())` para otimizacao
-- de initplan (ADR-029). Fonte de verdade:
--   - 11 policies base: backend/migrations/rls/005_initplan_optimization.sql
--   - movimentacoes INSERT + SELECT expandida: backend/migrations/rls/006_movimentacoes_insert_and_expand_select.sql
--
-- Semantica (apos RLS 006):
--   usuarios             SELECT (self ou is_admin), INSERT (is_admin), UPDATE (is_admin)
--   provas_digitais      SELECT (is_admin + vendedor own + motorista by status + clicheria by status),
--                        INSERT (is_admin), UPDATE (is_admin)
--   movimentacoes        SELECT (is_admin + vendedor das suas provas + autor + MOTORISTA quando
--                                prova em COM_MOTORISTA + CLICHERIA quando prova em status de clicheria),
--                        INSERT (is_admin)                       -- novo em RLS 006 (ADR-082)
--   etiquetas            SELECT (is_admin + vendedor das suas provas)
--   audit_logs           SELECT (is_admin only)
--   configuracoes_sistema SELECT (is_admin), UPDATE (is_admin)
--
-- UPDATE/DELETE em movimentacoes, etiquetas e audit_logs continuam bloqueados
-- pelos triggers de imutabilidade (RNF-005) — nao ha policy necessaria.
--
-- Backend usa service_role e BYPASSA RLS por design. O scoping real no backend
-- e implementado via `_scoping_filter(user)` em app/api/v1/provas.py (ADR-046, ADR-049).
-- RLS continua ativa como defesa em profundidade para acesso direto via
-- Supabase client do frontend.


-- 7. SEEDS

-- Seed original da Wave 0 (migration 002):
--   template_etiqueta foi '"padrao"' (string JSONB)
--
-- Pos-Wave 2 Componente 06 (migration 009 — ADR-036), evoluiu para objeto JSONB.
-- Pos-Wave 5 Bloco 5.0 (migration 011 — ADR-099), descricao da chave
-- `tempo_atraso_horas_uteis` foi atualizada para refletir que o calculo e em
-- horas CORRIDAS (consistencia com Wave 4 ADR-091, desvio explicito do RN-008
-- literal). O nome da chave permanece com o sufixo "_horas_uteis" por
-- compatibilidade com Waves 2 e 4.
INSERT INTO configuracoes_sistema (chave, valor, descricao) VALUES
    ('tempo_atraso_horas_uteis', '48',
     'Tempo em horas corridas sem movimentacao para classificar prova como Atrasada. Padrao: 48h.'),
    ('template_etiqueta',
     '{"nome":"padrao","formato":"A4","logo_enabled":true,"mostrar_data_criacao":false}'::jsonb,
     'Template de layout da etiqueta imprimivel (RN-011). Campos: nome, formato (A4|80mm_thermal), logo_enabled, mostrar_data_criacao.');
