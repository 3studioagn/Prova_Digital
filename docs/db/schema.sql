-- =============================================================================
-- SNAPSHOT DO SCHEMA ATUAL — Rastreio de Provas Digitais
-- Atualizado em: 2026-05-05 (Wave 2 v4.0 Audit Fixes — alembic_version = 012)
-- =============================================================================
-- Este arquivo e referencia rapida. A fonte de verdade sao as migrations Alembic
-- em backend/migrations/versions/ e os .sql em backend/migrations/rls/.
--
-- Estado apos Wave 2 v4.0 + Wave 1 v4.0 (Audit Round 2):
--   - 6 tabelas de dominio + alembic_version (todas RLS on)
--   - 12 policies RLS reescritas usando helpers SECURITY DEFINER em
--     schema `app_private` (Wave 1 v4.0 — RLS 012)
--   - 34 indexes cobrindo queries de filtro/paginacao/scoping/relatorios +
--     codigo_publico (UNIQUE) + rota (Wave 2 v4.0)
--   - 7 triggers (3 imutabilidade + 3 updated_at + 1 rota imutavel) com
--     search_path=''
--   - rota_enum com 6 valores: 4 v4.0 (MATRIZ/LAM_MATRIZ/FILIAL/LAM_FILIAL)
--     + 2 legacy v3.0 (PADRAO/DIRETA — mantidos ate Wave 7 / Componente 21)
--   - Coluna provas_digitais.codigo_publico VARCHAR(20) UNIQUE NOT NULL
--     (Wave 2 v4.0 — DAT v3.0 §8.3, ADR-116)
--   - audit_logs com 4 camadas de defesa (RNF-005): trigger + RLS deny +
--     REVOKE INSERT/UPDATE/DELETE + REVOKE TRUNCATE
--
-- Migrations Alembic aplicadas (1-12):
--   001  create_enums_tables_triggers_indexes
--   002  seed_configuracoes_iniciais
--   003  fix_constraints_indexes_trigger
--   004  add_is_admin_created_by_to_usuarios
--   005  add_index_on_usuarios_created_by (ADR-023)
--   006  set_search_path_on_trigger_functions (ADR-024)
--   007  enable_rls_on_alembic_version (ADR-025)
--   008  add_index_on_configuracoes_sistema_updated_by (ADR-026)
--   009  evolve_template_etiqueta_schema (ADR-036)
--   010  add_indexes_for_wave5_reports (ADR-095)
--   011  clarify_tempo_atraso_descricao (ADR-099)
--   012  add_codigo_publico_and_rotas_v4_to_provas (ADRs 115-119)
--        ↳ ALTER TYPE rota_enum ADD VALUE (4 novos)
--        ↳ ADD COLUMN codigo_publico VARCHAR(20) UNIQUE NOT NULL + backfill
--        ↳ CREATE UNIQUE INDEX idx_provas_codigo_publico
--        ↳ CREATE INDEX idx_provas_rota
--        ↳ CREATE FUNCTION fn_bloquear_alteracao_rota + TRIGGER
--          trg_provas_rota_imutavel (RN-002 v4.0; permite NULL→valor
--          para Wave 7 backfill — ADR-117)
--
-- IMPORTANTE — divergencia repo vs producao na migration 012 (AUD-W2V4-M02):
--   A migration 012 do REPO e uma migration Alembic atomica. Em PRODUCAO,
--   foi aplicada via MCP `apply_migration` em 3 chunks (`012a`, `012b`,
--   `012c` em `supabase_migrations.schema_migrations`) para contornar a
--   limitacao do Postgres `ALTER TYPE ADD VALUE` em transacao que usa o
--   valor recem-adicionado. O `alembic_version='012'` foi setado
--   manualmente apos o terceiro chunk. Idempotencia da Alembic atomic do
--   repo e validada em `backend/tests/test_migration_012.py`
--   (AUD-W2V4-T03).
--
-- Policies RLS em producao (apos Wave 1 v4.0 + Wave 1 v4.0 Audit Round 2):
--   001_enable_rls.sql                         (RLS ligado nas 6 tabelas)
--   002_policies_por_perfil.sql                (legacy — substituida pela 004)
--   003_policies_wave1_usuarios.sql            (is_admin-based em usuarios)
--   004_unify_rls_is_admin.sql                 (ADR-018)
--   005_initplan_optimization.sql              (ADR-029)
--   006_movimentacoes_insert_and_expand_select.sql (ADR-082)
--   007_enable_realtime_provas.sql             (Wave 4)
--   008_revoke_audit_logs_mutation.sql         (Wave 6 — ADR-112)
--   009_helpers_v4.sql                         (Wave 1 v4.0 — superseded por 012)
--   010_rebase_rls_v4.sql                      (Wave 1 v4.0 — superseded por 012)
--   011_etiquetas_select_motorista_clicheria.sql (Wave 1 v4.0 — superseded por 012)
--   012_move_helpers_to_app_private.sql        (Wave 1 v4.0 — estado final)
--   013_revoke_truncate_audit_logs.sql         (Wave 1 v4.0 Audit Round 2 —
--                                               AUD-W1V4-101, 4a camada RNF-005)
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

-- Wave 2 v4.0 (Componente 06, ADR-115): 6 valores totais — 4 v4.0
-- adicionados via ALTER TYPE; 2 legacy v3.0 mantidos ate Wave 7
-- (Componente 21) que fara o backfill final. Postgres nao suporta
-- DROP VALUE em transacao — remocao definitiva dos legacy fica
-- para wave futura.
CREATE TYPE rota_enum AS ENUM (
    'PADRAO',      -- legacy v3.0: equivalente a MATRIZ
    'DIRETA',      -- legacy v3.0: equivalente a FILIAL
    'MATRIZ',      -- Wave 2 v4.0
    'LAM_MATRIZ',  -- Wave 2 v4.0
    'FILIAL',      -- Wave 2 v4.0
    'LAM_FILIAL'   -- Wave 2 v4.0
);


-- 2. SCHEMA app_private (Wave 1 v4.0 — RLS 012)
--
-- Helpers SECURITY DEFINER usados pelas 12 policies RLS. Schema NAO
-- exposto via PostgREST (db-schemas mantem apenas public). Resolve
-- advisor `function_search_path_mutable` e organiza a logica de
-- autorizacao em um lugar so.

CREATE SCHEMA app_private;
COMMENT ON SCHEMA app_private IS
    'Helpers SECURITY DEFINER usados por policies RLS. Nao exposto via PostgREST (db-schemas mantem apenas public).';

-- Funcoes (todas com search_path = '' — ADR-024):
--   app_private.current_user_is_admin() -> boolean
--   app_private.current_user_setor()    -> setor_enum
--   app_private.current_user_id()       -> uuid


-- 3. TABELAS

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
    -- Wave 2 v4.0 (ADR-116): identificador humano-legivel
    -- PRV-AAAA-MM-NNNNNN (DAT v3.0 §8.3). Embutido no payload do QR
    -- (idempotencia camera↔digitacao manual via Componente 19,
    -- Wave 3 v4.0). Alfabeto sem chars ambiguos (sem 0/O/1/I/L) — 31
    -- chars; 31^6 ≈ 887M combinacoes/mes.
    codigo_publico       VARCHAR(20) UNIQUE NOT NULL,
    cliente              VARCHAR(200) NOT NULL,
    vendedor_id          UUID NOT NULL REFERENCES usuarios(id),
    imagem_url           TEXT NOT NULL,
    qr_code_hash         VARCHAR(64) UNIQUE NOT NULL,
    status               status_prova_enum NOT NULL DEFAULT 'CRIADA',
    -- Wave 2 v4.0: rota persistida na criacao (admin escolhe entre 4
    -- valores v4.0). Nullable para suportar provas legadas v3.0 ate
    -- a Wave 7 fazer o backfill. Imutabilidade via trigger
    -- trg_provas_rota_imutavel (RN-002 v4.0, ADR-117).
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


-- 4. FUNCOES

CREATE OR REPLACE FUNCTION fn_bloquear_alteracao()
RETURNS TRIGGER
SET search_path = ''
AS $$
BEGIN
    RAISE EXCEPTION 'Operacao % nao permitida na tabela %. Registros sao imutaveis (RNF-005).',
        TG_OP, TG_TABLE_NAME;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_atualizar_updated_at()
RETURNS TRIGGER
SET search_path = ''
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Wave 2 v4.0 (ADR-117): bloqueia mudanca de `rota` apos definicao
-- (RN-002 v4.0). Permite NULL → valor (Wave 7 backfill); bloqueia
-- valor → outro_valor e valor → NULL com SQLSTATE 22023.
CREATE OR REPLACE FUNCTION fn_bloquear_alteracao_rota()
RETURNS TRIGGER
SET search_path = ''
AS $$
BEGIN
    IF OLD.rota IS NOT NULL AND NEW.rota IS DISTINCT FROM OLD.rota THEN
        RAISE EXCEPTION
            'Coluna rota e imutavel apos definicao (RN-002 v4.0). '
            'Para alterar rota, cancele a prova e crie uma nova.'
            USING ERRCODE = '22023';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- 5. TRIGGERS

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

-- Wave 2 v4.0 (ADR-117): imutabilidade da rota apos definicao.
CREATE TRIGGER trg_provas_rota_imutavel
    BEFORE UPDATE ON provas_digitais
    FOR EACH ROW
    WHEN (OLD.rota IS DISTINCT FROM NEW.rota)
    EXECUTE FUNCTION fn_bloquear_alteracao_rota();

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


-- 6. INDICES
--
-- NOTA: primary keys e UNIQUE constraints geram indexes automaticamente
-- (usuarios_pkey, usuarios_auth_uid_key, usuarios_email_key,
-- provas_digitais_pkey, provas_digitais_nro_requerimento_key,
-- provas_digitais_qr_code_hash_key, etc). Esses nao estao listados
-- abaixo — so os indexes criados EXPLICITAMENTE.

-- usuarios
CREATE INDEX idx_usuarios_setor ON usuarios (setor);
CREATE INDEX idx_usuarios_ativo ON usuarios (ativo) WHERE ativo = true;
CREATE INDEX idx_usuarios_created_by ON usuarios (created_by);  -- migration 005

-- provas_digitais
CREATE INDEX idx_provas_status ON provas_digitais (status);
CREATE INDEX idx_provas_vendedor ON provas_digitais (vendedor_id);
CREATE INDEX idx_provas_created_at ON provas_digitais (created_at);
CREATE INDEX idx_provas_status_created ON provas_digitais (status, created_at);
CREATE INDEX idx_provas_vendedor_status ON provas_digitais (vendedor_id, status);  -- migration 010
CREATE UNIQUE INDEX idx_provas_codigo_publico ON provas_digitais (codigo_publico);  -- migration 012 (Wave 2 v4.0)
CREATE INDEX idx_provas_rota ON provas_digitais (rota);  -- migration 012 (Wave 2 v4.0)

-- movimentacoes
CREATE INDEX idx_movimentacoes_prova ON movimentacoes (prova_id);
CREATE INDEX idx_movimentacoes_usuario ON movimentacoes (usuario_id);
CREATE INDEX idx_movimentacoes_prova_ciclo ON movimentacoes (prova_id, ciclo);
CREATE INDEX idx_movimentacoes_created_at ON movimentacoes (created_at);  -- migration 003
CREATE INDEX idx_movimentacoes_prova_data ON movimentacoes (prova_id, created_at DESC);  -- migration 003
CREATE INDEX idx_movimentacoes_status_novo_created_at ON movimentacoes (status_novo, created_at DESC);  -- migration 010

-- etiquetas
CREATE INDEX idx_etiquetas_prova ON etiquetas (prova_id);

-- audit_logs
CREATE INDEX idx_audit_prova ON audit_logs (prova_id);
CREATE INDEX idx_audit_usuario ON audit_logs (usuario_id);
CREATE INDEX idx_audit_acao ON audit_logs (acao);
CREATE INDEX idx_audit_created_at ON audit_logs (created_at);

-- configuracoes_sistema
CREATE INDEX idx_configuracoes_sistema_updated_by ON configuracoes_sistema (updated_by);  -- migration 008


-- 7. ROW LEVEL SECURITY

ALTER TABLE usuarios ENABLE ROW LEVEL SECURITY;
ALTER TABLE provas_digitais ENABLE ROW LEVEL SECURITY;
ALTER TABLE movimentacoes ENABLE ROW LEVEL SECURITY;
ALTER TABLE etiquetas ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE configuracoes_sistema ENABLE ROW LEVEL SECURITY;
ALTER TABLE alembic_version ENABLE ROW LEVEL SECURITY;  -- migration 007 (ADR-025)

-- Policies pos Wave 1 v4.0 (RLS 012 — superseded RLS 009/010/011) +
-- Wave 1 v4.0 Audit Round 2 (RLS 013):
--
-- Estado final: 12 policies no schema public, todas usando os helpers
-- SECURITY DEFINER `app_private.current_user_is_admin()` /
-- `current_user_setor()` / `current_user_id()`.
--
-- Semantica:
--   usuarios             SELECT (self ou is_admin), INSERT (is_admin), UPDATE (is_admin)
--   provas_digitais      SELECT (is_admin + vendedor own + motorista by status +
--                                clicheria by status), INSERT (is_admin), UPDATE (is_admin)
--   movimentacoes        SELECT (is_admin + vendedor das suas provas + autor +
--                                MOTORISTA quando prova em COM_MOTORISTA +
--                                CLICHERIA quando prova em status de clicheria),
--                        INSERT (is_admin)
--   etiquetas            SELECT (is_admin + vendedor das suas provas +
--                                MOTORISTA + CLICHERIA — ampliada em RLS 011/012)
--   audit_logs           SELECT (is_admin only)
--                        REVOKE INSERT/UPDATE/DELETE para anon/authenticated
--                          (Wave 6 — RLS 008, ADR-112)
--                        REVOKE TRUNCATE para anon/authenticated
--                          (Wave 1 v4.0 Audit Round 2 — RLS 013, AUD-W1V4-101)
--   configuracoes_sistema SELECT (is_admin), UPDATE (is_admin)
--
-- UPDATE/DELETE em movimentacoes, etiquetas e audit_logs continuam
-- bloqueados pelos triggers de imutabilidade (RNF-005) — nao ha
-- policy necessaria.
--
-- Wave 2 v4.0 NAO criou nova policy — `pol_provas_insert WITH CHECK
-- (current_user_is_admin())` ja cobre o cenario v4.0.
--
-- Backend usa service_role e BYPASSA RLS por design. O scoping real
-- e implementado via `app.access.scopes.scope_filter_for(rule_key, user)`
-- (Wave 1 v4.0 — Componente 05). RLS continua ativa como defesa em
-- profundidade para acesso direto via Supabase client do frontend.
--
-- service_role bypassa RLS mas NAO bypassa triggers — o trigger
-- `trg_provas_rota_imutavel` continua disparando para o backend
-- (AUD-W2V4-S03 confirmado).


-- 8. SEEDS

-- Seed original da Wave 0 (migration 002):
--   template_etiqueta foi '"padrao"' (string JSONB)
--
-- Pos-Wave 2 Componente 06 (migration 009 — ADR-036), evoluiu para
-- objeto JSONB. Pos-Wave 5 Bloco 5.0 (migration 011 — ADR-099),
-- descricao da chave `tempo_atraso_horas_uteis` foi atualizada para
-- refletir que o calculo e em horas CORRIDAS.
INSERT INTO configuracoes_sistema (chave, valor, descricao) VALUES
    ('tempo_atraso_horas_uteis', '48',
     'Tempo em horas corridas sem movimentacao para classificar prova como Atrasada. Padrao: 48h.'),
    ('template_etiqueta',
     '{"nome":"padrao","formato":"A4","logo_enabled":true,"mostrar_data_criacao":false}'::jsonb,
     'Template de layout da etiqueta imprimivel (RN-011). Campos: nome, formato (A4|80mm_thermal), logo_enabled, mostrar_data_criacao.');
