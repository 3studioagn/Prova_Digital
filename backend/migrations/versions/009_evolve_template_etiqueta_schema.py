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

╔══════════════════════════════════════════════════════════════════════════╗
║  WARNING — DOWNGRADE LOSSY (F12, auditoria externa Wave 2)               ║
╠══════════════════════════════════════════════════════════════════════════╣
║  O downgrade() reverte TODAS as customizacoes do admin (logo_enabled,    ║
║  mostrar_data_criacao, formato) para a string literal '"padrao"'.        ║
║  Qualquer configuracao customizada via PATCH /api/v1/configuracoes/      ║
║  template_etiqueta sera PERDIDA IRREVERSIVELMENTE.                       ║
║                                                                          ║
║  Isso e intencional porque o schema antigo era apenas uma string — nao   ║
║  ha como representar os 3 flags booleanos + formato em uma string.       ║
║  Nao ha correcao possivel sem introduzir uma tabela de historico.        ║
║                                                                          ║
║  Antes de rodar `alembic downgrade` abaixo da revisao 009:               ║
║    1. Exportar o valor atual:                                            ║
║       `SELECT valor FROM configuracoes_sistema                           ║
║        WHERE chave = 'template_etiqueta';`                               ║
║    2. Salvar em um local externo para restauracao manual posterior.      ║
║    3. Avisar todos os operadores que o template sera resetado.           ║
╚══════════════════════════════════════════════════════════════════════════╝
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
    # F12 (auditoria externa Wave 2): WARNING lossy. Ver bloco no topo do
    # arquivo. O print() abaixo aparece no stdout do `alembic downgrade`
    # como ultimo alerta antes do UPDATE.
    print(
        "\n[WARNING] Migration 009 downgrade: customizacoes do template_etiqueta "
        "(logo_enabled, mostrar_data_criacao, formato) serao PERDIDAS. "
        "Exporte o valor atual antes se precisar preservar.\n"
    )
    op.execute("""
    UPDATE public.configuracoes_sistema
    SET valor = '"padrao"'::jsonb
    WHERE chave = 'template_etiqueta'
      AND jsonb_typeof(valor) = 'object';
    """)
