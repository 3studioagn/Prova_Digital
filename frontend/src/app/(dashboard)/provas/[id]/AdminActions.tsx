"use client";

import { useCallback, useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import { useCancelarProva } from "@/hooks/useCancelarProva";
import { useReiniciarCiclo } from "@/hooks/useReiniciarCiclo";
import type { ProvaResponse, StatusProva } from "@/lib/types/prova";
import styles from "./detalhe.module.css";

/** Estados ativos que permitem cancelamento (RN-005). */
const CANCELAVEIS: Set<StatusProva> = new Set([
  "CRIADA",
  "RETIRADA_PELO_VENDEDOR",
  "APROVADA_PELO_VENDEDOR",
  "DE_VOLTA_3STUDIO",
  "COM_MOTORISTA",
  "ENVIADA_PARA_CLICHERIA",
  "ENCAMINHADA_A_CLICHERIA",
  "REPROVADA_PELO_VENDEDOR",
]);

interface Props {
  prova: ProvaResponse;
  onActionComplete: () => void;
}

type ModalState =
  | { kind: "closed" }
  | { kind: "cancelar" }
  | { kind: "reiniciar" };

export function AdminActions({ prova, onActionComplete }: Props) {
  const { user, loading: userLoading } = useCurrentUser();
  const [modal, setModal] = useState<ModalState>({ kind: "closed" });
  const [motivo, setMotivo] = useState("");

  const getToken = useCallback(async () => {
    const supabase = createClient();
    const { data } = await supabase.auth.getSession();
    return data.session?.access_token ?? null;
  }, []);

  const {
    cancelar,
    loading: cancelLoading,
    error: cancelError,
    reset: resetCancelar,
  } = useCancelarProva(getToken);

  const {
    reiniciar,
    loading: reiniciarLoading,
    error: reiniciarError,
    reset: resetReiniciar,
  } = useReiniciarCiclo(getToken);

  // ESC fecha modal
  useEffect(() => {
    if (modal.kind === "closed") return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") handleCloseModal();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  const handleCloseModal = useCallback(() => {
    setModal({ kind: "closed" });
    setMotivo("");
    resetCancelar();
    resetReiniciar();
  }, [resetCancelar, resetReiniciar]);

  const handleCancelar = useCallback(async () => {
    const trimmed = motivo.trim();
    if (!trimmed) return;
    const result = await cancelar(prova.id, trimmed);
    if (result) {
      handleCloseModal();
      onActionComplete();
    }
  }, [motivo, cancelar, prova.id, handleCloseModal, onActionComplete]);

  const handleReiniciar = useCallback(async () => {
    const result = await reiniciar(prova.id);
    if (result) {
      handleCloseModal();
      onActionComplete();
    }
  }, [reiniciar, prova.id, handleCloseModal, onActionComplete]);

  // Nao renderiza se nao e admin ou ainda carregando
  if (userLoading || !user?.is_admin) return null;

  const podeCancelar = CANCELAVEIS.has(prova.status);
  const podeReiniciar = prova.status === "REPROVADA_PELO_VENDEDOR";

  // Nenhuma acao disponivel
  if (!podeCancelar && !podeReiniciar) return null;

  return (
    <>
      {podeReiniciar && (
        <button
          type="button"
          className={styles.btnPrimary}
          onClick={() => setModal({ kind: "reiniciar" })}
        >
          Reiniciar ciclo
        </button>
      )}
      {podeCancelar && (
        <button
          type="button"
          className={styles.btnDanger}
          onClick={() => setModal({ kind: "cancelar" })}
        >
          Cancelar prova
        </button>
      )}

      {/* Modal de cancelamento */}
      {modal.kind === "cancelar" && (
        <div
          className={styles.modalOverlay}
          onClick={(e) => {
            if (e.target === e.currentTarget) handleCloseModal();
          }}
          role="dialog"
          aria-modal="true"
          aria-labelledby="cancelar-modal-title"
        >
          <div className={styles.adminModalContent}>
            <h2 id="cancelar-modal-title" className={styles.adminModalTitle}>
              Cancelar prova — {prova.nro_requerimento}
            </h2>
            <p className={styles.adminModalDesc}>
              Esta acao e irreversivel. A prova sera cancelada e nenhuma
              transicao futura sera possivel.
            </p>
            <textarea
              className={styles.adminModalTextarea}
              placeholder="Motivo do cancelamento (obrigatorio)"
              value={motivo}
              onChange={(e) => setMotivo(e.target.value)}
              rows={3}
              maxLength={500}
              disabled={cancelLoading}
            />
            {cancelError && (
              <p className={styles.adminModalError}>{cancelError}</p>
            )}
            <div className={styles.adminModalActions}>
              <button
                type="button"
                className={styles.btnSecondary}
                onClick={handleCloseModal}
                disabled={cancelLoading}
              >
                Voltar
              </button>
              <button
                type="button"
                className={styles.btnDanger}
                onClick={handleCancelar}
                disabled={cancelLoading || !motivo.trim()}
              >
                {cancelLoading ? "Cancelando..." : "Confirmar cancelamento"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal de reinicio */}
      {modal.kind === "reiniciar" && (
        <div
          className={styles.modalOverlay}
          onClick={(e) => {
            if (e.target === e.currentTarget) handleCloseModal();
          }}
          role="dialog"
          aria-modal="true"
          aria-labelledby="reiniciar-modal-title"
        >
          <div className={styles.adminModalContent}>
            <h2 id="reiniciar-modal-title" className={styles.adminModalTitle}>
              Reiniciar ciclo — {prova.nro_requerimento}
            </h2>
            <p className={styles.adminModalDesc}>
              A prova voltara ao status &quot;Criada&quot; (ciclo{" "}
              {prova.ciclo_atual + 1}). O historico do ciclo atual sera
              preservado integralmente.
            </p>
            {reiniciarError && (
              <p className={styles.adminModalError}>{reiniciarError}</p>
            )}
            <div className={styles.adminModalActions}>
              <button
                type="button"
                className={styles.btnSecondary}
                onClick={handleCloseModal}
                disabled={reiniciarLoading}
              >
                Voltar
              </button>
              <button
                type="button"
                className={styles.btnPrimary}
                onClick={handleReiniciar}
                disabled={reiniciarLoading}
              >
                {reiniciarLoading ? "Reiniciando..." : "Confirmar reinicio"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
