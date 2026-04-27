"use client";

/**
 * Cartao de KPI compartilhado pelas 4 perspectivas (Wave 5, Componente 16).
 *
 * Suporta `highlight` para realcar valores de atencao (atrasadas) ou positivos
 * (concluidas). Animacao de entrada via Framer Motion (já no bundle).
 */
import { motion } from "framer-motion";

import styles from "../relatorios.module.css";

interface Props {
  label: string;
  value: string;
  /** Texto auxiliar abaixo do valor (ex: "no periodo"). */
  hint?: string;
  /** Realce visual do valor. */
  highlight?: "warning" | "success" | "neutral";
  /** Indice da animacao de entrada — usado pra stagger. */
  delayIndex?: number;
}

export function KpiCard({
  label,
  value,
  hint,
  highlight = "neutral",
  delayIndex = 0,
}: Props) {
  const valueClass =
    highlight === "warning"
      ? styles.kpiValueWarn
      : highlight === "success"
        ? styles.kpiValueSuccess
        : styles.kpiValue;

  return (
    <motion.div
      className={styles.kpiCard}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, delay: delayIndex * 0.04 }}
    >
      <span className={styles.kpiLabel}>{label}</span>
      <span className={valueClass}>{value}</span>
      {hint && <span className={styles.kpiHint}>{hint}</span>}
    </motion.div>
  );
}
