"use client";

import { useCallback, useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { useAuthorization } from "@/lib/hooks/use-authorization";
import { useCancelarProva } from "@/hooks/useCancelarProva";
import { useReiniciarCiclo } from "@/hooks/useReiniciarCiclo";
import { useFocusTrap } from "@/hooks/useFocusTrap";
import type { ProvaResponse, StatusProva } from "@/lib/types/prova";
import styles from "./detalhe.module.css";

/** Estados ativos que permitem cancelamento (RN-005).
 *
 * Wave 3 v4.0 / C11: 7 novos valores adicionados ao status_prova_enum.
 * Todos os ativos (nao-terminais) sao cancelaveis — espelho de
 * `pode_cancelar` em backend/app/state_machine/v4/machine.py. Os unicos
 * 2 estados NAO cancelaveis sao terminais: RECEBIDA_PELA_CLICHERIA
 * (sucesso) e CANCELADA (ja cancelada).
 */
const CANCELAVEIS: Set<StatusProva> = new Set([
  // Legacy v3.0 (8 ativos)
  "CRIADA",
  "RETIRADA_PELO_VENDEDOR",
  "APROVADA_PELO_VENDEDOR",
  "DE_VOLTA_3STUDIO",
  "COM_MOTORISTA",
  "ENVIADA_PARA_CLICHERIA",
  "ENCAMINHADA_A_CLICHERIA",
  "REPROVADA_PELO_VENDEDOR",
  // v4.0 (7 novos — todos ativos por construcao)
  "COM_MOTORISTA_IDA_LAMINACAO",
  "COM_MOTORISTA_VOLTA_LAMINACAO",
  "COM_MOTORISTA_ENTREGA_FINAL",
  "ENCAMINHADA_PARA_LAMINACAO",
  "LAMINACAO_CONCLUIDA",
  "DE_VOLTA_3STUDIO_POS_LAMINACAO",
  "ENCAMINHADA_PARA_O_VENDEDOR",
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
  // Wave 1 v4.0: cada acao tem chave propria na Matriz de Acesso
  // (provas.cancel + provas.restart). Hoje ambas sao admin-only, mas a
  // checagem por chave deixa explicito qual celula esta sendo aplicada
  // e permite expansao futura sem refactor.
  const cancelAuth = useAuthorization("provas.cancel");
  const restartAuth = useAuthorization("provas.restart");
  const [modal, setModal] = useState<ModalState>({ kind: "closed" });
  const [motivo, setMotivo] = useState("");
  const focusTrapRef = useFocusTrap<HTMLDivElement>(modal.kind !== "closed");

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

  const handleCloseModal = useCallback(() => {
    setModal({ kind: "closed" });
    setMotivo("");
    resetCancelar();
    resetReiniciar();
  }, [resetCancelar, resetReiniciar]);

  // ESC fecha modal
  useEffect(() => {
    if (modal.kind === "closed") return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") handleCloseModal();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [modal.kind, handleCloseModal]);

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

  // Nao renderiza se nenhuma das duas acoes esta autorizada (loading
  // tambem cai aqui — Hook devolve hasAccess=false enquanto loading).
  if (!cancelAuth.hasAccess && !restartAuth.hasAccess) return null;

  const podeCancelar = cancelAuth.hasAccess && CANCELAVEIS.has(prova.status);
  const podeReiniciar =
    restartAuth.hasAccess && prova.status === "REPROVADA_PELO_VENDEDOR";

  // Nenhuma acao disponivel para o estado atual
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
          ref={focusTrapRef}
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
          ref={focusTrapRef}
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
