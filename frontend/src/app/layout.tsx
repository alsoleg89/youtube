import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin", "cyrillic"] });

export const metadata: Metadata = {
  title: "YouTube → Articles",
  description: "Конвертируйте YouTube видео в статьи для Medium, Habr и LinkedIn",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ru" className="dark">
      <body
        className={`${inter.className} min-h-screen bg-zinc-950 text-zinc-100 antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
