export const metadata = {
  title: "Rastreio de Provas Digitais",
  description: "Sistema de rastreio de provas digitais - 3Studio",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
