import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Semi Senti — 반도체 감성 분석 대시보드",
  description:
    "반도체 특화 NLP 감성 분석과 재무 펀더멘털을 결합한 매매 시그널 대시보드",
  applicationName: "Semi Senti",
  authors: [{ name: "Semi Senti" }],
};

export const viewport: Viewport = {
  themeColor: "#09090b", // zinc-950
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko" className="dark" suppressHydrationWarning>
      <body className="min-h-screen bg-background font-sans text-foreground">
        {children}
      </body>
    </html>
  );
}
