"use client";

import { FormEvent, useState } from "react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import styles from "./login.module.css";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const supabase = createClient();
    const { error: authError } = await supabase.auth.signInWithPassword({
      email,
      password: senha,
    });

    if (authError) {
      setLoading(false);
      if (authError.message.includes("Invalid login")) {
        setError("E-mail ou senha incorretos.");
      } else if (authError.message.includes("Email not confirmed")) {
        setError("Conta ainda nao confirmada.");
      } else {
        setError("Erro ao fazer login. Tente novamente.");
      }
      return;
    }

    router.replace("/usuarios");
    router.refresh();
  }

  return (
    <div className={styles.container}>
      {/* SVG clip-path for the image panel's custom shape (slanted right edge) */}
      <svg className={styles.clipSvg} aria-hidden="true">
        <defs>
          <clipPath id="imagePanelClip" clipPathUnits="objectBoundingBox">
            <path d="M0 0.0347 C0 0.0155 0.0163 0 0.0364 0 L0.9636 0 C0.9856 0 1.0026 0.0185 0.9997 0.0393 L0.8699 0.9699 C0.8674 0.9871 0.852 1 0.8337 1 H0.0364 C0.0163 1 0 0.9845 0 0.9653 V0.0347Z" />
          </clipPath>
        </defs>
      </svg>

      <div className={styles.imagePanel} />

      <div className={styles.formPanel}>
        <div className={styles.formContent}>
          <Image
            src="/images/logo-3studio.svg"
            alt="3Studio"
            width={122}
            height={26}
            className={styles.logo}
            priority
          />

          <h1 className={styles.title}>Fazer login</h1>
          <p className={styles.subtitle}>
            Sistema de rastreio de provas digitais
          </p>

          <form className={styles.form} onSubmit={handleSubmit}>
            {error && <div className={styles.error}>{error}</div>}

            <div className={styles.fieldGroup}>
              <label className={styles.label} htmlFor="email">
                E-mail:
              </label>
              <input
                id="email"
                className={styles.input}
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="seu@email.com"
                required
                autoComplete="email"
              />
            </div>

            <div className={styles.fieldGroup}>
              <label className={styles.label} htmlFor="senha">
                Senha:
              </label>
              <input
                id="senha"
                className={styles.input}
                type="password"
                value={senha}
                onChange={(e) => setSenha(e.target.value)}
                placeholder="********"
                required
                autoComplete="current-password"
                minLength={8}
              />
            </div>

            <div className={styles.linksRow}>
              <span className={styles.linkRegister}>
                Nao possui uma conta?{" "}
                <span className={styles.linkRegisterUnderline}>
                  Registre-se
                </span>
              </span>
              <span className={styles.linkForgot}>Esqueci minha senha</span>
            </div>

            <button
              type="submit"
              className={styles.submitBtn}
              disabled={loading}
            >
              {loading ? "Entrando..." : "Entrar"}
            </button>
          </form>

          <p className={styles.footer}>&copy;3Studio 2026</p>
        </div>
      </div>
    </div>
  );
}
