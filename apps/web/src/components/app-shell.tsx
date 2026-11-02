"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Aperture, ArrowUpRight, BookOpen, Fingerprint, ImageIcon, LayoutGrid, ScanLine, ShieldCheck } from "lucide-react";

const navigation = [
  { href: "/", label: "Vérifier une image", icon: ScanLine },
  { href: "/medias", label: "Espace média", icon: LayoutGrid },
  { href: "/comprendre", label: "Comprendre Prisme", icon: BookOpen },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  return <div className="app-shell">
    <a className="skip-link" href="#contenu">Aller au contenu</a>
    <aside className="sidebar">
      <Link href="/" className="brand" aria-label="Prisme, accueil"><span className="brand-mark"><Aperture size={27} /></span>prisme<span className="brand-dot">.</span></Link>
      <div className="workspace-label">L’IMAGE, EN CONFIANCE</div>
      <nav aria-label="Navigation principale">{navigation.map(({ href, label, icon: Icon }) => <Link key={href} href={href} className={`nav-item ${pathname === href ? "active" : ""}`} aria-current={pathname === href ? "page" : undefined}><Icon size={19} />{label}{pathname === href && <span className="nav-dot" />}</Link>)}</nav>
      <div className="sidebar-note"><div className="note-icon"><Fingerprint size={25} /></div><h3>Remonter à la source.</h3><p>Des indices de provenance pour regarder les images autrement.</p><Link href="/comprendre">Découvrir l’approche <ArrowUpRight size={15} /></Link></div>
      <div className="sidebar-bottom"><span className="status-dot" /><span>Prototype local</span><span className="version">v0.1</span></div>
    </aside>
    <div className="main-shell">
      <header className="topbar"><div className="breadcrumb"><ImageIcon size={16} /><span>Plateforme de vérification</span><span className="breadcrumb-slash">/</span><strong>{navigation.find(n => n.href === pathname)?.label ?? "Prisme"}</strong></div><span className="demo-badge"><span />Mode démonstration</span></header>
      <main id="contenu" tabIndex={-1}>{children}</main>
      <footer className="footer"><span>© {new Date().getFullYear()} Prisme · Projet académique</span><span><ShieldCheck size={14} /> Une preuve de provenance n’est pas une preuve de vérité.</span></footer>
    </div>
  </div>;
}
