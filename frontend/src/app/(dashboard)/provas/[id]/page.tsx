"use client";

import { useCallback, useState } from "react";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";
import { useProvaDetail } from "@/hooks/useProvaDetail";
import {
  ROTA_LABELS,
  type Rota,
} from "@/lib/types/prova";
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

function formatRota(rota: Rota | null, rotaProjetada: Rota | null): string {
  if (rota) return ROTA_LABELS[rota];
  if (rotaProjetada) return `${ROTA_LABELS[rotaProjetada]} (projetada)`;
  return "—";
}

/** Ícone seta esquerda SVG inline para o botão Voltar.
 * Evita tocar em `components/icons.tsx` (fora do escopo desta sessão). */
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
      // Sem token: feedback imediato + redireciona fluxo para login
      // (o middleware ja trata o redirect no proximo navigate).
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
        // Tenta ler o detail do backend (422 de gerar_pdf, 502 de DB).
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
      // M1 (auditoria Wave 2 — Sessao 20): feedback explicito em caso
      // de falha. Antes o catch era silencioso (comentario "noop"), o
      // que deixava o usuario confuso quando o botao "Baixar etiqueta"
      // nao fazia nada. Usa alert() nativo como fallback — nao ha
      // sistema de toast no projeto ainda.
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
            {/* Card branco principal: envolve dados + arte no topo E o
                card preto do historico abaixo, tudo em um unico container. */}
            <section className={styles.innerCard}>
              <div className={styles.innerCardGrid}>
                <div className={styles.mainInfo}>
                  <h1 className={styles.title}>{prova.nro_requerimento}</h1>
                  <h2 className={styles.subtitle}>{prova.nome}</h2>

                  <div className={styles.metadata}>
                    <p className={styles.metadataItem}>
                      <strong>Cliente:</strong> {prova.cliente}
                    </p>
                    <p className={styles.metadataItem}>
                      <strong>Vendedor:</strong> {prova.vendedor_nome}
                    </p>
                    <p className={styles.metadataItem}>
                      <strong>Rota:</strong>{" "}
                      {formatRota(prova.rota, prova.rota_projetada)}
                    </p>
                    <p className={styles.metadataItem}>
                      <strong>Ciclo Atual:</strong> {prova.ciclo_atual}
                    </p>
                    <p className={styles.metadataItem}>
                      <strong>Criada em:</strong> {formatDate(prova.created_at)}
                    </p>
                    {prova.motivo_cancelamento && (
                      <p
                        className={`${styles.metadataItem} ${styles.motivoCancelamento}`}
                      >
                        <strong>Motivo do cancelamento:</strong>{" "}
                        {prova.motivo_cancelamento}
                      </p>
                    )}
                  </div>

                  <div className={styles.actions}>
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
              </div>

              {/* Card preto ANINHADO dentro do innerCard branco */}
              <section className={styles.timelineCard}>
                <h2 className={styles.timelineTitle}>
                  Historico de movimentacoes
                </h2>
                <Timeline movimentacoes={movimentacoes} prova={prova} />
              </section>
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
