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
 * Busca o usuario corrente via GET /api/v1/users/me.
 *
 * O layout tambem faz essa chamada — a duplicacao e aceita porque o
 * response e <1 KB e o browser pode cachear (ADR-087, Lote C).
 * Alternativa seria React Context no layout, mas isso requer tocar
 * em codigo Wave 1.
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
      const user = await apiFetch<UserInfo>("/api/v1/users/me", { token });
      setState({ user, loading: false });
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
