"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { apiFetch } from "@/lib/api";
import { useInactivityTimeout } from "@/hooks/useInactivityTimeout";
import styles from "./layout.module.css";

interface UserInfo {
  nome: string;
  setor: string;
  is_admin: boolean;
}

const INACTIVITY_TIMEOUT_MS = 30 * 60 * 1000; // 30 minutes (RNF-003)

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<UserInfo | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    const supabase = createClient();
    supabase.auth.getSession().then(async ({ data: { session } }) => {
      if (!session || controller.signal.aborted) return;
      try {
        const data = await apiFetch<UserInfo>("/api/v1/users/me", {
          token: session.access_token,
          signal: controller.signal,
        });
        if (!controller.signal.aborted) setUser(data);
      } catch {
        // silent — sidebar will show fallback (includes AbortError)
      }
    });
    return () => controller.abort();
  }, []);

  const handleLogout = useCallback(async () => {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.replace("/login");
  }, [router]);

  // RNF-003: 30 min inactivity timeout
  useInactivityTimeout(INACTIVITY_TIMEOUT_MS, handleLogout);

  const initials = user?.nome
    ? user.nome.split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase()
    : "?";

  return (
    <div className={styles.wrapper}>
      <aside className={styles.sidebar}>
        <div className={styles.logo}>3STUDIO</div>

        <nav className={styles.nav}>
          <Link
            href="/usuarios"
            className={
              pathname === "/usuarios" ? styles.navItemActive : styles.navItem
            }
          >
            Usuarios
          </Link>
        </nav>

        {user?.is_admin && (
          <div className={styles.navSection}>
            <span
              className={styles.navItem}
              style={{ opacity: 0.5, cursor: "default" }}
            >
              Configuracoes (Wave 2+)
            </span>
          </div>
        )}

        <div className={styles.userBlock}>
          <div className={styles.avatar}>{initials}</div>
          <div className={styles.userInfo}>
            <div className={styles.userName}>{user?.nome || "..."}</div>
            <div className={styles.userRole}>{user?.setor || ""}</div>
          </div>
          <button className={styles.logoutBtn} onClick={handleLogout}>
            Sair
          </button>
        </div>
      </aside>

      <main className={styles.main}>{children}</main>
    </div>
  );
}
