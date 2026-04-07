-- =============================================================================
-- SNAPSHOT DO SCHEMA ATUAL — Rastreio de Provas Digitais
-- Gerado em: 2026-04-07 (pos-Wave 1)
-- =============================================================================
-- Este arquivo e referencia rapida. A fonte de verdade sao as migrations Alembic
-- em backend/migrations/versions/ e os .sql em backend/migrations/rls/.
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

-- usuarios
CREATE INDEX idx_usuarios_setor ON usuarios (setor);
CREATE INDEX idx_usuarios_ativo ON usuarios (ativo) WHERE ativo = true;

-- provas_digitais
CREATE INDEX idx_provas_status ON provas_digitais (status);
CREATE INDEX idx_provas_vendedor ON provas_digitais (vendedor_id);
CREATE INDEX idx_provas_created_at ON provas_digitais (created_at);
CREATE INDEX idx_provas_status_created ON provas_digitais (status, created_at);

-- movimentacoes
CREATE INDEX idx_movimentacoes_prova ON movimentacoes (prova_id);
CREATE INDEX idx_movimentacoes_usuario ON movimentacoes (usuario_id);
CREATE INDEX idx_movimentacoes_prova_ciclo ON movimentacoes (prova_id, ciclo);
CREATE INDEX idx_movimentacoes_created_at ON movimentacoes (created_at);
CREATE INDEX idx_movimentacoes_prova_data ON movimentacoes (prova_id, created_at DESC);

-- etiquetas
CREATE INDEX idx_etiquetas_prova ON etiquetas (prova_id);

-- audit_logs
CREATE INDEX idx_audit_prova ON audit_logs (prova_id);
CREATE INDEX idx_audit_usuario ON audit_logs (usuario_id);
CREATE INDEX idx_audit_acao ON audit_logs (acao);
CREATE INDEX idx_audit_created_at ON audit_logs (created_at);


-- 6. ROW LEVEL SECURITY

ALTER TABLE usuarios ENABLE ROW LEVEL SECURITY;
ALTER TABLE provas_digitais ENABLE ROW LEVEL SECURITY;
ALTER TABLE movimentacoes ENABLE ROW LEVEL SECURITY;
ALTER TABLE etiquetas ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE configuracoes_sistema ENABLE ROW LEVEL SECURITY;

-- Policies: ver backend/migrations/rls/002_policies_por_perfil.sql e 003_policies_wave1_usuarios.sql
-- Resumo: 11 policies (usuarios: is_admin-based; demais: por setor)
--   usuarios: SELECT (self ou admin), INSERT/UPDATE (admin only)
--   provas/movimentacoes/etiquetas: por setor (STUDIO, VENDEDOR, MOTORISTA, CLICHERIA)
--   audit_logs e config: STUDIO only


-- 7. SEEDS

INSERT INTO configuracoes_sistema (chave, valor, descricao) VALUES
    ('tempo_atraso_horas_uteis', '48',
     'Tempo em horas uteis sem movimentacao para classificar prova como Atrasada (RN-008). Padrao: 48h.'),
    ('template_etiqueta', '"padrao"',
     'Template de layout da etiqueta imprimivel. Opcoes: padrao, personalizado (RN-011).');
