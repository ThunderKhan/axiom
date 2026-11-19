import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";
import { publicApiBaseUrl } from "../lib/public-api";

export const metadata: Metadata = {
  title: "Axiom | Founder workspace",
  description:
    "Axiom is developing an evidence-grounded founder intelligence workspace. Live provider and product capabilities are verified separately.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <head>
        <meta name="axiom-api-base-url" content={publicApiBaseUrl} />
      </head>
      <body>{children}</body>
    </html>
  );
}
