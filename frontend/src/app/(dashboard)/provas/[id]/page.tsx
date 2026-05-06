"use client";

import { useCallback, useState } from "react";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";
import { useProvaDetail } from "@/hooks/useProvaDetail";
import { STATUS_LABELS, formatRota } from "@/lib/types/prova";
import { AdminActions } from "./AdminActions";
import { VisualizarEtiquetaModal } from "./VisualizarEtiquetaModal";
import { Timeline } from "./Timeline";
import styles from "./detalhe.module.css";

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}

/** Icone seta esquerda SVG inline para o botao Voltar.
 * Evita tocar em `components/icons.tsx` (fora do escopo desta sessao). */
function ArrowLeftIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      width={18}
      height={18}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...props}
    >
      <path d="M19 12H5M12 19l-7-7 7-7" />
    </svg>
  );
}

interface PageProps {
  params: { id: string };
}

export default function ProvaDetalhePage({ params }: PageProps) {
  // Next 14: `params` e sincrono (plain object). Next 15+ passaria a ser
  // Promise<{id}> e exigiria `use(params)` — mas este projeto esta no 14.2.
  const { id } = params;

  const getToken = useCallback(async () => {
    const supabase = createClient();
    const { data } = await supabase.auth.getSession();
    return data.session?.access_token ?? null;
  }, []);

  const {
    loading,
    error,
    prova,
    imagemUrl,
    imagemError,
    movimentacoes,
    reload,
  } = useProvaDetail(id, getToken);

  const [etiquetaModalOpen, setEtiquetaModalOpen] = useState(false);
  const [imgLoadError, setImgLoadError] = useState(false);

  const handleDownloadEtiqueta = useCallback(async () => {
    const token = await getToken();
    if (!token) {
      alert("Sessao expirada. Faca login novamente.");
      return;
    }
    const apiBase =
      process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    try {
      const resp = await fetch(
        `${apiBase}/api/v1/provas/${id}/etiqueta.pdf`,
        { headers: { Authorization: `Bearer ${token}` } },
      );
      if (!resp.ok) {
        let detail: string | null = null;
        try {
          const body = await resp.json();
          detail = body?.detail ?? null;
        } catch {
          // Resposta nao-JSON — ignora e usa fallback.
        }
        throw new Error(detail ?? `HTTP ${resp.status}`);
      }
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `etiqueta-${prova?.nro_requerimento ?? id}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      const msg =
        err instanceof Error
          ? err.message
          : "Nao foi possivel baixar a etiqueta.";
      alert(
        `Nao foi possivel baixar a etiqueta: ${msg}\n\n` +
          "Tente novamente ou use o botao 'Visualizar etiqueta' para abrir o PDF no modal.",
      );
    }
  }, [id, getToken, prova?.nro_requerimento]);

  return (
    <>
      <div className={styles.mobileNotice}>
        <p>Para acessar esse recurso, acesse a versao desktop.</p>
      </div>
      <div className={styles.desktopOnly}>
        <div className={styles.breadcrumb}>
          <Link href="/provas" className={styles.backBtn}>
            <ArrowLeftIcon />
            <span>Voltar</span>
          </Link>
        </div>

        {loading && <div className={styles.loadingBox}>Carregando prova...</div>}

        {error && !loading && (
          <div className={styles.errorBox}>
            <p>{error}</p>
            <button
              type="button"
              className={styles.btnSecondary}
              onClick={reload}
            >
              Tentar novamente
            </button>
          </div>
        )}

        {!loading && !error && prova && (
          <>
            <section className={styles.innerCard}>
              <div className={styles.innerCardGrid}>
                {/* Wave 2 v4.0 / C08: arte AGORA NA ESQUERDA (alinhamento Figma do Mario). */}
                <div className={styles.artSlot}>
                  {imagemError && (
                    <div className={styles.artPlaceholder}>
                      Falha ao carregar URL da arte: {imagemError}
                    </div>
                  )}
                  {!imagemError && imagemUrl && !imgLoadError && (
                    /* eslint-disable-next-line @next/next/no-img-element */
                    <img
                      src={imagemUrl.url}
                      alt={`Arte da prova ${prova.nro_requerimento}`}
                      className={styles.artImg}
                      onError={() => setImgLoadError(true)}
                    />
                  )}
                  {!imagemError && imagemUrl && imgLoadError && (
                    <div className={styles.artPlaceholder}>
                      <p>Nao foi possivel carregar a arte.</p>
                      <p className={styles.artHint}>
                        A prova pode ter sido cadastrada com um arquivo que
                        nao existe mais no storage.
                      </p>
                    </div>
                  )}
                  {!imagemUrl && !imagemError && (
                    <div className={styles.artPlaceholder}>
                      Carregando arte...
                    </div>
                  )}
                </div>

                <div className={styles.mainInfo}>
                  <p className={styles.requerimentoLabel}>
                    Requerimento: {prova.nro_requerimento}
                    <span className={styles.requerimentoSep} aria-hidden="true">
                      {" · "}
                    </span>
                    <span className={styles.codigoPublico}>
                      {prova.codigo_publico}
                    </span>
                  </p>
                  <h1 className={styles.title}>{prova.nome}</h1>
                  <hr className={styles.divider} />

                  <div className={styles.metaGrid}>
                    <div className={styles.metaItem}>
                      <span className={styles.metaLabel}>Cliente:</span>
                      <span className={styles.metaValue}>{prova.cliente}</span>
                    </div>
                    <div className={styles.metaItem}>
                      <span className={styles.metaLabel}>Rota:</span>
                      <span
                        className={styles.metaValue}
                        title={
                          prova.rota === null
                            ? "Prova legacy v3.0 — rota sera definida pelo backfill da Wave 7"
                            : undefined
                        }
                      >
                        {formatRota(prova.rota)}
                      </span>
                    </div>
                    <div className={styles.metaItem}>
                      <span className={styles.metaLabel}>Criada em:</span>
                      <span className={styles.metaValue}>
                        {formatDate(prova.created_at)}
                      </span>
                    </div>
                    <div className={styles.metaItem}>
                      <span className={styles.metaLabel}>Vendedor:</span>
                      <span className={styles.metaValue}>
                        {prova.vendedor_nome}
                      </span>
                    </div>
                    <div className={styles.metaItem}>
                      <span className={styles.metaLabel}>Ciclo Atual:</span>
                      <span className={styles.metaValue}>
                        {prova.ciclo_atual}
                      </span>
                    </div>
                    <div className={styles.metaItem}>
                      <span className={styles.metaLabel}>Status:</span>
                      <span className={styles.metaValue}>
                        {STATUS_LABELS[prova.status]}
                      </span>
                    </div>
                  </div>

                  {prova.motivo_cancelamento && (
                    <div className={styles.motivoCancelamento}>
                      <strong>Motivo do cancelamento:</strong>
                      {prova.motivo_cancelamento}
                    </div>
                  )}

                  {/* Wave 2 v4.0 / C08: linha de acoes com 2/3/4 botoes
                      side-by-side (decisao A2 do Mario). AdminActions adiciona
                      Cancelar (sempre que admin + status cancelavel) e/ou
                      Reiniciar (apenas em REPROVADA). Modais sao position:
                      fixed e nao competem por slots. */}
                  <div className={styles.actionsRow}>
                    <button
                      type="button"
                      className={styles.btnPrimary}
                      onClick={() => setEtiquetaModalOpen(true)}
                    >
                      Visualizar etiqueta
                    </button>
                    <button
                      type="button"
                      className={styles.btnSecondary}
                      onClick={handleDownloadEtiqueta}
                    >
                      Baixar etiqueta
                    </button>
                    <AdminActions prova={prova} onActionComplete={reload} />
                  </div>
                </div>
              </div>
            </section>

            {/* Wave 2 v4.0 / C08: card preto SEPARADO (nao mais aninhado),
                espelha o Figma do Mario. Empty state literal preservado. */}
            <section className={styles.timelineCard}>
              <h2 className={styles.timelineTitle}>
                Historico de movimentacoes
              </h2>
              <Timeline movimentacoes={movimentacoes} prova={prova} />
            </section>

            <VisualizarEtiquetaModal
              provaId={id}
              nroRequerimento={prova.nro_requerimento}
              qrCodeHash={prova.qr_code_hash}
              isOpen={etiquetaModalOpen}
              onClose={() => setEtiquetaModalOpen(false)}
              getToken={getToken}
            />
          </>
        )}
      </div>
    </>
  );
}
