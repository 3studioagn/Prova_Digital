"""Unit tests para app/services/report_filters.py (Wave 5, Componente 16).

Cobre:
  - Validacao Pydantic de cada campo (scope, from, to, q, vendedor_id, rota, status).
  - Defaults (janela 30 dias).
  - Invariantes (from < to, range <= 366 dias, q max 200 chars).
  - Cache key deterministico (filtros equivalentes => mesma chave).
  - Conversao tz-aware automatica de datas naive.
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.db.models import RotaEnum, StatusProvaEnum
from app.services.report_filters import (
    DEFAULT_PERIOD_DAYS,
    MAX_PERIOD_DAYS,
    MAX_Q_LENGTH,
    ReportFilters,
    filters_equivalent,
    to_cache_key,
)

UTC = timezone.utc


# ─── Construcao basica ─────────────────────────────────────────────────────


class TestReportFiltersConstrucao:
    def test_minimo_apenas_scope(self):
        f = ReportFilters(scope="geral")
        assert f.scope == "geral"
        # Defaults: to = now, from = now - 30d
        assert f.to is not None
        assert f.from_ is not None
        assert (f.to - f.from_) == timedelta(days=DEFAULT_PERIOD_DAYS)

    def test_aceita_todos_os_4_scopes(self):
        for scope in ("geral", "3studio", "vendedores", "clicheria"):
            f = ReportFilters(scope=scope)
            assert f.scope == scope

    def test_scope_invalido_rejeitado(self):
        with pytest.raises(ValidationError):
            ReportFilters(scope="invalid")  # type: ignore[arg-type]

    def test_alias_from_funciona(self):
        """Pydantic aceita 'from' como alias (chave reservada em Python)."""
        from_dt = datetime(2026, 4, 1, tzinfo=UTC)
        to_dt = datetime(2026, 4, 27, tzinfo=UTC)
        f = ReportFilters.model_validate(
            {"scope": "geral", "from": from_dt, "to": to_dt}
        )
        assert f.from_ == from_dt
        assert f.to == to_dt

    def test_atributo_from_funciona(self):
        """Pelo nome da variavel (from_) tambem funciona via populate_by_name."""
        from_dt = datetime(2026, 4, 1, tzinfo=UTC)
        f = ReportFilters(scope="geral", from_=from_dt)  # type: ignore[call-arg]
        assert f.from_ == from_dt


# ─── Defaults e tz-aware ───────────────────────────────────────────────────


class TestReportFiltersDefaults:
    def test_to_default_eh_now(self):
        before = datetime.now(UTC)
        f = ReportFilters(scope="geral")
        after = datetime.now(UTC)
        assert before <= f.to <= after

    def test_from_default_eh_to_menos_30_dias(self):
        f = ReportFilters(scope="geral")
        assert (f.to - f.from_) == timedelta(days=DEFAULT_PERIOD_DAYS)

    def test_from_naive_vira_tz_aware_utc(self):
        naive = datetime(2026, 4, 1, 10, 0)  # sem tzinfo
        f = ReportFilters.model_validate(
            {"scope": "geral", "from": naive, "to": datetime(2026, 4, 27, tzinfo=UTC)}
        )
        assert f.from_.tzinfo == UTC
        assert f.from_.replace(tzinfo=None) == naive

    def test_to_naive_vira_tz_aware_utc(self):
        naive = datetime(2026, 4, 27, 10, 0)
        f = ReportFilters.model_validate(
            {"scope": "geral", "from": datetime(2026, 4, 1, tzinfo=UTC), "to": naive}
        )
        assert f.to.tzinfo == UTC


# ─── Invariantes ───────────────────────────────────────────────────────────


class TestReportFiltersInvariantes:
    def test_from_igual_to_rejeitado(self):
        ts = datetime(2026, 4, 27, tzinfo=UTC)
        with pytest.raises(ValidationError, match="anterior"):
            ReportFilters.model_validate(
                {"scope": "geral", "from": ts, "to": ts}
            )

    def test_from_maior_que_to_rejeitado(self):
        with pytest.raises(ValidationError, match="anterior"):
            ReportFilters.model_validate(
                {
                    "scope": "geral",
                    "from": datetime(2026, 4, 28, tzinfo=UTC),
                    "to": datetime(2026, 4, 27, tzinfo=UTC),
                }
            )

    def test_range_acima_de_366_dias_rejeitado(self):
        from_dt = datetime(2025, 1, 1, tzinfo=UTC)
        to_dt = from_dt + timedelta(days=MAX_PERIOD_DAYS + 1)
        with pytest.raises(ValidationError, match=f"{MAX_PERIOD_DAYS} dias"):
            ReportFilters.model_validate(
                {"scope": "geral", "from": from_dt, "to": to_dt}
            )

    def test_range_exato_366_dias_aceito(self):
        from_dt = datetime(2025, 1, 1, tzinfo=UTC)
        to_dt = from_dt + timedelta(days=MAX_PERIOD_DAYS)
        f = ReportFilters.model_validate(
            {"scope": "geral", "from": from_dt, "to": to_dt}
        )
        assert (f.to - f.from_) == timedelta(days=MAX_PERIOD_DAYS)


# ─── Campo q (busca) ───────────────────────────────────────────────────────


class TestReportFiltersQ:
    def test_q_simples(self):
        f = ReportFilters(scope="geral", q="ACME")
        assert f.q == "ACME"

    def test_q_com_espacos_strip(self):
        f = ReportFilters(scope="geral", q="  ACME  ")
        assert f.q == "ACME"

    def test_q_so_espacos_vira_none(self):
        f = ReportFilters(scope="geral", q="   ")
        assert f.q is None

    def test_q_vazio_vira_none(self):
        f = ReportFilters(scope="geral", q="")
        assert f.q is None

    def test_q_max_length_aceita(self):
        f = ReportFilters(scope="geral", q="x" * MAX_Q_LENGTH)
        assert len(f.q) == MAX_Q_LENGTH

    def test_q_acima_max_length_rejeitado(self):
        with pytest.raises(ValidationError):
            ReportFilters(scope="geral", q="x" * (MAX_Q_LENGTH + 1))


# ─── Filtros opcionais ─────────────────────────────────────────────────────


class TestReportFiltersOpcionais:
    def test_vendedor_id_uuid_aceito(self):
        vid = uuid.uuid4()
        f = ReportFilters(scope="vendedores", vendedor_id=vid)
        assert f.vendedor_id == vid

    def test_vendedor_id_string_aceito(self):
        """Pydantic v2 deserializa string UUID automaticamente."""
        vid = uuid.uuid4()
        f = ReportFilters.model_validate(
            {"scope": "vendedores", "vendedor_id": str(vid)}
        )
        assert f.vendedor_id == vid

    def test_vendedor_id_invalido_rejeitado(self):
        with pytest.raises(ValidationError):
            ReportFilters.model_validate(
                {"scope": "vendedores", "vendedor_id": "not-a-uuid"}
            )

    def test_rota_padrao(self):
        f = ReportFilters(scope="geral", rota=RotaEnum.PADRAO)
        assert f.rota == RotaEnum.PADRAO

    def test_rota_direta(self):
        f = ReportFilters(scope="geral", rota=RotaEnum.DIRETA)
        assert f.rota == RotaEnum.DIRETA

    def test_status(self):
        f = ReportFilters(scope="geral", status=StatusProvaEnum.CRIADA)
        assert f.status == StatusProvaEnum.CRIADA


# ─── total_dias property ───────────────────────────────────────────────────


class TestReportFiltersTotalDias:
    def test_30_dias_default(self):
        f = ReportFilters(scope="geral")
        # `now()` exato pode dar 30 ou 31 dependendo de quando rodar
        # pq from_ = now - 30d; total_dias arredonda up
        assert f.total_dias in (30, 31)

    def test_7_dias_exatos(self):
        from_dt = datetime(2026, 4, 20, 0, 0, tzinfo=UTC)
        to_dt = datetime(2026, 4, 27, 0, 0, tzinfo=UTC)
        f = ReportFilters.model_validate(
            {"scope": "geral", "from": from_dt, "to": to_dt}
        )
        assert f.total_dias == 7

    def test_minutos_round_up_para_1(self):
        from_dt = datetime(2026, 4, 27, 10, 0, tzinfo=UTC)
        to_dt = datetime(2026, 4, 27, 10, 30, tzinfo=UTC)
        f = ReportFilters.model_validate(
            {"scope": "geral", "from": from_dt, "to": to_dt}
        )
        assert f.total_dias == 1


# ─── Imutabilidade ─────────────────────────────────────────────────────────


class TestReportFiltersImutavel:
    def test_frozen(self):
        f = ReportFilters(scope="geral")
        with pytest.raises((ValidationError, AttributeError, TypeError)):
            f.scope = "vendedores"  # type: ignore[misc]


# ─── to_cache_key — determinismo ──────────────────────────────────────────


class TestCacheKey:
    def test_chave_64_chars_hex(self):
        f = ReportFilters(scope="geral")
        key = to_cache_key(f)
        assert len(key) == 64
        assert all(c in "0123456789abcdef" for c in key)

    def test_filtros_iguais_chaves_iguais(self):
        from_dt = datetime(2026, 4, 1, tzinfo=UTC)
        to_dt = datetime(2026, 4, 27, tzinfo=UTC)
        a = ReportFilters.model_validate(
            {"scope": "geral", "from": from_dt, "to": to_dt}
        )
        b = ReportFilters.model_validate(
            {"scope": "geral", "from": from_dt, "to": to_dt}
        )
        assert to_cache_key(a) == to_cache_key(b)

    def test_filtros_diferentes_chaves_diferentes(self):
        a = ReportFilters(scope="geral")
        b = ReportFilters(scope="3studio")
        assert to_cache_key(a) != to_cache_key(b)

    def test_q_afeta_chave(self):
        from_dt = datetime(2026, 4, 1, tzinfo=UTC)
        to_dt = datetime(2026, 4, 27, tzinfo=UTC)
        a = ReportFilters.model_validate(
            {"scope": "geral", "from": from_dt, "to": to_dt}
        )
        b = ReportFilters.model_validate(
            {"scope": "geral", "from": from_dt, "to": to_dt, "q": "ACME"}
        )
        assert to_cache_key(a) != to_cache_key(b)

    def test_vendedor_id_afeta_chave(self):
        from_dt = datetime(2026, 4, 1, tzinfo=UTC)
        to_dt = datetime(2026, 4, 27, tzinfo=UTC)
        vid = uuid.uuid4()
        a = ReportFilters.model_validate(
            {"scope": "vendedores", "from": from_dt, "to": to_dt}
        )
        b = ReportFilters.model_validate(
            {
                "scope": "vendedores",
                "from": from_dt,
                "to": to_dt,
                "vendedor_id": str(vid),
            }
        )
        assert to_cache_key(a) != to_cache_key(b)

    def test_q_normalizado_mesma_chave(self):
        """`q='  ACME  '` e `q='ACME'` => mesma chave (apos strip)."""
        from_dt = datetime(2026, 4, 1, tzinfo=UTC)
        to_dt = datetime(2026, 4, 27, tzinfo=UTC)
        a = ReportFilters.model_validate(
            {"scope": "geral", "from": from_dt, "to": to_dt, "q": "  ACME  "}
        )
        b = ReportFilters.model_validate(
            {"scope": "geral", "from": from_dt, "to": to_dt, "q": "ACME"}
        )
        assert to_cache_key(a) == to_cache_key(b)

    def test_filters_equivalent_helper(self):
        a = ReportFilters(scope="geral")
        b = ReportFilters.model_validate(
            {"scope": "geral", "from": a.from_, "to": a.to}
        )
        assert filters_equivalent(a, b)


# ─── Edge cases extras ────────────────────────────────────────────────────


class TestReportFiltersEdgeCases:
    def test_q_com_caracteres_especiais_preservados(self):
        f = ReportFilters(scope="geral", q="Cliente/2026 #99 (urgent!)")
        assert f.q == "Cliente/2026 #99 (urgent!)"

    def test_q_unicode(self):
        f = ReportFilters(scope="geral", q="acentuação")
        assert f.q == "acentuação"

    def test_serializacao_json_round_trip(self):
        """Modelo serializa e desserializa sem perder informacao."""
        original = ReportFilters(
            scope="vendedores",
            from_=datetime(2026, 4, 1, tzinfo=UTC),
            to=datetime(2026, 4, 27, tzinfo=UTC),
            q="test",
            vendedor_id=uuid.uuid4(),
            rota=RotaEnum.PADRAO,
        )
        as_json = original.model_dump_json(by_alias=True)
        restored = ReportFilters.model_validate_json(as_json)
        assert to_cache_key(original) == to_cache_key(restored)
