"""Unit tests para app/domain/schemas/report.py (Wave 5, Componente 16).

Cobre:
  - Construcao basica de cada sub-schema (PeriodoMeta, IndicadoresGeral, etc).
  - Discriminated union resolve corretamente por `scope`.
  - Imutabilidade (frozen=True).
  - Aliases de campo (`from_` <-> `from`).
  - Tipagem de Optional (None permitido onde declarado).
"""
import uuid
from datetime import datetime, timezone

import pytest
from pydantic import TypeAdapter, ValidationError

from app.db.models import LocalizacaoEnum, RotaEnum, StatusProvaEnum
from app.domain.schemas.report import (
    CancelamentoTop,
    DistLocalizacao,
    DistOrigemRota,
    DistRota,
    DistStatus,
    Indicadores3Studio,
    IndicadoresClicheria,
    IndicadoresGeral,
    PeriodoMeta,
    PontoSerie,
    ReportResponse,
    ReportResponse3Studio,
    ReportResponseClicheria,
    ReportResponseGeral,
    ReportResponseVendedores,
    VendedorAtrasoAtual,
    VendedorMetrica,
)

UTC = timezone.utc


# ─── PeriodoMeta ──────────────────────────────────────────────────────────


class TestPeriodoMeta:
    def test_construcao_basica(self):
        p = PeriodoMeta(
            from_=datetime(2026, 4, 1, tzinfo=UTC),
            to=datetime(2026, 4, 27, tzinfo=UTC),
            total_dias=27,
        )
        assert p.from_.day == 1
        assert p.total_dias == 27

    def test_alias_from(self):
        """Aceita `from` como alias para `from_`."""
        p = PeriodoMeta.model_validate(
            {
                "from": datetime(2026, 4, 1, tzinfo=UTC),
                "to": datetime(2026, 4, 27, tzinfo=UTC),
                "total_dias": 27,
            }
        )
        assert p.from_.day == 1

    def test_serializa_com_chave_from(self):
        """Ao serializar com by_alias, campo vira 'from'."""
        p = PeriodoMeta(
            from_=datetime(2026, 4, 1, tzinfo=UTC),
            to=datetime(2026, 4, 27, tzinfo=UTC),
            total_dias=27,
        )
        data = p.model_dump(by_alias=True)
        assert "from" in data
        assert "from_" not in data

    def test_frozen(self):
        p = PeriodoMeta(
            from_=datetime(2026, 4, 1, tzinfo=UTC),
            to=datetime(2026, 4, 27, tzinfo=UTC),
            total_dias=27,
        )
        with pytest.raises(ValidationError):
            p.total_dias = 99  # type: ignore[misc]


# ─── DistStatus / DistRota / DistLocalizacao / DistOrigemRota ─────────────


class TestDistStatus:
    def test_construcao(self):
        d = DistStatus(status=StatusProvaEnum.CRIADA, quantidade=5)
        assert d.quantidade == 5


class TestDistRota:
    def test_padrao(self):
        d = DistRota(rota=RotaEnum.PADRAO, quantidade=10)
        assert d.rota == RotaEnum.PADRAO

    def test_direta(self):
        d = DistRota(rota=RotaEnum.DIRETA, quantidade=3)
        assert d.rota == RotaEnum.DIRETA

    def test_rota_none(self):
        """Provas com rota nao definida (status pre-aprovacao)."""
        d = DistRota(rota=None, quantidade=2)
        assert d.rota is None


class TestDistLocalizacao:
    def test_basico(self):
        d = DistLocalizacao(matriz=10, filial=5)
        assert d.matriz == 10
        assert d.filial == 5


class TestDistOrigemRota:
    def test_basico(self):
        d = DistOrigemRota(via_padrao=10, via_direta=5)
        assert d.via_padrao == 10


# ─── PontoSerie / CancelamentoTop ─────────────────────────────────────────


class TestPontoSerie:
    def test_basico(self):
        p = PontoSerie(data=datetime(2026, 4, 27, tzinfo=UTC), quantidade=3)
        assert p.quantidade == 3


class TestCancelamentoTop:
    def test_basico(self):
        c = CancelamentoTop(motivo="Cliente desistiu", quantidade=2)
        assert c.motivo == "Cliente desistiu"

    def test_motivo_string_vazia_aceito(self):
        """Schema nao impoe obrigatoriedade de motivo nao-vazio (validacao no
        endpoint, dado que pode haver historico)."""
        c = CancelamentoTop(motivo="", quantidade=1)
        assert c.motivo == ""


# ─── IndicadoresGeral ─────────────────────────────────────────────────────


class TestIndicadoresGeral:
    def _basico(self):
        return IndicadoresGeral(
            total_provas=10,
            tempo_medio_ciclo_horas=24.5,
            tempo_mediano_ciclo_horas=20.0,
            tempo_medio_aprovacao_horas=4.5,
            taxa_reprovacao=0.15,
            qtd_atrasadas=2,
        )

    def test_construcao(self):
        ind = self._basico()
        assert ind.total_provas == 10
        assert ind.taxa_reprovacao == 0.15

    def test_tempos_none_aceitos(self):
        """Quando nao ha dado, campos de tempo sao None."""
        ind = IndicadoresGeral(
            total_provas=0,
            tempo_medio_ciclo_horas=None,
            tempo_mediano_ciclo_horas=None,
            tempo_medio_aprovacao_horas=None,
            taxa_reprovacao=0.0,
            qtd_atrasadas=0,
        )
        assert ind.tempo_medio_ciclo_horas is None


# ─── Indicadores3Studio ───────────────────────────────────────────────────


class TestIndicadores3Studio:
    def test_basico(self):
        ind = Indicadores3Studio(
            provas_criadas=20,
            media_diaria_criacao=0.67,
            reinicios_de_ciclo=2,
            devolvidas_motorista=8,
            reprovadas_aguardando_acao=1,
            cancelamentos=3,
            tempo_medio_criacao_ate_primeira_mov_horas=2.3,
        )
        assert ind.reinicios_de_ciclo == 2

    def test_tempo_none_aceito(self):
        ind = Indicadores3Studio(
            provas_criadas=0,
            media_diaria_criacao=0.0,
            reinicios_de_ciclo=0,
            devolvidas_motorista=0,
            reprovadas_aguardando_acao=0,
            cancelamentos=0,
            tempo_medio_criacao_ate_primeira_mov_horas=None,
        )
        assert ind.tempo_medio_criacao_ate_primeira_mov_horas is None


# ─── VendedorMetrica / VendedorAtrasoAtual ────────────────────────────────


class TestVendedorMetrica:
    def test_basico(self):
        m = VendedorMetrica(
            vendedor_id=uuid.uuid4(),
            vendedor_nome="Joao",
            localizacao=LocalizacaoEnum.MATRIZ,
            volume=10,
            taxa_aprovacao=0.8,
            taxa_reprovacao=0.2,
            tempo_medio_retirada_a_decisao_horas=5.5,
            provas_atrasadas_em_poder=1,
        )
        assert m.localizacao == LocalizacaoEnum.MATRIZ
        assert m.volume == 10

    def test_tempo_none_aceito(self):
        m = VendedorMetrica(
            vendedor_id=uuid.uuid4(),
            vendedor_nome="Joao",
            localizacao=LocalizacaoEnum.FILIAL,
            volume=0,
            taxa_aprovacao=0.0,
            taxa_reprovacao=0.0,
            tempo_medio_retirada_a_decisao_horas=None,
            provas_atrasadas_em_poder=0,
        )
        assert m.tempo_medio_retirada_a_decisao_horas is None


class TestVendedorAtrasoAtual:
    def test_basico(self):
        v = VendedorAtrasoAtual(
            vendedor_id=uuid.uuid4(),
            vendedor_nome="Maria",
            localizacao=LocalizacaoEnum.FILIAL,
            qtd_atrasadas=3,
        )
        assert v.qtd_atrasadas == 3


# ─── IndicadoresClicheria ─────────────────────────────────────────────────


class TestIndicadoresClicheria:
    def test_basico(self):
        ind = IndicadoresClicheria(
            recebidas_no_periodo=15,
            tempo_medio_aguardando_recebimento_horas=12.5,
            em_transito_atual=3,
            por_origem_rota=DistOrigemRota(via_padrao=10, via_direta=5),
        )
        assert ind.recebidas_no_periodo == 15
        assert ind.por_origem_rota.via_padrao == 10


# ─── ReportResponseGeral ──────────────────────────────────────────────────


class TestReportResponseGeral:
    def _periodo(self):
        return PeriodoMeta(
            from_=datetime(2026, 4, 1, tzinfo=UTC),
            to=datetime(2026, 4, 27, tzinfo=UTC),
            total_dias=27,
        )

    def _indicadores(self):
        return IndicadoresGeral(
            total_provas=10,
            tempo_medio_ciclo_horas=24.0,
            tempo_mediano_ciclo_horas=20.0,
            tempo_medio_aprovacao_horas=4.0,
            taxa_reprovacao=0.1,
            qtd_atrasadas=1,
        )

    def test_construcao_default_scope(self):
        """Campo `scope` tem default 'geral'."""
        r = ReportResponseGeral(
            periodo=self._periodo(),
            indicadores=self._indicadores(),
            serie_temporal=[],
            distribuicao_status=[],
            distribuicao_rota=[],
            atualizado_em=datetime.now(UTC),
        )
        assert r.scope == "geral"

    def test_aceita_listas_vazias(self):
        r = ReportResponseGeral(
            periodo=self._periodo(),
            indicadores=self._indicadores(),
            serie_temporal=[],
            distribuicao_status=[],
            distribuicao_rota=[],
            atualizado_em=datetime.now(UTC),
        )
        assert r.serie_temporal == []

    def test_aceita_listas_populadas(self):
        r = ReportResponseGeral(
            periodo=self._periodo(),
            indicadores=self._indicadores(),
            serie_temporal=[
                PontoSerie(data=datetime(2026, 4, 1, tzinfo=UTC), quantidade=3)
            ],
            distribuicao_status=[
                DistStatus(status=StatusProvaEnum.CRIADA, quantidade=2)
            ],
            distribuicao_rota=[DistRota(rota=RotaEnum.PADRAO, quantidade=8)],
            atualizado_em=datetime.now(UTC),
        )
        assert len(r.serie_temporal) == 1
        assert r.distribuicao_rota[0].rota == RotaEnum.PADRAO


# ─── ReportResponse3Studio / Vendedores / Clicheria ──────────────────────


class TestOutrasResposta:
    def _periodo(self):
        return PeriodoMeta(
            from_=datetime(2026, 4, 1, tzinfo=UTC),
            to=datetime(2026, 4, 27, tzinfo=UTC),
            total_dias=27,
        )

    def test_3studio_scope_default(self):
        r = ReportResponse3Studio(
            periodo=self._periodo(),
            indicadores=Indicadores3Studio(
                provas_criadas=10,
                media_diaria_criacao=0.37,
                reinicios_de_ciclo=1,
                devolvidas_motorista=3,
                reprovadas_aguardando_acao=2,
                cancelamentos=1,
                tempo_medio_criacao_ate_primeira_mov_horas=3.0,
            ),
            cancelamentos_top=[],
            atualizado_em=datetime.now(UTC),
        )
        assert r.scope == "3studio"

    def test_vendedores_scope_default(self):
        r = ReportResponseVendedores(
            periodo=self._periodo(),
            ranking=[],
            distribuicao_localizacao=DistLocalizacao(matriz=0, filial=0),
            atrasadas_em_poder=[],
            atualizado_em=datetime.now(UTC),
        )
        assert r.scope == "vendedores"

    def test_clicheria_scope_default(self):
        r = ReportResponseClicheria(
            periodo=self._periodo(),
            indicadores=IndicadoresClicheria(
                recebidas_no_periodo=0,
                tempo_medio_aguardando_recebimento_horas=None,
                em_transito_atual=0,
                por_origem_rota=DistOrigemRota(via_padrao=0, via_direta=0),
            ),
            atualizado_em=datetime.now(UTC),
        )
        assert r.scope == "clicheria"


# ─── Discriminated union ──────────────────────────────────────────────────


class TestDiscriminatedUnion:
    """Pydantic deve resolver automaticamente o sub-modelo certo via `scope`."""

    def _periodo_dict(self):
        return {
            "from": "2026-04-01T00:00:00+00:00",
            "to": "2026-04-27T00:00:00+00:00",
            "total_dias": 27,
        }

    def test_resolve_geral(self):
        adapter = TypeAdapter(ReportResponse)
        data = {
            "scope": "geral",
            "periodo": self._periodo_dict(),
            "indicadores": {
                "total_provas": 0,
                "tempo_medio_ciclo_horas": None,
                "tempo_mediano_ciclo_horas": None,
                "tempo_medio_aprovacao_horas": None,
                "taxa_reprovacao": 0.0,
                "qtd_atrasadas": 0,
            },
            "serie_temporal": [],
            "distribuicao_status": [],
            "distribuicao_rota": [],
            "atualizado_em": "2026-04-27T10:00:00+00:00",
        }
        r = adapter.validate_python(data)
        assert isinstance(r, ReportResponseGeral)
        assert r.scope == "geral"

    def test_resolve_3studio(self):
        adapter = TypeAdapter(ReportResponse)
        data = {
            "scope": "3studio",
            "periodo": self._periodo_dict(),
            "indicadores": {
                "provas_criadas": 0,
                "media_diaria_criacao": 0.0,
                "reinicios_de_ciclo": 0,
                "devolvidas_motorista": 0,
                "reprovadas_aguardando_acao": 0,
                "cancelamentos": 0,
                "tempo_medio_criacao_ate_primeira_mov_horas": None,
            },
            "cancelamentos_top": [],
            "atualizado_em": "2026-04-27T10:00:00+00:00",
        }
        r = adapter.validate_python(data)
        assert isinstance(r, ReportResponse3Studio)

    def test_resolve_vendedores(self):
        adapter = TypeAdapter(ReportResponse)
        data = {
            "scope": "vendedores",
            "periodo": self._periodo_dict(),
            "ranking": [],
            "distribuicao_localizacao": {"matriz": 0, "filial": 0},
            "atrasadas_em_poder": [],
            "atualizado_em": "2026-04-27T10:00:00+00:00",
        }
        r = adapter.validate_python(data)
        assert isinstance(r, ReportResponseVendedores)

    def test_resolve_clicheria(self):
        adapter = TypeAdapter(ReportResponse)
        data = {
            "scope": "clicheria",
            "periodo": self._periodo_dict(),
            "indicadores": {
                "recebidas_no_periodo": 0,
                "tempo_medio_aguardando_recebimento_horas": None,
                "em_transito_atual": 0,
                "por_origem_rota": {"via_padrao": 0, "via_direta": 0},
            },
            "atualizado_em": "2026-04-27T10:00:00+00:00",
        }
        r = adapter.validate_python(data)
        assert isinstance(r, ReportResponseClicheria)

    def test_scope_invalido_rejeitado(self):
        adapter = TypeAdapter(ReportResponse)
        with pytest.raises(ValidationError):
            adapter.validate_python({"scope": "invalid"})

    def test_campos_de_outro_scope_rejeitados(self):
        """Pydantic deve aplicar o sub-schema certo e rejeitar shape errado."""
        adapter = TypeAdapter(ReportResponse)
        # scope='geral' mas faltam campos obrigatorios de Geral
        with pytest.raises(ValidationError):
            adapter.validate_python({"scope": "geral"})
