/**
 * Matriz de Acesso (RBAC) — Wave 1 v4.0, Componente 05.
 *
 * Le shared/access-matrix.json (fonte unica espelhada por TS, Python, RLS)
 * e expoe API tipada para middleware + hook + componentes.
 *
 * Ver tambem:
 *  - shared/access-matrix.json (SSoT)
 *  - backend/app/access/matrix.py (espelho Python)
 *  - backend/migrations/rls/012_move_helpers_to_app_private.sql (espelho RLS)
 *  - docs/wave1-v4/analysis.md Secao 4
 *
 * Decisao chave (analysis Secao 6.0):
 *  - Perfil "3Studio" da Matriz = `is_admin = true` (qualquer setor).
 *  - Outros 3 perfis: `is_admin = false AND setor = '<NOME>'`.
 *  - STUDIO sem is_admin retorna profile=null -> tratado como NEGADO em todo lugar.
 */
import matrixData from "../../../shared/access-matrix.json";

// ── Tipos ──────────────────────────────────────────────────────────────────

export type Profile = "studio_admin" | "vendedor" | "motorista" | "clicheria";
export type Setor = "STUDIO" | "VENDEDOR" | "MOTORISTA" | "CLICHERIA";
export type Acesso = "full" | "parcial" | "negado";
export type ScopeKind =
  | "self_vendedor"
  | "status_motorista_em_transito"
  | "status_clicheria";
export type MatchKind = "exact" | "prefix" | "dynamic" | "action";

export interface PerfilDecision {
  acesso: Acesso;
  scope?: ScopeKind;
}

export interface AccessRule {
  key: string;
  path: string;
  match: MatchKind;
  perfis: Record<Profile, PerfilDecision>;
}

// ── Carregamento + validacao do JSON (uma vez no boot) ────────────────────

interface RawRule {
  key: string;
  path: string;
  match: string;
  perfis: Record<string, { acesso: string; scope?: string }>;
}

interface RawMatrix {
  version: string;
  perfis: string[];
  home_by_profile: Record<string, string>;
  rules: RawRule[];
}

const raw = matrixData as unknown as RawMatrix;

const PROFILES_ORDER: Profile[] = [
  "studio_admin",
  "vendedor",
  "motorista",
  "clicheria",
];

function buildHomeByProfile(): Record<Profile, string> {
  const out = {} as Record<Profile, string>;
  for (const p of PROFILES_ORDER) {
    const v = raw.home_by_profile[p];
    if (typeof v !== "string" || !v.startsWith("/")) {
      throw new Error(
        `access-matrix.json: home_by_profile['${p}'] invalido: ${v}`,
      );
    }
    out[p] = v;
  }
  return out;
}

// M-3 (audit fixes): conjuntos canonicos para validacao runtime — paridade
// com matrix.py (FAIL FAST se JSON tiver typo ou esquema invalido).
const VALID_ACESSOS = new Set<Acesso>(["full", "parcial", "negado"]);
const VALID_SCOPES = new Set<ScopeKind>([
  "self_vendedor",
  "status_motorista_em_transito",
  "status_clicheria",
]);
const VALID_MATCHES = new Set<MatchKind>(["exact", "prefix", "dynamic", "action"]);

function buildRules(): { rules: AccessRule[]; byKey: Record<string, AccessRule> } {
  const rules: AccessRule[] = [];
  const byKey: Record<string, AccessRule> = {};
  for (const r of raw.rules) {
    if (!VALID_MATCHES.has(r.match as MatchKind)) {
      throw new Error(
        `access-matrix.json: regra '${r.key}' tem match='${r.match}' invalido. ` +
          `Aceitos: ${[...VALID_MATCHES].join(", ")}.`,
      );
    }
    const perfis = {} as Record<Profile, PerfilDecision>;
    for (const p of PROFILES_ORDER) {
      const d = r.perfis[p];
      if (!d) {
        throw new Error(
          `access-matrix.json: regra '${r.key}' sem decisao para perfil '${p}'.`,
        );
      }
      // M-3 (audit fixes): valida `acesso` e `scope` em runtime (typo no
      // JSON quebra startup, em vez de cair no fallback false() em runtime).
      if (!VALID_ACESSOS.has(d.acesso as Acesso)) {
        throw new Error(
          `access-matrix.json: regra '${r.key}'[${p}] acesso='${d.acesso}' ` +
            `invalido. Aceitos: ${[...VALID_ACESSOS].join(", ")}.`,
        );
      }
      const acesso = d.acesso as Acesso;
      const scope = d.scope as ScopeKind | undefined;
      if (acesso === "parcial") {
        if (scope === undefined) {
          throw new Error(
            `access-matrix.json: regra '${r.key}'[${p}] e parcial mas sem 'scope'.`,
          );
        }
        if (!VALID_SCOPES.has(scope)) {
          throw new Error(
            `access-matrix.json: regra '${r.key}'[${p}] scope='${scope}' invalido. ` +
              `Aceitos: ${[...VALID_SCOPES].join(", ")}. Para adicionar um novo, ` +
              `atualize tambem ScopeKind + scope_filter_for (Python) e o ` +
              `branch correspondente do middleware.`,
          );
        }
      } else if (scope !== undefined) {
        throw new Error(
          `access-matrix.json: regra '${r.key}'[${p}] tem acesso='${acesso}' mas ` +
            `tem 'scope' definido. 'scope' so faz sentido para acesso=parcial.`,
        );
      }
      perfis[p] = { acesso, scope };
    }
    const rule: AccessRule = {
      key: r.key,
      path: r.path,
      match: r.match as MatchKind,
      perfis,
    };
    rules.push(rule);
    byKey[r.key] = rule;
  }
  return { rules, byKey };
}

const { rules: ALL_RULES, byKey: RULES_BY_KEY } = buildRules();
const HOME_BY_PROFILE = buildHomeByProfile();

// ── API publica ────────────────────────────────────────────────────────────

export const ACCESS_MATRIX: readonly AccessRule[] = ALL_RULES;

export function getRuleByKey(key: string): AccessRule | null {
  return RULES_BY_KEY[key] ?? null;
}

/**
 * Resolve a regra que aplica a um pathname (ex.: '/auditoria',
 * '/provas/abc-123'). Tenta na ordem:
 *   1. exact (path exato)
 *   2. dynamic (path com [id] — match prefixo + 1 segmento qualquer)
 *   3. prefix (path comeca com a regra)
 *
 * Regras tipo 'action' nao tem path navegavel (path = '(action)'); sao
 * usadas apenas via getRuleByKey.
 *
 * M-4 (audit fixes): trailing slashes sao normalizados antes do match para
 * fechar o gap onde Next.js poderia entregar `/provas/` ao middleware
 * (por config trailingSlash:true ou comportamento futuro). Sem essa
 * normalizacao, exact/dynamic/prefix falham todos para `/provas/` e o
 * middleware passaria `null -> pass-through` (bypass do RBAC).
 */
export function getRuleForPath(pathname: string): AccessRule | null {
  if (pathname.length > 1 && pathname.endsWith("/")) {
    pathname = pathname.slice(0, -1);
  }
  // exact match primeiro
  for (const r of ALL_RULES) {
    if (r.match === "exact" && r.path === pathname) return r;
  }
  // dynamic: /provas/[id] cobre /provas/<qualquer-coisa> mas nao /provas
  for (const r of ALL_RULES) {
    if (r.match !== "dynamic") continue;
    const dynamicPrefix = r.path.replace(/\[[^\]]+\]/g, ""); // '/provas/'
    if (pathname.startsWith(dynamicPrefix) && pathname.length > dynamicPrefix.length) {
      return r;
    }
  }
  // prefix: /usuarios cobre /usuarios e /usuarios/foo
  for (const r of ALL_RULES) {
    if (r.match !== "prefix") continue;
    if (pathname === r.path || pathname.startsWith(r.path + "/")) return r;
  }
  return null;
}

export interface UserLike {
  is_admin: boolean;
  setor: Setor;
}

/**
 * Classifica um Usuario em um Profile.
 *
 * - is_admin=true -> 'studio_admin' (precedencia sobre setor).
 * - setor=VENDEDOR/MOTORISTA/CLICHERIA -> perfil correspondente.
 * - STUDIO sem admin -> null (sem perfil mapeado, NEGADO em todo lugar).
 */
export function resolveProfile(user: UserLike | null | undefined): Profile | null {
  if (!user) return null;
  if (user.is_admin) return "studio_admin";
  switch (user.setor) {
    case "VENDEDOR":
      return "vendedor";
    case "MOTORISTA":
      return "motorista";
    case "CLICHERIA":
      return "clicheria";
    case "STUDIO":
    default:
      return null;
  }
}

/**
 * Avalia uma regra para um Usuario. Sem user (anon) ou perfil nao mapeado
 * -> NEGADO.
 */
export function evaluateRule(rule: AccessRule, user: UserLike | null | undefined): PerfilDecision {
  const profile = resolveProfile(user);
  if (profile === null) return { acesso: "negado" };
  return rule.perfis[profile];
}

export function homeForProfile(profile: Profile | null): string {
  if (profile === null) return "/login";
  return HOME_BY_PROFILE[profile];
}

export function homeForUser(user: UserLike | null | undefined): string {
  return homeForProfile(resolveProfile(user));
}
