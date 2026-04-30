"use client";

/**
 * Atalhos de teclado globais (Wave 5 C17 — RF-016; Wave 1 v4.0 alinhado
 * com Matriz de Acesso).
 *
 * State machine de 2 keystrokes (estilo GitHub):
 *   1. Usuario pressiona `g` -> entra em modo "leader" por 1.5s.
 *   2. Dentro do timeout, segunda tecla dispara a navegacao.
 *   3. Tecla `?` (sem leader) abre/fecha o modal de help.
 *   4. `Esc` no modo leader cancela.
 *
 * Wave 1 v4.0: a lista de atalhos visiveis e derivada da Matriz de
 * Acesso (shared/access-matrix.json) — para cada SHORTCUT_KEYS abaixo,
 * o atalho aparece apenas se `evaluateRule(rule, user).acesso != negado`.
 * Substitui o flag `adminOnly` hardcoded.
 *
 * Ignora keystrokes quando o foco esta em <input>, <textarea> ou
 * `[contenteditable]` — para nao quebrar digitacao em formularios/buscas.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import {
  evaluateRule,
  getRuleByKey,
  type UserLike,
} from "@/lib/access-matrix";

const LEADER_TIMEOUT_MS = 1_500;

export interface ShortcutDef {
  /** Tecla apos `g` (e.g. "s", "p", "r"). */
  key: string;
  /** Caminho a navegar. */
  path: string;
  /** Texto exibido no modal de help. */
  label: string;
  /** Chave correspondente na Matriz (shared/access-matrix.json). */
  ruleKey: string;
}

/** Lista canonica de atalhos. Chave da Matriz controla visibilidade. */
export const SHORTCUT_DEFS: ShortcutDef[] = [
  { key: "s", path: "/escanear", label: "Escanear QR Code", ruleKey: "scanner" },
  { key: "p", path: "/provas", label: "Listar provas", ruleKey: "provas.list" },
  { key: "r", path: "/relatorios", label: "Acessar relatorios", ruleKey: "relatorios" },
  { key: "a", path: "/auditoria", label: "Acessar auditoria", ruleKey: "auditoria" },
];

interface Options {
  /** Usuario logado (resposta de /users/me). null durante carga. */
  user: UserLike | null;
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
  const { user } = options;
  const router = useRouter();
  const [helpOpen, setHelpOpen] = useState(false);
  const leaderActiveRef = useRef(false);
  const leaderTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Wave 1 v4.0: filtra atalhos consultando a Matriz de Acesso por
  // ruleKey. Se a regra inexiste ou avalia para 'negado', o atalho nao
  // aparece. useMemo evita re-attach do listener (audit 2026-04-29 L-F1).
  const visibleShortcuts = useMemo(
    () =>
      SHORTCUT_DEFS.filter((s) => {
        const rule = getRuleByKey(s.ruleKey);
        if (rule === null) return false;
        return evaluateRule(rule, user).acesso !== "negado";
      }),
    [user],
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
