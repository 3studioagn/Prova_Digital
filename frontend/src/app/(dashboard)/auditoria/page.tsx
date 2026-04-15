"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";
import { apiFetch } from "@/lib/api";
import { useAuditoria } from "@/hooks/useAuditoria";
import {
  TIPO_EVENTO_LABELS,
  TIPO_EVENTO_VALUES,
  TOTAL_ESTIMADO_CAP,
} from "@/lib/types/auditoria";
import type {
  AuditLogItem,
  AuditoriaFilters,
  TipoEventoEnum,
} from "@/lib/types/auditoria";
import type {
  UsuarioListResponse,
  UsuarioResponse,
} from "@/lib/types/usuario";
import { AuditoriaDetailModal } from "./AuditoriaDetailModal";
import styles from "./auditoria.module.css";

/**
 * Pagina /auditoria — Componente 18 (Wave 6, RNF-005).
 *
 * Listagem admin-only do log de auditoria imutavel. Gate de RBAC e feito
 * pelo backend via `get_admin_user` (ADR-018) — nao-admin recebe 403.
 * O item de menu correspondente em `layout.tsx` e filtrado por `adminOnly`,
 * entao na pratica o usuario nao-admin nem ve o link.
 *
 * Client component puro seguindo o padrao de `/relatorios` (Wave 5).
 * O server component com redirect nao agrega valor aqui porque o
 * backend ja tem autoridade sobre o gate.
 */
export default function AuditoriaPage() {
  // Padrao ADR-098 L-01: createClient DENTRO do useCallback com deps=[].
  const getToken = useCallback(async () => {
    const supabase = createClient();
    const { data } = await supabase.auth.getSession();
    return data.session?.access_token ?? null;
  }, []);

  // -------------------------------------------------------------------
  // Filtros: picker (o que o usuario esta editando) vs aplicado (o que
  // esta alimentando o hook). Padrao do /relatorios (Wave 5, M-03).
  // -------------------------------------------------------------------

  const [pickerInicio, setPickerInicio] = useState("");
  const [pickerFim, setPickerFim] = useState("");
  const [pickerUsuario, setPickerUsuario] = useState("");
  const [pickerNroReq, setPickerNroReq] = useState("");
  const [pickerTipos, setPickerTipos] = useState<TipoEventoEnum[]>([]);

  const [applied, setApplied] = useState<AuditoriaFilters>({});

  const { items, loading, loadingMore, error, hasMore, totalEstimado, refresh, loadMore } =
    useAuditoria(getToken, applied);

  // -------------------------------------------------------------------
  // Lista de usuarios (para o filtro de autor). Fetchada uma vez no mount.
  // -------------------------------------------------------------------

  const [usuarios, setUsuarios] = useState<UsuarioResponse[]>([]);

  useEffect(() => {
    let aborted = false;
    (async () => {
      const token = await getToken();
      if (!token) return;
      try {
        // O endpoint retorna paginado — pegamos pagina 1 com tamanho grande
        // para ter todos os usuarios ativos. O projeto tem < 10 usuarios
        // em producao hoje; nao precisa de paginacao real aqui.
        const resp = await apiFetch<UsuarioListResponse>(
          "/api/v1/users/?page=1&page_size=100",
          { token },
        );
        if (!aborted) setUsuarios(resp.items);
      } catch {
        // Silent — o filtro de autor fica vazio, mas a listagem continua.
      }
    })();
    return () => {
      aborted = true;
    };
  }, [getToken]);

  // -------------------------------------------------------------------
  // Handlers
  // -------------------------------------------------------------------

  const handleApply = useCallback(() => {
    setApplied({
      dataInicio: pickerInicio || null,
      dataFim: pickerFim || null,
      usuarioId: pickerUsuario || null,
      nroRequerimento: pickerNroReq.trim() || null,
      tipoEvento: pickerTipos.length > 0 ? pickerTipos : null,
    });
  }, [pickerInicio, pickerFim, pickerUsuario, pickerNroReq, pickerTipos]);

  const handleClear = useCallback(() => {
    setPickerInicio("");
    setPickerFim("");
    setPickerUsuario("");
    setPickerNroReq("");
    setPickerTipos([]);
    setApplied({});
  }, []);

  const toggleTipoEvento = useCallback((tipo: TipoEventoEnum) => {
    setPickerTipos((prev) =>
      prev.includes(tipo) ? prev.filter((t) => t !== tipo) : [...prev, tipo],
    );
  }, []);

  const isApplyDisabled = useMemo(() => {
    // Compara picker com applied para desabilitar quando nao ha mudanca.
    const sortedPickerTipos = [...pickerTipos].sort().join(",");
    const sortedAppliedTipos = [...(applied.tipoEvento ?? [])].sort().join(",");
    return (
      (pickerInicio || "") === (applied.dataInicio ?? "") &&
      (pickerFim || "") === (applied.dataFim ?? "") &&
      (pickerUsuario || "") === (applied.usuarioId ?? "") &&
      pickerNroReq.trim() === (applied.nroRequerimento ?? "") &&
      sortedPickerTipos === sortedAppliedTipos
    );
  }, [
    pickerInicio,
    pickerFim,
    pickerUsuario,
    pickerNroReq,
    pickerTipos,
    applied,
  ]);

  // -------------------------------------------------------------------
  // Modal de detalhes
  // -------------------------------------------------------------------

  const [selectedLogId, setSelectedLogId] = useState<string | null>(null);

  const openDetail = useCallback((logId: string) => {
    setSelectedLogId(logId);
  }, []);

  const closeDetail = useCallback(() => {
    setSelectedLogId(null);
  }, []);

  // -------------------------------------------------------------------
  // Renders
  // -------------------------------------------------------------------

  const totalLabel = useMemo(() => {
    if (totalEstimado >= TOTAL_ESTIMADO_CAP) return "100k+";
    return String(totalEstimado);
  }, [totalEstimado]);

  if (loading && items.length === 0 && !error) {
    return (
      <div className={styles.loadingContainer}>
        Carregando log de auditoria...
      </div>
    );
  }

  if (error && items.length === 0) {
    return (
      <div className={styles.errorContainer}>
        <span>{error}</span>
        <button
          type="button"
          className={styles.retryButton}
          onClick={refresh}
        >
          Tentar novamente
        </button>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      {/* ============================================================
          Filtros
      ============================================================ */}
      <div className={styles.filterCard}>
        <div className={styles.filterGrid}>
          <label className={styles.filterField}>
            <span className={styles.filterLabel}>De</span>
            <input
              type="date"
              className={styles.filterInput}
              value={pickerInicio}
              onChange={(e) => setPickerInicio(e.target.value)}
            />
          </label>

          <label className={styles.filterField}>
            <span className={styles.filterLabel}>Ate</span>
            <input
              type="date"
              className={styles.filterInput}
              value={pickerFim}
              onChange={(e) => setPickerFim(e.target.value)}
            />
          </label>

          <label className={styles.filterField}>
            <span className={styles.filterLabel}>Autor</span>
            <select
              className={styles.filterInput}
              value={pickerUsuario}
              onChange={(e) => setPickerUsuario(e.target.value)}
            >
              <option value="">Todos os autores</option>
              {usuarios.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.nome} ({u.setor})
                </option>
              ))}
            </select>
          </label>

          <label className={styles.filterField}>
            <span className={styles.filterLabel}>Prova (nro requerimento)</span>
            <input
              type="text"
              className={styles.filterInput}
              placeholder="Ex: 000236"
              value={pickerNroReq}
              onChange={(e) => setPickerNroReq(e.target.value)}
              maxLength={50}
            />
          </label>
        </div>

        <fieldset className={styles.tipoEventoGroup}>
          <legend className={styles.filterLabel}>Tipo de evento</legend>
          <div className={styles.tipoEventoChips}>
            {TIPO_EVENTO_VALUES.map((tipo) => {
              const active = pickerTipos.includes(tipo);
              return (
                <button
                  key={tipo}
                  type="button"
                  className={`${styles.chipToggle} ${
                    active ? styles[`chip_${tipo}_active`] ?? styles.chipActive : ""
                  }`}
                  onClick={() => toggleTipoEvento(tipo)}
                  aria-pressed={active}
                >
                  {TIPO_EVENTO_LABELS[tipo]}
                </button>
              );
            })}
          </div>
        </fieldset>

        <div className={styles.filterActions}>
          <button
            type="button"
            className={styles.applyBtn}
            onClick={handleApply}
            disabled={isApplyDisabled}
            title={
              isApplyDisabled
                ? "Os filtros do picker ja estao aplicados."
                : "Aplicar filtros"
            }
          >
            Aplicar
          </button>
          <button
            type="button"
            className={styles.clearBtn}
            onClick={handleClear}
          >
            Limpar
          </button>
          <button
            type="button"
            className={styles.refreshBtn}
            onClick={refresh}
            disabled={loading}
          >
            {loading ? "Atualizando..." : "Atualizar"}
          </button>
        </div>
      </div>

      {/* ============================================================
          Contador + tabela
      ============================================================ */}
      <div className={styles.tableCard}>
        <div className={styles.tableHeader}>
          <span className={styles.tableCount} aria-live="polite">
            Mostrando <strong>{items.length}</strong> de{" "}
            <strong>{totalLabel}</strong> eventos
          </span>
        </div>

        <div className={styles.tableScroll}>
          {items.length === 0 && !loading ? (
            <div className={styles.emptyMsg}>
              Nenhum evento encontrado com os filtros atuais.
            </div>
          ) : (
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Quando</th>
                  <th>Quem</th>
                  <th>Evento</th>
                  <th>Prova</th>
                  <th>IP</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <AuditoriaRow
                    key={item.id}
                    item={item}
                    onClick={() => openDetail(item.id)}
                  />
                ))}
              </tbody>
            </table>
          )}
        </div>

        {hasMore && (
          <div className={styles.loadMoreWrap}>
            <button
              type="button"
              className={styles.loadMoreBtn}
              onClick={loadMore}
              disabled={loadingMore}
            >
              {loadingMore ? "Carregando..." : "Carregar mais"}
            </button>
          </div>
        )}
      </div>

      {/* ============================================================
          Modal de detalhes
      ============================================================ */}
      <AuditoriaDetailModal
        logId={selectedLogId}
        onClose={closeDetail}
        getToken={getToken}
      />
    </div>
  );
}

// =============================================================================
// Row component (isolado para memoizacao + clareza)
// =============================================================================

interface RowProps {
  item: AuditLogItem;
  onClick: () => void;
}

function AuditoriaRow({ item, onClick }: RowProps) {
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTableRowElement>) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onClick();
    }
  };

  return (
    <tr
      className={styles.tableRow}
      onClick={onClick}
      onKeyDown={handleKeyDown}
      tabIndex={0}
      role="button"
      aria-label={`Abrir detalhes do evento ${item.tipo_evento_label} de ${item.usuario.nome}`}
    >
      <td className={styles.cellWhen}>{formatWhen(item.created_at)}</td>
      <td>
        <span className={styles.who}>
          <strong>{item.usuario.nome}</strong>
          <span className={styles.whoSetor}>{item.usuario.setor}</span>
        </span>
      </td>
      <td>
        <span
          className={`${styles.chip} ${styles[`chip_${item.tipo_evento}`] ?? ""}`}
        >
          {item.tipo_evento_label}
        </span>
      </td>
      <td className={styles.cellProva}>
        {item.prova ? (
          <Link
            href={`/provas/${item.prova.id}`}
            className={styles.provaLink}
            onClick={(e) => e.stopPropagation()}
            title={item.prova.nome}
          >
            {item.prova.nro_requerimento}
          </Link>
        ) : (
          <span className={styles.noProva}>—</span>
        )}
      </td>
      <td className={styles.cellIp}>{item.ip_address || "—"}</td>
    </tr>
  );
}

// =============================================================================
// Helpers
// =============================================================================

function formatWhen(iso: string): string {
  // "2026-04-14 19:55" em BRT. Usa Intl.DateTimeFormat para respeitar o
  // fuso local do browser (consistente com o resto do projeto que assume
  // America/Sao_Paulo no cliente).
  try {
    const d = new Date(iso);
    return d.toLocaleString("pt-BR", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}
