"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { apiFetch } from "@/lib/api";
import type { Setor } from "@/lib/access-matrix";

interface UserInfo {
  id: string;
  nome: string;
  /** Wave 1 v4.0: tipado como union literal pelo `lib/access-matrix.ts`
   *  para que o hook seja consumivel direto pelo `evaluateRule`. */
  setor: Setor;
  is_admin: boolean;
}

interface State {
  user: UserInfo | null;
  loading: boolean;
}

/**
 * AUD-W1V4-104 (audit Round 2): conjunto canonico de setores aceitos
 * em runtime. Espelha o enum `Setor` em `@/lib/access-matrix`.
 * `apiFetch<UserInfo>` faz cast TypeScript sem validacao runtime —
 * se o backend retornar um setor fora deste conjunto, sem este guard
 * o componente continua e `resolveProfile` retorna null silenciosamente
 * ("negado em tudo", deny seguro mas dificil de diagnosticar).
 */
const VALID_SETORES: ReadonlySet<Setor> = new Set<Setor>([
  "STUDIO",
  "VENDEDOR",
  "MOTORISTA",
  "CLICHERIA",
]);

function isValidUserInfo(payload: unknown): payload is UserInfo {
  if (typeof payload !== "object" || payload === null) return false;
  const u = payload as Record<string, unknown>;
  return (
    typeof u.id === "string" &&
    typeof u.nome === "string" &&
    typeof u.is_admin === "boolean" &&
    typeof u.setor === "string" &&
    VALID_SETORES.has(u.setor as Setor)
  );
}

/**
 * Busca o usuario corrente via GET /api/v1/users/me.
 *
 * O layout tambem faz essa chamada — a duplicacao e aceita porque o
 * response e <1 KB e o browser pode cachear (ADR-087, Lote C).
 * Alternativa seria React Context no layout, mas isso requer tocar
 * em codigo Wave 1.
 *
 * AUD-W1V4-104: payload e validado em runtime contra o conjunto de
 * setores canonicos. Setor invalido -> user=null (deny seguro) com
 * console.warn explicito para facilitar diagnostico.
 */
export function useCurrentUser(): State {
  const [state, setState] = useState<State>({ user: null, loading: true });
  const didFetch = useRef(false);

  const load = useCallback(async () => {
    const supabase = createClient();
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token ?? null;
    if (!token) {
      setState({ user: null, loading: false });
      return;
    }
    try {
      const payload = await apiFetch<unknown>("/api/v1/users/me", { token });
      if (!isValidUserInfo(payload)) {
        console.warn(
          "[useCurrentUser] payload invalido em /api/v1/users/me; tratando como nao-autenticado",
          payload,
        );
        setState({ user: null, loading: false });
        return;
      }
      setState({ user: payload, loading: false });
    } catch {
      setState({ user: null, loading: false });
    }
  }, []);

  useEffect(() => {
    if (didFetch.current) return;
    didFetch.current = true;
    load();
  }, [load]);

  return state;
}
