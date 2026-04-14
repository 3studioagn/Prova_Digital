"use client";

import { useCallback, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";
import { createClient } from "@/lib/supabase/client";
import { useRelatorios } from "@/hooks/useRelatorios";
import { useExportCsv } from "@/hooks/useExportCsv";
import type { VendedorRelatorio, StatusCount } from "@/lib/types/relatorio";
import styles from "./relatorios.module.css";

const PIE_COLORS = [
  "#ffcb5c", "#db6607", "#ff9640", "#6bb6c7",
  "#c5d4cd", "#FFEAA7", "#DDA0DD", "#98D8C8",
];

function formatHours(h: number | null): string {
  if (h === null || h === undefined) return "-";
  if (h < 1) return `${Math.round(h * 60)}min`;
  return `${h}h`;
}

export default function RelatoriosPage() {
  // L-01 (auditoria Wave 5 ronda 2): padrao alinhado com as outras paginas
  // dashboard (nova-prova, provas, escanear) — `createClient()` e chamado
  // DENTRO do `useCallback` com dependency array vazio, garantindo que
  // `getToken` e estavel entre renders. Funciona porque o
  // `@supabase/ssr.createBrowserClient` tem singleton interno, entao mesmo
  // chamando a cada invocacao nao custa nada (sempre retorna a mesma
  // instancia cached em `cachedBrowserClient`).
  //
  // Padrao anterior (`const supabase = createClient()` no corpo + `[supabase]`
  // no deps) tambem funcionava por causa do singleton, mas era code smell e
  // frago contra uma eventual major version do pacote que remova o cache.
  const getToken = useCallback(async () => {
    const supabase = createClient();
    const { data } = await supabase.auth.getSession();
    return data.session?.access_token ?? null;
  }, []);

  const today = new Date();
  const thirtyDaysAgo = new Date(today);
  thirtyDaysAgo.setDate(today.getDate() - 30);
  // Usa fuso local (nao UTC) — getFullYear/getMonth/getDate preservam o
  // calendario do browser, enquanto toISOString() converte p/ UTC e causa
  // off-by-one em BRT apos 21h (M-03 auditoria Wave 5). O backend interpreta
  // o input como BRT via BRT_TIMEZONE, entao o picker tem que casar.
  const toIso = (d: Date) => {
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  };

  const [inicio, setInicio] = useState(toIso(thirtyDaysAgo));
  const [fim, setFim] = useState(toIso(today));
  const [appliedInicio, setAppliedInicio] = useState(inicio);
  const [appliedFim, setAppliedFim] = useState(fim);

  const { data, loading, error, refresh } = useRelatorios(
    getToken,
    appliedInicio,
    appliedFim,
  );
  const csv = useExportCsv(getToken);

  // M-03 (auditoria Wave 5): o botao "Aplicar" e desabilitado quando o
  // picker ja esta com as datas aplicadas (seria no-op silencioso — o
  // useEffect([refresh]) do useRelatorios nao re-dispara porque inicio/fim
  // nao mudaram). Para forcar um re-fetch do mesmo periodo, o usuario
  // usa o botao "Atualizar" ao lado (M-02 auditoria Wave 5).
  const isApplyDisabled = inicio === appliedInicio && fim === appliedFim;

  const handleApply = () => {
    setAppliedInicio(inicio);
    setAppliedFim(fim);
  };

  const handleCsv = () => {
    csv.download(appliedInicio, appliedFim);
  };

  if (loading && !data) {
    return (
      <div className={styles.loadingContainer}>Carregando relatorios...</div>
    );
  }

  if (error && !data) {
    return (
      <div className={styles.errorContainer}>
        <span>{error}</span>
        <button className={styles.retryButton} onClick={refresh}>
          Tentar novamente
        </button>
      </div>
    );
  }

  if (!data) return null;

  // L-10 (auditoria Wave 5 ronda 2): taxa de reprovacao geral vem pronta do
  // backend (campo `taxa_reprovacao_geral_pct`). Antes era calculada aqui
  // via reduce, o que duplicava logica de negocio no frontend. Usamos
  // toFixed(1) apenas para formatacao consistente.
  const taxaPct = data.taxa_reprovacao_geral_pct.toFixed(1);

  const rotaText = `Padrao: ${data.distribuicao_por_rota.PADRAO} | Direta: ${data.distribuicao_por_rota.DIRETA}`;

  // Dados para os graficos
  const pieData: StatusCount[] = data.distribuicao_por_status;
  const tempoMedioData: { name: string; horas: number }[] = data.por_vendedor
    .filter((v: VendedorRelatorio) => v.tempo_medio_aprovacao_horas !== null)
    .map((v: VendedorRelatorio) => ({
      name: v.vendedor_nome.split(" ")[0],
      horas: v.tempo_medio_aprovacao_horas as number,
    }));
  const topVendedores: { name: string; total: number }[] = [...data.por_vendedor]
    .sort((a: VendedorRelatorio, b: VendedorRelatorio) => b.total_provas - a.total_provas)
    .slice(0, 10)
    .map((v: VendedorRelatorio) => ({
      name: v.vendedor_nome.split(" ")[0],
      total: v.total_provas,
    }));

  return (
    <div className={styles.container}>
      {/* Filtro de periodo + CSV */}
      <div className={styles.filterBar}>
        <input
          type="date"
          className={styles.filterInput}
          value={inicio}
          onChange={(e) => setInicio(e.target.value)}
        />
        <input
          type="date"
          className={styles.filterInput}
          value={fim}
          onChange={(e) => setFim(e.target.value)}
        />
        <button
          className={styles.filterBtn}
          onClick={handleApply}
          disabled={isApplyDisabled}
          title={
            isApplyDisabled
              ? "As datas do picker ja estao aplicadas. Use Atualizar para recarregar o mesmo periodo."
              : "Aplicar o periodo selecionado ao relatorio"
          }
        >
          Aplicar
        </button>
        <button
          className={styles.refreshBtn}
          onClick={refresh}
          disabled={loading}
          title="Recarrega os dados do periodo atual sem precisar alterar as datas."
        >
          {loading ? "Atualizando..." : "Atualizar"}
        </button>
        <button
          className={styles.csvBtn}
          onClick={handleCsv}
          disabled={csv.loading}
        >
          {csv.loading ? "Exportando..." : "Exportar planilha"}
        </button>
      </div>

      {csv.error && (
        <div className={styles.errorInline}>
          <span>{csv.error}</span>
        </div>
      )}

      {/* Cards de resumo */}
      <div className={styles.summaryGrid}>
        <div className={styles.summaryCard}>
          <span className={styles.summaryLabel}>Total geral</span>
          <span className={styles.summaryValue}>{data.total_geral}</span>
        </div>
        <div
          className={styles.summaryCard}
          title="Media de horas entre a criacao da prova e cada aprovacao. Provas re-aprovadas em novos ciclos sao contadas multiplas vezes (reflete tempo total no fluxo)."
        >
          <span className={styles.summaryLabel}>Tempo medio aprovacao</span>
          <span className={styles.summaryValue}>
            {formatHours(data.tempo_medio_aprovacao_horas)}
          </span>
        </div>
        <div className={styles.summaryCard}>
          <span className={styles.summaryLabel}>Taxa reprovacao geral</span>
          <span className={styles.summaryValue}>{taxaPct}%</span>
        </div>
        <div className={styles.summaryCard}>
          <span className={styles.summaryLabel}>Distribuicao por rota</span>
          <span className={styles.summaryValueNarrow}>
            {rotaText}
          </span>
        </div>
      </div>

      {/* Graficos Recharts */}
      <div className={styles.chartsGrid}>
        {/* PieChart: Provas Ativas por Status */}
        <div className={styles.chartCard}>
          <div
            className={styles.chartTitle}
            title="Distribuicao atual de todas as provas em status nao-terminal, independente do filtro de periodo. CANCELADA e RECEBIDA_PELA_CLICHERIA sao excluidas por serem estados finais."
          >
            Provas Ativas
          </div>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={pieData}
                  dataKey="quantidade"
                  nameKey="label"
                  cx="50%"
                  cy="50%"
                  innerRadius={40}
                  outerRadius={80}
                  paddingAngle={2}
                >
                  {pieData.map((_, i) => (
                    <Cell
                      key={`cell-${i}`}
                      fill={PIE_COLORS[i % PIE_COLORS.length]}
                    />
                  ))}
                </Pie>
                <Tooltip />
                <Legend
                  layout="vertical"
                  align="right"
                  verticalAlign="middle"
                  wrapperStyle={{ fontSize: "0.75rem" }}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className={styles.emptyMsg}>Sem provas ativas</div>
          )}
        </div>

        {/* BarChart: Tempo Medio por Vendedor */}
        <div className={styles.chartCard}>
          <div className={styles.chartTitle}>Tempo Medio de Aprovacao</div>
          {tempoMedioData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart
                data={tempoMedioData}
                layout="vertical"
                margin={{ left: 0, right: 10, top: 5, bottom: 5 }}
              >
                <XAxis type="number" unit="h" />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={60}
                  tick={{ fontSize: 12 }}
                />
                <Tooltip formatter={(v) => `${v}h`} />
                <Bar dataKey="horas" fill="#ffcb5c" radius={[0, 8, 8, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className={styles.emptyMsg}>Sem dados de aprovacao</div>
          )}
        </div>

        {/* BarChart: Vendedor com Mais Artes */}
        <div className={styles.chartCard}>
          <div className={styles.chartTitle}>Vendedor com Mais Artes</div>
          {topVendedores.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart
                data={topVendedores}
                layout="vertical"
                margin={{ left: 0, right: 10, top: 5, bottom: 5 }}
              >
                <XAxis type="number" />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={60}
                  tick={{ fontSize: 12 }}
                />
                <Tooltip />
                <Bar dataKey="total" fill="#ff9640" radius={[0, 8, 8, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className={styles.emptyMsg}>Sem dados</div>
          )}
        </div>
      </div>

      {/* Tabela: Metricas por Vendedor */}
      <div className={styles.tableCard}>
        <div className={styles.tableTitle}>Metricas por Vendedor</div>
        <div className={styles.tableScroll}>
          {data.por_vendedor.length > 0 ? (
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Vendedor</th>
                  <th>Localizacao</th>
                  <th>Total</th>
                  <th>Aprovadas</th>
                  <th>Reprovadas</th>
                  <th>Taxa Rep. %</th>
                  <th title="Media de horas entre a criacao da prova e cada aprovacao. Provas re-aprovadas em novos ciclos sao contadas multiplas vezes (reflete tempo total no fluxo).">
                    Tempo Medio
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.por_vendedor.map((v: VendedorRelatorio) => (
                  <tr key={v.vendedor_id}>
                    <td>{v.vendedor_nome}</td>
                    <td>{v.vendedor_localizacao || "-"}</td>
                    <td>{v.total_provas}</td>
                    <td>{v.aprovadas}</td>
                    <td>{v.reprovadas}</td>
                    <td>{v.taxa_reprovacao_pct}%</td>
                    <td>{formatHours(v.tempo_medio_aprovacao_horas)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className={styles.emptyMsg}>Nenhum vendedor no periodo</div>
          )}
        </div>
      </div>

      {/* Tabela: Provas Atrasadas */}
      <div className={styles.tableCard}>
        <div
          className={styles.tableTitle}
          title="Lista todas as provas atualmente atrasadas (sem movimentacao ha mais que o tempo configurado em Configuracoes), independente do filtro de periodo acima. RN-008 trata atraso como conceito 'agora', nao historico."
        >
          Provas Atrasadas ({data.total_atrasadas})
        </div>
        <div className={styles.tableScroll}>
          {data.atrasadas.length > 0 ? (
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Nome</th>
                  <th>Requerimento</th>
                  <th>Cliente</th>
                  <th>Vendedor</th>
                  <th>Status</th>
                  <th>Rota</th>
                  <th>Dias Atraso</th>
                </tr>
              </thead>
              <tbody>
                {data.atrasadas.map((a) => (
                  <tr key={a.prova_id}>
                    <td>{a.nome}</td>
                    <td>{a.nro_requerimento}</td>
                    <td>{a.cliente}</td>
                    <td>{a.vendedor_nome}</td>
                    <td>{a.status}</td>
                    <td>{a.rota || "-"}</td>
                    <td>{a.dias_atraso} dias</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className={styles.emptyMsg}>Nenhuma prova atrasada</div>
          )}
        </div>
      </div>
    </div>
  );
}
