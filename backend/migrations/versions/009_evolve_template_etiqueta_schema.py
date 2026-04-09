"""Evolui o valor de configuracoes_sistema.template_etiqueta de string para JSONB estruturado.

Revision ID: 009
Revises: 008
Create Date: 2026-04-09

Contexto (ADR-036):
  O seed da Wave 0 (migration 002) gravou `template_etiqueta = '"padrao"'`
  (string JSONB). Para Wave 2 (Componente 06 — Cadastro + Etiqueta) precisamos
  de um JSONB estruturado porque a UI de configuracoes (Componente 09) vai
  permitir editar campos individuais sem rewriting da chave toda:

    {
      "nome": "padrao",
      "formato": "A4",
      "logo_enabled": true,
      "mostrar_data_criacao": false
    }

  - `nome`: identifica o template ativo (compativel com o seed original)
  - `formato`: "A4" ou "80mm_thermal" (impressora termica)
  - `logo_enabled`: renderizar o logo 3Studio na etiqueta
  - `mostrar_data_criacao`: incluir a data de criacao da prova na etiqueta

Idempotente: o WHERE filtra pelo valor string legado, entao roda multiplas
vezes sem efeito quando ja aplicada.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
    UPDATE public.configuracoes_sistema
    SET valor = '{
        "nome": "padrao",
        "formato": "A4",
        "logo_enabled": true,
        "mostrar_data_criacao": false
    }'::jsonb
    WHERE chave = 'template_etiqueta'
      AND jsonb_typeof(valor) = 'string';
    """)


def downgrade() -> None:
    op.execute("""
    UPDATE public.configuracoes_sistema
    SET valor = '"padrao"'::jsonb
    WHERE chave = 'template_etiqueta'
      AND jsonb_typeof(valor) = 'object';
    """)
