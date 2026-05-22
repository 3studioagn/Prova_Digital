# Arqueologia de Codigo — Componente 22 (Wave 8 v5.0)

**Sessao:** Wave 8 v5.0 / C22 — Reativacao da Tela de Assinatura no Fluxo de Escaneamento
**Tipo:** Investigacao read-only de historico Git — fase preliminar do Gate 1 (prompt Secao 2.1)
**Data:** 2026-05-22
**Branch base:** `development`
**Status:** CONCLUIDA — recuperacao bem-sucedida (codigo recuperado verbatim, zero lacunas bloqueantes)

---

## 0. Objetivo e metodo

O frontend da "tela de assinatura" foi descontinuado no redesenho do
Componente 10 (Scanner) durante a Wave 3 v4.0. Hoje, o ator escaneia uma
prova, ela e identificada corretamente, mas **nao ha como assinar para
movimenta-la** — o `/escanear` apenas redireciona para `/provas/[id]`.

Esta arqueologia recupera o codigo da tela de assinatura original do
historico Git para que o C22 possa reativa-la com fidelidade.

**Metodo (read-only, sem checkout, sem modificacao):**

- `git log --oneline --all -- <arquivos>` para localizar o redesenho.
- `git show <sha>:<path>` para recuperar conteudo de commits antigos.
- `git ls-files` + leitura dos arquivos atuais para comparar `development`.

---

## 1. Commits identificados

### 1.1 Commit PRE-redesenho (ultimo com a UI de assinatura intacta)

| Campo | Valor |
|---|---|
| SHA curto | `6add246` |
| SHA completo | `6add2462fd0c51703ddba8d0a3f5494fdf26480d` |
| Mensagem | `Wave 04 concluida` |
| Data | 2026-04-14 11:03:12 -0300 |
| `escanear/page.tsx` | **740 LOC** com a UI de assinatura completa |

> A fluidez do canvas de assinatura recebeu correcoes em `63a50f3`
> (`fix(wave-3/review-c11): corrigir bugs + fluidez da assinatura + UX do C11`,
> 2026-04-13). `6add246` e o ultimo commit antes do redesenho tocar o arquivo
> — e a fonte canonica de recuperacao.

### 1.2 Commit do REDESENHO (removeu a UI de assinatura)

| Campo | Valor |
|---|---|
| SHA curto | `e4d543b` |
| SHA completo | `e4d543b859e7fd1e5cc35f41d55d75257c63adb6` |
| Mensagem | `feat(wave3-v4/c10): frontend — scanner reformulado + camada de servico desacoplada` |
| Data | 2026-05-07 09:16:44 -0300 |
| Branch | `wave3-v4/componente-10` (depois mergeado em `development`) |

Diffstat do `e4d543b`:

```
 frontend/src/app/(dashboard)/escanear/escanear.module.css  | 830 +++++-----
 frontend/src/app/(dashboard)/escanear/page.tsx             | 1057 ++++------
 frontend/src/hooks/useScanProva.ts                         |  91 --   (ARQUIVO DELETADO)
 3 files changed, 837 insertions(+), 1141 deletions(-)
```

---

## 2. Correcao factual ao CHANGELOG / CLAUDE.md

O CHANGELOG afirma que `react-signature-canvas` e `@types/react-signature-canvas`
foram **removidos do `package.json`** no redesenho. **Isso e FALSO.**

Ambos os pacotes continuam declarados em `frontend/package.json` em **todas as
branches**, incluindo `development` atual:

```json
"react-signature-canvas": "^1.0.7"          // dependencies
"@types/react-signature-canvas": "^1.0.7"   // devDependencies
```

O redesenho `e4d543b` removeu apenas o **import e uso** da biblioteca em
`page.tsx`. As entradas do `package.json` nunca foram limpas — sao
**dependencias orfas**. **Boa noticia para o C22:** a biblioteca de captura
de assinatura ja esta instalada e disponivel; nao e preciso adicionar
dependencia nova.

---

## 3. Inventario: removido vs preservado em `development`

| Artefato | Estado em `development` | Observacao |
|---|---|---|
| `AssinaturaModal` (componente) | **DELETADO** | Reescrito em `e4d543b`. Recuperavel verbatim (Secao 6.3). |
| `ScanReadyView`, `DoneView`, `ErrorView`, `IdleView`, `ScanningView` | **DELETADO** | Sub-componentes inline no `page.tsx` original. |
| Maquina de estados `PageState` da pagina | **DELETADO** | Uniao discriminada de 8 estados. |
| `useScanProva.ts` (hook) | **DELETADO** (`-91 LOC`) | Recuperavel verbatim (Secao 6.5). |
| `useExecutarTransicao.ts` (hook) | **PRESERVADO** ⚠️ | Ainda existe em `development`, mas ORFAO — nenhum arquivo o importa. POSTa para `/{id}/transicoes`. **C22 pode reusar diretamente.** |
| `useScanner.ts`, `useFocusTrap.ts` | **PRESERVADO** | `useScanner` ainda usado pelo `page.tsx` atual; `useFocusTrap` reusavel para o modal. |
| CSS do modal/canvas (`escanear.module.css`) | **DELETADO** | Arquivo CSS reescrito por completo. Classes recuperaveis (Secao 6.4). |
| `react-signature-canvas` (npm) | **PRESERVADO** ⚠️ | Orfao mas instalado — `^1.0.7`. |
| `ScanResponse` (tipo) | **PRESERVADO** | `prova.ts` — `prova` + `transicoes_permitidas` + `motivo_obrigatorio_em`. |
| `TransicaoRequest` / `TransicaoResponse` (tipos) | **PRESERVADO** | `prova.ts` — formato identico. |
| `ASSINATURA_BASE64_MAX_BYTES` | **PRESERVADO** | `prova.ts` — `= 700_000`. |
| Endpoint `POST /{id}/transicoes` | **PRESERVADO** | Backend 100% intacto e operacional (ver `analysis.md` §5.2). |
| Tokens CSS (`--color-overlay`, `--color-danger-soft`, etc.) | **PRESERVADOS** | Confirmados em `globals.css` — a recuperacao do CSS funciona sem ajuste. |

**Conclusao:** o que foi removido e **exclusivamente a camada de UI**. O
contrato de backend, os tipos TypeScript, o hook `useExecutarTransicao` e o
pacote `react-signature-canvas` estao todos intactos. A reativacao do C22 e
um esforco de **reconstrucao de UI** — sem trabalho de backend nem de tipos.

---

## 4. Mecanismo de captura de assinatura recuperado

O sistema original capturava a assinatura com **`react-signature-canvas`**:

- Componente `<SigCanvas>` (default export de `react-signature-canvas`).
- Canvas HTML onde o usuario desenha com **dedo (touch) ou mouse**.
- Export via `sigRef.current.getCanvas().toDataURL("image/png")`.
- Strip do prefixo `data:image/png;base64,` com `.split(",")[1]`.
- Validacao de tamanho contra `ASSINATURA_BASE64_MAX_BYTES` (700_000 chars).
- Largura do canvas dimensionada por `ResizeObserver` (mobile-first).
- `width` setado pela largura real do container; `height` fixo 200px (180px
  em telas ≤640px).

Esse e o mecanismo confirmado para a **Decisao 2** do Gate 1 (o solicitante
disse "vamos usar o mesmo que ja estavamos fazendo"). Nao havia PIN nem
biometria — sempre foi canvas de tracado.

---

## 5. Discrepancia de metrica (nao-bloqueante)

O CHANGELOG diz que o `page.tsx` redesenhado tem "~414 LOC". No commit do
redesenho (`e4d543b`) o arquivo tem **545 LOC**; em `development` atual tem
**777 LOC** (apos C19 + iteracoes visuais). Discrepancia de documentacao,
nao de recuperacao — ambas as versoes reais sao acessiveis.

---

## 6. Codigo recuperado (verbatim)

> Fonte: `git show 6add246:<path>`. Reproduzido integralmente — a
> completude do codigo recuperado importa mais que a brevidade (o Gate 2
> reconstroi a partir daqui).

### 6.1 `frontend/src/app/(dashboard)/escanear/page.tsx` — maquina de estados da pagina + orquestracao

```tsx
type PageState =
  | { kind: "idle" }
  | { kind: "scanning" }
  | { kind: "scan-loading"; payload: string }
  | { kind: "scan-ready"; scan: ScanResponse }
  | {
      kind: "signing";
      scan: ScanResponse;
      statusNovo: StatusProva;
      precisaMotivo: boolean;
    }
  | {
      kind: "submitting";
      scan: ScanResponse;
      statusNovo: StatusProva;
      precisaMotivo: boolean;
    }
  | {
      kind: "done";
      scan: ScanResponse;
      statusAplicado: StatusProva;
    }
  | { kind: "scan-error"; message: string };
```

Labels de botao por transicao (pt-BR), com fallback para `STATUS_LABELS`:

```tsx
const ACTION_LABELS: Partial<Record<StatusProva, string>> = {
  RETIRADA_PELO_VENDEDOR: "Retirar prova",
  APROVADA_PELO_VENDEDOR: "Aprovar",
  REPROVADA_PELO_VENDEDOR: "Reprovar",
  DE_VOLTA_3STUDIO: "Devolver a 3Studio",
  ENCAMINHADA_A_CLICHERIA: "Encaminhar a clicheria",
  COM_MOTORISTA: "Enviar ao motorista",
  ENVIADA_PARA_CLICHERIA: "Confirmar transporte",
  RECEBIDA_PELA_CLICHERIA: "Confirmar recebimento",
};

function labelParaTransicao(destino: StatusProva): string {
  return ACTION_LABELS[destino] ?? STATUS_LABELS[destino];
}
```

> NOTA C22: este `ACTION_LABELS` esta no vocabulario v3.0 (9 estados). O C22
> precisa estende-lo para os 7 estados v4.0 (ver `analysis.md` §5.3 + §5.9).

Orquestracao da escolha de transicao e do submit (do componente principal):

```tsx
const escolherTransicao = useCallback(
  (destino: StatusProva) => {
    if (state.kind !== "scan-ready") return;
    const precisaMotivo = state.scan.motivo_obrigatorio_em.includes(destino);
    setState({
      kind: "signing",
      scan: state.scan,
      statusNovo: destino,
      precisaMotivo,
    });
  },
  [state],
);

const submeterTransicao = useCallback(
  async (assinaturaBase64: string, motivo: string | null) => {
    if (state.kind !== "signing") return;
    const provaId = state.scan.prova.id;
    const statusNovo = state.statusNovo;

    setState({
      kind: "submitting",
      scan: state.scan,
      statusNovo,
      precisaMotivo: state.precisaMotivo,
    });
    const { data, error, isConflict } = await transicaoHook.executar({
      provaId,
      statusNovo,
      assinaturaBase64,
      motivoReprovacao: motivo,
    });

    if (!data) {
      if (isConflict) {
        // B-03: 409 = status mudou. Volta ao inicio para re-escanear.
        setState({
          kind: "scan-error",
          message: error ?? "O status da prova mudou. Escaneie novamente.",
        });
        return;
      }
      // Volta para `signing` para o usuario poder retentar
      setState({
        kind: "signing",
        scan: state.scan,
        statusNovo,
        precisaMotivo: state.precisaMotivo,
      });
      return;
    }

    setState({
      kind: "done",
      scan: { ...state.scan, prova: data.prova },
      statusAplicado: statusNovo,
    });
  },
  [state, transicaoHook],
);
```

Renderizacao do bloco de assinatura (modal SOBRE o `ScanReadyView` readOnly):

```tsx
{(state.kind === "signing" || state.kind === "submitting") && (
  <>
    <ScanReadyView
      scan={state.scan}
      onEscolher={() => {/* opaco — modal esta aberto */}}
      onCancelar={resetar}
      readOnly
    />
    <AssinaturaModal
      statusAtual={state.scan.prova.status}
      statusNovo={state.statusNovo}
      precisaMotivo={state.precisaMotivo}
      loading={state.kind === "submitting"}
      error={transicaoHook.error}
      onCancelar={cancelarAssinatura}
      onConfirmar={submeterTransicao}
    />
  </>
)}
```

### 6.2 `ScanReadyView` — lista `transicoes_permitidas` como botoes

```tsx
function ScanReadyView({
  scan,
  onEscolher,
  onCancelar,
  readOnly = false,
}: {
  scan: ScanResponse;
  onEscolher: (destino: StatusProva) => void;
  onCancelar: () => void;
  readOnly?: boolean;
}) {
  const { prova, transicoes_permitidas } = scan;
  return (
    <>
      <div className={styles.provaCard}>
        <div className={styles.provaCardHeader}>
          <div>
            <div className={styles.provaNome}>{prova.nome}</div>
            <div className={styles.provaNroReq}>{prova.nro_requerimento}</div>
          </div>
          <span className={styles.statusBadge}>
            {STATUS_LABELS[prova.status]}
          </span>
        </div>
        <div className={styles.provaInfoGrid}>
          <div>
            <div className={styles.provaInfoLabel}>Cliente</div>
            <div className={styles.provaInfoValue}>{prova.cliente}</div>
          </div>
          <div>
            <div className={styles.provaInfoLabel}>Vendedor</div>
            <div className={styles.provaInfoValue}>{prova.vendedor_nome}</div>
          </div>
          {prova.rota && (
            <div>
              <div className={styles.provaInfoLabel}>Rota</div>
              <div className={styles.provaInfoValue}>
                {ROTA_LABELS[prova.rota]}
              </div>
            </div>
          )}
          <div>
            <div className={styles.provaInfoLabel}>Ciclo</div>
            <div className={styles.provaInfoValue}>{prova.ciclo_atual}</div>
          </div>
        </div>
      </div>

      <div className={styles.actionsWrapper}>
        <div className={styles.actionsTitle}>Acoes disponiveis</div>
        {transicoes_permitidas.length === 0 ? (
          <p className={styles.noActions}>
            {prova.status === "CANCELADA" || prova.status === "RECEBIDA_PELA_CLICHERIA"
              ? `Esta prova ja foi finalizada (${STATUS_LABELS[prova.status]}).`
              : "Voce nao tem permissao para movimentar esta prova no estado atual."}
          </p>
        ) : (
          <>
            <p className={styles.actionsHint}>
              Escolha uma acao abaixo e assine para confirmar.
            </p>
            <div className={styles.actionsList}>
              {transicoes_permitidas.map((destino) => {
                const reprovar = destino === "REPROVADA_PELO_VENDEDOR";
                const cls = reprovar ? styles.dangerButton : styles.primaryButton;
                return (
                  <button
                    key={destino}
                    type="button"
                    className={cls}
                    disabled={readOnly}
                    onClick={() => onEscolher(destino)}
                  >
                    {labelParaTransicao(destino)}
                  </button>
                );
              })}
            </div>
          </>
        )}
        <div style={{ marginTop: "1rem" }}>
          <button
            type="button"
            className={styles.secondaryButton}
            onClick={onCancelar}
            disabled={readOnly}
          >
            Escanear outra
          </button>
        </div>
      </div>
    </>
  );
}
```

> NOTA C22: o tratamento de "estado terminal" e "sem permissao" ja estava
> presente (bloco `transicoes_permitidas.length === 0`). **Atencao
> anti-enumeracao (RN-014 v5.0):** o original DISTINGUE "ja finalizada" de
> "sem permissao" — o C22 precisa **uniformizar** ambos para uma mensagem
> generica (ver `analysis.md` Decisao 6 e Decisao 8).

### 6.3 `AssinaturaModal` — componente central recuperado (verbatim)

```tsx
function AssinaturaModal({
  statusAtual,
  statusNovo,
  precisaMotivo,
  loading,
  error,
  onCancelar,
  onConfirmar,
}: {
  statusAtual: StatusProva;
  statusNovo: StatusProva;
  precisaMotivo: boolean;
  loading: boolean;
  error: string | null;
  onCancelar: () => void;
  onConfirmar: (assinaturaBase64: string, motivo: string | null) => void;
}) {
  const sigRef = useRef<SignatureCanvas | null>(null);
  const canvasContainerRef = useRef<HTMLDivElement>(null);
  const focusTrapRef = useFocusTrap<HTMLDivElement>(true);
  const [canvasWidth, setCanvasWidth] = useState(0);
  const [motivo, setMotivo] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);

  // B-02: Dimensionar canvas pela largura real do container (mobile-first).
  useEffect(() => {
    const el = canvasContainerRef.current;
    if (!el) return;
    const update = () => {
      const w = el.clientWidth;
      if (w > 0) setCanvasWidth(w);
    };
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // D-04: Fechar modal com Escape (WAI-ARIA).
  useEffect(() => {
    if (loading) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCancelar();
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [loading, onCancelar]);

  const label = labelParaTransicao(statusNovo);
  const isReprovar = statusNovo === "REPROVADA_PELO_VENDEDOR";
  const titulo = isReprovar ? "Reprovar prova" : `Confirmar: ${label}`;
  const descricao = isReprovar
    ? "Descreva o motivo da reprovacao e assine para confirmar."
    : "Assine no quadro abaixo para confirmar a movimentacao.";
  const transicaoLabel = `${STATUS_LABELS[statusAtual]} → ${STATUS_LABELS[statusNovo]}`;

  const handleLimpar = useCallback(() => {
    sigRef.current?.clear();
    setLocalError(null);
  }, []);

  const handleSubmit = useCallback(
    (e: FormEvent<HTMLFormElement>) => {
      e.preventDefault();
      setLocalError(null);

      const canvas = sigRef.current;
      if (!canvas || canvas.isEmpty()) {
        setLocalError("Assinatura e obrigatoria.");
        return;
      }
      if (precisaMotivo && !motivo.trim()) {
        setLocalError("Motivo da reprovacao e obrigatorio.");
        return;
      }

      // Exporta como dataURL e remove o prefixo `data:image/png;base64,`.
      const dataUrl = canvas.getCanvas().toDataURL("image/png");
      const base64 = dataUrl.split(",")[1] ?? "";

      if (base64.length > ASSINATURA_BASE64_MAX_BYTES) {
        setLocalError("Assinatura muito complexa. Tente um traco mais simples.");
        return;
      }

      onConfirmar(base64, precisaMotivo ? motivo.trim() : null);
    },
    [precisaMotivo, motivo, onConfirmar],
  );

  const displayError = error ?? localError;

  return (
    <div
      className={styles.modalBackdrop}
      role="dialog"
      aria-modal="true"
      aria-labelledby="assinatura-modal-title"
      ref={focusTrapRef}
    >
      <form className={styles.modalCard} onSubmit={handleSubmit}>
        <h2 id="assinatura-modal-title" className={styles.modalTitle}>
          {titulo}
        </h2>
        <p className={styles.modalDescription}>{descricao}</p>
        <p className={styles.modalTransicao}>{transicaoLabel}</p>

        {precisaMotivo && (
          <div className={styles.modalField}>
            <label className={styles.modalLabel} htmlFor="motivo-reprovacao">
              Motivo da reprovacao
            </label>
            <textarea
              id="motivo-reprovacao"
              className={styles.modalTextarea}
              value={motivo}
              onChange={(e) => setMotivo(e.target.value)}
              maxLength={1000}
              placeholder="Ex: Cor do logo errada"
              required
            />
          </div>
        )}

        <div className={styles.signatureWrapper}>
          <label className={styles.modalLabel}>Assinatura</label>
          <div ref={canvasContainerRef}>
            {canvasWidth > 0 && (
              <SigCanvas
                ref={sigRef}
                penColor="#000000"
                backgroundColor="#ffffff"
                canvasProps={{
                  className: styles.signatureCanvas,
                  width: canvasWidth,
                  height: 200,
                }}
              />
            )}
          </div>
          <div className={styles.signatureActions}>
            <span className={styles.signatureHint}>
              Assine com o dedo ou mouse no quadro acima.
            </span>
            <button
              type="button"
              className={styles.clearButton}
              onClick={handleLimpar}
            >
              Limpar
            </button>
          </div>
        </div>

        {displayError && (
          <div className={styles.modalError} role="alert">
            {displayError}
          </div>
        )}

        <div className={styles.modalFooter}>
          <button
            type="button"
            className={styles.secondaryButton}
            onClick={onCancelar}
            disabled={loading}
          >
            Cancelar
          </button>
          <button
            type="submit"
            className={isReprovar ? styles.dangerButton : styles.primaryButton}
            disabled={loading}
          >
            {loading ? "Enviando..." : "Confirmar"}
          </button>
        </div>
      </form>
    </div>
  );
}
```

Imports de `react-signature-canvas` (linhas 11-12 do `page.tsx` original):

```tsx
import type SignatureCanvas from "react-signature-canvas";
import SigCanvas from "react-signature-canvas";
```

### 6.4 `DoneView` e `ErrorView`

```tsx
function DoneView({
  scan,
  statusAplicado,
  onNovaLeitura,
}: {
  scan: ScanResponse;
  statusAplicado: StatusProva;
  onNovaLeitura: () => void;
}) {
  const mensagem = useMemo(() => {
    const labelAcao = ACTION_LABELS[statusAplicado] ?? STATUS_LABELS[statusAplicado];
    return `${labelAcao} — movimentacao registrada.`;
  }, [statusAplicado]);

  return (
    <div className={styles.successCard}>
      <div className={styles.successIcon} aria-hidden="true">✓</div>
      <div className={styles.successTitle}>Tudo certo!</div>
      <p className={styles.successMessage}>
        <strong>{scan.prova.nome}</strong> — {mensagem}
      </p>
      <span className={styles.statusBadge}>
        {STATUS_LABELS[scan.prova.status]}
      </span>
      <button type="button" className={styles.primaryButton} onClick={onNovaLeitura}>
        Escanear proxima
      </button>
    </div>
  );
}

function ErrorView({
  message,
  onTentarNovamente,
}: {
  message: string;
  onTentarNovamente: () => void;
}) {
  return (
    <div className={styles.errorCard}>
      <div className={styles.errorTitle}>Nao foi possivel escanear</div>
      <p className={styles.errorMessage}>{message}</p>
      <button type="button" className={styles.primaryButton} onClick={onTentarNovamente}>
        Tentar novamente
      </button>
    </div>
  );
}
```

### 6.5 `escanear.module.css` — classes do modal/canvas (verbatim, `6add246`)

```css
.modalBackdrop {
  position: fixed;
  inset: 0;
  background: var(--color-overlay);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}

.modalCard {
  background: var(--color-card-bg);
  border-radius: var(--radius-card-lg);
  padding: 2rem;
  max-width: 560px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.modalTitle { font-size: var(--fs-h2); font-weight: 500; color: var(--color-card-text); }
.modalDescription { font-size: var(--fs-base); color: var(--color-card-text-muted); }
.modalTransicao {
  font-size: var(--fs-sm);
  font-weight: 500;
  color: var(--color-card-text);
  padding: 0.5rem 0.75rem;
  background: var(--color-card-surface-alt);
  border-radius: var(--radius-sm);
}
.modalField { display: flex; flex-direction: column; gap: 0.5rem; }
.modalLabel { font-size: var(--fs-sm); font-weight: 500; color: var(--color-card-text); }
.modalTextarea {
  width: 100%;
  min-height: 80px;
  padding: 0.75rem 1rem;
  background: var(--color-card-bg);
  border: 1px solid var(--color-card-border);
  border-radius: var(--radius-card);
  font-family: var(--font-family);
  font-size: var(--fs-base);
  color: var(--color-card-text);
  resize: vertical;
}
.modalTextarea:focus { outline: 2px solid var(--color-accent); outline-offset: 1px; }

.signatureWrapper { display: flex; flex-direction: column; gap: 0.5rem; }
.signatureCanvas {
  background: #ffffff;
  border: 2px dashed var(--color-card-border);
  border-radius: var(--radius-card);
  width: 100%;
  touch-action: none;
  cursor: crosshair;
}
.signatureActions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.signatureHint { font-size: var(--fs-xs); color: var(--color-card-text-muted); }
.clearButton {
  background: none;
  border: none;
  color: var(--color-card-text-muted);
  cursor: pointer;
  font-size: var(--fs-sm);
  padding: 0.25rem 0.5rem;
  text-decoration: underline;
}
.clearButton:hover { color: var(--color-card-text); }

.modalFooter {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin-top: 0.5rem;
}
.modalError {
  padding: 0.75rem 1rem;
  background: var(--color-danger-soft);
  color: var(--color-danger);
  border-radius: var(--radius-sm);
  font-size: var(--fs-sm);
}

@media (max-width: 640px) {
  .modalCard { padding: 1.25rem; }
  .signatureCanvas { height: 180px; }
}
```

> Todos os tokens referenciados (`--color-overlay`, `--color-card-bg`,
> `--color-card-surface-alt`, `--color-card-text`, `--color-card-border`,
> `--color-accent`, `--color-danger`, `--color-danger-soft`, `--radius-card`,
> `--radius-card-lg`) foram **confirmados presentes** em
> `frontend/src/app/globals.css`. `--radius-sm`, `--fs-*` e `--font-family`
> tambem devem ser confirmados no Gate 2 (uso disseminado no projeto).

### 6.6 `useScanProva.ts` — hook DELETADO (verbatim, `6add246`)

```tsx
"use client";

import { useCallback, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import type { ScanResponse } from "@/lib/types/prova";

interface ScanState {
  loading: boolean;
  error: string | null;
  result: ScanResponse | null;
}

const INITIAL: ScanState = { loading: false, error: null, result: null };

export function useScanProva(getToken: () => Promise<string | null>) {
  const [state, setState] = useState<ScanState>(INITIAL);
  const reset = useCallback(() => setState(INITIAL), []);

  const escanear = useCallback(
    async (
      payload: string,
    ): Promise<{ data: ScanResponse | null; error: string | null }> => {
      setState({ loading: true, error: null, result: null });

      let token: string | null;
      try {
        token = await getToken();
      } catch {
        token = null;
      }
      if (!token) {
        const error = "Sessao expirada. Faca login novamente.";
        setState({ loading: false, error, result: null });
        return { data: null, error };
      }

      try {
        const result = await apiFetch<ScanResponse>("/api/v1/provas/scan", {
          method: "POST",
          token,
          body: JSON.stringify({ payload }),
        });
        setState({ loading: false, error: null, result });
        return { data: result, error: null };
      } catch (err) {
        let msg = "Nao foi possivel resolver o QR Code.";
        if (err instanceof ApiError) {
          if (err.status === 401) msg = "Sessao expirada. Faca login novamente.";
          else if (err.status === 404) msg = "Prova nao encontrada.";
          else if (err.status === 422) msg = err.message;
          else if (err.status >= 500) msg = "Falha de conexao. Tente novamente em instantes.";
          else msg = err.message;
        }
        setState({ loading: false, error: msg, result: null });
        return { data: null, error: msg };
      }
    },
    [getToken],
  );

  return { ...state, escanear, reset };
}
```

> NOTA C22: `useScanProva` esta **superado** pela camada de servico
> `frontend/src/lib/services/identificacao-prova.ts` (entregue no C10 v4.0).
> O C22 **NAO** deve recriar `useScanProva` — deve consumir a camada de
> servico existente (que ja e usada pelo `escanear/page.tsx` atual).

### 6.7 `useExecutarTransicao.ts` — hook PRESERVADO em `development` (orfao)

Ainda existe em `frontend/src/hooks/useExecutarTransicao.ts`. Nenhum
arquivo o importa hoje (codigo orfao desde o redesenho do C10). **O C22
pode reativa-lo diretamente — zero recriacao necessaria.**

```tsx
"use client";

import { useCallback, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import type { StatusProva, TransicaoResponse } from "@/lib/types/prova";

interface ExecutarTransicaoState {
  loading: boolean;
  error: string | null;
  result: TransicaoResponse | null;
}

const INITIAL: ExecutarTransicaoState = { loading: false, error: null, result: null };

interface ExecutarTransicaoInput {
  provaId: string;
  statusNovo: StatusProva;
  assinaturaBase64: string;
  motivoReprovacao?: string | null;
}

export function useExecutarTransicao(getToken: () => Promise<string | null>) {
  const [state, setState] = useState<ExecutarTransicaoState>(INITIAL);
  const reset = useCallback(() => setState(INITIAL), []);

  const executar = useCallback(
    async (
      input: ExecutarTransicaoInput,
    ): Promise<{
      data: TransicaoResponse | null;
      error: string | null;
      isConflict: boolean;
    }> => {
      setState({ loading: true, error: null, result: null });

      let token: string | null;
      try {
        token = await getToken();
      } catch {
        token = null;
      }
      if (!token) {
        const error = "Sessao expirada. Faca login novamente.";
        setState({ loading: false, error, result: null });
        return { data: null, error, isConflict: false };
      }

      try {
        const result = await apiFetch<TransicaoResponse>(
          `/api/v1/provas/${input.provaId}/transicoes`,
          {
            method: "POST",
            token,
            body: JSON.stringify({
              status_novo: input.statusNovo,
              assinatura_base64: input.assinaturaBase64,
              motivo_reprovacao: input.motivoReprovacao ?? null,
            }),
          },
        );
        setState({ loading: false, error: null, result });
        return { data: result, error: null, isConflict: false };
      } catch (err) {
        let msg = "Nao foi possivel executar a transicao.";
        let isConflict = false;
        if (err instanceof ApiError) {
          if (err.status === 401) msg = "Sessao expirada. Faca login novamente.";
          else if (err.status === 404) msg = "Prova nao encontrada.";
          else if (err.status === 409) {
            msg = "O status da prova mudou. Escaneie novamente.";
            isConflict = true;
          } else if (err.status === 422) msg = err.message;
          else if (err.status >= 500) msg = "Falha de conexao. Tente novamente em instantes.";
          else msg = err.message;
        }
        setState({ loading: false, error: msg, result: null });
        return { data: null, error: msg, isConflict };
      }
    },
    [getToken],
  );

  return { ...state, executar, reset };
}
```

> NOTA C22 (anti-enumeracao): o mapeamento `422 -> err.message` repassa a
> mensagem crua do backend. No fluxo normal isso e seguro (422 = "motivo
> obrigatorio"). Mas o backend pode retornar `AtorNaoAutorizadoError` como
> 422 com texto que LISTA os setores permitidos. O C22 nunca deve cair
> nesse caminho no fluxo feliz (so renderiza assinatura quando
> `transicoes_permitidas` e nao-vazio), mas o tratamento de erro do C22
> deve **mapear 422 inesperado para mensagem generica** — ver
> `analysis.md` §5.9 R-3.

### 6.8 `prova.ts` — tipos de scan/transicao PRESERVADOS em `development`

```ts
export interface ScanResponse {
  prova: ProvaResponse;
  transicoes_permitidas: StatusProva[];
  motivo_obrigatorio_em: StatusProva[];
}

export interface TransicaoRequest {
  status_novo: StatusProva;
  assinatura_base64: string;       // PNG base64 sem o prefixo data:; max 700_000 chars
  motivo_reprovacao?: string | null;
}

export interface TransicaoResponse {
  prova: ProvaResponse;
  movimentacao: MovimentacaoResponse;
}

export const ASSINATURA_BASE64_MAX_BYTES = 700_000;
```

`ScanRequest` evoluiu no C10 v4.0 (de `{ payload }` para `{ payload?; codigo? }`)
— mas isso e transparente para o C22, que consome a camada de servico
`identificacao-prova.ts`, nao o tipo cru.

---

## 7. Analise de reuso: verbatim vs adaptar

| Artefato recuperado | Recomendacao para o C22 |
|---|---|
| `AssinaturaModal` | **Reusar como base** — recriar como componente proprio em `components/assinatura/`. Adaptar: (a) labels v4.0; (b) anti-enumeracao; (c) seletor Aprovar/Reprovar explicito (RF-008). |
| `react-signature-canvas` + canvas | **Reusar verbatim** — pacote ja instalado; mecanismo confirmado (Decisao 2). |
| `escanear.module.css` (classes do modal) | **Reusar verbatim** — todos os tokens existem. Migrar para CSS Module do novo componente. |
| `useExecutarTransicao.ts` | **Reusar diretamente** — hook intacto e funcional, so esta orfao. |
| `useFocusTrap.ts` | **Reusar verbatim** — ja presente, usado para focus trap WCAG do modal. |
| `useScanProva.ts` | **NAO reusar** — superado por `identificacao-prova.ts`. |
| `PageState` (maquina da pagina) | **Adaptar** — a maquina do `escanear/page.tsx` atual e diferente (`cameraState`/`manualState`). O C22 adiciona um estado de "assinatura aberta" sem reescrever a maquina do C10. |
| `ScanReadyView` | **Nao reusar como esta** — o `escanear/page.tsx` atual ja renderiza identificacao. O C22 nao precisa de "card da prova" intermediario; pode abrir o modal direto apos identificacao (RF-028 "automaticamente"). |
| `IdleView` / `ScanningView` | **Nao reusar** — sao do scanner pre-redesenho, ja substituidos por `CameraPanel`/`ManualPanel`. |
| `DoneView` / `ErrorView` | **Reusar como base** para `FeedbackSucesso`/`FeedbackErro`. |
| `ACTION_LABELS` | **Adaptar/estender** — vocabulario v3.0; estender para os 7 estados v4.0. |

---

## 8. Lacunas (gaps)

1. **Nenhuma lacuna bloqueante.** Todo o codigo da UI de assinatura foi
   recuperado verbatim do `6add246`.
2. **`react-signature-canvas` removido do `package.json`:** nao existe tal
   commit — o CHANGELOG estava errado. Correcao factual, nao lacuna.
3. **Discrepancia "~414 LOC":** documentacao, nao recuperacao. Ambas as
   versoes reais do `page.tsx` sao acessiveis.
4. **`useScanner.ts` / `useFocusTrap.ts` pre-redesenho:** nao recuperados —
   nao foi necessario, ambos existem inalterados em `development`.
5. **Compatibilidade do sistema original com a maquina v4.0:** o
   `AssinaturaModal` original e **agnostico de rota** — recebe
   `statusAtual`/`statusNovo` e `precisaMotivo` ja resolvidos. Ele NAO
   conhece as 14 transicoes v4.0. A unica adaptacao real e o vocabulario
   de labels (`ACTION_LABELS` + `isReprovar` hardcoded em
   `REPROVADA_PELO_VENDEDOR`, que ja serve a v4.0 — o estado de reprovacao
   nao mudou de nome). **O modelo do componente e compativel com a v4.0**;
   nao ha incompatibilidade estrutural que exija reescrita. Ponto de
   escalacao do prompt resolvido: **a reativacao e viavel sem adaptacoes
   maiores na maquina de estados.**

---

## 9. Recomendacoes para o Gate 2

1. **Reconstruir o `AssinaturaModal`** como componente proprio, partindo
   verbatim da Secao 6.3, com 3 adaptacoes: labels v4.0, seletor
   Aprovar/Reprovar explicito (RF-008), anti-enumeracao (RN-014).
2. **Reusar `useExecutarTransicao` diretamente** — descomissionar o status
   "orfao" reativando o unico importador (o C22).
3. **Consumir `identificacao-prova.ts`** para identificacao — nao recriar
   `useScanProva`.
4. **Migrar o CSS do modal verbatim** para um CSS Module proprio.
5. **Confirmar no inicio do Gate 2** os tokens `--radius-sm`, `--fs-*` e
   `--font-family` em `globals.css` (uso disseminado — alta probabilidade
   de existirem; `globals.css` tem alteracoes nao-commitadas do Mario).
6. **Limpeza opcional:** o `package.json` tem `react-signature-canvas`
   orfao — o C22 o reativa, entao a "orfandade" se resolve naturalmente.

---

**Fim da arqueologia.** Continuacao: `analysis.md` (Gate 1 — analise +
proposta de estrategia + 11 decisoes de design).
