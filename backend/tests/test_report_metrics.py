"""Unit tests para app/services/report_metrics.py (Wave 5, Componente 16).

Funcoes puras testadas isoladamente, sem fixtures de banco. Cada teste
documenta o cenario e a asserção esperada.

Cobertura alvo: 100% (modulo e pure function).
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.services.report_metrics import (
    SECONDS_PER_HOUR,
    arredondar_horas,
    assert_utc,
    calcular_total_dias,
    horas_corridas,
    limite_atraso,
    media_diaria,
    media_horas,
    mediana_horas,
    taxa,
)

UTC = timezone.utc


# ─── horas_corridas ───────────────────────────────────────────────────────


class TestHorasCorridas:
    def test_uma_hora_exata(self):
        start = datetime(2026, 4, 27, 10, 0, tzinfo=UTC)
        end = datetime(2026, 4, 27, 11, 0, tzinfo=UTC)
        assert horas_corridas(start, end) == 1.0

    def test_meia_hora(self):
        start = datetime(2026, 4, 27, 10, 0, tzinfo=UTC)
        end = datetime(2026, 4, 27, 10, 30, tzinfo=UTC)
        assert horas_corridas(start, end) == 0.5

    def test_zero_quando_iguais(self):
        ts = datetime(2026, 4, 27, 10, 0, tzinfo=UTC)
        assert horas_corridas(ts, ts) == 0.0

    def test_negativo_quando_invertidos(self):
        """Funcao nao valida ordem — caller responsavel."""
        start = datetime(2026, 4, 27, 11, 0, tzinfo=UTC)
        end = datetime(2026, 4, 27, 10, 0, tzinfo=UTC)
        assert horas_corridas(start, end) == -1.0

    def test_atravessa_dia(self):
        start = datetime(2026, 4, 27, 23, 0, tzinfo=UTC)
        end = datetime(2026, 4, 28, 1, 30, tzinfo=UTC)
        assert horas_corridas(start, end) == 2.5

    def test_seconds_per_hour_constant(self):
        assert SECONDS_PER_HOUR == 3600.0


# ─── media_horas ──────────────────────────────────────────────────────────


class TestMediaHoras:
    def test_lista_vazia_retorna_none(self):
        assert media_horas([]) is None

    def test_um_valor_retorna_ele_proprio(self):
        # 7200s = 2 horas
        assert media_horas([7200.0]) == 2.0

    def test_multiplos_valores(self):
        # 3600 (1h) + 7200 (2h) + 10800 (3h) = 21600 / 3 = 7200 = 2h
        assert media_horas([3600.0, 7200.0, 10800.0]) == 2.0

    def test_iterator_consumido(self):
        """Aceita generator (consumido 1x)."""
        gen = (s for s in [3600.0, 7200.0])
        assert media_horas(gen) == 1.5

    def test_zeros(self):
        assert media_horas([0.0, 0.0, 0.0]) == 0.0

    def test_precisao_float(self):
        # 3600 + 1800 + 1800 = 7200 / 3 = 2400 = 0.6666...h
        result = media_horas([3600.0, 1800.0, 1800.0])
        assert result is not None
        assert abs(result - (2400.0 / 3600.0)) < 1e-9


# ─── mediana_horas ────────────────────────────────────────────────────────


class TestMedianaHoras:
    def test_lista_vazia(self):
        assert mediana_horas([]) is None

    def test_um_valor(self):
        assert mediana_horas([3600.0]) == 1.0

    def test_impar(self):
        # [1h, 2h, 5h] -> mediana 2h
        assert mediana_horas([3600.0, 7200.0, 18000.0]) == 2.0

    def test_par(self):
        # [1h, 2h, 3h, 10h] -> mediana (2+3)/2 = 2.5h
        assert mediana_horas([3600.0, 7200.0, 10800.0, 36000.0]) == 2.5

    def test_resistente_a_outlier(self):
        """Diferentemente da media, mediana ignora outlier."""
        # Media seria distorcida; mediana = 2h
        valores = [3600.0, 7200.0, 10800.0, 360000.0]  # ultimo = 100h
        assert mediana_horas(valores) == (7200.0 + 10800.0) / 2 / 3600.0


# ─── taxa ─────────────────────────────────────────────────────────────────


class TestTaxa:
    def test_metade(self):
        assert taxa(5, 10) == 0.5

    def test_zero_de_zero(self):
        """Denominador zero retorna 0.0 (nao crash)."""
        assert taxa(0, 0) == 0.0

    def test_zero_no_numerador(self):
        assert taxa(0, 100) == 0.0

    def test_completo(self):
        assert taxa(100, 100) == 1.0

    def test_denominador_negativo_retorna_zero(self):
        """Defesa: denominador <= 0 sempre 0.0."""
        assert taxa(5, -1) == 0.0

    def test_clamp_inferior(self):
        """Numerador negativo seria invalido, mas clampamos."""
        assert taxa(-5, 10) == 0.0

    def test_clamp_superior(self):
        """Numerador > denominador clampa em 1.0."""
        assert taxa(15, 10) == 1.0


# ─── media_diaria ─────────────────────────────────────────────────────────


class TestMediaDiaria:
    def test_basico(self):
        # 30 provas em 30 dias = 1.0/dia
        assert media_diaria(30, 30) == 1.0

    def test_arredondamento_2_casas(self):
        # 10 provas em 7 dias = 1.4285714... -> 1.43
        assert media_diaria(10, 7) == 1.43

    def test_zero_dias(self):
        assert media_diaria(10, 0) == 0.0

    def test_dias_negativos(self):
        assert media_diaria(10, -1) == 0.0

    def test_zero_provas(self):
        assert media_diaria(0, 30) == 0.0


# ─── limite_atraso ────────────────────────────────────────────────────────


class TestLimiteAtraso:
    def test_subtrai_horas(self):
        now = datetime(2026, 4, 27, 12, 0, tzinfo=UTC)
        result = limite_atraso(now, 48)
        assert result == datetime(2026, 4, 25, 12, 0, tzinfo=UTC)

    def test_zero_horas(self):
        now = datetime(2026, 4, 27, 12, 0, tzinfo=UTC)
        assert limite_atraso(now, 0) == now

    def test_horas_negativas_levanta(self):
        now = datetime(2026, 4, 27, 12, 0, tzinfo=UTC)
        with pytest.raises(ValueError, match="negativo"):
            limite_atraso(now, -1)

    def test_preserva_timezone(self):
        now = datetime(2026, 4, 27, 12, 0, tzinfo=UTC)
        result = limite_atraso(now, 24)
        assert result.tzinfo == UTC


# ─── calcular_total_dias ──────────────────────────────────────────────────


class TestCalcularTotalDias:
    def test_um_dia_exato(self):
        from_ = datetime(2026, 4, 27, 0, 0, tzinfo=UTC)
        to = datetime(2026, 4, 28, 0, 0, tzinfo=UTC)
        assert calcular_total_dias(from_, to) == 1

    def test_meio_dia_arredonda_para_1(self):
        """Janelas curtas (< 1 dia) sao 1 dia (round up). Min absoluto = 1."""
        from_ = datetime(2026, 4, 27, 0, 0, tzinfo=UTC)
        to = datetime(2026, 4, 27, 12, 0, tzinfo=UTC)
        assert calcular_total_dias(from_, to) == 1

    def test_30_dias(self):
        from_ = datetime(2026, 3, 28, 0, 0, tzinfo=UTC)
        to = datetime(2026, 4, 27, 0, 0, tzinfo=UTC)
        assert calcular_total_dias(from_, to) == 30

    def test_invertido_retorna_1(self):
        """to <= from_ retorna 1 (nao crash)."""
        from_ = datetime(2026, 4, 27, 0, 0, tzinfo=UTC)
        to = datetime(2026, 4, 26, 0, 0, tzinfo=UTC)
        assert calcular_total_dias(from_, to) == 1

    def test_extra_minuto_round_up(self):
        """30 dias e 1 minuto = 31 dias (nao 30)."""
        from_ = datetime(2026, 3, 28, 0, 0, tzinfo=UTC)
        to = datetime(2026, 4, 27, 0, 1, tzinfo=UTC)
        assert calcular_total_dias(from_, to) == 31


# ─── arredondar_horas ─────────────────────────────────────────────────────


class TestArredondarHoras:
    def test_arredonda_2_casas_default(self):
        assert arredondar_horas(1.23456) == 1.23

    def test_arredonda_4_casas(self):
        assert arredondar_horas(1.23456, casas=4) == 1.2346

    def test_none_propaga(self):
        assert arredondar_horas(None) is None

    def test_zero(self):
        assert arredondar_horas(0.0) == 0.0


# ─── assert_utc ───────────────────────────────────────────────────────────


class TestAssertUtc:
    def test_aceita_utc(self):
        assert_utc(datetime(2026, 4, 27, tzinfo=UTC))

    def test_rejeita_naive(self):
        with pytest.raises(ValueError, match="tz-aware"):
            assert_utc(datetime(2026, 4, 27))

    def test_rejeita_outro_tz(self):
        brt = timezone(timedelta(hours=-3))
        with pytest.raises(ValueError, match="UTC"):
            assert_utc(datetime(2026, 4, 27, tzinfo=brt))

    def test_aceita_alias_offset_zero(self):
        """timezone(timedelta(0)) e equivalente a UTC."""
        utc_alias = timezone(timedelta(0))
        # Nao levanta — offset 0 == UTC
        assert_utc(datetime(2026, 4, 27, tzinfo=utc_alias))

    def test_mensagem_inclui_nome_param(self):
        with pytest.raises(ValueError, match="meu_dt"):
            assert_utc(datetime(2026, 4, 27), name="meu_dt")
