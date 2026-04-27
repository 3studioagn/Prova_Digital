"use client";

import { useCallback, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import { createBrowserClient } from "@supabase/ssr";

import { useDashboard } from "@/hooks/useDashboard";

import styles from "./dashboard.module.css";

// ─── Supabase browser client ────────────────────────────────────────────

const supabase = createBrowserClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
);

async function getToken(): Promise<string | null> {
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? null;
}

// ─── Icone de documento (Figma: quadrado amarelo com icone) ─────────────

function DocIcon() {
  return (
    <div className={styles.cardIcon}>
      <svg className={styles.cardIconSvg} viewBox="0 0 28 32">
        <path d="M4 1h14l8 8v20a2 2 0 01-2 2H4a2 2 0 01-2-2V3a2 2 0 012-2z" />
        <path d="M18 1v8h8" />
        <path d="M8 17h12M8 22h12M8 12h5" />
      </svg>
    </div>
  );
}

// ─── Icone QR Code (Figma: icone branco no botao preto) ─────────────────

function QrIcon() {
  return (
    <svg className={styles.shortcutScanIcon} viewBox="0 0 48 48" fill="none">
      <rect x="4" y="4" width="16" height="16" rx="2" stroke="#fff" strokeWidth="2" />
      <rect x="8" y="8" width="8" height="8" rx="1" fill="#fff" />
      <rect x="28" y="4" width="16" height="16" rx="2" stroke="#fff" strokeWidth="2" />
      <rect x="32" y="8" width="8" height="8" rx="1" fill="#fff" />
      <rect x="4" y="28" width="16" height="16" rx="2" stroke="#fff" strokeWidth="2" />
      <rect x="8" y="32" width="8" height="8" rx="1" fill="#fff" />
      <rect x="28" y="28" width="4" height="4" fill="#fff" />
      <rect x="36" y="28" width="8" height="4" fill="#fff" />
      <rect x="28" y="36" width="4" height="8" fill="#fff" />
      <rect x="36" y="40" width="8" height="4" fill="#fff" />
    </svg>
  );
}

// ─── Card de contador ───────────────────────────────────────────────────

function ContadorCard({
  label,
  value,
  onClick,
  className,
}: {
  label: string;
  value: number;
  onClick: () => void;
  className: string;
}) {
  return (
    <motion.div
      className={`${styles.card} ${className}`}
      onClick={onClick}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onClick();
        }
      }}
    >
      <div className={styles.cardHeader}>
        <span className={styles.cardLabel}>{label}</span>
        <DocIcon />
      </div>
      <span className={styles.cardValue}>{value}</span>
    </motion.div>
  );
}

// ─── Constantes ─────────────────────────────────────────────────────────

const POLLING_INTERVAL_MS = 10_000;
const REALTIME_DEBOUNCE_MS = 2_000;

// ─── Pagina principal (match Figma) ─────────────────────────────────────

export default function DashboardPage() {
  const router = useRouter();
  const { loading, error, data, refresh } = useDashboard(getToken);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Realtime subscription ─────────────────────────────────────────────
  const debouncedRefresh = useCallback(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      refresh();
    }, REALTIME_DEBOUNCE_MS);
  }, [refresh]);

  useEffect(() => {
    const channel = supabase
      .channel("dashboard-provas")
      .on(
        "postgres_changes",
        { event: "*", schema: "public", table: "provas_digitais" },
        () => {
          debouncedRefresh();
        },
      )
      .subscribe((status) => {
        if (status === "SUBSCRIBED") {
          if (pollingRef.current) {
            clearInterval(pollingRef.current);
            pollingRef.current = null;
          }
        } else if (status === "CHANNEL_ERROR" || status === "TIMED_OUT") {
          if (!pollingRef.current) {
            pollingRef.current = setInterval(refresh, POLLING_INTERVAL_MS);
          }
        }
      });

    pollingRef.current = setInterval(refresh, POLLING_INTERVAL_MS);

    return () => {
      channel.unsubscribe();
      if (debounceRef.current) clearTimeout(debounceRef.current);
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [debouncedRefresh, refresh]);

  // ── Navegacao ─────────────────────────────────────────────────────────
  const goToStatus = useCallback(
    (statusFilter: string) => {
      router.push(`/provas?status=${statusFilter}`);
    },
    [router],
  );

  const goToCriadasHoje = useCallback(() => {
    const today = new Date().toISOString().split("T")[0];
    router.push(`/provas?periodo_inicio=${today}&periodo_fim=${today}`);
  }, [router]);

  // ── Loading ───────────────────────────────────────────────────────────
  if (loading && !data) {
    return (
      <div className={styles.loadingContainer}>Carregando dashboard...</div>
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

  const { contadores, atrasadas_por_vendedor } = data;

  return (
    <div className={styles.grid}>
      {/* Row 1, Col 1: Criadas hoje */}
      <ContadorCard
        label="Criadas hoje"
        value={contadores.criadas_hoje}
        onClick={goToCriadasHoje}
        className={styles.cardCriadas}
      />

      {/* Row 1, Col 2: Com Vendedor */}
      <ContadorCard
        label="Com Vendedor"
        value={contadores.com_vendedor}
        onClick={() => goToStatus("RETIRADA_PELO_VENDEDOR")}
        className={styles.cardComVendedor}
      />

      {/* Row 2, Col 1-2: Aprovadas */}
      <ContadorCard
        label="Aprovadas"
        value={contadores.aprovadas}
        onClick={() => goToStatus("APROVADA_PELO_VENDEDOR")}
        className={styles.cardAprovadas}
      />

      {/* Row 3, Col 1: Shortcuts empilhados (dividem a altura do card) */}
      <div className={styles.shortcutsCell}>
        <Link href="/escanear" className={styles.shortcutScan}>
          <span className={styles.shortcutScanLabel}>Escanear QR Code</span>
          <QrIcon />
        </Link>
        <Link href="/nova-prova" className={styles.shortcutNova}>
          <span className={styles.shortcutNovaLabel}>Nova Prova</span>
        </Link>
        <Link href="/relatorios" className={styles.shortcutRelatorios}>
          <span className={styles.shortcutRelatoriosLabel}>
            Acessar Relatorios
          </span>
        </Link>
      </div>

      {/* Row 3, Col 2: Na clicheria (mesma altura dos outros cards)
       *
       * Navega para /provas SEM filtro de status porque na_clicheria agrega
       * 2 statuses (ENVIADA + ENCAMINHADA) e a listagem so suporta filtro
       * por 1 status. Filtrar por apenas ENVIADA causaria discrepancia
       * entre o valor do card e a contagem na lista. Mesmo padrao do card
       * Atrasadas. Multi-status sera suportado na Wave 5 (relatorios).
       */}
      <ContadorCard
        label="Na clicheria"
        value={contadores.na_clicheria}
        onClick={() => router.push("/provas")}
        className={styles.cardNaClicheria}
      />

      {/* Row 1-4, Col 3: Atrasadas (full height) */}
      <motion.div
        className={`${styles.card} ${styles.cardAtrasadas}`}
        onClick={() => router.push("/provas")}
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.1 }}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            router.push("/provas");
          }
        }}
      >
        <div className={styles.cardHeader}>
          <span className={`${styles.cardLabel} ${styles.atrasadasLabelColor}`}>
            Atrasadas
          </span>
          <DocIcon />
        </div>

        <div className={styles.atrasadasList}>
          {atrasadas_por_vendedor.map((item) => (
            <div key={item.vendedor_nome} className={styles.atrasadasItem}>
              <span className={styles.atrasadasNome}>{item.vendedor_nome}</span>
              <span className={styles.atrasadasQtd}>{item.quantidade}</span>
            </div>
          ))}
          {atrasadas_por_vendedor.length === 0 && (
            <div className={styles.atrasadasItem}>
              <span className={styles.atrasadasNome}>Nenhuma prova atrasada</span>
            </div>
          )}
        </div>

        <span className={styles.atrasadasTotal}>{contadores.atrasadas}</span>
      </motion.div>
    </div>
  );
}
