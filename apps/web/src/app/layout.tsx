import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";
import { publicApiBaseUrl } from "../lib/public-api";

export const metadata: Metadata = {
  title: "Axiom | Foundation",
  description:
    "Axiom frontend foundation. Product features are not yet available.",
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
