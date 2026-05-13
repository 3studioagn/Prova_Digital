/**
 * Parsers puros para `useReportFilters` (Wave 5 v4.0 / C16 fix AUD-W5C16-006).
 *
 * Extraidos de `useReportFilters.ts` para permitir reuso direto por testes
 * Vitest sem precisar mockar `next/navigation`. Antes desta extracao, os
 * testes em `useReportFilters.test.ts` re-implementavam estas funcoes
 * localmente (duplicacao com risco de drift); agora importam diretamente
 * deste modulo, exercendo o codigo real.
 *
 * O prefixo `_` no nome do arquivo indica "interno do hook" (convencao
 * do projeto). Padrao validado pela Wave 3 / C12 AUD-W3C12-003
 * (extracao `formatRota`/`isPathActive` para `lib/`).
 *
 * Nao depende de `next/navigation` — testavel em
 * `vitest --environment node` (alinhado com D-13 da Wave 1 v4.0).
 */
import type { ReportScope, RotaCategoria } from "@/lib/types/report";
import { REPORT_SCOPES } from "@/lib/types/report";
import {
  ROTA_OPTIONS,
  STATUS_OPTIONS,
  type Rota,
  type StatusProva,
} from "@/lib/types/prova";

const SCOPE_SET = new Set(REPORT_SCOPES);

/** Wave 5: aceita os 4 valores de `ReportScope`. Default `geral`. */
export function parseScope(value: string | null): ReportScope {
  if (value && (SCOPE_SET as Set<string>).has(value)) {
    return value as ReportScope;
  }
  return "geral";
}

/** Wave 5 v4.0: aceita os 6 valores de `Rota` (4 v4.0 + 2 legacy).
 *
 * Fonte: `ROTA_OPTIONS` em `@/lib/types/prova` — TypeScript barra a build
 * se algum valor de `Rota` for esquecido aqui. URL com valor invalido
 * retorna `null` (filtro desativado, sem erro). */
export function parseRota(value: string | null): Rota | null {
  if (value && (ROTA_OPTIONS as ReadonlyArray<string>).includes(value)) {
    return value as Rota;
  }
  return null;
}

/** Wave 5 v4.0: aceita `matriz` ou `filial` como categoria consolidada. */
export function parseRotaCategoria(value: string | null): RotaCategoria | null {
  if (value === "matriz" || value === "filial") return value;
  return null;
}

/** Wave 5 v4.0: aceita os 17 valores de `StatusProva` (10 v3.0 + 7 v4.0).
 *
 * Fonte: `STATUS_OPTIONS` em `@/lib/types/prova`. Antes da Wave 5 v4.0,
 * o array era hard-codeado com os 10 valores v3.0 — filtros v4.0 na
 * URL (`?status=COM_MOTORISTA_IDA_LAMINACAO`) zeravam silenciosamente. */
export function parseStatus(value: string | null): StatusProva | null {
  if (value && (STATUS_OPTIONS as ReadonlyArray<string>).includes(value)) {
    return value as StatusProva;
  }
  return null;
}

/** Retorna `null` para vazio/null/undefined; trim em strings. */
export function nullableString(value: string | null): string | null {
  if (value === null) return null;
  const t = value.trim();
  return t === "" ? null : t;
}
