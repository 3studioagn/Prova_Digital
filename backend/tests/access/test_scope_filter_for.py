"""Testes do helper scope_filter_for (Wave 1 v4.0).

Garantias:
- FULL  -> retorna None (sem WHERE adicional).
- NEGADO -> retorna sqlalchemy.false() (defensivo, 0 linhas).
- PARCIAL self_vendedor -> ProvaDigital.vendedor_id == user.id.
- PARCIAL status_motorista_em_transito -> ProvaDigital.status IN (COM_MOTORISTA,).
- PARCIAL status_clicheria -> ProvaDigital.status IN (3 status clicheria).

Comparamos via str(clause.compile(...)) — comparacao estrutural seria
fragil. Suficiente para garantir que a clausula correta foi gerada.
"""
from sqlalchemy.dialects import postgresql

from app.access import scope_filter_for
from app.db.models import LocalizacaoEnum, SetorEnum
from tests.conftest import make_user


def _compile(clause) -> str:
    """Renderiza a clausula como SQL para comparacao."""
    return str(
        clause.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )


class TestScopeFilterFor:
    def test_admin_provas_list_returns_none(self):
        admin = make_user(setor=SetorEnum.STUDIO, is_admin=True)
        assert scope_filter_for("provas.list", admin) is None

    def test_clicheria_provas_list_filters_by_status_clicheria(self):
        """Clicheria PARCIAL com scope status_clicheria — comportamento v3.0
        preservado (ver _clicheria_divergence_note em access-matrix.json)."""
        cl = make_user(setor=SetorEnum.CLICHERIA, is_admin=False)
        clause = scope_filter_for("provas.list", cl)
        assert clause is not None
        sql = _compile(clause)
        assert "status" in sql
        for s in ("ENVIADA_PARA_CLICHERIA", "ENCAMINHADA_A_CLICHERIA", "RECEBIDA_PELA_CLICHERIA"):
            assert s in sql, f"esperado '{s}' na clausula clicheria, sql={sql}"

    def test_vendedor_provas_list_filters_by_self(self):
        v = make_user(
            setor=SetorEnum.VENDEDOR,
            localizacao=LocalizacaoEnum.MATRIZ,
            is_admin=False,
        )
        clause = scope_filter_for("provas.list", v)
        assert clause is not None
        sql = _compile(clause)
        assert "vendedor_id" in sql
        assert str(v.id) in sql

    def test_motorista_provas_list_filters_by_status_em_transito(self):
        m = make_user(setor=SetorEnum.MOTORISTA, is_admin=False)
        clause = scope_filter_for("provas.list", m)
        assert clause is not None
        sql = _compile(clause)
        assert "status" in sql
        assert "COM_MOTORISTA" in sql

    def test_motorista_provas_list_inclui_3_contextos_v4(self):
        """AUD-W3C11-001 (pos-auditoria): defesa primaria motorista
        cobre os 3 contextos v4.0 (RN-006 v4.0 / Matriz Secao 5)
        alem do COM_MOTORISTA legacy.

        Antes do C11 audit fix: scope so cobria COM_MOTORISTA v3.0 — provas
        v4.0 em estados de motorista retornavam 0 linhas para o usuario."""
        m = make_user(setor=SetorEnum.MOTORISTA, is_admin=False)
        clause = scope_filter_for("provas.list", m)
        assert clause is not None
        sql = _compile(clause)
        for estado in (
            "COM_MOTORISTA",
            "COM_MOTORISTA_IDA_LAMINACAO",
            "COM_MOTORISTA_VOLTA_LAMINACAO",
            "COM_MOTORISTA_ENTREGA_FINAL",
        ):
            assert f"'{estado}'" in sql, (
                f"esperado literal '{estado}' na clausula motorista, sql={sql}"
            )

    def test_clicheria_provas_list_inclui_4_estados_v4(self):
        """AUD-W3C11-002 (pos-auditoria): defesa primaria clicheria
        cobre os 4 estados v4.0 (US-007 v4.0 + ultima transicao
        Matriz/Lam.Matriz) alem dos 3 v3.0.

        Cenario critico: clicheria escaneando prova v4.0 em
        COM_MOTORISTA_ENTREGA_FINAL para confirmar recebimento (ultima
        transicao das rotas Matriz e Lam.Matriz). Antes do fix: 0 linhas."""
        cl = make_user(setor=SetorEnum.CLICHERIA, is_admin=False)
        clause = scope_filter_for("provas.list", cl)
        assert clause is not None
        sql = _compile(clause)
        for estado in (
            # Legacy v3.0
            "ENVIADA_PARA_CLICHERIA",
            "ENCAMINHADA_A_CLICHERIA",
            "RECEBIDA_PELA_CLICHERIA",
            # v4.0 — laminacao (US-007)
            "ENCAMINHADA_PARA_LAMINACAO",
            "COM_MOTORISTA_IDA_LAMINACAO",
            "LAMINACAO_CONCLUIDA",
            # v4.0 — entrega final (Matriz / Lam.Matriz)
            "COM_MOTORISTA_ENTREGA_FINAL",
        ):
            assert f"'{estado}'" in sql, (
                f"esperado literal '{estado}' na clausula clicheria, sql={sql}"
            )

    def test_motorista_provas_detail_inclui_3_contextos_v4(self):
        """Espelho do test_motorista_provas_list para provas.detail —
        scoping de detalhe usa o mesmo helper, mesma cobertura esperada."""
        m = make_user(setor=SetorEnum.MOTORISTA, is_admin=False)
        clause = scope_filter_for("provas.detail", m)
        assert clause is not None
        sql = _compile(clause)
        for estado in (
            "COM_MOTORISTA_IDA_LAMINACAO",
            "COM_MOTORISTA_VOLTA_LAMINACAO",
            "COM_MOTORISTA_ENTREGA_FINAL",
        ):
            assert f"'{estado}'" in sql

    def test_clicheria_provas_detail_inclui_4_estados_v4(self):
        """Espelho do test_clicheria_provas_list para provas.detail."""
        cl = make_user(setor=SetorEnum.CLICHERIA, is_admin=False)
        clause = scope_filter_for("provas.detail", cl)
        assert clause is not None
        sql = _compile(clause)
        for estado in (
            "ENCAMINHADA_PARA_LAMINACAO",
            "COM_MOTORISTA_IDA_LAMINACAO",
            "LAMINACAO_CONCLUIDA",
            "COM_MOTORISTA_ENTREGA_FINAL",
        ):
            assert f"'{estado}'" in sql

    def test_admin_only_rule_returns_false_for_vendedor(self):
        """Se enforce_access_for e' bypassed (bug), scope_filter_for retorna
        false() defensivamente -> WHERE false -> 0 linhas."""
        v = make_user(
            setor=SetorEnum.VENDEDOR,
            localizacao=LocalizacaoEnum.MATRIZ,
            is_admin=False,
        )
        clause = scope_filter_for("auditoria", v)
        assert clause is not None
        sql = _compile(clause).lower()
        assert "false" in sql

    def test_unknown_rule_returns_false(self):
        admin = make_user(setor=SetorEnum.STUDIO, is_admin=True)
        clause = scope_filter_for("rule.does.not.exist", admin)
        assert clause is not None
        sql = _compile(clause).lower()
        assert "false" in sql

    def test_unmapped_user_provas_list_returns_false(self):
        """STUDIO sem admin -> profile None -> NEGADO -> false()."""
        u = make_user(setor=SetorEnum.STUDIO, is_admin=False)
        clause = scope_filter_for("provas.list", u)
        assert clause is not None
        assert "false" in _compile(clause).lower()
