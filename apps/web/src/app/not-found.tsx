import Link from "next/link";
export default function NotFound() { return <div className="page-content"><div className="page-eyebrow">ERREUR 404</div><h1>Cette page est introuvable.</h1><p className="page-description">Revenez à l’accueil pour poursuivre votre exploration.</p><Link className="button button-primary" href="/">Vérifier une image</Link></div>; }
