"""Correcoes de auditoria: constraints, indices redundantes, trigger etiquetas.

Revision ID: 003
Revises: 002
Create Date: 2026-04-07

Correcoes aplicadas (auditoria senior):
  C2: Trigger de imutabilidade em etiquetas (snapshot nao pode ser alterado)
  M1: Remove indices redundantes (duplicados de UNIQUE constraints)
  M2: CHECK status_anterior != status_novo em movimentacoes
  M3: CHECK ciclo >= 1 em movimentacoes e ciclo_atual >= 1 em provas_digitais
  M4: Indice em movimentacoes.created_at (deteccao de atraso 48h)
  R1: Indice composto movimentacoes(prova_id, created_at DESC) para query "ultima movimentacao"
"""
from typing import Sequence, Union

from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- C2: Trigger de imutabilidade em etiquetas ---
    # Etiquetas sao snapshots para impressao (RF-003). Uma vez geradas, nao podem
    # ser alteradas — mesmo principio de movimentacoes e audit_logs (RNF-005).
    op.execute("""
    CREATE TRIGGER trg_etiquetas_imutavel
        BEFORE UPDATE OR DELETE ON etiquetas
        FOR EACH ROW
        EXECUTE FUNCTION fn_bloquear_alteracao();
    """)

    # --- M1: Remove indices redundantes ---
    # PostgreSQL cria automaticamente um btree index para cada UNIQUE constraint.
    # Ter um indice adicional na mesma coluna dobra a escrita sem beneficio de leitura.
    #   idx_usuarios_auth_uid  =  duplicata de usuarios_auth_uid_key (UNIQUE)
    #   idx_provas_nro_requerimento  =  duplicata de provas_digitais_nro_requerimento_key (UNIQUE)
    op.execute("DROP INDEX IF EXISTS idx_usuarios_auth_uid;")
    op.execute("DROP INDEX IF EXISTS idx_provas_nro_requerimento;")

    # --- M2: CHECK status_anterior != status_novo ---
    # Impede transicoes nulas (de X para X) a nivel de banco.
    op.execute("""
    ALTER TABLE movimentacoes
        ADD CONSTRAINT chk_status_diferente
        CHECK (status_anterior != status_novo);
    """)

    # --- M3: CHECK ciclo >= 1 ---
    # Ciclos comecam em 1. Valores 0 ou negativos sao invalidos.
    op.execute("""
    ALTER TABLE movimentacoes
        ADD CONSTRAINT chk_ciclo_positivo
        CHECK (ciclo >= 1);
    """)
    op.execute("""
    ALTER TABLE provas_digitais
        ADD CONSTRAINT chk_ciclo_atual_positivo
        CHECK (ciclo_atual >= 1);
    """)

    # --- M4: Indice em movimentacoes.created_at ---
    # Necessario para deteccao de atraso (48h uteis) com query temporal.
    op.execute("""
    CREATE INDEX idx_movimentacoes_created_at
        ON movimentacoes (created_at);
    """)

    # --- R1: Indice composto para "ultima movimentacao da prova" ---
    # Query mais executada do sistema: ORDER BY created_at DESC LIMIT 1 por prova.
    op.execute("""
    CREATE INDEX idx_movimentacoes_prova_data
        ON movimentacoes (prova_id, created_at DESC);
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_movimentacoes_prova_data;")
    op.execute("DROP INDEX IF EXISTS idx_movimentacoes_created_at;")
    op.execute("ALTER TABLE provas_digitais DROP CONSTRAINT IF EXISTS chk_ciclo_atual_positivo;")
    op.execute("ALTER TABLE movimentacoes DROP CONSTRAINT IF EXISTS chk_ciclo_positivo;")
    op.execute("ALTER TABLE movimentacoes DROP CONSTRAINT IF EXISTS chk_status_diferente;")
    op.execute("CREATE INDEX IF NOT EXISTS idx_provas_nro_requerimento ON provas_digitais (nro_requerimento);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_usuarios_auth_uid ON usuarios (auth_uid);")
    op.execute("DROP TRIGGER IF EXISTS trg_etiquetas_imutavel ON etiquetas;")
