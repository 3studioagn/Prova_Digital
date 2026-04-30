import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

import {
  ACCESS_MATRIX,
  evaluateRule,
  getRuleByKey,
  getRuleForPath,
  homeForProfile,
  homeForUser,
  resolveProfile,
  type Profile,
  type Setor,
  type UserLike,
} from "@/lib/access-matrix";

/**
 * Wave 1 v4.0 — Componente 05: middleware com RBAC.
 *
 * Camada superior da defesa em profundidade (RN-013, RNF-007). Le a
 * Matriz de Acesso unificada (shared/access-matrix.json) via
 * frontend/src/lib/access-matrix.ts e:
 *
 *   1. Pass-through em PUBLIC_PATHS (login, _next, favicon, api/health).
 *   2. Refresh da sessao Supabase. Sem user em rota nao-publica -> /login.
 *   3. Com user em /login -> redirect para homeForUser (era /usuarios fixo).
 *   4. Para qualquer outra rota: getRuleForPath -> avalia.
 *      - Rule null (path nao mapeado): pass-through (defensivo: novas
 *        rotas nao quebram navegacao ate serem adicionadas a Matriz).
 *      - Decision = full: pass-through.
 *      - Decision = parcial: pass-through + injeta header x-rbac-scope.
 *      - Decision = negado: 302 para homeForProfile + cookie auth-toast.
 *
 * Performance:
 *   - Lookup do perfil (setor/is_admin) so e feito quando a regra
 *     EXIGE — ou seja, quando ha ao menos 1 perfil != full na matriz
 *     daquela rota. Para login/dashboard/scanner (universais) nao ha
 *     query SQL extra alem do refresh de sessao.
 *   - Cache LRU em memoria por auth_uid (TTL 30s) para amortizar
 *     lookups consecutivos do mesmo user. Trade-off documentado em
 *     analysis Secao 11 (R-7).
 */

interface ProfileSnapshot extends UserLike {
  user_id: string;
}

// Rotas que pulam todo o pipeline RBAC (autenticadas pelo cookie ou nao).
// Aplicadas via startsWith — '/login' tambem cobre '/login/qualquercoisa'.
const PUBLIC_PATHS = ["/login", "/_next", "/favicon.ico", "/api/health"];

// Cache em memoria. No edge runtime cada cold start zera, mas dentro de
// uma instancia warm requests do mesmo user batem no cache.
const PROFILE_CACHE = new Map<
  string,
  { profile: ProfileSnapshot | null; expiresAt: number }
>();
const PROFILE_TTL_MS = 30_000;
const PROFILE_CACHE_MAX = 200;

function isPublicPath(pathname: string): boolean {
  return PUBLIC_PATHS.some((p) => pathname.startsWith(p));
}

/**
 * True se a rota tem ao menos 1 perfil com acesso != full — ou seja, vale
 * a pena fazer o lookup do perfil. Universal (todos full) = false.
 */
function ruleNeedsProfileLookup(rule: ReturnType<typeof getRuleForPath>): boolean {
  if (rule === null) return false;
  for (const p of Object.values(rule.perfis)) {
    if (p.acesso !== "full") return true;
  }
  return false;
}

async function loadProfile(
  supabase: ReturnType<typeof createServerClient>,
  authUid: string,
): Promise<ProfileSnapshot | null> {
  // Cache hit
  const cached = PROFILE_CACHE.get(authUid);
  const now = Date.now();
  if (cached && cached.expiresAt > now) {
    return cached.profile;
  }

  const { data, error } = await supabase
    .from("usuarios")
    .select("id, setor, is_admin, ativo")
    .eq("auth_uid", authUid)
    .maybeSingle();

  let snapshot: ProfileSnapshot | null = null;
  // H-1 (audit fixes): coluna `ativo` agora vem no select e e checada
  // explicitamente. Antes o campo nao era selecionado e a checagem
  // `(data as ...).ativo !== false` era sempre true (undefined !== false),
  // permitindo que usuario desativado passasse pelo middleware (defesa em
  // profundidade comprometida; backend ainda bloqueava via get_current_user).
  if (!error && data) {
    const row = data as {
      id: string;
      setor: string;
      is_admin: boolean;
      ativo: boolean;
    };
    if (row.ativo !== false) {
      snapshot = {
        user_id: row.id,
        setor: row.setor as Setor,
        is_admin: row.is_admin,
      };
    }
  }

  // Cache (best-effort LRU: drop oldest se exceder)
  if (PROFILE_CACHE.size >= PROFILE_CACHE_MAX) {
    const firstKey = PROFILE_CACHE.keys().next().value;
    if (firstKey !== undefined) PROFILE_CACHE.delete(firstKey);
  }
  PROFILE_CACHE.set(authUid, {
    profile: snapshot,
    expiresAt: now + PROFILE_TTL_MS,
  });

  return snapshot;
}

function redirectWithToast(
  request: NextRequest,
  to: string,
  reason: "rota_negada" | "perfil_ausente",
): NextResponse {
  const url = request.nextUrl.clone();
  url.pathname = to;
  url.search = "";
  const res = NextResponse.redirect(url, 302);
  res.cookies.set(
    "auth-toast",
    JSON.stringify({ kind: reason, ts: Date.now() }),
    {
      httpOnly: false, // lido por client component (AuthToast)
      sameSite: "lax",
      // H-2 (audit fixes): em producao (HTTPS) o cookie precisa ter Secure
      // para nao ser enviado via HTTP (boa pratica). Em dev (localhost) o
      // browser aceita Secure=false. NODE_ENV=='production' no build da Vercel.
      secure: process.env.NODE_ENV === "production",
      path: "/",
      maxAge: 10,
    },
  );
  return res;
}

export async function updateSession(request: NextRequest): Promise<NextResponse> {
  const pathname = request.nextUrl.pathname;
  let supabaseResponse = NextResponse.next({ request });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) =>
            request.cookies.set(name, value),
          );
          supabaseResponse = NextResponse.next({ request });
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options),
          );
        },
      },
    },
  );

  const {
    data: { user },
  } = await supabase.auth.getUser();

  // (1) Public paths: pass-through. Note que precisamos AINDA fazer o
  // refresh da sessao para nao perder cookie em /login -> /dashboard.
  if (isPublicPath(pathname)) {
    // Caso especial: ja autenticado em /login -> manda para home do perfil.
    if (user && pathname.startsWith("/login")) {
      // Carrega perfil para escolher home correto (vendedor != admin).
      const profile = await loadProfile(supabase, user.id);
      const url = request.nextUrl.clone();
      url.pathname = homeForUser(profile);
      url.search = "";
      return NextResponse.redirect(url);
    }
    return supabaseResponse;
  }

  // (2) Sem auth em rota nao-publica -> /login.
  if (!user) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    return NextResponse.redirect(url);
  }

  // (3) Localizar regra. Se nao encontrada, pass-through defensivo.
  const rule = getRuleForPath(pathname);
  if (rule === null) {
    return supabaseResponse;
  }

  // (4) Otimizacao: se a regra e universal, evita lookup do perfil.
  if (!ruleNeedsProfileLookup(rule)) {
    return supabaseResponse;
  }

  // (5) Carrega perfil. Usuario sumiu de public.usuarios -> /login.
  const profile = await loadProfile(supabase, user.id);
  if (profile === null) {
    PROFILE_CACHE.delete(user.id);
    return redirectWithToast(request, "/login", "perfil_ausente");
  }

  // (6) Avalia decisao.
  const decision = evaluateRule(rule, profile);
  const profileKey = resolveProfile(profile);

  if (decision.acesso === "negado") {
    return redirectWithToast(
      request,
      homeForProfile(profileKey),
      "rota_negada",
    );
  }

  // FULL ou PARCIAL: pass-through. Para PARCIAL, injeta header com
  // hint de escopo para handlers eventuais lerem (ex.: SSR custom).
  if (decision.acesso === "parcial" && decision.scope) {
    supabaseResponse.headers.set(
      "x-rbac-scope",
      JSON.stringify({
        kind: decision.scope,
        user_id: profile.user_id,
        rule_key: rule.key,
      }),
    );
  }

  return supabaseResponse;
}

// Re-exportacoes para conveniencia em test/debug.
export { ACCESS_MATRIX, getRuleByKey };
export type { Profile };
