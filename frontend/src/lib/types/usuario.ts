/**
 * Tipos compartilhados do dominio de usuarios usados pelo frontend.
 * Espelho parcial de backend/app/domain/schemas/user.py (apenas o subset
 * necessario para exibir vendedor em selects/listas).
 */

export type Setor = "STUDIO" | "VENDEDOR" | "MOTORISTA" | "CLICHERIA";
export type Localizacao = "MATRIZ" | "FILIAL";

export interface UsuarioResponse {
  id: string;
  auth_uid: string;
  nome: string;
  email: string;
  setor: Setor;
  localizacao: Localizacao | null;
  is_admin: boolean;
  ativo: boolean;
  created_at: string;
  updated_at: string;
  created_by: string | null;
}

export interface UsuarioListResponse {
  items: UsuarioResponse[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

/**
 * Shape da resposta do `GET /api/v1/users/me` — usado pelas paginas do
 * dashboard para mostrar o usuario logado e decidir visibilidade de
 * filtros/acoes admin-only.
 *
 * C07 B1 (auditoria externa Wave 2): antes esse tipo era duplicado
 * inline em multiplos arquivos (`provas/page.tsx`, `layout.tsx`). Agora
 * a Wave 2 consome esta fonte unica; a duplicacao restante em
 * `layout.tsx` sera migrada quando Wave 1 for destravada (baixa prioridade,
 * tipo privado isolado de Wave 1 nao causa drift com a Wave 2).
 */
export interface MeResponse {
  id: string;
  nome: string;
  setor: Setor;
  localizacao: Localizacao | null;
  is_admin: boolean;
}
