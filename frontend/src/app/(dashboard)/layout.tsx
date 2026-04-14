"use client";

import { useCallback, useEffect, useState, type ReactNode } from "react";
import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { apiFetch } from "@/lib/api";
import { useInactivityTimeout } from "@/hooks/useInactivityTimeout";
import {
  ChartIcon,
  CloseIcon,
  GearIcon,
  HomeIcon,
  InfoIcon,
  LaptopIcon,
  PlusIcon,
  ScanIcon,
  SearchIcon,
  UserIcon,
} from "@/components/icons";
import styles from "./layout.module.css";

interface UserInfo {
  nome: string;
  setor: string;
  is_admin: boolean;
}

const INACTIVITY_TIMEOUT_MS = 30 * 60 * 1000; // 30 minutes (RNF-003)

/**
 * Cada item do menu. Quando `href` e omitido, renderizamos um <span> com o
 * mesmo visual do <Link>, mas nao-navegavel — essas rotas sao de Wave 2+ e
 * sao adicionadas trocando o span por um Link assim que a pagina existir.
 */
interface NavItemSpec {
  key: string;
  label: string;
  icon: ReactNode;
  href?: string;
}

const MAIN_NAV: NavItemSpec[] = [
  { key: "dashboard", label: "Dashboard", icon: <HomeIcon />, href: "/dashboard" },
  { key: "provas", label: "Provas", icon: <LaptopIcon />, href: "/provas" },
  { key: "nova-prova", label: "Nova prova", icon: <PlusIcon />, href: "/nova-prova" },
  { key: "escanear", label: "Escanear", icon: <ScanIcon />, href: "/escanear" },
  { key: "relatorios", label: "Relatorios", icon: <ChartIcon /> },
  { key: "usuarios", label: "Usuarios", icon: <UserIcon />, href: "/usuarios" },
];

const SECONDARY_NAV: NavItemSpec[] = [
  { key: "configuracoes", label: "Configuracoes", icon: <GearIcon />, href: "/configuracoes" },
  { key: "informacoes", label: "Informacoes", icon: <InfoIcon /> },
];

function NavEntry({
  item,
  active,
}: {
  item: NavItemSpec;
  active: boolean;
}) {
  const className = active ? styles.navItemActive : styles.navItem;
  const content = (
    <>
      <span className={styles.navIcon}>{item.icon}</span>
      <span>{item.label}</span>
    </>
  );

  if (!item.href) {
    return (
      <span className={className} aria-disabled="true">
        {content}
      </span>
    );
  }

  return (
    <Link href={item.href} className={className}>
      {content}
    </Link>
  );
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<UserInfo | null>(null);
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);

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

  // Auto-close mobile drawer on route change.
  useEffect(() => {
    setIsMobileNavOpen(false);
  }, [pathname]);

  // Lock body scroll while drawer is open.
  useEffect(() => {
    if (!isMobileNavOpen) return;
    const original = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = original;
    };
  }, [isMobileNavOpen]);

  // ESC closes the drawer.
  useEffect(() => {
    if (!isMobileNavOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setIsMobileNavOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [isMobileNavOpen]);

  const handleLogout = useCallback(async () => {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.replace("/login");
  }, [router]);

  // RNF-003: 30 min inactivity timeout
  useInactivityTimeout(INACTIVITY_TIMEOUT_MS, handleLogout);

  const firstName = user?.nome ? user.nome.split(" ")[0] : "";
  const greeting = firstName ? `Ola ${firstName}!` : "Ola!";

  const sidebarClassName = isMobileNavOpen
    ? `${styles.sidebar} ${styles.sidebarOpen}`
    : styles.sidebar;

  return (
    <div className={styles.wrapper}>
      {/* Mobile-only top bar: floating pill with logo + hamburger */}
      <header className={styles.mobileHeader}>
        <div className={styles.mobileHeaderInner}>
          <Image
            src="/images/logo-3studio.svg"
            alt="3Studio"
            width={100}
            height={22}
            className={styles.mobileLogo}
            priority
          />
          <button
            type="button"
            className={styles.hamburger}
            aria-label="Abrir menu"
            aria-expanded={isMobileNavOpen}
            aria-controls="sidebar-nav"
            onClick={() => setIsMobileNavOpen(true)}
          >
            <span className={styles.hamburgerBar} />
            <span className={styles.hamburgerBar} />
            <span className={styles.hamburgerBar} />
          </button>
        </div>
      </header>

      {/* Backdrop closes the drawer on tap. Only rendered when open. */}
      {isMobileNavOpen && (
        <div
          className={styles.backdrop}
          onClick={() => setIsMobileNavOpen(false)}
          aria-hidden="true"
        />
      )}

      <aside id="sidebar-nav" className={sidebarClassName}>
        {/* X close button — visible only inside the mobile drawer */}
        <button
          type="button"
          className={styles.closeBtn}
          aria-label="Fechar menu"
          onClick={() => setIsMobileNavOpen(false)}
        >
          <CloseIcon width={24} height={24} />
        </button>

        <div className={styles.sidebarTop}>
          <Image
            src="/images/logo-3studio.svg"
            alt="3Studio"
            width={132}
            height={28}
            className={styles.logo}
            priority
          />

          <div className={styles.greeting}>{greeting}</div>

          <div className={styles.searchBox}>
            <SearchIcon className={styles.searchIcon} aria-hidden="true" />
            <input
              type="search"
              className={styles.searchInput}
              placeholder="Buscar..."
              aria-label="Buscar no sistema"
            />
          </div>

          <nav className={styles.nav} aria-label="Navegacao principal">
            {MAIN_NAV.map((item) => (
              <NavEntry
                key={item.key}
                item={item}
                active={Boolean(item.href && pathname === item.href)}
              />
            ))}
          </nav>

          <div className={styles.navDivider} role="separator" />

          <nav className={styles.nav} aria-label="Navegacao secundaria">
            {SECONDARY_NAV.map((item) => (
              <NavEntry key={item.key} item={item} active={false} />
            ))}
          </nav>
        </div>

        <div className={styles.userBlock}>
          <div className={styles.avatar} aria-hidden="true" />
          <div className={styles.userInfo}>
            <div className={styles.userName}>{user?.nome || "..."}</div>
            <div className={styles.userRole}>3Studio</div>
          </div>
          <button
            type="button"
            className={styles.logoutBtn}
            onClick={handleLogout}
          >
            Sair
          </button>
        </div>
      </aside>

      <main className={styles.main}>
        <div className={styles.card}>
          <div className={styles.cardInner}>{children}</div>
        </div>
      </main>
    </div>
  );
}
