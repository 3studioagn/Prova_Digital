import type { Viewport } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
});

// Wave 3 v4.0 / Componente 10: JetBrains Mono usado no input do tab Manual
// (`/escanear`) — fidelidade visual ao Figma.
const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-jetbrains-mono",
});

export const metadata = {
  title: "Rastreio de Provas Digitais",
  description: "Sistema de rastreio de provas digitais - 3Studio",
};

// Wave 8 v5.0 / C23: viewport-fit=cover habilita as CSS env(safe-area-inset-*)
// em dispositivos com notch/home indicator (Decisao 5.ii). width/initialScale
// sao o default do Next, declarados aqui por explicitude. NAO definimos
// maximumScale/userScalable — bloquear zoom viola WCAG 2.1 SC 1.4.4/1.4.10.
// Inerte no desktop: sem safe areas, os insets resolvem para 0.
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR" className={`${inter.variable} ${jetbrainsMono.variable}`}>
      <body className={inter.className}>{children}</body>
    </html>
  );
}
