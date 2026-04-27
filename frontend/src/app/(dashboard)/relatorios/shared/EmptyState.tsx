"use client";

/**
 * Estado vazio reutilizavel (Wave 5, Componente 16).
 *
 * Usado quando o agregador retorna 0 ou listas vazias dentro de uma
 * perspectiva (cancelamentos_top, ranking, atrasadas_em_poder, etc).
 */
import styles from "../relatorios.module.css";

interface Props {
  message: string;
  hint?: string;
}

export function EmptyState({ message, hint }: Props) {
  return (
    <div className={styles.emptyBlock} role="status">
      <p className={styles.emptyTitle}>{message}</p>
      {hint && <p className={styles.emptyHint}>{hint}</p>}
    </div>
  );
}
