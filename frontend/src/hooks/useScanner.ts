"use client";

import { useEffect, useId, useRef, useState } from "react";

import type { CodigoErro } from "@/lib/services/identificacao-prova";

interface UseScannerOptions {
  /** Chamado quando um QR Code e detectado. O valor e o texto decodificado. */
  onDetect: (payload: string) => void;
  /** Chamado em erros de inicializacao ou stream da camera. */
  onError?: (err: Error) => void;
  /** Controla se o scanner deve estar ativo. Setar `false` desmonta a camera. */
  enabled: boolean;
}

interface UseScannerResult {
  /** `id` HTML estavel para o container do scanner (usar no `<div id={divId}>`). */
  divId: string;
  /** `true` quando a camera foi iniciada com sucesso. */
  ready: boolean;
  /** Mensagem de erro do ciclo de vida da camera, ou `null`. */
  error: string | null;
  /**
   * Codigo de erro tipado quando aplicavel. Wave 3 v4.0 (Componente 10):
   * sempre `DISPOSITIVO_SEM_CAMERA` em caso de falha — `getUserMedia`
   * indisponivel, permissao negada, ou stream rejeitado pelo browser.
   * `null` quando nao ha erro.
   *
   * O componente chamador usa este codigo para decidir o comportamento
   * (ex.: trocar para tab Manual + mostrar mensagem padrao em pt-BR
   * de `MENSAGENS_ERRO['DISPOSITIVO_SEM_CAMERA']`).
   */
  errorCode: CodigoErro | null;
}

/**
 * Hook wrapper em volta do `html5-qrcode`. Encapsula:
 *   - Lazy import da lib (SSR-safe — Next.js renderiza o componente primeiro
 *     no servidor, e a lib so pode rodar no browser porque depende de
 *     `navigator.mediaDevices`).
 *   - Montagem/desmontagem da camera conforme `enabled`.
 *   - Cleanup defensivo no unmount: `.stop()` + `.clear()` dentro de
 *     try/catch — a lib tem bug conhecido onde stop() pode lancar se o
 *     stream ja foi interrompido externamente. Sem o cleanup, a camera
 *     fica em uso ate o refresh da pagina.
 *   - `useId` garante um ID HTML estavel e unico entre renders e multiplas
 *     instancias na mesma pagina.
 *
 * Constraints:
 *   - `navigator.mediaDevices.getUserMedia` exige HTTPS (ou localhost).
 *     Em producao no Vercel, HTTPS e automatico.
 *   - Permite ao usuario conceder/recusar permissao de camera no prompt do
 *     browser — erro explicito em caso de recusa.
 *   - Configurado para fps=10, qrbox 250x250 — balanco entre CPU e latencia.
 *
 * Uso:
 *   const { divId, ready, error } = useScanner({
 *     enabled: estado === "scanning",
 *     onDetect: (payload) => { handleScan(payload); },
 *     onError: (err) => console.error(err),
 *   });
 *   return <div id={divId} />;
 */
export function useScanner(options: UseScannerOptions): UseScannerResult {
  const { onDetect, onError, enabled } = options;
  const divId = useId();
  // useId gera um id que contem ":" (invalido em alguns CSS selectors).
  // html5-qrcode usa o id em querySelector internamente — sanitizamos.
  const safeDivId = `scanner-${divId.replace(/:/g, "")}`;

  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorCode, setErrorCode] = useState<CodigoErro | null>(null);

  // Refs para guardar a instancia e callbacks mais recentes.
  // Callbacks vao em ref para evitar re-montar a camera quando eles
  // mudam entre renders do caller.
  const scannerRef = useRef<unknown>(null);
  const onDetectRef = useRef(onDetect);
  const onErrorRef = useRef(onError);
  onDetectRef.current = onDetect;
  onErrorRef.current = onError;

  useEffect(() => {
    if (!enabled) {
      // Transicao enabled=true -> false: desmonta (cleanup cuida abaixo).
      return;
    }

    // Lazy import — SSR-safe. O hook so roda client-side (marked "use client"),
    // mas o dynamic import garante que o bundle SSR nao tenta avaliar o modulo.
    let mounted = true;
    let localInstance: {
      stop: () => Promise<void>;
      clear: () => void;
    } | null = null;

    (async () => {
      try {
        const { Html5Qrcode } = await import("html5-qrcode");
        if (!mounted) return;

        // Confirma que o container existe no DOM antes de instanciar.
        if (!document.getElementById(safeDivId)) {
          throw new Error(
            `Container do scanner (#${safeDivId}) nao encontrado no DOM`,
          );
        }

        const instance = new Html5Qrcode(safeDivId);
        scannerRef.current = instance;
        localInstance = instance;

        await instance.start(
          { facingMode: "environment" },
          { fps: 10, qrbox: { width: 250, height: 250 } },
          (decodedText: string) => {
            // Callback de sucesso — chama o callback externo.
            onDetectRef.current(decodedText);
          },
          (_errMessage: string) => {
            // Callback de falha de leitura (frame sem QR detectado).
            // E esperado quando a camera esta procurando — nao propagamos.
          },
        );

        if (mounted) {
          setReady(true);
          setError(null);
          setErrorCode(null);
        }
      } catch (err) {
        if (!mounted) return;
        const msg =
          err instanceof Error ? err.message : "Falha ao iniciar a camera";
        setReady(false);
        setError(msg);
        // Wave 3 v4.0 (Componente 10): qualquer falha de inicializacao
        // de camera vira `DISPOSITIVO_SEM_CAMERA` na visao do chamador.
        // Diferenciacoes finas (permissao negada vs lib falhou) ficam
        // em `error` (mensagem crua) para debug; o codigo tipado e
        // suficiente para decidir o fluxo.
        setErrorCode("DISPOSITIVO_SEM_CAMERA");
        if (onErrorRef.current) {
          onErrorRef.current(err instanceof Error ? err : new Error(msg));
        }
      }
    })();

    // Cleanup: roda quando enabled vira false OU no unmount.
    return () => {
      mounted = false;
      const instance =
        (localInstance as { stop: () => Promise<void>; clear: () => void } | null) ||
        (scannerRef.current as
          | { stop: () => Promise<void>; clear: () => void }
          | null);
      if (!instance) return;

      // stop() pode rejeitar se o stream ja foi encerrado — try/catch.
      instance
        .stop()
        .catch(() => {
          /* already stopped or never started */
        })
        .finally(() => {
          try {
            instance.clear();
          } catch {
            /* best-effort */
          }
        });
      scannerRef.current = null;
      setReady(false);
    };
  }, [enabled, safeDivId]);

  return { divId: safeDivId, ready, error, errorCode };
}
