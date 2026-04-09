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
