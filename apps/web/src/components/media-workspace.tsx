"use client";

import { FormEvent, RefObject, useEffect, useRef, useState } from "react";
import {
  ArrowRight, Ban, Building2, Check, Database, Download, ExternalLink,
  FileImage, Info, LoaderCircle, LockKeyhole, LogOut, Plus, RotateCcw,
  Search, ShieldCheck, Trash2, Wallet, X,
} from "lucide-react";
import { ImageDropzone } from "@/components/image-dropzone";
import { formatSize, SelectedImage } from "@/lib/files";
import {
  ApiError, ApiImage, AuthSession, WalletActionResponse, clearSession,
  confirmImageRegistration, confirmImageRevocation, createImage, deleteImage,
  exportImage, getCurrentMedia, listImages, loginMedia, prepareImageRegistration,
  prepareImageRevocation, readSession, registerMedia, storeSession,
} from "@/lib/api";
import {
  BASE_SEPOLIA_CHAIN_ID, WalletError, connectWallet, currentWallet,
  getWalletProvider, sendWalletTransaction, waitForWalletReceipt,
} from "@/lib/wallet";

type AuthMode = "login" | "register";

const statusLabels: Record<ApiImage["status"], string> = {
  draft: "Brouillon",
  fingerprinted: "Empreintes calculées",
  ipfs_stored: "Stockée sur IPFS",
  blockchain_pending: "Transaction en attente",
  registration_failed: "Enregistrement à reprendre",
  registered: "Preuve on-chain vérifiable",
  revoked: "Preuve révoquée",
};

const retryableStatuses = new Set<ApiImage["status"]>([
  "ipfs_stored", "blockchain_pending", "registration_failed",
]);

export function MediaWorkspace() {
  const [auth, setAuth] = useState<AuthSession | null>(null);
  const [authMode, setAuthMode] = useState<AuthMode>("login");
  const [images, setImages] = useState<ApiImage[]>([]);
  const [selected, setSelected] = useState<SelectedImage | null>(null);
  const [query, setQuery] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [activeImage, setActiveImage] = useState<ApiImage | null>(null);
  const [deleteCandidate, setDeleteCandidate] = useState<string | null>(null);
  const [walletAddress, setWalletAddress] = useState<string | null>(null);
  const [walletChainId, setWalletChainId] = useState<string | null>(null);
  const [walletLoading, setWalletLoading] = useState(false);
  const form = useRef<HTMLFormElement>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const fileArea = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const saved = readSession();
    if (!saved) { setLoading(false); return; }
    Promise.all([getCurrentMedia(saved.accessToken), listImages(saved.accessToken)])
      .then(([media, page]) => {
        const restored = { ...saved, media };
        storeSession(restored);
        setAuth(restored);
        setImages(page.items);
      })
      .catch(() => { clearSession(); setError("Votre session a expiré. Reconnectez-vous."); })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { if (activeImage) dialog.current?.showModal(); }, [activeImage]);

  useEffect(() => {
    const provider = getWalletProvider();
    if (!provider) return;
    void currentWallet().then(wallet => {
      setWalletAddress(wallet.address);
      setWalletChainId(wallet.chainId);
    });
    const accountsChanged = (...args: unknown[]) => {
      const accounts = args[0];
      setWalletAddress(Array.isArray(accounts) && typeof accounts[0] === "string" ? accounts[0] : null);
    };
    const chainChanged = (...args: unknown[]) => {
      setWalletChainId(typeof args[0] === "string" ? args[0].toLowerCase() : null);
    };
    provider.on?.("accountsChanged", accountsChanged);
    provider.on?.("chainChanged", chainChanged);
    return () => {
      provider.removeListener?.("accountsChanged", accountsChanged);
      provider.removeListener?.("chainChanged", chainChanged);
    };
  }, []);

  const walletReady = Boolean(walletAddress && walletChainId === BASE_SEPOLIA_CHAIN_ID);

  function handleApiError(reason: unknown) {
    if (reason instanceof ApiError && reason.status === 401) {
      clearSession(); setAuth(null); setImages([]);
      setError("Votre session a expiré. Reconnectez-vous.");
    } else {
      setError(reason instanceof ApiError || reason instanceof WalletError || reason instanceof Error
        ? reason.message : "Une erreur inattendue est survenue.");
    }
  }

  async function requestWallet() {
    setError(""); setWalletLoading(true);
    try {
      const address = await connectWallet();
      const wallet = await currentWallet();
      setWalletAddress(address); setWalletChainId(wallet.chainId);
      setMessage("Portefeuille connecté à Base Sepolia.");
    } catch (reason) { handleApiError(reason); }
    finally { setWalletLoading(false); }
  }

  function replaceImage(updated: ApiImage) {
    setImages(current => current.map(item => item.id === updated.id ? updated : item));
    setActiveImage(current => current?.id === updated.id ? updated : current);
  }

  async function completeRegistration(action: WalletActionResponse): Promise<ApiImage> {
    if (!auth) return action.image;
    const txHash = action.transaction
      ? await sendWalletTransaction(action.transaction)
      : action.image.blockchain_tx_hash;
    if (!txHash) return action.image;
    replaceImage({ ...action.image, status: "blockchain_pending", blockchain_tx_hash: txHash });
    const firstCheck = await confirmImageRegistration(auth.accessToken, action.image.id, txHash);
    replaceImage(firstCheck);
    if (firstCheck.status === "registered" || firstCheck.status === "revoked") return firstCheck;
    await waitForWalletReceipt(txHash);
    return confirmImageRegistration(auth.accessToken, action.image.id, txHash);
  }

  async function completeRevocation(action: WalletActionResponse): Promise<ApiImage> {
    if (!auth) return action.image;
    const txHash = action.transaction
      ? await sendWalletTransaction(action.transaction)
      : action.image.revocation_tx_hash;
    if (!txHash) return action.image;
    const firstCheck = await confirmImageRevocation(auth.accessToken, action.image.id, txHash);
    replaceImage(firstCheck);
    if (firstCheck.status === "revoked") return firstCheck;
    await waitForWalletReceipt(txHash);
    return confirmImageRevocation(auth.accessToken, action.image.id, txHash);
  }

  async function authenticate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setMessage(""); setSubmitting(true);
    const data = new FormData(event.currentTarget);
    const email = String(data.get("email") ?? "").trim();
    const password = String(data.get("password") ?? "");
    try {
      const session = authMode === "register"
        ? await registerMedia(String(data.get("organizationName") ?? "").trim(), email, password)
        : await loginMedia(email, password);
      storeSession(session); setAuth(session);
      setImages((await listImages(session.accessToken)).items);
      setMessage(authMode === "register" ? "Compte média créé." : "Connexion réussie.");
    } catch (reason) { handleApiError(reason); }
    finally { setSubmitting(false); }
  }

  async function refreshImages(search = query) {
    if (!auth) return;
    try { setImages((await listImages(auth.accessToken, search)).items); }
    catch (reason) { handleApiError(reason); }
  }

  async function submitImage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setMessage(""); setError("");
    if (!auth) return;
    if (!selected) {
      setError("Ajoutez une image avant de publier sa preuve.");
      fileArea.current?.scrollIntoView({ behavior: "smooth" }); return;
    }
    if (!walletAddress || !walletReady) {
      setError("Connectez MetaMask à Base Sepolia avant de préparer la publication.");
      return;
    }
    setSubmitting(true);
    const data = new FormData(event.currentTarget);
    data.set("image", selected.file); data.set("wallet_address", walletAddress);
    try {
      const prepared = await createImage(auth.accessToken, data);
      setImages(current => [prepared.image, ...current]); form.current?.reset(); setSelected(null);
      setMessage("Preuves IPFS préparées. Confirmez maintenant la transaction dans MetaMask.");
      const confirmed = await completeRegistration(prepared);
      replaceImage(confirmed);
      setMessage(`« ${confirmed.title} » est enregistrée sur Base Sepolia par votre portefeuille.`);
    } catch (reason) { handleApiError(reason); }
    finally { setSubmitting(false); }
  }

  async function retryRegistration(image: ApiImage) {
    if (!auth) return;
    if (!walletReady) { setError("Connectez le portefeuille lié à cette preuve sur Base Sepolia."); return; }
    setError(""); setMessage(""); setSubmitting(true);
    try {
      const prepared = await prepareImageRegistration(auth.accessToken, image.id);
      const updated = await completeRegistration(prepared);
      replaceImage(updated);
      setMessage(updated.status === "registered"
        ? `« ${updated.title} » est maintenant confirmée sur Base Sepolia.`
        : "La transaction est toujours en attente ; la reprise reste idempotente.");
    } catch (reason) { handleApiError(reason); }
    finally { setSubmitting(false); }
  }

  async function remove(image: ApiImage) {
    if (!auth) return;
    if (image.status === "registered" && !walletReady) {
      setError("Connectez le portefeuille ayant publié cette preuve sur Base Sepolia."); return;
    }
    setError("");
    try {
      if (image.status === "registered") {
        const prepared = await prepareImageRevocation(auth.accessToken, image.id);
        const updated = await completeRevocation(prepared);
        replaceImage(updated); setDeleteCandidate(null); setActiveImage(null);
        setMessage("La révocation a été confirmée dans MetaMask et archivée par Prisme.");
      } else {
        await deleteImage(auth.accessToken, image.id);
        await refreshImages(); setDeleteCandidate(null); setActiveImage(null);
        setMessage("La publication incomplète a été supprimée et désépinglée.");
      }
    } catch (reason) { handleApiError(reason); }
  }

  function logout() {
    clearSession(); setAuth(null); setImages([]); setSelected(null);
    setQuery(""); setMessage(""); setError("");
  }

  return <div className="page-content">
    <div className="page-eyebrow"><span className="eyebrow-line" /> L’ORIGINE COMMENCE AVEC VOUS</div>
    <div className="intro-row"><div><h1>Espace média<span className="accent-dot">.</span></h1><p className="page-description">Documentez la provenance de vos photos,<br className="desktop-break" /> avec des preuves publiques et vérifiables.</p></div>{auth && <button className="button button-secondary" onClick={logout}><LogOut size={16} />Se déconnecter</button>}</div>
    <div className="notice media-notice"><Info size={18} /><p><strong>Signature personnelle.</strong> Prisme prépare C2PA et IPFS, puis MetaMask vous demande de confirmer chaque enregistrement ou révocation sur Base Sepolia. Aucune clé privée n’est confiée au serveur.</p></div>
    <section className="panel wallet-panel"><div className="wallet-copy"><span className="feature-icon teal"><Wallet size={22} /></span><div><strong>Portefeuille de publication</strong><p>{walletAddress ? `${walletAddress.slice(0, 8)}…${walletAddress.slice(-6)}` : "Connectez MetaMask pour publier."}</p></div></div><div className="row-actions"><span className={`tag ${walletReady ? "green" : ""}`}>{walletReady ? "Base Sepolia" : walletAddress ? "Mauvais réseau" : "Non connecté"}</span><button className="button button-secondary" type="button" onClick={() => void requestWallet()} disabled={walletLoading}>{walletLoading ? <LoaderCircle className="spin" size={16} /> : <Wallet size={16} />}{walletAddress ? "Changer ou reconnecter" : "Connecter MetaMask"}</button></div></section>
    {loading ? <div className="panel loading-panel"><LoaderCircle className="spin" size={25} />Restauration de la session…</div>
      : !auth ? <AuthPanel mode={authMode} setMode={setAuthMode} submit={authenticate} submitting={submitting} error={error} />
      : <>
        <div className="media-heading"><div className="media-avatar"><Building2 size={22} /></div><div><h2>{auth.media.name}</h2><span>{auth.media.email} · compte PostgreSQL</span></div><span className="tag green"><Database size={12} /> {images.length} image{images.length > 1 ? "s" : ""}</span></div>
        <div role="status" aria-live="polite">{message && <p className="success-message"><Check size={17} />{message}</p>}</div>
        {error && <p className="error-message" role="alert">{error}</p>}
        <div className="media-editor-grid">
          <section className="panel"><div className="panel-header"><div><span className="step-label">NOUVELLE PHOTO</span><h2>Publier une preuve</h2></div><Plus size={20} /></div>
            <form ref={form} onSubmit={submitImage} className="media-form">
              <div ref={fileArea}><ImageDropzone value={selected} onChange={setSelected} compact /></div>
              <div className="form-two-cols"><div><label htmlFor="title">Titre de la photo <span>*</span></label><input id="title" name="title" required maxLength={150} placeholder="Ex. Le marché au lever du jour" /></div><div><label htmlFor="author">Photographe <span>*</span></label><input id="author" name="author" required maxLength={100} placeholder="Nom de l’auteur" autoComplete="name" /></div></div>
              <div><label htmlFor="source_url">URL de publication <small>facultatif</small></label><input id="source_url" name="source_url" type="url" maxLength={500} placeholder="https://votre-media.fr/article" /></div>
              <div><label htmlFor="license">Droits d’utilisation <span>*</span></label><select name="license" id="license" required defaultValue="Tous droits réservés"><option>Tous droits réservés</option><option>CC BY 4.0</option><option>CC BY-SA 4.0</option><option>CC0</option></select></div>
              <div><label htmlFor="description">Contexte de la photo <small>facultatif</small></label><textarea id="description" name="description" rows={3} maxLength={1200} placeholder="Lieu, événement, date de prise de vue…" /></div>
              <label className="checkbox-label"><input name="rights" type="checkbox" required /><span>Je confirme disposer des droits nécessaires et certifie les informations de provenance fournies. <span>*</span></span></label>
              <div className="form-actions"><span>Champs obligatoires : *</span><button className="button button-primary" type="submit" disabled={submitting || !walletReady}>{submitting ? <LoaderCircle className="spin" size={16} /> : <Wallet size={16} />}Préparer et signer avec MetaMask</button></div>
            </form>
          </section>
          <aside className="media-help"><span className="feature-icon teal"><ShieldCheck size={23} /></span><h3>Votre portefeuille signe</h3><p>Le serveur calcule les empreintes, ajoute C2PA et publie sur IPFS. MetaMask affiche ensuite la transaction exacte à confirmer.</p><div className="help-divider" /><h4>Preuves conservées</h4><p>Adresse du signataire, manifeste C2PA, CID, empreintes, reçu et bloc du contrat.</p><h4>Attention</h4><p>Le registre est public : la première adresse qui inscrit un SHA-256 en devient le publicateur on-chain. Vérifiez toujours la transaction MetaMask.</p><span className="tag green">MetaMask · Base Sepolia</span></aside>
        </div>
        <ImageLibrary images={images} query={query} setQuery={setQuery} search={() => void refreshImages()} setActiveImage={setActiveImage} retry={retryRegistration} deleting={deleteCandidate} setDeleting={setDeleteCandidate} remove={remove} submitting={submitting} />
      </>}
    <ImageDialog dialog={dialog} image={activeImage} mediaName={auth?.media.name} close={() => setActiveImage(null)} retry={retryRegistration} submitting={submitting} />
  </div>;
}

function AuthPanel({ mode, setMode, submit, submitting, error }: { mode: AuthMode; setMode: (value: AuthMode) => void; submit: (event: FormEvent<HTMLFormElement>) => void; submitting: boolean; error: string }) {
  return <div className="login-grid"><section className="panel login-panel"><span className="feature-icon teal"><LockKeyhole size={25} /></span><h2>{mode === "login" ? "Accéder à votre rédaction" : "Créer un média partenaire"}</h2><p>Le compte protège la publication et isole les preuves de chaque média.</p><div className="auth-tabs"><button className={mode === "login" ? "active" : ""} onClick={() => setMode("login")}>Connexion</button><button className={mode === "register" ? "active" : ""} onClick={() => setMode("register")}>Créer un compte</button></div><form onSubmit={submit}>{mode === "register" && <><label htmlFor="organizationName">Nom du média</label><input id="organizationName" name="organizationName" required minLength={2} maxLength={150} autoComplete="organization" /></>}<label htmlFor="email">Adresse e-mail</label><input id="email" name="email" type="email" required maxLength={320} autoComplete="email" /><label htmlFor="password">Mot de passe</label><input id="password" name="password" type="password" required minLength={12} maxLength={128} autoComplete={mode === "login" ? "current-password" : "new-password"} />{error && <p className="error-message" role="alert">{error}</p>}<button className="button button-primary full-width" type="submit" disabled={submitting}>{submitting ? <LoaderCircle className="spin" size={17} /> : <LockKeyhole size={16} />}{mode === "login" ? "Se connecter" : "Créer et se connecter"}<ArrowRight size={17} /></button></form></section><div className="media-benefits"><span className="step-label">DES PREUVES PERSISTANTES</span><h2>La provenance commence<br />avec un compte identifié.</h2>{["Mot de passe haché avec Argon2.", "Accès protégé par un jeton de courte durée.", "Publications isolées entre les médias."].map(text => <div key={text}><Check size={18} /><span>{text}</span></div>)}</div></div>;
}

function ImageLibrary({ images, query, setQuery, search, setActiveImage, retry, deleting, setDeleting, remove, submitting }: { images: ApiImage[]; query: string; setQuery: (value: string) => void; search: () => void; setActiveImage: (image: ApiImage) => void; retry: (image: ApiImage) => Promise<void>; deleting: string | null; setDeleting: (id: string | null) => void; remove: (image: ApiImage) => Promise<void>; submitting: boolean }) {
  return <section className="panel library-panel"><div className="library-header"><div><span className="step-label">VOTRE BIBLIOTHÈQUE</span><h2>Les preuves publiées</h2></div><form className="search-field" onSubmit={event => { event.preventDefault(); search(); }}><Search size={16} /><input aria-label="Rechercher une image" value={query} onChange={event => setQuery(event.target.value)} placeholder="Rechercher une photo…" /></form></div>
    {images.length ? <div className="table-scroll"><table><thead><tr><th>Photo</th><th>Auteur</th><th>Statut</th><th><span className="sr-only">Actions</span></th></tr></thead><tbody>{images.map(image => <tr key={image.id}><td><button className="draft-title" onClick={() => setActiveImage(image)}><span className="draft-file-icon"><FileImage size={20} /></span><span><strong>{image.title}</strong><small>{image.original_filename} · {formatSize(image.size_bytes)}</small></span></button></td><td>{image.author}</td><td><span className={`tag ${image.status === "registered" ? "green" : ""}`}>{statusLabels[image.status]}</span></td><td><div className="row-actions">{retryableStatuses.has(image.status) && <button className="icon-button" aria-label={`Réessayer l’enregistrement de ${image.title}`} disabled={submitting} onClick={() => void retry(image)}><RotateCcw size={17} /></button>}<button className="icon-button" aria-label={`Exporter ${image.title}`} onClick={() => exportImage(image)}><Download size={17} /></button>{image.status !== "revoked" && <button className="icon-button danger" aria-label={`${image.status === "registered" ? "Révoquer" : "Supprimer"} ${image.title}`} onClick={() => setDeleting(image.id)}>{image.status === "registered" ? <Ban size={17} /> : <Trash2 size={17} />}</button>}</div>{deleting === image.id && <div className="delete-confirm"><span>{image.status === "registered" ? "Révoquer cette preuve ?" : "Supprimer cette publication ?"}</span><button onClick={() => void remove(image)}>{image.status === "registered" ? "Révoquer" : "Supprimer"}</button><button onClick={() => setDeleting(null)}>Annuler</button></div>}</td></tr>)}</tbody></table></div>
      : <div className="empty-library"><FileImage size={30} strokeWidth={1.3} /><h3>{query ? "Aucun résultat" : "Votre première preuve commence ici."}</h3><p>{query ? "Lancez une autre recherche." : "Les images publiées apparaîtront ici."}</p></div>}
  </section>;
}

function ImageDialog({ dialog, image, mediaName, close, retry, submitting }: { dialog: RefObject<HTMLDialogElement | null>; image: ApiImage | null; mediaName?: string; close: () => void; retry: (image: ApiImage) => Promise<void>; submitting: boolean }) {
  return <dialog ref={dialog} className="draft-dialog" aria-labelledby="image-detail-title" onCancel={close} onClose={close}>
    <div className="dialog-header"><span className="step-label">PREUVES DE PUBLICATION</span><button className="icon-button" aria-label="Fermer le détail" onClick={() => dialog.current?.close()}><X size={20} /></button></div>
    {image && <>
      <h2 id="image-detail-title">{image.title}</h2>
      <span className={`tag ${image.status === "registered" ? "green" : ""}`}>{statusLabels[image.status]}</span>
      <dl>
        <dt>Média</dt><dd>{mediaName}</dd>
        <dt>Photographe</dt><dd>{image.author}</dd>
        <dt>Fichier source</dt><dd>{image.original_filename} · {image.width} × {image.height} px</dd>
        <dt>SHA-256 source</dt><dd>{image.sha256}</dd>
        <dt>Provenance C2PA</dt><dd>{image.c2pa_status === "valid_untrusted" ? "Manifeste valide · certificat de test" : image.c2pa_status || "Non disponible"}</dd>
        <dt>Générateur C2PA</dt><dd>{image.c2pa_claim_generator || "Non renseigné"}</dd>
        <dt>Émetteur C2PA</dt><dd>{image.c2pa_issuer || "Non renseigné"}</dd>
        <dt>SHA-256 signé</dt><dd>{image.c2pa_asset_sha256 || "Non disponible"}</dd>
        <dt>CID image</dt><dd>{image.ipfs_url ? <a href={image.ipfs_url} target="_blank" rel="noreferrer">{image.ipfs_cid} <ExternalLink size={13} /></a> : image.ipfs_cid || "Non publié"}</dd>
        <dt>CID JSON</dt><dd>{image.metadata_url ? <a href={image.metadata_url} target="_blank" rel="noreferrer">{image.metadata_cid} <ExternalLink size={13} /></a> : image.metadata_cid || "Non publié"}</dd>
        <dt>Transaction</dt><dd>{image.blockchain_explorer_url ? <a href={image.blockchain_explorer_url} target="_blank" rel="noreferrer">{image.blockchain_tx_hash} <ExternalLink size={13} /></a> : image.blockchain_tx_hash || "Non envoyée"}</dd>
        <dt>Bloc</dt><dd>{image.blockchain_block_number ?? "Non confirmé"}</dd>
        <dt>Contrat</dt><dd>{image.blockchain_contract_address || "Non renseigné"}</dd>
        <dt>Signataire</dt><dd>{image.blockchain_publisher_address || "Non renseigné"}</dd>
        {image.revocation_tx_hash && <><dt>Révocation</dt><dd>{image.revocation_tx_hash}</dd></>}
      </dl>
      {image.registration_error && <p className="error-message">{image.registration_error}</p>}
      <p className="muted">Une signature C2PA intacte atteste une déclaration signée, pas la vérité de la scène. Le désépinglage ne garantit pas l’effacement des copies IPFS conservées ailleurs.</p>
      <div className="row-actions">{retryableStatuses.has(image.status) && <button className="button button-secondary" disabled={submitting} onClick={() => void retry(image)}><RotateCcw size={16} />Réessayer l’enregistrement</button>}<button className="button button-primary" onClick={() => exportImage(image)}><Download size={16} />Exporter les preuves</button></div>
    </>}
  </dialog>;
}
