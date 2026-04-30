"use client";

/**
 * useAuthorization — Hook React de RBAC para a Matriz de Acesso (Wave 1 v4.0).
 *
 * Consulta a Matriz unificada (shared/access-matrix.json) via `getRuleByKey`
 * + `evaluateRule` e devolve `{ hasAccess, level, scope, loading }` para
 * gating proativo em pages/components.
 *
 * Use:
 *   const { hasAccess, loading } = useAuthorization("auditoria");
 *   if (loading) return <Skeleton />;
 *   if (!hasAccess) return <Restricted ruleKey="auditoria" />;
 *   return <RealContent />;
 *
 * Importante:
 *   - Enquanto loading=true, hasAccess=false (defensivo: nao mostra UI
 *     proibida durante carregamento de /users/me).
 *   - Para regras tipo 'parcial', .scope traz o kind para o consumer
 *     decidir como filtrar (ex.: vendedor=self_vendedor -> nao mostrar
 *     filtro de vendedor).
 */
import { useMemo } from "react";

import {
  evaluateRule,
  getRuleByKey,
  resolveProfile,
  type Acesso,
  type Profile,
  type ScopeKind,
} from "@/lib/access-matrix";
import { useCurrentUser } from "@/hooks/useCurrentUser";

export interface AuthorizationResult {
  /** True se acesso = full ou parcial. False enquanto loading. */
  hasAccess: boolean;
  /** Nivel literal: 'full' | 'parcial' | 'negado'. 'negado' quando loading. */
  level: Acesso;
  /** Kind do escopo quando level='parcial'. Indefinido caso contrario. */
  scope?: ScopeKind;
  /** Perfil resolvido do usuario corrente, ou null se anon/loading/unmapped. */
  profile: Profile | null;
  /** True enquanto useCurrentUser ainda carrega. */
  loading: boolean;
}

const NEGADO_LOADING: AuthorizationResult = {
  hasAccess: false,
  level: "negado",
  profile: null,
  loading: true,
};

const NEGADO_FINAL: AuthorizationResult = {
  hasAccess: false,
  level: "negado",
  profile: null,
  loading: false,
};

export function useAuthorization(ruleKey: string): AuthorizationResult {
  const { user, loading } = useCurrentUser();

  return useMemo(() => {
    if (loading) return NEGADO_LOADING;
    if (!user) return NEGADO_FINAL;

    const rule = getRuleByKey(ruleKey);
    if (!rule) {
      // Rule_key inexistente e bug de configuracao — log e nega defensivamente.
      // Nao queremos crashar a UI por causa disso.
      // eslint-disable-next-line no-console
      console.error(
        `useAuthorization: rule_key '${ruleKey}' nao encontrada em ACCESS_MATRIX`,
      );
      return NEGADO_FINAL;
    }

    const decision = evaluateRule(rule, user);
    const profile = resolveProfile(user);

    return {
      hasAccess: decision.acesso !== "negado",
      level: decision.acesso,
      scope: decision.acesso === "parcial" ? decision.scope : undefined,
      profile,
      loading: false,
    };
  }, [ruleKey, user, loading]);
}
