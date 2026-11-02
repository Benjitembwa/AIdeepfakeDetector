import type { Metadata } from "next";
import { AppShell } from "@/components/app-shell";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "Prisme — Vérifier une image", template: "%s · Prisme" },
  description: "Explorez l'origine des images. Prototype de vérification de provenance et de détection des images générées par IA.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="fr"><body><AppShell>{children}</AppShell></body></html>;
}
