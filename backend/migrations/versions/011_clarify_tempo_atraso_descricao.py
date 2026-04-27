"""011 clarify tempo_atraso descricao (Wave 5 - RN-008 desvio documentado)

Revision ID: 011
Revises: 010
Create Date: 2026-04-27

Atualiza o campo `descricao` da chave `tempo_atraso_horas_uteis` em
`configuracoes_sistema` para refletir a realidade: o calculo real e em
horas CORRIDAS (decisao Wave 4 ADR-091, mantida na Wave 5 ADR-099),
nao em horas uteis como o nome legacy da chave sugere.

A chave em si NAO e renomeada - `tempo_atraso_horas_uteis` permanece
para preservar compatibilidade com Wave 2 (Componente 09 -
schemas/configuracao.py) e Wave 4 (handler do dashboard). ADR-099
documenta o desvio explicito do RN-008 literal ("horas uteis").

Contexto:
  - Wave 4 (ADR-091, decisao 4) adotou horas corridas com aprovacao do
    Mario, justificando que calcular horas uteis exigiria tabela de
    feriados + logica de calendario (complexidade desproporcional p/ MVP).
  - Wave 5 reforca essa decisao para manter consistencia entre Dashboard
    (RF-014) e Relatorios (RF-015) - drift entre as duas e blocker
    documentado no WAVE5_ANALYSIS Secao 8 (R7).

Texto curto exibido na UI da tela `/configuracoes` (Componente 09 - Wave 2).
A racional tecnica completa fica em ADR-091/099 e WAVE5_ANALYSIS.

IDEMPOTENTE: rodar 2x produz o mesmo resultado.
Reversivel: downgrade() restaura o texto Wave 0/2 (referencia ao RN-008
literal). Reverter NAO altera a logica de calculo (que continua em horas
corridas no codigo); apenas o texto da `descricao` volta ao estado pre-W5.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        UPDATE public.configuracoes_sistema
        SET descricao = 'Tempo em horas corridas sem movimentacao para classificar prova como Atrasada. Padrao: 48h.'
        WHERE chave = 'tempo_atraso_horas_uteis';
    """)


def downgrade() -> None:
    op.execute("""
        UPDATE public.configuracoes_sistema
        SET descricao = 'Tempo em horas uteis sem movimentacao para classificar prova como Atrasada (RN-008). Padrao: 48h.'
        WHERE chave = 'tempo_atraso_horas_uteis';
    """)
