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
import { PlusIcon } from "@/components/icons";
import {
  ALLOWED_IMAGE_TYPES,
  MAX_UPLOAD_BYTES,
  type ProvaCreateResponse,
} from "@/lib/types/prova";
import type { UsuarioListResponse, UsuarioResponse } from "@/lib/types/usuario";
import styles from "./nova-prova.module.css";

interface FormState {
  nome: string;
  nro_requerimento: string;
  cliente: string;
  vendedor_id: string;
}

const INITIAL_FORM: FormState = {
  nome: "",
  nro_requerimento: "",
  cliente: "",
  vendedor_id: "",
};

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export default function NovaProvaPage() {
  const [form, setForm] = useState<FormState>(INITIAL_FORM);
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [arquivoPreview, setArquivoPreview] = useState<string | null>(null);
  const [arquivoError, setArquivoError] = useState<string | null>(null);
  const [vendedores, setVendedores] = useState<UsuarioResponse[]>([]);
  const [vendedoresLoading, setVendedoresLoading] = useState(true);
  const [vendedoresError, setVendedoresError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Token provider — re-busca a sessao do Supabase a cada chamada para
  // garantir access_token atual (o middleware refresca em background).
  //
  // Fonte UNICA de truth para o access token nesta pagina: tanto o
  // fetch de vendedores (logo abaixo) quanto o useCreateProva usam este
  // callback. Evita divergencia entre duas chamadas a getSession() que
  // poderiam pegar tokens diferentes em caso de refresh concorrente.
  // (A5 da auditoria Wave 2.)
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

  // Revoga object URLs antigos quando o arquivo muda (evitar leak).
  useEffect(() => {
    return () => {
      if (arquivoPreview) URL.revokeObjectURL(arquivoPreview);
    };
  }, [arquivoPreview]);

  const handleFileSelect = useCallback((file: File | null) => {
    if (arquivoPreview) URL.revokeObjectURL(arquivoPreview);
    if (!file) {
      setArquivo(null);
      setArquivoPreview(null);
      setArquivoError(null);
      return;
    }
    // Validacao de tipo — feedback imediato (A3).
    if (!(ALLOWED_IMAGE_TYPES as readonly string[]).includes(file.type)) {
      setArquivo(null);
      setArquivoPreview(null);
      setArquivoError(
        `Tipo de arquivo nao permitido (${file.type || "desconhecido"}). Use JPG ou PNG.`,
      );
      return;
    }
    // Validacao de tamanho — feedback imediato (A3).
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
    a.download = `etiqueta-${res.prova.nro_requerimento}.pdf`;
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
  if (result) {
    const pdfDataUrl = `data:application/pdf;base64,${result.etiqueta_pdf_base64}`;
    return (
      <>
        <div className={styles.mobileNotice}>
          <p>Para acessar esse recurso, acesse a versao desktop.</p>
        </div>
        <div className={styles.desktopOnly}>
          <header className={styles.pageHeader}>
            <h1 className={styles.title}>Prova criada com sucesso</h1>
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
                <dt>Rota projetada</dt>
                <dd>
                  {result.prova.rota_projetada === "PADRAO"
                    ? "Rota padrao (via Matriz)"
                    : "Rota direta (Filial)"}
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

  // ─── Formulario de criacao ──────────────────────────────────────────
  return (
    <>
      <div className={styles.mobileNotice}>
        <p>Para acessar esse recurso, acesse a versao desktop.</p>
      </div>
      <div className={styles.desktopOnly}>
        {/* Form wrapper envolve TUDO (header + grid + dropzone) porque o
            botao "Criar prova" esta no header mas precisa submitar o form. */}
        <form className={styles.form} onSubmit={handleSubmit} noValidate>
          <header className={styles.pageHeader}>
            <h1 className={styles.title}>Nova prova digital</h1>
            <button
              type="submit"
              className={styles.btnPrimary}
              disabled={!canSubmit}
            >
              {loading ? "Criando..." : "Criar prova"}
            </button>
          </header>

          <div className={styles.formGrid}>
            <div className={styles.field}>
              <label htmlFor="nome" className={styles.label}>
                Nome:
              </label>
              <input
                id="nome"
                type="text"
                className={styles.input}
                placeholder="Nome da prova"
                value={form.nome}
                onChange={(e) => setForm({ ...form, nome: e.target.value })}
                maxLength={200}
                required
                disabled={loading}
              />
            </div>

            <div className={styles.field}>
              <label htmlFor="nro_requerimento" className={styles.label}>
                Numero do requerimento:
              </label>
              <input
                id="nro_requerimento"
                type="text"
                className={styles.input}
                placeholder="Ex: REQ-2026-001"
                value={form.nro_requerimento}
                onChange={(e) =>
                  setForm({ ...form, nro_requerimento: e.target.value })
                }
                maxLength={50}
                required
                disabled={loading}
              />
            </div>

            <div className={styles.field}>
              <label htmlFor="cliente" className={styles.label}>
                Cliente:
              </label>
              <input
                id="cliente"
                type="text"
                className={styles.input}
                placeholder="Nome do cliente"
                value={form.cliente}
                onChange={(e) => setForm({ ...form, cliente: e.target.value })}
                maxLength={200}
                required
                disabled={loading}
              />
            </div>

            <div className={styles.field}>
              <label htmlFor="vendedor" className={styles.label}>
                Vendedor:
              </label>
              <select
                id="vendedor"
                className={styles.select}
                value={form.vendedor_id}
                onChange={(e) =>
                  setForm({ ...form, vendedor_id: e.target.value })
                }
                required
                disabled={loading || vendedoresLoading || vendedores.length === 0}
              >
                <option value="">
                  {vendedoresLoading
                    ? "Carregando..."
                    : vendedores.length === 0
                    ? "Nenhum vendedor ativo"
                    : "Selecione um vendedor"}
                </option>
                {vendedores.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.nome} ({v.localizacao ?? "?"})
                  </option>
                ))}
              </select>
              {vendedoresError && (
                <span className={styles.inlineError}>{vendedoresError}</span>
              )}
            </div>
          </div>

          <label
            htmlFor="arquivo"
            className={`${styles.dropzone} ${
              dragOver ? styles.dropzoneActive : ""
            } ${arquivo ? styles.dropzoneFilled : ""}`}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
          >
            <input
              ref={fileInputRef}
              id="arquivo"
              type="file"
              accept="image/jpeg,image/png"
              className={styles.fileInput}
              onChange={handleFileInputChange}
              disabled={loading}
            />
            {arquivo && arquivoPreview ? (
              <div className={styles.previewContainer}>
                {/* Preview local usando URL.createObjectURL. Nao requer R2. */}
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
                <span className={styles.dropzoneTitle}>
                  Arraste uma imagem ou clique para selecionar
                </span>
                <span className={styles.dropzoneHint}>JPG ou PNG</span>
                <span className={styles.dropzoneIcon} aria-hidden="true">
                  <PlusIcon width={56} height={56} />
                </span>
              </div>
            )}
          </label>
          {arquivoError && (
            <span className={styles.inlineError}>{arquivoError}</span>
          )}

          {error && <div className={styles.errorBox}>{error}</div>}
        </form>
      </div>
    </>
  );
}
