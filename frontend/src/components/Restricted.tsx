"use client";

/**
 * Restricted — componente de "Acesso restrito" reutilizavel (Wave 1 v4.0).
 *
 * Renderiza mensagem padronizada + link para a pagina inicial do perfil
 * quando uma rota esta marcada como NEGADO na Matriz de Acesso para o
 * usuario corrente.
 *
 * Uso tipico:
 *   const { hasAccess, loading, profile } = useAuthorization("auditoria");
 *   if (loading) return <PageSkeleton />;
 *   if (!hasAccess) return <Restricted ruleKey="auditoria" />;
 */
import Link from "next/link";

import { homeForProfile, type Profile } from "@/lib/access-matrix";

import styles from "./Restricted.module.css";

export interface RestrictedProps {
  /** Chave da regra negada — usada para mensagem contextual. */
  ruleKey?: string;
  /** Perfil resolvido para escolher o link "Voltar". Se null, vai para /login. */
  profile?: Profile | null;
  /** Sobreescreve a mensagem padrao. */
  message?: string;
  /** Sobreescreve o titulo padrao. */
  title?: string;
}

const DEFAULT_MESSAGES: Record<string, string> = {
  auditoria:
    "A interface de auditoria e restrita ao perfil 3Studio (Administrador). " +
    "Caso precise acessar, solicite a um administrador (RNF-005).",
  relatorios:
    "A area de relatorios e restrita ao perfil 3Studio (Administrador).",
  configuracoes:
    "As configuracoes do sistema so podem ser editadas pelo perfil 3Studio.",
  usuarios:
    "O cadastro de usuarios e restrito ao perfil 3Studio (Administrador).",
  "provas.create":
    "A criacao de provas e restrita ao perfil 3Studio (Administrador).",
};

const DEFAULT_TITLE = "Acesso restrito";
const DEFAULT_MESSAGE =
  "Voce nao tem permissao para acessar esta pagina com seu perfil atual.";

export function Restricted({
  ruleKey,
  profile = null,
  message,
  title,
}: RestrictedProps) {
  const finalMessage =
    message ??
    (ruleKey && DEFAULT_MESSAGES[ruleKey]) ??
    DEFAULT_MESSAGE;
  const home = homeForProfile(profile);

  return (
    <div className={styles.container} role="alert">
      <h1 className={styles.title}>{title ?? DEFAULT_TITLE}</h1>
      <p className={styles.message}>{finalMessage}</p>
      <Link href={home} className={styles.link}>
        {profile === null ? "Ir para o login" : "Voltar"}
      </Link>
    </div>
  );
}
