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
import { AnimatePresence, motion } from "framer-motion";
import { createClient } from "@/lib/supabase/client";
import { apiFetch, ApiError } from "@/lib/api";
import { useCreateProva } from "@/hooks/useCreateProva";
import { useAuthorization } from "@/lib/hooks/use-authorization";
import { Restricted } from "@/components/Restricted";
import {
  isAllowedImageType,
  MAX_UPLOAD_BYTES,
  type ProvaCreateResponse,
  type RotaCriacao,
} from "@/lib/types/prova";
import type { UsuarioListResponse, UsuarioResponse } from "@/lib/types/usuario";
import styles from "./nova-prova.module.css";

// ─── Estado do form ────────────────────────────────────────────────────────
//
// Wave 2 v4.0 — Visual Refresh v2 (2026-05-05): a rota agora e um unico
// controle de 4 botoes diretos (alinhado ao design Figma entregue pelo
// Mario). Substituiu o composto origem+laminacao da entrega anterior
// (ADR-118 supersedido). O `rota` armazena diretamente `RotaCriacao`.

interface FormState {
  nome: string;
  nro_requerimento: string;
  cliente: string;
  vendedor_id: string;
  rota: RotaCriacao;
}

const INITIAL_FORM: FormState = {
  nome: "",
  nro_requerimento: "",
  cliente: "",
  vendedor_id: "",
  rota: "MATRIZ", // Default conforme o print: "Matriz" selecionado
};

// Ordem das 4 rotas no segment — espelha o design (Matriz / Filial /
// Lam. Matriz / Lam. Filial). Labels human-readable inline para nao
// depender de ROTA_LABELS (que tambem cobre legacy v3.0).
const ROTA_BUTTONS: ReadonlyArray<{ value: RotaCriacao; label: string }> = [
  { value: "MATRIZ", label: "Matriz" },
  { value: "FILIAL", label: "Filial" },
  { value: "LAM_MATRIZ", label: "Lam. Matriz" },
  { value: "LAM_FILIAL", label: "Lam. Filial" },
] as const;

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
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
    if (!isAllowedImageType(file.type)) {
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
  // o mesmo handler do upload. Defensivo contra acionar dentro de inputs:
  // usa `instanceof` (em vez de cast) para narrowing seguro do EventTarget.
  useEffect(() => {
    function onPaste(e: ClipboardEvent) {
      const target = e.target;
      if (
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        target instanceof HTMLSelectElement
      ) {
        return;
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

  const handleSubmit = useCallback(
    async (e: FormEvent) => {
      e.preventDefault();
      if (!canSubmit || !arquivo) return;
      await submit({
        nome: form.nome.trim(),
        nro_requerimento: form.nro_requerimento.trim(),
        cliente: form.cliente.trim(),
        vendedor_id: form.vendedor_id,
        rota: form.rota,
        arquivo,
      });
    },
    [canSubmit, arquivo, form, submit],
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

  // Wave 1 v4.0: sem acesso -> Restricted (sem renderizar form).
  // M-1 (audit fixes): retorna null durante loading evita flash de UI.
  // Quando ja existe `result` (prova criada), preservamos a tela de
  // sucesso mesmo se a sessao ficar momentaneamente revalidando.
  if (!result) {
    if (auth.loading) return null;
    if (!auth.hasAccess) {
      return <Restricted ruleKey="provas.create" profile={auth.profile} />;
    }
  }

  // ─── Layout de criacao (Wave 2 v4.0 — Visual Refresh v2) ─────────────
  const pdfDataUrl = result
    ? `data:application/pdf;base64,${result.etiqueta_pdf_base64}`
    : null;

  // Easing curve compartilhada entre header, ficha e dropzone.
  const ENTER_EASE = [0.32, 0.72, 0, 1] as const;

  return (
    <>
      <div className={styles.mobileNotice}>
        <p>Para acessar esse recurso, acesse a versao desktop.</p>
      </div>

      <AnimatePresence mode="wait">
        {result && pdfDataUrl ? (
          <motion.div
            key="success"
            className={styles.desktopOnly}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.25, ease: ENTER_EASE }}
          >
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
          </motion.div>
        ) : (
          <motion.form
            key="form"
            id="nova-prova-form"
            className={styles.canvas}
            onSubmit={handleSubmit}
            noValidate
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            {/* Header da pagina: titulo grande a esquerda + botao primario
                a direita. Mesmo padrao de /usuarios e /provas — entra no
                flow do form (sem position:absolute). */}
            <motion.header
              className={styles.pageHeader}
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.28, ease: ENTER_EASE, delay: 0.04 }}
            >
              <h1 className={styles.pageTitle}>Nova prova Digital</h1>
              <button
                type="submit"
                className={styles.btnSubmit}
                disabled={!canSubmit}
              >
                {loading ? "Cadastrando…" : "Cadastrar prova"}
              </button>
            </motion.header>

            {/* Box branco unico — ocupa toda a area restante do .cardInner */}
            <motion.section
              className={styles.ficha}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.32, ease: ENTER_EASE, delay: 0.1 }}
            >
            <div className={styles.fieldRow}>
              <div className={styles.field}>
                <label htmlFor="np-nome" className={styles.label}>Nome</label>
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
                <label htmlFor="np-req" className={styles.label}>Requerimento</label>
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
            </div>

            <div className={styles.fieldRow}>
              <div className={styles.field}>
                <label htmlFor="np-cli" className={styles.label}>Cliente</label>
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
                <label htmlFor="np-vend" className={styles.label}>Vendedor</label>
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

            {/* ── ROTA: segment de 4 botoes diretos (Visual Refresh v2) ─
                Substituiu o composto origem (segment 2) + laminacao (switch)
                da entrega anterior — alinhamento com o design Figma. */}
            <fieldset className={styles.field}>
              <legend className={styles.label}>Rota</legend>
              <div
                className={styles.segment4}
                role="radiogroup"
                aria-label="Rota da prova"
              >
                {ROTA_BUTTONS.map((opt) => {
                  const active = form.rota === opt.value;
                  return (
                    <button
                      key={opt.value}
                      type="button"
                      role="radio"
                      aria-checked={active}
                      className={`${styles.segmentBtn} ${
                        active ? styles.segmentBtnActive : ""
                      }`}
                      onClick={() => setForm({ ...form, rota: opt.value })}
                      disabled={loading}
                    >
                      {active && (
                        <motion.span
                          layoutId="rota-pill"
                          className={styles.segmentPill}
                          transition={{
                            type: "spring",
                            bounce: 0.2,
                            duration: 0.35,
                          }}
                          aria-hidden="true"
                        />
                      )}
                      <span className={styles.segmentLabel}>{opt.label}</span>
                    </button>
                  );
                })}
              </div>
            </fieldset>

            {/* ── ANEXO: dropzone — cresce para preencher o resto da ficha ─ */}
            <div className={`${styles.field} ${styles.anexoField}`}>
              <label className={styles.label} htmlFor="np-arquivo">Anexo</label>
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
                      JPG · PNG
                    </span>
                  </div>
                )}
              </label>
              {arquivoError && (
                <span className={styles.inlineError}>{arquivoError}</span>
              )}
            </div>

            {error && <div className={styles.errorBox}>{error}</div>}
          </motion.section>
      </motion.form>
        )}
      </AnimatePresence>
    </>
  );
}
