"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ChangeEvent,
  type DragEvent,
  type FormEvent,
} from "react";
import { createClient } from "@/lib/supabase/client";
import { apiFetch, ApiError } from "@/lib/api";
import { useCreateProva } from "@/hooks/useCreateProva";
import { useAuthorization } from "@/lib/hooks/use-authorization";
import { Restricted } from "@/components/Restricted";
import {
  ALLOWED_IMAGE_TYPES,
  MAX_UPLOAD_BYTES,
  type ProvaCreateResponse,
  type RotaCriacao,
} from "@/lib/types/prova";
import type { UsuarioListResponse, UsuarioResponse } from "@/lib/types/usuario";
import styles from "./nova-prova.module.css";

// ─── Estado do form ────────────────────────────────────────────────────────
//
// Wave 2 v4.0 (Componente 06): a rota e dividida em 2 controles
// independentes na UI (decisao de UX do design) que sao combinados em
// `RotaCriacao` no submit:
//   - origem (MATRIZ | FILIAL) — segment com 2 botoes
//   - laminacao (boolean) — switch on/off
// Combinacoes:
//   MATRIZ + lam OFF -> "MATRIZ"
//   MATRIZ + lam ON  -> "LAM_MATRIZ"
//   FILIAL + lam OFF -> "FILIAL"
//   FILIAL + lam ON  -> "LAM_FILIAL"

type Origem = "MATRIZ" | "FILIAL";

interface FormState {
  nome: string;
  nro_requerimento: string;
  cliente: string;
  vendedor_id: string;
  origem: Origem;
  laminacao: boolean;
}

const INITIAL_FORM: FormState = {
  nome: "",
  nro_requerimento: "",
  cliente: "",
  vendedor_id: "",
  origem: "FILIAL",   // Default conforme o print: "Filial" selecionado
  laminacao: false,
};

function deriveRota(origem: Origem, laminacao: boolean): RotaCriacao {
  if (laminacao) {
    return origem === "MATRIZ" ? "LAM_MATRIZ" : "LAM_FILIAL";
  }
  return origem;
}

// Endereco institucional da unidade — Wave 2 v4.0 hardcoded; futura
// iteracao pode mover para `configuracoes_sistema` via chave dedicada.
const UNIDADES_INFO: Record<Origem, { titulo: string; endereco: string }> = {
  MATRIZ: {
    titulo: "Matriz · São Paulo",
    endereco: "Av. Paulista, 1000 — Bela Vista, São Paulo · SP",
  },
  FILIAL: {
    titulo: "Filial · Campinas",
    endereco: "Av. Norte-Sul, 450 — Cambuí, Campinas · SP",
  },
};

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

// Timestamp `dd/MM, HH:mm` em pt-BR (atualiza a cada minuto).
function useCurrentTimestamp(): string {
  const [now, setNow] = useState<Date | null>(null);
  useEffect(() => {
    setNow(new Date());
    const id = setInterval(() => setNow(new Date()), 60_000);
    return () => clearInterval(id);
  }, []);
  if (!now) return "";  // Evita SSR mismatch — vazio ate o hydrate.
  const dd = String(now.getDate()).padStart(2, "0");
  const mm = String(now.getMonth() + 1).padStart(2, "0");
  const hh = String(now.getHours()).padStart(2, "0");
  const mi = String(now.getMinutes()).padStart(2, "0");
  return `${dd}/${mm}, ${hh}:${mi}`;
}

export default function NovaProvaPage() {
  // Wave 1 v4.0 — guard via Matriz. provas.create = admin-only.
  const auth = useAuthorization("provas.create");

  const [form, setForm] = useState<FormState>(INITIAL_FORM);
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [arquivoPreview, setArquivoPreview] = useState<string | null>(null);
  const [arquivoError, setArquivoError] = useState<string | null>(null);
  const [vendedores, setVendedores] = useState<UsuarioResponse[]>([]);
  const [vendedoresLoading, setVendedoresLoading] = useState(true);
  const [vendedoresError, setVendedoresError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const timestamp = useCurrentTimestamp();

  const getToken = useCallback(async () => {
    const supabase = createClient();
    const { data } = await supabase.auth.getSession();
    return data.session?.access_token ?? null;
  }, []);

  const { loading, error, result, submit, reset } = useCreateProva(getToken);

  // ─── Carrega vendedores ativos para o select ─────────────────────────
  useEffect(() => {
    const controller = new AbortController();
    async function fetchVendedores() {
      setVendedoresLoading(true);
      setVendedoresError(null);
      try {
        const token = await getToken();
        if (!token) {
          if (!controller.signal.aborted) {
            setVendedoresError("Sessao expirada.");
            setVendedoresLoading(false);
          }
          return;
        }
        const resp = await apiFetch<UsuarioListResponse>(
          "/api/v1/users/?setor=VENDEDOR&ativo=true&page_size=100",
          { token, signal: controller.signal },
        );
        if (!controller.signal.aborted) {
          setVendedores(resp.items);
        }
      } catch (err) {
        if (controller.signal.aborted) return;
        const msg =
          err instanceof ApiError
            ? err.message
            : "Nao foi possivel carregar vendedores.";
        setVendedoresError(msg);
      } finally {
        if (!controller.signal.aborted) {
          setVendedoresLoading(false);
        }
      }
    }
    fetchVendedores();
    return () => controller.abort();
  }, [getToken]);

  const handleFileSelect = useCallback((file: File | null) => {
    if (arquivoPreview) URL.revokeObjectURL(arquivoPreview);
    if (!file) {
      setArquivo(null);
      setArquivoPreview(null);
      setArquivoError(null);
      return;
    }
    if (!(ALLOWED_IMAGE_TYPES as readonly string[]).includes(file.type)) {
      setArquivo(null);
      setArquivoPreview(null);
      setArquivoError(
        `Tipo de arquivo nao permitido (${file.type || "desconhecido"}). Use JPG ou PNG.`,
      );
      return;
    }
    if (file.size > MAX_UPLOAD_BYTES) {
      setArquivo(null);
      setArquivoPreview(null);
      setArquivoError(
        `Arquivo excede o limite de ${MAX_UPLOAD_BYTES / (1024 * 1024)} MB (${(file.size / (1024 * 1024)).toFixed(1)} MB).`,
      );
      return;
    }
    setArquivo(file);
    setArquivoPreview(URL.createObjectURL(file));
    setArquivoError(null);
  }, [arquivoPreview]);

  const handleFileInputChange = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0] ?? null;
      handleFileSelect(file);
    },
    [handleFileSelect],
  );

  const handleDrop = useCallback(
    (e: DragEvent<HTMLLabelElement>) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files?.[0] ?? null;
      handleFileSelect(file);
    },
    [handleFileSelect],
  );

  const handleDragOver = useCallback((e: DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    setDragOver(false);
  }, []);

  // Wave 2 v4.0: paste-from-clipboard (atalho ⌘V mostrado no card lateral).
  // Aceita imagens coladas direto no body — converte em File e dispara
  // o mesmo handler do upload. Defensivo contra acionar dentro de inputs.
  useEffect(() => {
    function onPaste(e: ClipboardEvent) {
      const target = e.target as HTMLElement | null;
      if (target) {
        const tag = target.tagName;
        if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
      }
      const items = e.clipboardData?.items;
      if (!items) return;
      for (const item of items) {
        if (item.type.startsWith("image/")) {
          const file = item.getAsFile();
          if (file) {
            e.preventDefault();
            handleFileSelect(file);
            return;
          }
        }
      }
    }
    window.addEventListener("paste", onPaste);
    return () => window.removeEventListener("paste", onPaste);
  }, [handleFileSelect]);

  const canSubmit = useMemo(() => {
    return (
      !loading &&
      form.nome.trim().length > 0 &&
      form.nro_requerimento.trim().length > 0 &&
      form.cliente.trim().length > 0 &&
      form.vendedor_id.length > 0 &&
      arquivo !== null
    );
  }, [loading, form, arquivo]);

  const rotaDerivada = useMemo(
    () => deriveRota(form.origem, form.laminacao),
    [form.origem, form.laminacao],
  );

  const handleSubmit = useCallback(
    async (e: FormEvent) => {
      e.preventDefault();
      if (!canSubmit || !arquivo) return;
      await submit({
        nome: form.nome.trim(),
        nro_requerimento: form.nro_requerimento.trim(),
        cliente: form.cliente.trim(),
        vendedor_id: form.vendedor_id,
        rota: rotaDerivada,
        arquivo,
      });
    },
    [canSubmit, arquivo, form, rotaDerivada, submit],
  );

  const handleNovaProva = useCallback(() => {
    reset();
    setForm(INITIAL_FORM);
    setArquivoError(null);
    handleFileSelect(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }, [reset, handleFileSelect]);

  const handleDownloadPdf = useCallback((res: ProvaCreateResponse) => {
    const bin = atob(res.etiqueta_pdf_base64);
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    const blob = new Blob([bytes], { type: "application/pdf" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `etiqueta-${res.prova.codigo_publico}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, []);

  const handlePrint = useCallback((res: ProvaCreateResponse) => {
    const bin = atob(res.etiqueta_pdf_base64);
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    const blob = new Blob([bytes], { type: "application/pdf" });
    const url = URL.createObjectURL(blob);
    const w = window.open(url, "_blank");
    if (w) {
      w.onload = () => {
        w.focus();
        w.print();
      };
    }
  }, []);

  // ─── Tela de sucesso (depois de criar) ──────────────────────────────
  // Mantida a estrutura da Wave 2 v3.0; ajustes minimos para mostrar
  // codigo_publico + rota persistida (Wave 2 v4.0).
  if (result) {
    const pdfDataUrl = `data:application/pdf;base64,${result.etiqueta_pdf_base64}`;
    return (
      <>
        <div className={styles.mobileNotice}>
          <p>Para acessar esse recurso, acesse a versao desktop.</p>
        </div>
        <div className={styles.desktopOnly}>
          <header className={styles.successHeader}>
            <h1 className={styles.successTitle}>Prova criada com sucesso</h1>
            <button
              type="button"
              className={styles.btnPrimary}
              onClick={handleNovaProva}
            >
              Nova prova
            </button>
          </header>

          <section className={styles.successGrid}>
            <div className={styles.infoCard}>
              <h2 className={styles.h2}>Detalhes da prova</h2>
              <dl className={styles.dl}>
                <dt>Código</dt>
                <dd className={styles.codigoPublico}>
                  {result.prova.codigo_publico}
                </dd>
                <dt>Nome</dt>
                <dd>{result.prova.nome}</dd>
                <dt>Requerimento</dt>
                <dd>{result.prova.nro_requerimento}</dd>
                <dt>Cliente</dt>
                <dd>{result.prova.cliente}</dd>
                <dt>Vendedor</dt>
                <dd>
                  {result.prova.vendedor_nome}
                  {result.prova.vendedor_localizacao
                    ? ` (${result.prova.vendedor_localizacao})`
                    : ""}
                </dd>
                <dt>Rota</dt>
                <dd>
                  {result.prova.rota === "MATRIZ" && "Matriz"}
                  {result.prova.rota === "LAM_MATRIZ" && "Lam. Matriz"}
                  {result.prova.rota === "FILIAL" && "Filial"}
                  {result.prova.rota === "LAM_FILIAL" && "Lam. Filial"}
                  {result.prova.rota === "PADRAO" && "Matriz (legada)"}
                  {result.prova.rota === "DIRETA" && "Filial (legada)"}
                  {!result.prova.rota && "—"}
                </dd>
                <dt>Status</dt>
                <dd>{result.prova.status}</dd>
                <dt>Ciclo</dt>
                <dd>{result.prova.ciclo_atual}</dd>
              </dl>

              <div className={styles.actions}>
                <button
                  type="button"
                  className={styles.btnSecondary}
                  onClick={() => handleDownloadPdf(result)}
                >
                  Baixar etiqueta (PDF)
                </button>
                <button
                  type="button"
                  className={styles.btnSecondary}
                  onClick={() => handlePrint(result)}
                >
                  Imprimir etiqueta
                </button>
              </div>
            </div>

            <div className={styles.pdfPreview}>
              <h2 className={styles.h2}>Etiqueta</h2>
              <iframe
                title="Preview da etiqueta"
                src={pdfDataUrl}
                className={styles.pdfFrame}
              />
            </div>
          </section>
        </div>
      </>
    );
  }

  // Wave 1 v4.0: sem acesso -> Restricted (sem renderizar form).
  // M-1 (audit fixes): retorna null durante loading evita flash de UI.
  if (auth.loading) return null;
  if (!auth.hasAccess) {
    return <Restricted ruleKey="provas.create" profile={auth.profile} />;
  }

  // ─── Layout de criacao (Wave 2 v4.0 — segue o print do Mario) ────────
  const unidade = UNIDADES_INFO[form.origem];

  return (
    <>
      <div className={styles.mobileNotice}>
        <p>Para acessar esse recurso, acesse a versao desktop.</p>
      </div>

      {/* Canvas com background ambient (grid de pontos + blob amarelo + onda) */}
      <form
        id="nova-prova-form"
        className={styles.canvas}
        onSubmit={handleSubmit}
        noValidate
      >
        {/* Camadas decorativas do canvas (atras do conteudo) */}
        <div className={styles.gridDots} aria-hidden="true" />
        <div className={styles.blob} aria-hidden="true" />
        <svg
          className={styles.wave}
          viewBox="0 0 1200 200"
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          <path
            d="M0,140 C200,80 400,160 600,120 C800,80 1000,140 1200,100 L1200,200 L0,200 Z"
            fill="rgba(0,0,0,0.04)"
          />
          <path
            d="M0,140 C200,80 400,160 600,120 C800,80 1000,140 1200,100"
            fill="none"
            stroke="rgba(0,0,0,0.18)"
            strokeWidth="1"
          />
          <circle cx="442" cy="138" r="6" fill="#1a1a1a" />
          <circle cx="585" cy="125" r="3" fill="#1a1a1a" />
        </svg>

        {/* Topo — pill com timestamp + botoes a direita */}
        <header className={styles.topbar}>
          <span className={styles.timestamp}>{timestamp || "—/—, —:—"}</span>
          <div className={styles.topActions}>
            <button
              type="button"
              className={styles.btnGhost}
              disabled
              title="Em desenvolvimento — use 'Cadastrar prova' para salvar."
            >
              Salvar rascunho
            </button>
            <button
              type="submit"
              className={styles.btnSubmit}
              disabled={!canSubmit}
            >
              {loading ? "Cadastrando…" : "Cadastrar prova"}
            </button>
          </div>
        </header>

        {/* Layout principal: ficha (esquerda) + cards (direita) */}
        <main className={styles.layout}>
          {/* ── Box branco esquerdo: ficha de cadastro ───────────────── */}
          <section className={styles.ficha}>
            <p className={styles.fichaEyebrow}>
              <span className={styles.checkIcon} aria-hidden="true">☑</span>
              FICHA DE CADASTRO
            </p>
            <h1 className={styles.fichaTitle}>Nova prova digital</h1>

            <div className={styles.field}>
              <label htmlFor="np-nome" className={styles.label}>NOME</label>
              <input
                id="np-nome"
                type="text"
                className={styles.input}
                placeholder="Identificação"
                value={form.nome}
                onChange={(e) => setForm({ ...form, nome: e.target.value })}
                maxLength={200}
                required
                disabled={loading}
              />
            </div>

            <div className={styles.field}>
              <label htmlFor="np-req" className={styles.label}>REQUERIMENTO</label>
              <input
                id="np-req"
                type="text"
                className={styles.input}
                placeholder="000000"
                value={form.nro_requerimento}
                onChange={(e) => setForm({ ...form, nro_requerimento: e.target.value })}
                maxLength={50}
                required
                disabled={loading}
              />
            </div>

            <div className={styles.fieldRow}>
              <div className={styles.field}>
                <label htmlFor="np-cli" className={styles.label}>CLIENTE</label>
                <input
                  id="np-cli"
                  type="text"
                  className={styles.input}
                  placeholder="—"
                  value={form.cliente}
                  onChange={(e) => setForm({ ...form, cliente: e.target.value })}
                  maxLength={200}
                  required
                  disabled={loading}
                />
              </div>
              <div className={styles.field}>
                <label htmlFor="np-vend" className={styles.label}>VENDEDOR</label>
                <select
                  id="np-vend"
                  className={styles.input}
                  value={form.vendedor_id}
                  onChange={(e) => setForm({ ...form, vendedor_id: e.target.value })}
                  required
                  disabled={loading || vendedoresLoading || vendedores.length === 0}
                >
                  <option value="">
                    {vendedoresLoading
                      ? "…"
                      : vendedores.length === 0
                      ? "—"
                      : "—"}
                  </option>
                  {vendedores.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.nome}
                    </option>
                  ))}
                </select>
                {vendedoresError && (
                  <span className={styles.inlineError}>{vendedoresError}</span>
                )}
              </div>
            </div>

            {/* ── ROTA: segment Matriz / Filial ────────────────────── */}
            <fieldset className={styles.field} aria-describedby="np-rota-help">
              <legend className={styles.label}>ROTA</legend>
              <div
                className={styles.segment}
                role="radiogroup"
                aria-label="Origem da rota"
              >
                <button
                  type="button"
                  role="radio"
                  aria-checked={form.origem === "MATRIZ"}
                  className={`${styles.segmentBtn} ${
                    form.origem === "MATRIZ" ? styles.segmentBtnActive : ""
                  }`}
                  onClick={() => setForm({ ...form, origem: "MATRIZ" })}
                  disabled={loading}
                >
                  <span className={styles.segmentIcon} aria-hidden="true">⌂</span>
                  Matriz
                </button>
                <button
                  type="button"
                  role="radio"
                  aria-checked={form.origem === "FILIAL"}
                  className={`${styles.segmentBtn} ${
                    form.origem === "FILIAL" ? styles.segmentBtnActive : ""
                  }`}
                  onClick={() => setForm({ ...form, origem: "FILIAL" })}
                  disabled={loading}
                >
                  <span className={styles.segmentIcon} aria-hidden="true">▤</span>
                  Filial
                </button>
              </div>
            </fieldset>

            {/* ── LAMINAÇÃO: switch ────────────────────────────────── */}
            <div className={styles.toggleRow}>
              <span className={styles.toggleIcon} aria-hidden="true">▥</span>
              <div className={styles.toggleText}>
                <span className={styles.toggleTitle}>Laminação</span>
                <span className={styles.toggleSub}>
                  {form.laminacao ? "Com laminação" : "Sem laminação"}
                </span>
              </div>
              <button
                type="button"
                role="switch"
                aria-checked={form.laminacao}
                aria-label="Laminação"
                className={`${styles.switch} ${
                  form.laminacao ? styles.switchOn : ""
                }`}
                onClick={() => setForm({ ...form, laminacao: !form.laminacao })}
                disabled={loading}
              >
                <span className={styles.switchKnob} aria-hidden="true" />
              </button>
            </div>

            {/* Texto auxiliar de imutabilidade — mitigacao do risco
                "Confusao operacional na escolha manual da rota"
                (Backlog v4.0 §6). */}
            <p id="np-rota-help" className={styles.hint}>
              A rota escolhida é imutável após o cadastro.
            </p>

            {/* ── ANEXO: dropzone ──────────────────────────────────── */}
            <div className={styles.field}>
              <div className={styles.anexoHead}>
                <span className={styles.label}>ANEXO</span>
                <span className={styles.anexoMeta}>
                  {arquivo ? "selecionado" : "pendente"} · ⌘V
                </span>
              </div>
              <label
                htmlFor="np-arquivo"
                className={`${styles.dropzone} ${
                  dragOver ? styles.dropzoneActive : ""
                } ${arquivo ? styles.dropzoneFilled : ""}`}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
              >
                <input
                  ref={fileInputRef}
                  id="np-arquivo"
                  type="file"
                  accept="image/jpeg,image/png"
                  className={styles.fileInput}
                  onChange={handleFileInputChange}
                  disabled={loading}
                />
                {arquivo && arquivoPreview ? (
                  <div className={styles.previewContainer}>
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={arquivoPreview}
                      alt={arquivo.name}
                      className={styles.previewImg}
                    />
                    <div className={styles.previewInfo}>
                      <strong>{arquivo.name}</strong>
                      <span>
                        {arquivo.type.replace("image/", "").toUpperCase()} ·{" "}
                        {formatBytes(arquivo.size)}
                      </span>
                    </div>
                  </div>
                ) : (
                  <div className={styles.dropzoneEmpty}>
                    <span className={styles.dropzoneIcon} aria-hidden="true">↑</span>
                    <span className={styles.dropzoneTitle}>
                      Solte ou clique
                    </span>
                    <span className={styles.dropzoneHint}>
                      JPG · PNG · ⌘V
                    </span>
                  </div>
                )}
              </label>
              {arquivoError && (
                <span className={styles.inlineError}>{arquivoError}</span>
              )}
            </div>

            {/* ── Footer da ficha: ORIGEM / STATUS ──────────────────── */}
            <footer className={styles.fichaFooter}>
              <div>
                <span className={styles.label}>ORIGEM</span>
                <span className={styles.fichaFooterValue}>
                  {form.origem === "MATRIZ" ? "Matriz" : "Filial"}
                </span>
              </div>
              <div>
                <span className={styles.label}>STATUS</span>
                <span className={styles.fichaFooterValue}>
                  <span className={styles.statusDot} aria-hidden="true" />
                  Ativa
                </span>
              </div>
            </footer>

            {error && <div className={styles.errorBox}>{error}</div>}
          </section>

          {/* ── Cards a direita ───────────────────────────────────────── */}
          <aside className={styles.aside}>
            <div className={styles.card}>
              <p className={styles.cardLabel}>
                <span className={styles.cardDot} aria-hidden="true" />
                UNIDADE SELECIONADA
              </p>
              <h3 className={styles.cardTitle}>{unidade.titulo}</h3>
              <p className={styles.cardBody}>{unidade.endereco}</p>
            </div>

            <div className={styles.card}>
              <p className={styles.cardLabel}>
                <kbd className={styles.kbd}>⌘V</kbd> cole imagem
              </p>
              <p className={styles.cardBody}>
                Você também pode arrastar direto no anexo da ficha à esquerda.
              </p>
            </div>
          </aside>
        </main>
      </form>
    </>
  );
}
