"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import { ArrowRight, ArrowUpRight, BadgeCheck, ChevronRight, CircleHelp, FileCheck2, Fingerprint, FlaskConical, Info, LoaderCircle, ScanLine, SearchX, ShieldCheck, Sparkles } from "lucide-react";
import { ImageDropzone } from "@/components/image-dropzone";
import { ApiError, VerificationMatch, VerificationReport, verifyImage } from "@/lib/api";
import { SelectedImage } from "@/lib/files";

type Result = "demo" | VerificationReport | null;

const matchLabels: Record<VerificationMatch["matched_by"], string> = {
  exact: "Copie exacte",
  perceptual: "Similarité perceptuelle",
  local_features: "Correspondance après recadrage",
};

export function VerificationWorkspace() {
  const [selected, setSelected] = useState<SelectedImage | null>(null);
  const [result, setResult] = useState<Result>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const resultRef = useRef<HTMLElement>(null);

  function revealResult(next: Exclude<Result, null>) {
    setResult(next);
    setTimeout(() => {
      resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      resultRef.current?.focus({ preventScroll: true });
    }, 50);
  }

  async function analyze() {
    if (!selected || loading) return;
    setError("");
    setLoading(true);
    try {
      revealResult(await verifyImage(selected.file));
    } catch (reason) {
      setResult(null);
      setError(reason instanceof ApiError ? reason.message : "La vérification a échoué.");
    } finally {
      setLoading(false);
    }
  }

  const report = result && result !== "demo" ? result : null;
  const primaryMatch = report?.matches[0];

  return <div className="page-content">
    <div className="page-eyebrow"><span className="eyebrow-line" /> VOIR AU-DELÀ DES PIXELS</div>
    <div className="intro-row"><div><h1>Chaque image a une histoire.<br /><span>Vérifiez la sienne.</span></h1><p className="page-description">Retrouvez sa source, explorez sa provenance et examinez<br className="desktop-break" /> les indices d’une création par intelligence artificielle.</p></div><div className="hero-seal" aria-hidden="true"><ScanLine size={44} strokeWidth={1} /><span>IMAGE • ORIGINE • CONFIANCE</span></div></div>
    <div className="verification-grid">
      <section className="panel upload-panel" aria-labelledby="upload-title"><div className="panel-header"><div><span className="step-label">01 / VOTRE IMAGE</span><h2 id="upload-title">Le premier pas : une image.</h2></div><span className="small-icon"><ScanLine size={19} /></span></div>
        <ImageDropzone value={selected} onChange={image => { setSelected(image); setResult(null); setError(""); }} />
        {selected && <button className="button button-primary full-width analyze-button" onClick={() => void analyze()} disabled={loading}>{loading ? <LoaderCircle className="spin" size={17} /> : <ScanLine size={17} />}{loading ? "Recherche en cours…" : "Vérifier cette image"}<ArrowRight size={16} /></button>}
        {error && <p className="error-message" role="alert">{error}</p>}
      </section>
      <aside className="analysis-panel"><div className="panel-header"><div><span className="step-label">02 / LES INDICES</span><h2>Une image, plusieurs regards.</h2></div></div>
        <div className="analysis-item"><span className="feature-icon teal"><Fingerprint size={21} /></span><div><h3>Une origine à retrouver</h3><p>Comparer l’image aux empreintes des médias partenaires, même après recompression ou recadrage.</p></div></div>
        <div className="analysis-item"><span className="feature-icon violet"><Sparkles size={20} /></span><div><h3>Les indices d’une création IA</h3><p>Estimer si l’image présente des caractéristiques de génération artificielle.</p></div></div>
        <div className="analysis-item"><span className="feature-icon sand"><FileCheck2 size={20} /></span><div><h3>Une provenance à examiner</h3><p>Lire les informations signées et retracer l’historique disponible.</p></div></div>
        <Link className="text-link" href="/comprendre">Comment lire ces indices <ArrowUpRight size={15} /></Link>
      </aside>
    </div>
    <section className="demo-strip"><div className="demo-strip-icon"><FlaskConical size={22} /></div><div><h3>Curieux de voir le résultat ?</h3><p>Explorez un rapport fictif pour découvrir le parcours de vérification.</p></div><button className="button button-secondary" onClick={() => revealResult("demo")}>Essayer un exemple <ArrowRight size={16} /></button></section>
    {result && <section className="panel results-panel" ref={resultRef} tabIndex={-1} aria-labelledby="results-title">
      <div className="panel-header"><div><span className="step-label">03 / LE RAPPORT</span><h2 id="results-title">{result === "demo" ? "Une origine retrouvée, dans cet exemple." : primaryMatch ? "Une image partenaire semble correspondre." : "Aucune origine partenaire retrouvée."}</h2></div><span className={`tag ${primaryMatch ? "green" : ""}`}>{result === "demo" ? "Exemple fictif" : primaryMatch ? matchLabels[primaryMatch.matched_by] : "Aucune correspondance"}</span></div>
      {result === "demo" ? <DemoReport /> : <RealReport report={result} />}
    </section>}
    <section className="how-section"><div className="section-heading"><h2>De l’image à ses origines.</h2><Link href="/comprendre">Comprendre la démarche <ArrowRight size={15} /></Link></div><div className="how-grid"><div><span className="how-number">01</span><h3>Déposez une image</h3><p>Une photo reçue, publiée ou partagée : commencez par le fichier.</p></div><ChevronRight className="step-arrow" size={18} /><div><span className="how-number">02</span><h3>Croisez les indices</h3><p>Origine, similarité et provenance apportent des éclairages complémentaires.</p></div><ChevronRight className="step-arrow" size={18} /><div><span className="how-number">03</span><h3>Gardez un regard critique</h3><p>Une image authentique peut aussi être partagée hors de son contexte.</p></div></div></section>
    <div className="trust-note"><ShieldCheck size={18} /><span>La transparence avant la certitude. Prisme vous aide à examiner les preuves disponibles.</span></div>
  </div>;
}

function PendingEvidence() {
  return <><div className="evidence-row"><Sparkles size={20} /><div><strong>Détection IA</strong><p>L’analyse externe n’est pas exécutée dans ce rapport fictif.</p></div><span className="tag">Non évaluée</span></div><div className="evidence-row"><FileCheck2 size={20} /><div><strong>Provenance signée</strong><p>La vérification C2PA n’est pas exécutée dans ce rapport fictif.</p></div><span className="tag">Non vérifiée</span></div></>;
}

function AiEvidence({ detection }: { detection: VerificationReport["ai_detection"] }) {
  if (detection.status !== "evaluated" || detection.ai_generated_score === null || detection.deepfake_score === null) {
    return <div className="evidence-row"><CircleHelp size={20} /><div><strong>Analyse IA</strong><p>Le service d’analyse n’a pas pu produire de résultat.</p></div><span className="tag">Indisponible</span></div>;
  }
  const generator = detection.likely_generator?.replaceAll("_", " ");
  return <><div className="evidence-row"><Sparkles size={20} /><div><strong>Image générée ou retouchée par IA</strong><p>{generator ? `Générateur possible : ${generator}. ` : ""}Signal calculé par analyse visuelle.</p></div><span className="tag green">{Math.round(detection.ai_generated_score * 100)} %</span></div><div className="evidence-row"><ScanLine size={20} /><div><strong>Deepfake facial</strong><p>Recherche de visages échangés ou modifiés par intelligence artificielle.</p></div><span className="tag">{Math.round(detection.deepfake_score * 100)} %</span></div></>;
}

function C2paEvidence({ provenance }: { provenance: VerificationReport["c2pa_provenance"] }) {
  const content = {
    valid: ["Content Credential C2PA valide", "La signature et les liaisons cryptographiques du manifeste sont valides.", "Valide"],
    valid_untrusted: ["Content Credential C2PA valide, certificat de test", "Le manifeste est intact, mais son certificat n’appartient pas à une liste de confiance de production.", "Test"],
    invalid: ["Content Credential C2PA invalide", "Le manifeste contient une erreur de validation ou une liaison cryptographique rompue.", "Invalide"],
    absent: ["Aucun manifeste C2PA", "Le fichier vérifié ne contient pas de Content Credential. Une recompression ou un réseau social peut retirer ces métadonnées.", "Absent"],
    unavailable: ["Analyse C2PA indisponible", "Le lecteur C2PA n’a pas pu analyser ce fichier.", "Indisponible"],
  }[provenance.status];
  return <div className="evidence-row"><FileCheck2 size={20} /><div><strong>{content[0]}</strong><p>{content[1]}{provenance.issuer && <> Émetteur : {provenance.issuer}.</>}</p></div><span className={`tag ${provenance.status === "valid" ? "green" : ""}`}>{content[2]}</span></div>;
}

function RegistryEvidence({ match }: { match: VerificationMatch }) {
  const proof = match.registry;
  const content = {
    verified: ["Preuve Base Sepolia vérifiée", "Les empreintes, CID, métadonnées et identité du média correspondent au registre.", "Vérifiée"],
    revoked: ["Preuve Base Sepolia révoquée", "L’enregistrement existe mais le média partenaire l’a explicitement révoqué.", "Révoquée"],
    mismatch: ["Divergence avec Base Sepolia", "Les données publiques du contrat ne correspondent pas entièrement à PostgreSQL.", "Divergence"],
    not_registered: ["Aucune preuve on-chain", "Cette correspondance visuelle ne possède pas d’enregistrement dans le contrat.", "Non enregistrée"],
    unavailable: ["Preuve blockchain indisponible", "La reconnaissance reste valable, mais le RPC Base Sepolia n’a pas pu être consulté.", "Indisponible"],
  }[proof.status];
  return <div className="evidence-row"><ShieldCheck size={20} /><div><strong>{content[0]}</strong><p>{content[1]}{proof.explorer_url && <> · <a href={proof.explorer_url} target="_blank" rel="noreferrer">voir la transaction</a></>}</p></div><span className={`tag ${proof.status === "verified" ? "green" : ""}`}>{content[2]}</span></div>;
}

function DemoReport() {
  return <><div className="notice"><Info size={18} /><p>Rapport entièrement fictif, indépendant de votre fichier. Aucune analyse IA, vérification C2PA ou transaction blockchain n’a été effectuée.</p></div><div className="report-layout"><div className="sample-visual"><div className="landscape-art" role="img" aria-label="Illustration abstraite de montagnes, exemple fictif"><span className="sun" /><span className="mountain mountain-back" /><span className="mountain mountain-front" /><span className="lake" /><span className="art-caption">PRISME / IMAGE D’EXEMPLE</span></div><div className="sample-caption"><strong>Les reliefs au petit matin</strong><span>Le Journal Horizon · média fictif</span></div></div><div className="report-evidence"><div className="evidence-row"><BadgeCheck size={20} /><div><strong>Correspondance illustrée</strong><p>Le scénario présente une image retrouvée dans le registre d’un média partenaire.</p></div><span className="tag green">Exemple</span></div><PendingEvidence /><div className="score-placeholder"><span>Score d’authenticité</span><strong>— <small>Disponible après intégration et évaluation</small></strong></div></div></div></>;
}

function RealReport({ report }: { report: VerificationReport }) {
  const match = report.matches[0];
  return <><div className="notice"><Info size={18} /><p>{report.limitation}</p></div><div className="report-layout"><div className="sample-visual"><div className="verification-summary-icon">{match ? <BadgeCheck size={52} /> : <SearchX size={52} />}</div><div className="sample-caption"><strong>{report.query.filename}</strong><span>{report.query.width} × {report.query.height} px · {report.match_count} correspondance{report.match_count > 1 ? "s" : ""}</span></div></div><div className="report-evidence">{match ? <><div className="evidence-row"><BadgeCheck size={20} /><div><strong>{match.image.title}</strong><p>{match.media.name} · {match.image.author}{match.image.source_url && <> · <a href={match.image.source_url} target="_blank" rel="noreferrer">publication source</a></>}</p></div><span className="tag green">{Math.round(match.confidence * 100)} %</span></div><RegistryEvidence match={match} /></> : <div className="evidence-row"><CircleHelp size={20} /><div><strong>Pas de correspondance détectée</strong><p>L’image ne correspond pas aux empreintes actuellement enregistrées par les médias partenaires.</p></div><span className="tag">Registre actuel</span></div>}<AiEvidence detection={report.ai_detection} /><C2paEvidence provenance={report.c2pa_provenance} /><div className="score-placeholder"><span>Score de correspondance visuelle</span><strong>{match ? `${Math.round(match.confidence * 100)} %` : "—"} <small>{match ? matchLabels[match.matched_by] : "Aucun score au-dessus du seuil"}</small></strong></div></div></div></>;
}
