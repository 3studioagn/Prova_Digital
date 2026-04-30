"use client";

/**
 * AuthToast — le o cookie `auth-toast` setado pelo middleware quando ele
 * redireciona por acesso negado, exibe a mensagem por ~6s e remove o
 * cookie. Wave 1 v4.0, Componente 05.
 *
 * Renderizado uma unica vez no layout do dashboard. Sem dependencias
 * pesadas (sem Framer Motion — Wave 6 Componente 20 substituira por
 * `<Toaster>` global animado).
 */
import { useEffect, useState } from "react";

import styles from "./AuthToast.module.css";

const COOKIE_NAME = "auth-toast";
const VISIBLE_MS = 6000;

const MESSAGES: Record<string, string> = {
  rota_negada: "Voce nao tem permissao para acessar essa pagina.",
  perfil_ausente: "Sessao invalida. Faca login novamente.",
};

interface ToastPayload {
  kind: string;
  ts: number;
}

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const prefix = `${name}=`;
  for (const part of document.cookie.split(";")) {
    const trimmed = part.trim();
    if (trimmed.startsWith(prefix)) {
      return decodeURIComponent(trimmed.slice(prefix.length));
    }
  }
  return null;
}

function clearCookie(name: string): void {
  if (typeof document === "undefined") return;
  document.cookie = `${name}=; Max-Age=0; path=/; SameSite=Lax`;
}

export function AuthToast() {
  const [visible, setVisible] = useState<string | null>(null);

  useEffect(() => {
    const raw = readCookie(COOKIE_NAME);
    if (!raw) return;
    let payload: ToastPayload | null = null;
    try {
      payload = JSON.parse(raw) as ToastPayload;
    } catch {
      // cookie corrompido — apenas limpa
      clearCookie(COOKIE_NAME);
      return;
    }
    clearCookie(COOKIE_NAME);
    if (!payload || typeof payload.kind !== "string") return;

    const message = MESSAGES[payload.kind] ?? "Acesso restrito.";
    setVisible(message);
    const timer = window.setTimeout(() => setVisible(null), VISIBLE_MS);
    return () => window.clearTimeout(timer);
  }, []);

  if (!visible) return null;

  return (
    <div className={styles.toast} role="status" aria-live="polite">
      {visible}
    </div>
  );
}
