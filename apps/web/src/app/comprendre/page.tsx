import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, FileCheck2, Fingerprint, Info, ScanLine, Sparkles } from "lucide-react";

export const metadata: Metadata = { title: "Comprendre Prisme" };

const evidence = [
  {
    icon: Fingerprint,
    number: "01",
    title: "Retrouver une origine",
    text: "Prisme compare maintenant SHA-256, trois hachages perceptuels et des caractéristiques locales ORB aux photos documentées par les médias partenaires.",
    limit: "Une correspondance visuelle relie deux fichiers ; elle ne garantit ni la légende ni le contexte de la scène.",
  },
  {
    icon: Sparkles,
    number: "02",
    title: "Examiner les indices d’IA",
    text: "Une analyse visuelle recherche les indices d’une génération ou retouche par IA, ainsi que les manipulations faciales de type deepfake.",
    limit: "Ces probabilités sont des indices statistiques et peuvent produire des faux positifs ou des faux négatifs.",
  },
  {
    icon: FileCheck2,
    number: "03",
    title: "Lire la provenance",
    text: "Les informations C2PA décrivent une provenance signée. Le registre blockchain permet de consulter les déclarations enregistrées par les médias partenaires simulés.",
    limit: "Une signature valide ne suffit pas à établir la confiance dans son auteur. L’absence de C2PA ne prouve pas qu’une image est fausse.",
  },
];

export default function AboutPage() {
  return <div className="page-content about-page">
    <div className="page-eyebrow"><span className="eyebrow-line" /> LA TRANSPARENCE, PAR PRINCIPE</div>
    <h1>Des indices pour comprendre.<br /><span>Du recul pour décider.</span></h1>
    <p className="page-description">Prisme rapproche plusieurs éléments de preuve pour vous aider<br className="desktop-break" /> à examiner une image et son origine.</p>
    <div className="notice"><Info size={19} /><p><strong>Version actuelle : vérification multimodale connectée.</strong> Prisme recherche une origine partenaire et analyse les indices de génération IA ou de manipulation faciale.</p></div>
    <div className="about-cards">{evidence.map(({ icon: Icon, number, title, text, limit }) => <section className="panel about-card" key={number}><div className="about-card-top"><span className="feature-icon teal"><Icon size={24} /></span><span>{number}</span></div><h2>{title}</h2><p>{text}</p><div className="about-limit">{limit}</div></section>)}</div>
    <section className="principle-panel"><ScanLine size={32} /><div><h2>Une photo réelle peut raconter une histoire trompeuse.</h2><p>La provenance d’un fichier, son éventuelle génération par IA et la véracité de son contexte sont trois questions différentes. Consultez aussi la date, la légende, la source et d’autres informations fiables.</p></div></section>
    <section className="faq-section"><h2>Les questions essentielles</h2><details><summary>Que signifient les pourcentages affichés ?</summary><p>La correspondance visuelle mesure la proximité avec une image partenaire. Les scores IA et deepfake expriment des signaux statistiques distincts. Aucun de ces nombres n’est une preuve de vérité.</p></details><details><summary>Les comptes médias sont-ils déjà approuvés ?</summary><p>Non. L’inscription est ouverte pour le prototype afin de tester l’authentification et l’isolation des données. Une étape de validation administrative sera nécessaire pour de vrais partenaires.</p></details><details><summary>Que prouvera la blockchain ?</summary><p>Elle permettra de vérifier qu’une adresse autorisée a enregistré une déclaration concernant une empreinte. Elle ne certifiera ni la réalité de la scène photographiée ni la justesse de sa légende.</p></details></section>
    <Link href="/" className="button button-primary">Explorer la vérification <ArrowRight size={17} /></Link>
  </div>;
}
