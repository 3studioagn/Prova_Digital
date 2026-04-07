"""Cria enums, tabelas de dominio, triggers de imutabilidade e indices.

Revision ID: 001
Revises: None
Create Date: 2026-04-07

Este e o schema central do sistema. Todas as tabelas de dominio sao criadas aqui.
Tabelas auth.* sao gerenciadas pelo Supabase — NUNCA tocar via Alembic.

Tabelas criadas:
  - usuarios: espelho de perfil da app (setor, localizacao, ativo)
  - provas_digitais: objeto central do fluxo (QR Code, status, rota)
  - movimentacoes: log IMUTAVEL de transicoes de status (RNF-005)
  - etiquetas: snapshot dos dados para impressao (RF-003)
  - audit_logs: log IMUTAVEL geral do sistema (RNF-005)
  - configuracoes_sistema: parametros configuraveis pelo 3Studio (RF-021)

Triggers:
  - fn_bloquear_alteracao: impede UPDATE/DELETE em movimentacoes e audit_logs
  - fn_atualizar_updated_at: atualiza updated_at automaticamente

Enums: setor_enum, localizacao_enum, status_prova_enum, rota_enum
"""
from typing import Sequence, Union

from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
    -- 1. ENUMS

    -- Setores da organizacao. Cada usuario pertence a exatamente um setor (RN-009).
    CREATE TYPE setor_enum AS ENUM ('STUDIO', 'VENDEDOR', 'MOTORISTA', 'CLICHERIA');

    -- Localizacao fisica do vendedor. Determina a rota de encaminhamento (RN-007).
    CREATE TYPE localizacao_enum AS ENUM ('MATRIZ', 'FILIAL');

    -- Todos os estados possiveis de uma prova digital (Secao 5 dos Requisitos).
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

    -- Rota de encaminhamento: PADRAO (Matriz) ou DIRETA (Filial).
    CREATE TYPE rota_enum AS ENUM ('PADRAO', 'DIRETA');


    -- 2. TABELAS

    CREATE TABLE usuarios (
        id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        auth_uid    UUID UNIQUE NOT NULL,
        nome        VARCHAR(150) NOT NULL,
        email       VARCHAR(255) UNIQUE NOT NULL,
        setor       setor_enum NOT NULL,
        localizacao localizacao_enum,
        ativo       BOOLEAN NOT NULL DEFAULT true,
        created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
        -- RN-009: Vendedor DEVE ter localizacao; demais NAO podem ter.
        CONSTRAINT chk_vendedor_localizacao CHECK (
            (setor = 'VENDEDOR' AND localizacao IS NOT NULL)
            OR
            (setor != 'VENDEDOR' AND localizacao IS NULL)
        )
    );

    CREATE INDEX idx_usuarios_auth_uid ON usuarios (auth_uid);
    CREATE INDEX idx_usuarios_setor ON usuarios (setor);
    CREATE INDEX idx_usuarios_ativo ON usuarios (ativo) WHERE ativo = true;

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
        updated_at           TIMESTAMPTZ NOT NULL DEFAULT now()
    );

    CREATE INDEX idx_provas_status ON provas_digitais (status);
    CREATE INDEX idx_provas_vendedor ON provas_digitais (vendedor_id);
    CREATE INDEX idx_provas_created_at ON provas_digitais (created_at);
    CREATE INDEX idx_provas_nro_requerimento ON provas_digitais (nro_requerimento);
    CREATE INDEX idx_provas_status_created ON provas_digitais (status, created_at);

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
        created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
    );

    CREATE INDEX idx_movimentacoes_prova ON movimentacoes (prova_id);
    CREATE INDEX idx_movimentacoes_usuario ON movimentacoes (usuario_id);
    CREATE INDEX idx_movimentacoes_prova_ciclo ON movimentacoes (prova_id, ciclo);

    CREATE TABLE etiquetas (
        id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        prova_id         UUID NOT NULL REFERENCES provas_digitais(id),
        nome_prova       VARCHAR(200) NOT NULL,
        nro_requerimento VARCHAR(50) NOT NULL,
        vendedor_nome    VARCHAR(150) NOT NULL,
        qr_code_image    BYTEA NOT NULL,
        created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
    );

    CREATE INDEX idx_etiquetas_prova ON etiquetas (prova_id);

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

    CREATE INDEX idx_audit_prova ON audit_logs (prova_id);
    CREATE INDEX idx_audit_usuario ON audit_logs (usuario_id);
    CREATE INDEX idx_audit_acao ON audit_logs (acao);
    CREATE INDEX idx_audit_created_at ON audit_logs (created_at);

    CREATE TABLE configuracoes_sistema (
        id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        chave       VARCHAR(100) UNIQUE NOT NULL,
        valor       JSONB NOT NULL,
        descricao   TEXT,
        updated_by  UUID REFERENCES usuarios(id),
        updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
    );


    -- 3. TRIGGERS DE IMUTABILIDADE (RNF-005)
    -- Impede UPDATE/DELETE em movimentacoes e audit_logs a nivel de banco.

    CREATE OR REPLACE FUNCTION fn_bloquear_alteracao()
    RETURNS TRIGGER AS $$
    BEGIN
        RAISE EXCEPTION 'Operacao % nao permitida na tabela %. Registros sao imutaveis (RNF-005).',
            TG_OP, TG_TABLE_NAME;
        RETURN NULL;
    END;
    $$ LANGUAGE plpgsql;

    CREATE TRIGGER trg_movimentacoes_imutavel
        BEFORE UPDATE OR DELETE ON movimentacoes
        FOR EACH ROW
        EXECUTE FUNCTION fn_bloquear_alteracao();

    CREATE TRIGGER trg_audit_logs_imutavel
        BEFORE UPDATE OR DELETE ON audit_logs
        FOR EACH ROW
        EXECUTE FUNCTION fn_bloquear_alteracao();


    -- 4. TRIGGERS DE updated_at AUTOMATICO

    CREATE OR REPLACE FUNCTION fn_atualizar_updated_at()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = now();
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;

    CREATE TRIGGER trg_usuarios_updated_at
        BEFORE UPDATE ON usuarios
        FOR EACH ROW
        EXECUTE FUNCTION fn_atualizar_updated_at();

    CREATE TRIGGER trg_provas_updated_at
        BEFORE UPDATE ON provas_digitais
        FOR EACH ROW
        EXECUTE FUNCTION fn_atualizar_updated_at();

    CREATE TRIGGER trg_configuracoes_updated_at
        BEFORE UPDATE ON configuracoes_sistema
        FOR EACH ROW
        EXECUTE FUNCTION fn_atualizar_updated_at();
    """)


def downgrade() -> None:
    op.execute("""
    DROP TRIGGER IF EXISTS trg_configuracoes_updated_at ON configuracoes_sistema;
    DROP TRIGGER IF EXISTS trg_provas_updated_at ON provas_digitais;
    DROP TRIGGER IF EXISTS trg_usuarios_updated_at ON usuarios;
    DROP TRIGGER IF EXISTS trg_audit_logs_imutavel ON audit_logs;
    DROP TRIGGER IF EXISTS trg_movimentacoes_imutavel ON movimentacoes;
    DROP FUNCTION IF EXISTS fn_atualizar_updated_at();
    DROP FUNCTION IF EXISTS fn_bloquear_alteracao();
    DROP TABLE IF EXISTS configuracoes_sistema;
    DROP TABLE IF EXISTS audit_logs;
    DROP TABLE IF EXISTS etiquetas;
    DROP TABLE IF EXISTS movimentacoes;
    DROP TABLE IF EXISTS provas_digitais;
    DROP TABLE IF EXISTS usuarios;
    DROP TYPE IF EXISTS rota_enum;
    DROP TYPE IF EXISTS status_prova_enum;
    DROP TYPE IF EXISTS localizacao_enum;
    DROP TYPE IF EXISTS setor_enum;
    """)
