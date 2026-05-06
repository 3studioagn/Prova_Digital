/**
 * Helper de destaque de menu por prefix-match.
 *
 * Wave 2 v4.0 / C08 (ADR-128): destaca o item de menu correspondente ao
 * pathname atual mesmo quando ele e um subpath (ex.: "/provas" ativo em
 * "/provas/[id]"). Antes o C08 a comparacao era estrita (`===`) e quebrava
 * esse caso. A condicao `+ "/"` evita falsos positivos do tipo
 * "/provas-other" ativando "/provas".
 *
 * Extraido para `lib/` na sessao de correcoes pos-auditoria do C08
 * (AUD-W2C08-003 + AUD-W2C08-012) para permitir teste unitario isolado
 * via Vitest, sem precisar de DOM ou render do layout completo.
 */
export function isPathActive(
  pathname: string,
  href: string | undefined,
): boolean {
  if (!href) return false;
  if (pathname === href) return true;
  return pathname.startsWith(href + "/");
}
