import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "EML Calculator — two buttons compute everything",
  description:
    "A scientific calculator with two keys (1 and eml, where eml(x,y)=exp(x)−ln(y)), plus AI that compiles any formula to a verified EML button sequence.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full bg-zinc-900 antialiased`}
    >
      <body className="min-h-full flex flex-col bg-zinc-900">{children}</body>
    </html>
  );
}
