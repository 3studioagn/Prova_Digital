"use client";

/**
 * Atalhos de teclado globais (Wave 5, Componente 17 — RF-016).
 *
 * State machine de 2 keystrokes (estilo GitHub):
 *   1. Usuario pressiona `g` -> entra em modo "leader" por 1.5s.
 *   2. Dentro do timeout, segunda tecla dispara a navegacao:
 *      - `g s` -> /escanear
 *      - `g p` -> /provas
 *      - `g r` -> /relatorios (apenas admin; vendedor/motorista nao veem)
 *   3. Tecla `?` (sem leader) abre/fecha o modal de help.
 *   4. `Esc` no modo leader cancela.
 *
 * Ignora keystrokes quando o foco esta em <input>, <textarea> ou
 * `[contenteditable]` — para nao quebrar digitacao em formularios/buscas.
 *
 * Hook expoe `{ helpOpen, openHelp, closeHelp }` para que o caller
 * (layout) renderize o modal de help. `?` chama `openHelp`
 * internamente; modal pode ser fechado externamente via `closeHelp`.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";

const LEADER_TIMEOUT_MS = 1_500;

export interface ShortcutDef {
  /** Tecla apos `g` (e.g. "s", "p", "r"). */
  key: string;
  /** Caminho a navegar. */
  path: string;
  /** Texto exibido no modal de help. */
  label: string;
  /** Quando true, atalho so aparece para admin. */
  adminOnly?: boolean;
}

export const SHORTCUT_DEFS: ShortcutDef[] = [
  { key: "s", path: "/escanear", label: "Escanear QR Code" },
  { key: "p", path: "/provas", label: "Listar provas" },
  {
    key: "r",
    path: "/relatorios",
    label: "Acessar relatorios",
    adminOnly: true,
  },
];

interface Options {
  /** Habilita atalhos restritos a admin. Default: false. */
  isAdmin: boolean;
}

/** Verifica se o foco atual esta num campo editavel. */
function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName.toLowerCase();
  if (tag === "input" || tag === "textarea" || tag === "select") return true;
  if (target.isContentEditable) return true;
  return false;
}

export interface UseGlobalShortcutsResult {
  /** True se o modal de help deve estar aberto. */
  helpOpen: boolean;
  /** Abre o modal de help. */
  openHelp: () => void;
  /** Fecha o modal de help. */
  closeHelp: () => void;
  /** Lista de atalhos visiveis para o perfil atual (filtrada por isAdmin). */
  visibleShortcuts: ShortcutDef[];
}

export function useGlobalShortcuts(
  options: Options,
): UseGlobalShortcutsResult {
  const { isAdmin } = options;
  const router = useRouter();
  const [helpOpen, setHelpOpen] = useState(false);
  const leaderActiveRef = useRef(false);
  const leaderTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Audit 2026-04-29 L-F1: useMemo estabiliza a referencia para que o
  // useEffect de keydown nao re-attach o listener a cada render do layout.
  const visibleShortcuts = useMemo(
    () => SHORTCUT_DEFS.filter((s) => !s.adminOnly || isAdmin),
    [isAdmin],
  );

  const openHelp = useCallback(() => setHelpOpen(true), []);
  const closeHelp = useCallback(() => setHelpOpen(false), []);

  const cancelLeader = useCallback(() => {
    leaderActiveRef.current = false;
    if (leaderTimerRef.current) {
      clearTimeout(leaderTimerRef.current);
      leaderTimerRef.current = null;
    }
  }, []);

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      // Ignora se foco em input/textarea/contenteditable
      if (isEditableTarget(event.target)) return;
      // Ignora atalhos com modificadores (Ctrl/Cmd/Alt/Meta)
      if (event.ctrlKey || event.metaKey || event.altKey) return;

      const key = event.key;

      // `?` (Shift+/) abre/fecha o help. Independe do leader.
      if (key === "?") {
        event.preventDefault();
        setHelpOpen((prev) => !prev);
        cancelLeader();
        return;
      }

      // Esc fecha modal e cancela leader
      if (key === "Escape") {
        if (helpOpen) {
          closeHelp();
        }
        cancelLeader();
        return;
      }

      // Modo leader ativo: segunda tecla dispara navegacao
      if (leaderActiveRef.current) {
        cancelLeader();
        const match = visibleShortcuts.find(
          (s) => s.key === key.toLowerCase(),
        );
        if (match) {
          event.preventDefault();
          router.push(match.path);
        }
        return;
      }

      // Tecla `g` ativa modo leader
      if (key === "g" && !event.shiftKey) {
        event.preventDefault();
        leaderActiveRef.current = true;
        leaderTimerRef.current = setTimeout(() => {
          cancelLeader();
        }, LEADER_TIMEOUT_MS);
        return;
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      cancelLeader();
    };
  }, [cancelLeader, closeHelp, helpOpen, router, visibleShortcuts]);

  return { helpOpen, openHelp, closeHelp, visibleShortcuts };
}
