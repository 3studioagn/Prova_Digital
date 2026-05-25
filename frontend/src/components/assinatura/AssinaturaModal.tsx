"use client";

/**
 * AssinaturaModal — Wave 8 v5.0 / Componente 22.
 *
 * Reativa a tela de assinatura no fluxo de escaneamento (RF-028). Abre
 * automaticamente (Decisao Q2) apos a identificacao de uma prova quando
 * o usuario logado e o proximo ator habilitado pela maquina de estados
 * (`scan.transicoes_permitidas` nao-vazio — decisao tomada na pagina via
 * `deveAbrirAssinatura`).
 *
 * Decisoes do Gate 1 aplicadas aqui:
 *   D1  — apresentacao em modal sobre `/escanear`.
 *   D2  — captura via `react-signature-canvas` (componente CapturaAssinatura).
 *   D3  — seletor Aprovar/Reprovar antes da assinatura quando ha mais de
 *         uma transicao permitida (caso do vendedor).
 *   D4  — motivo da reprovacao em texto livre, sem minimo, no mesmo modal.
 *   D5  — falha de rede mantem o modal aberto com a assinatura preservada
 *         em memoria (o canvas nao desmonta entre "assinando" e "enviando").
 *   D7  — apos sucesso, a saida leva a `/provas/[id]` (callback `onFechar`).
 *   D10 — animacao via `framer-motion` direto (C20 pendente) + feedback
 *         inline; respeita `prefers-reduced-motion`.
 *
 * Contrato: TODA saida terminal (sucesso confirmado, cancelamento,
 * conflito, sessao expirada) chama `onFechar`, e a pagina navega para
 * `/provas/[id]`. O unico caminho nao-terminal e o erro de rede
 * retentavel, que volta para "assinando".
 */
import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";
import { motion, useReducedMotion } from "framer-motion";
import { CheckIcon, CloseIcon } from "@/components/icons";
import { useFocusTrap } from "@/hooks/useFocusTrap";
import { useExecutarTransicao } from "@/hooks/useExecutarTransicao";
import {
  ASSINATURA_BASE64_MAX_BYTES,
  ROTA_LABELS,
  STATUS_LABELS,
  type ProvaResponse,
  type ScanResponse,
  type StatusProva,
} from "@/lib/types/prova";
import {
  badgeContextoMotorista,
  descricaoTransicao,
  exigeMotivo,
  isReprovacao,
  labelParaTransicao,
  tituloAssinatura,
} from "@/lib/assinatura/helpers";
import {
  CapturaAssinatura,
  type CapturaAssinaturaHandle,
} from "./CapturaAssinatura";
import styles from "./assinatura.module.css";

/** Easing canonico do projeto (espelha ENTER_EASE da /nova-prova e /escanear). */
const ENTER_EASE = [0.32, 0.72, 0, 1] as const;

/**
 * ID do `<h2>` que serve de `aria-labelledby` do modal. AUD-W8C22-006:
 * declarado uma vez para evitar duplicacao literal (duas `<h2>` do
 * `CabecalhoContexto` e do `ResultadoView` compartilham o mesmo id —
 * elas sao mutuamente exclusivas via `view`). O `data-modal-title`
 * complementar permite ao effect de foco programatico localizar o
 * titulo montado sem depender do id literal (`[data-modal-title]`).
 */
const TITULO_ID = "assinatura-titulo";

interface AssinaturaModalProps {
  /** Resposta do `/scan` — prova + transicoes permitidas para o usuario. */
  scan: ScanResponse;
  /** Devolve o JWT atual (mesma assinatura usada pelos demais hooks). */
  getToken: () => Promise<string | null>;
  /** Saida terminal do modal — a pagina navega para `/provas/[id]`. */
  onFechar: () => void;
}

type ModalView =
  | "selecionando" // vendedor escolhe Aprovar/Reprovar (> 1 transicao)
  | "assinando" // captura da assinatura (+ motivo se reprovacao)
  | "enviando" // submit em andamento
  | "sucesso" // movimentacao registrada
  | "conflito" // 409 — outro ator movimentou a prova (race)
  | "sessao" // 401 — sessao expirada
  | "erro"; // 422/404/outro — terminal generico (anti-enumeracao)

export function AssinaturaModal({
  scan,
  getToken,
  onFechar,
}: AssinaturaModalProps) {
  const router = useRouter();
  const reduzirMovimento = useReducedMotion();
  const focusTrapRef = useFocusTrap<HTMLDivElement>(true);
  const cardRef = useRef<HTMLDivElement>(null);
  const capturaRef = useRef<CapturaAssinaturaHandle>(null);
  // Desestrutura `executar` (estavel — useCallback interno do hook); os
  // demais campos do hook nao sao usados (o modal mantem seu proprio
  // `view`). Evita warning de exhaustive-deps no `submeter`.
  const { executar: executarTransicao } = useExecutarTransicao(getToken);

  const transicoes = scan.transicoes_permitidas;
  const multiplas = transicoes.length > 1;

  const [view, setView] = useState<ModalView>(
    multiplas ? "selecionando" : "assinando",
  );
  const [destino, setDestino] = useState<StatusProva | null>(
    multiplas ? null : (transicoes[0] ?? null),
  );
  const [motivo, setMotivo] = useState("");
  /** Erro retentavel exibido no estado "assinando" (falha de rede — D5). */
  const [erro, setErro] = useState<string | null>(null);
  /**
   * AUD-W8C22-008: status efetivamente aplicado vindo do backend
   * (`data.prova.status` no 201 da transicao). Usado na view de sucesso
   * em vez de `destino` para defesa em profundidade — se algum dia o
   * backend transformar o destino internamente antes de gravar, a view
   * mostraria o valor errado. Hoje sempre bate com `destino` (o backend
   * grava exatamente o que recebeu), mas a defesa nao custa.
   */
  const [statusAplicado, setStatusAplicado] = useState<StatusProva | null>(
    null,
  );

  // Esc fecha o modal (WAI-ARIA), exceto durante o envio.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && view !== "enviando") onFechar();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [view, onFechar]);

  // a11y: a cada troca de view, reposiciona o foco no titulo. Sem isto, o
  // elemento clicado (ex.: botao "Aprovar") desmonta e o foco cai no
  // body. O `<h2>` tem tabIndex={-1} para receber foco programatico.
  // AUD-W8C22-006: busca via `[data-modal-title]` em vez do id literal —
  // robusto a renomeacoes do id e suporta dois h2 mutuamente exclusivos
  // (CabecalhoContexto vs ResultadoView) sem depender de seletor de id.
  useEffect(() => {
    const titulo = cardRef.current?.querySelector<HTMLElement>(
      "[data-modal-title]",
    );
    titulo?.focus();
  }, [view]);

  const escolher = useCallback((d: StatusProva) => {
    setDestino(d);
    setErro(null);
    setView("assinando");
  }, []);

  const voltarSelecao = useCallback(() => {
    setDestino(null);
    setMotivo("");
    setErro(null);
    setView("selecionando");
  }, []);

  const submeter = useCallback(
    async (e: FormEvent<HTMLFormElement>) => {
      e.preventDefault();
      if (!destino) return;
      setErro(null);

      // Validacao client-side antes de tocar o backend.
      const captura = capturaRef.current;
      if (!captura || captura.isEmpty()) {
        setErro("A assinatura e obrigatoria.");
        return;
      }
      const precisa = exigeMotivo(scan, destino);
      const motivoLimpo = motivo.trim();
      if (precisa && !motivoLimpo) {
        setErro("O motivo da reprovacao e obrigatorio.");
        return;
      }
      const base64 = captura.toBase64();
      if (base64.length > ASSINATURA_BASE64_MAX_BYTES) {
        setErro("Assinatura muito complexa. Tente um traco mais simples.");
        return;
      }

      setView("enviando");
      const { data, isConflict, status } = await executarTransicao({
        provaId: scan.prova.id,
        statusNovo: destino,
        assinaturaBase64: base64,
        motivoReprovacao: precisa ? motivoLimpo : null,
      });

      if (data) {
        // AUD-W8C22-008: defesa em profundidade — usa o status do backend.
        setStatusAplicado(data.prova.status);
        setView("sucesso");
        return;
      }
      if (isConflict) {
        setView("conflito"); // 409 — race condition (Cenario 9)
        return;
      }
      if (status === 401) {
        setView("sessao");
        return;
      }
      // 5xx ou falha de rede (status null): retentavel — volta para
      // "assinando" mantendo a assinatura no canvas (D5).
      if (status === null || status >= 500) {
        setErro("Falha de conexao. Verifique a internet e tente novamente.");
        setView("assinando");
        return;
      }
      // 422/404/403 e demais: terminal generico. NUNCA exibir a mensagem
      // crua do backend (anti-enumeracao R-3 — pode listar setores).
      setView("erro");
    },
    [destino, motivo, scan, executarTransicao],
  );

  const enviando = view === "enviando";
  const ctxBadge = destino ? badgeContextoMotorista(destino) : null;
  const precisaMotivo = destino ? exigeMotivo(scan, destino) : false;

  return (
    <motion.div
      className={styles.backdrop}
      role="dialog"
      aria-modal="true"
      aria-labelledby={TITULO_ID}
      ref={focusTrapRef}
      initial={reduzirMovimento ? false : { opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: reduzirMovimento ? 0 : 0.18 }}
    >
      <motion.div
        className={styles.card}
        ref={cardRef}
        initial={
          reduzirMovimento ? false : { opacity: 0, scale: 0.96, y: 8 }
        }
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{
          duration: reduzirMovimento ? 0 : 0.22,
          ease: ENTER_EASE,
        }}
      >
        {view === "sucesso" && destino && (
          <ResultadoView
            tom="sucesso"
            titulo="Movimentacao registrada"
            onFechar={onFechar}
            botaoLabel="Ver prova"
          >
            <strong>{scan.prova.nome}</strong> agora esta em{" "}
            {/* AUD-W8C22-008: prefere o status efetivo do backend; fallback
                seguro para `destino` se algum dia `statusAplicado` ficar
                null (impossivel hoje — o setView("sucesso") so e chamado
                apos `setStatusAplicado(data.prova.status)`). */}
            <strong>{STATUS_LABELS[statusAplicado ?? destino]}</strong>.
          </ResultadoView>
        )}

        {view === "conflito" && (
          <ResultadoView
            tom="aviso"
            titulo="A prova foi movimentada"
            onFechar={onFechar}
            botaoLabel="Ver prova atualizada"
          >
            Outro usuario registrou uma movimentacao nesta prova enquanto
            voce assinava. Veja o estado atualizado.
          </ResultadoView>
        )}

        {view === "sessao" && (
          <ResultadoView
            tom="aviso"
            titulo="Sessao expirada"
            onFechar={onFechar}
            // AUD-W8C22-007: navega direto a /login. O fluxo antigo
            // (onFechar -> /provas/[id] -> middleware -> /login) e UX
            // subotima — o label "Fazer login" cria expectativa de ir
            // direto. O middleware ainda funciona como fallback se o
            // botao nao for clicado (modal pode ser fechado por Esc).
            onClickPrincipal={() => router.push("/login")}
            botaoLabel="Fazer login"
          >
            Sua sessao expirou. Faca login novamente para continuar.
          </ResultadoView>
        )}

        {view === "erro" && (
          <ResultadoView
            tom="aviso"
            titulo="Nao foi possivel registrar"
            onFechar={onFechar}
            botaoLabel="Ver prova"
          >
            Houve um problema ao registrar a movimentacao. Recarregue a
            pagina e tente novamente.
          </ResultadoView>
        )}

        {view === "selecionando" && (
          <>
            <CabecalhoContexto prova={scan.prova} titulo="Movimentar prova" />
            <p className={styles.descricao}>
              Voce e o proximo responsavel por esta prova. Escolha a acao
              para assinar e confirmar.
            </p>
            <div className={styles.selecaoBotoes}>
              {transicoes.map((d) => (
                <button
                  key={d}
                  type="button"
                  className={
                    isReprovacao(d)
                      ? styles.botaoReprovar
                      : styles.botaoAprovar
                  }
                  onClick={() => escolher(d)}
                >
                  {labelParaTransicao(d)}
                </button>
              ))}
            </div>
            <div className={styles.rodape}>
              <button
                type="button"
                className={styles.botaoSecundario}
                onClick={onFechar}
              >
                Cancelar
              </button>
            </div>
          </>
        )}

        {(view === "assinando" || view === "enviando") && destino && (
          <form className={styles.form} onSubmit={submeter}>
            <CabecalhoContexto
              prova={scan.prova}
              titulo={tituloAssinatura(destino)}
            />
            <p className={styles.transicao}>
              {descricaoTransicao(scan.prova.status, destino)}
            </p>
            {ctxBadge && <p className={styles.contextoBadge}>{ctxBadge}</p>}

            {precisaMotivo && (
              <div className={styles.campo}>
                <label
                  htmlFor="motivo-reprovacao"
                  className={styles.label}
                >
                  Motivo da reprovacao
                </label>
                <textarea
                  id="motivo-reprovacao"
                  className={styles.textarea}
                  value={motivo}
                  onChange={(ev) => setMotivo(ev.target.value)}
                  maxLength={1000}
                  placeholder="Descreva o que precisa ser corrigido."
                  disabled={enviando}
                  required
                />
              </div>
            )}

            <div className={styles.campo}>
              <span className={styles.label}>Assinatura</span>
              <CapturaAssinatura ref={capturaRef} disabled={enviando} />
            </div>

            {erro && (
              <div className={styles.erroBanner} role="alert">
                {erro}
              </div>
            )}

            <div className={styles.rodape}>
              {multiplas && (
                <button
                  type="button"
                  className={styles.botaoSecundario}
                  onClick={voltarSelecao}
                  disabled={enviando}
                >
                  Voltar
                </button>
              )}
              <button
                type="button"
                className={styles.botaoSecundario}
                onClick={onFechar}
                disabled={enviando}
              >
                Cancelar
              </button>
              <button
                type="submit"
                className={
                  isReprovacao(destino)
                    ? styles.botaoReprovar
                    : styles.botaoAprovar
                }
                disabled={enviando}
              >
                {enviando ? "Registrando..." : "Confirmar"}
              </button>
            </div>
          </form>
        )}
      </motion.div>
    </motion.div>
  );
}

/* ──────────────────────────────────────────────────────────────────── */
/* Sub-componentes                                                      */
/* ──────────────────────────────────────────────────────────────────── */

/** Cabecalho com o titulo (focavel para a11y) + identificacao da prova. */
function CabecalhoContexto({
  prova,
  titulo,
}: {
  prova: ProvaResponse;
  titulo: string;
}) {
  return (
    <header className={styles.cabecalho}>
      <h2
        id={TITULO_ID}
        className={styles.titulo}
        data-modal-title
        tabIndex={-1}
      >
        {titulo}
      </h2>
      <div className={styles.provaInfo}>
        <span className={styles.provaNome}>{prova.nome}</span>
        <span className={styles.provaMeta}>
          {prova.codigo_publico}
          {prova.rota ? ` · ${ROTA_LABELS[prova.rota]}` : ""}
        </span>
      </div>
    </header>
  );
}

/** View terminal de resultado — sucesso ou aviso (conflito/sessao/erro). */
function ResultadoView({
  tom,
  titulo,
  botaoLabel,
  onFechar,
  onClickPrincipal,
  children,
}: {
  tom: "sucesso" | "aviso";
  titulo: string;
  botaoLabel: string;
  onFechar: () => void;
  /**
   * AUD-W8C22-007: handler opcional do botao principal. Se nao informado,
   * usa `onFechar` (saida terminal padrao). Usado pela view "sessao" para
   * navegar diretamente a `/login` em vez de cair em `/provas/[id]` →
   * middleware → `/login` (UX subotima).
   */
  onClickPrincipal?: () => void;
  children: ReactNode;
}) {
  return (
    <div className={styles.resultado}>
      <span
        className={
          tom === "sucesso"
            ? styles.resultadoIconeSucesso
            : styles.resultadoIconeAviso
        }
        aria-hidden="true"
      >
        {tom === "sucesso" ? (
          <CheckIcon width={30} height={30} />
        ) : (
          <CloseIcon width={28} height={28} />
        )}
      </span>
      <h2
        id={TITULO_ID}
        className={styles.titulo}
        data-modal-title
        tabIndex={-1}
      >
        {titulo}
      </h2>
      <p className={styles.resultadoTexto}>{children}</p>
      <button
        type="button"
        className={styles.botaoAprovar}
        onClick={onClickPrincipal ?? onFechar}
      >
        {botaoLabel}
      </button>
    </div>
  );
}
