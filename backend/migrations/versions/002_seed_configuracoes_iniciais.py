"""Seeds iniciais: configuracoes default do sistema.

Revision ID: 002
Revises: 001
Create Date: 2026-04-07

Insere os parametros iniciais obrigatorios para o funcionamento do sistema:
  - tempo_atraso_horas_uteis: 48h uteis (RF-021, RN-008)
  - template_etiqueta: layout padrao (RN-011)

Esta migration e executada uma unica vez no primeiro deploy.
Os seeds nao referenciam updated_by porque ainda nao existem usuarios cadastrados.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
    INSERT INTO configuracoes_sistema (chave, valor, descricao)
    VALUES (
        'tempo_atraso_horas_uteis',
        '48',
        'Tempo em horas uteis sem movimentacao para classificar prova como Atrasada (RN-008). Padrao: 48h.'
    );

    INSERT INTO configuracoes_sistema (chave, valor, descricao)
    VALUES (
        'template_etiqueta',
        '"padrao"',
        'Template de layout da etiqueta imprimivel. Opcoes: padrao, personalizado (RN-011).'
    );
    """)


def downgrade() -> None:
    op.execute("""
    DELETE FROM configuracoes_sistema WHERE chave IN ('tempo_atraso_horas_uteis', 'template_etiqueta');
    """)
