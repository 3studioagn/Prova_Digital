/**
 * Biblioteca de icones SVG inline.
 *
 * Todos os icones sao desenhados a mao com stroke="currentColor" para herdarem
 * a cor do elemento pai via CSS. O stroke width padrao e 1.75 — condiz com o
 * visual outline fino do Figma. Cada icone aceita props SVG padrao (size via
 * width/height, className, aria-*, etc).
 *
 * Usar <HomeIcon className={styles.icon} /> ou <HomeIcon width={20} height={20} />.
 */
import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement>;

const baseProps = {
  width: 22,
  height: 22,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.75,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

export function SearchIcon(props: IconProps) {
  return (
    <svg {...baseProps} {...props} aria-hidden={props["aria-label"] ? undefined : true}>
      <circle cx="11" cy="11" r="7.5" />
      <path d="m20 20-3.6-3.6" />
    </svg>
  );
}

export function HomeIcon(props: IconProps) {
  return (
    <svg {...baseProps} {...props} aria-hidden={props["aria-label"] ? undefined : true}>
      <path d="M3.5 10.5 12 3.75l8.5 6.75V20a1 1 0 0 1-1 1h-5v-6.5h-5V21h-5a1 1 0 0 1-1-1v-9.5Z" />
    </svg>
  );
}

export function LaptopIcon(props: IconProps) {
  return (
    <svg {...baseProps} {...props} aria-hidden={props["aria-label"] ? undefined : true}>
      <rect x="3.5" y="5" width="17" height="11" rx="1.5" />
      <path d="M2 19h20" />
    </svg>
  );
}

export function PlusIcon(props: IconProps) {
  return (
    <svg {...baseProps} {...props} aria-hidden={props["aria-label"] ? undefined : true}>
      <path d="M12 5v14M5 12h14" />
    </svg>
  );
}

export function ScanIcon(props: IconProps) {
  return (
    <svg {...baseProps} {...props} aria-hidden={props["aria-label"] ? undefined : true}>
      <rect x="3.5" y="3.5" width="7" height="7" rx="0.75" />
      <rect x="13.5" y="3.5" width="7" height="7" rx="0.75" />
      <rect x="3.5" y="13.5" width="7" height="7" rx="0.75" />
      <path d="M14 14h3M14 17v3M17 17h3M20 14v3" />
    </svg>
  );
}

export function ChartIcon(props: IconProps) {
  return (
    <svg {...baseProps} {...props} aria-hidden={props["aria-label"] ? undefined : true}>
      <path d="M4 20V10M10 20V4M16 20v-7M22 20H2" />
    </svg>
  );
}

export function UserIcon(props: IconProps) {
  return (
    <svg {...baseProps} {...props} aria-hidden={props["aria-label"] ? undefined : true}>
      <circle cx="12" cy="8.5" r="4" />
      <path d="M4 20c1.5-4 4.5-6 8-6s6.5 2 8 6" />
    </svg>
  );
}

export function GearIcon(props: IconProps) {
  return (
    <svg {...baseProps} {...props} aria-hidden={props["aria-label"] ? undefined : true}>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h.01A1.65 1.65 0 0 0 10 4.6V4a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v.01c.26.61.86 1 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z" />
    </svg>
  );
}

export function InfoIcon(props: IconProps) {
  return (
    <svg {...baseProps} {...props} aria-hidden={props["aria-label"] ? undefined : true}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 8h.01M11 12h1v5h1" />
    </svg>
  );
}

export function ChevronDownIcon(props: IconProps) {
  return (
    <svg {...baseProps} {...props} aria-hidden={props["aria-label"] ? undefined : true}>
      <path d="m6 9 6 6 6-6" />
    </svg>
  );
}

export function CheckIcon(props: IconProps) {
  return (
    <svg {...baseProps} {...props} aria-hidden={props["aria-label"] ? undefined : true}>
      <path d="m4 12 5 5L20 6" strokeWidth={2.5} />
    </svg>
  );
}

export function CloseIcon(props: IconProps) {
  return (
    <svg {...baseProps} {...props} aria-hidden={props["aria-label"] ? undefined : true}>
      <path d="M18 6 6 18M6 6l12 12" />
    </svg>
  );
}
