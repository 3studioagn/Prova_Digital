"use client";

import { useCallback, useState } from "react";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";
import { useProvaDetail } from "@/hooks/useProvaDetail";
import {
  ROTA_LABELS,
  STATUS_LABELS,
  type Rota,
} from "@/lib/types/prova";
import { VisualizarEtiquetaModal } from "./VisualizarEtiquetaModal";
import styles from "./detalhe.module.css";

function formatDateTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
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
    if (!token) return;
    const apiBase =
      process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    try {
      const resp = await fetch(
        `${apiBase}/api/v1/provas/${id}/etiqueta.pdf`,
        { headers: { Authorization: `Bearer ${token}` } },
      );
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `etiqueta-${prova?.nro_requerimento ?? id}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      // noop — o botao do modal tem feedback melhor
    }
  }, [id, getToken, prova?.nro_requerimento]);

  return (
    <>
      <div className={styles.mobileNotice}>
        <p>Para acessar esse recurso, acesse a versao desktop.</p>
      </div>
      <div className={styles.desktopOnly}>
        <div className={styles.breadcrumb}>
          <Link href="/provas" className={styles.backLink}>
            ← Voltar para provas
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
            <header className={styles.pageHeader}>
              <div>
                <h1 className={styles.title}>{prova.nro_requerimento}</h1>
                <p className={styles.subtitle}>{prova.nome}</p>
              </div>
              <span
                className={`${styles.statusBadge} ${styles[`status_${prova.status}`] ?? ""}`}
              >
                {STATUS_LABELS[prova.status]}
              </span>
            </header>

            <section className={styles.detailGrid}>
              <div className={styles.dataCard}>
                <h2 className={styles.h2}>Dados da prova</h2>

                <dl className={styles.dl}>
                  <dt>Cliente</dt>
                  <dd>{prova.cliente}</dd>

                  <dt>Vendedor</dt>
                  <dd>
                    {prova.vendedor_nome}
                    {prova.vendedor_localizacao && (
                      <span className={styles.chip}>
                        {prova.vendedor_localizacao}
                      </span>
                    )}
                  </dd>

                  <dt>Rota</dt>
                  <dd>{formatRota(prova.rota, prova.rota_projetada)}</dd>

                  <dt>Ciclo atual</dt>
                  <dd>{prova.ciclo_atual}</dd>

                  <dt>Criada em</dt>
                  <dd>{formatDateTime(prova.created_at)}</dd>

                  <dt>Atualizada em</dt>
                  <dd>{formatDateTime(prova.updated_at)}</dd>

                  {prova.motivo_cancelamento && (
                    <>
                      <dt>Motivo do cancelamento</dt>
                      <dd className={styles.motivoCancelamento}>
                        {prova.motivo_cancelamento}
                      </dd>
                    </>
                  )}
                </dl>

                <div className={styles.cardActions}>
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
                    Baixar etiqueta (PDF)
                  </button>
                </div>
              </div>

              <div className={styles.artCard}>
                <h2 className={styles.h2}>Arte</h2>
                <div className={styles.artContainer}>
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
            </section>

            <section className={styles.timelineCard}>
              <h2 className={styles.h2}>Historico de movimentacoes</h2>
              {movimentacoes && movimentacoes.total === 0 && (
                <div className={styles.timelineEmpty}>
                  <p>Esta prova ainda nao teve movimentacoes.</p>
                  <p className={styles.timelineHint}>
                    A timeline visual fica disponivel quando a prova for
                    escaneada pela primeira vez.
                  </p>
                </div>
              )}
              {movimentacoes && movimentacoes.total > 0 && (
                <ul className={styles.timelineList}>
                  {movimentacoes.items.map((m) => (
                    <li key={m.id} className={styles.timelineItem}>
                      <div className={styles.timelineHeader}>
                        <span className={styles.timelineStatus}>
                          {STATUS_LABELS[m.status_anterior]} →{" "}
                          {STATUS_LABELS[m.status_novo]}
                        </span>
                        <span className={styles.timelineDate}>
                          {formatDateTime(m.created_at)}
                        </span>
                      </div>
                      <div className={styles.timelineMeta}>
                        Por <strong>{m.usuario_nome}</strong> ({m.usuario_setor})
                        · Ciclo {m.ciclo}
                        {m.rota_no_momento &&
                          ` · ${ROTA_LABELS[m.rota_no_momento]}`}
                      </div>
                      {m.motivo_reprovacao && (
                        <div className={styles.timelineMotivo}>
                          Motivo: {m.motivo_reprovacao}
                        </div>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <VisualizarEtiquetaModal
              provaId={id}
              nroRequerimento={prova.nro_requerimento}
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
