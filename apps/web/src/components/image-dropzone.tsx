"use client";

import { useEffect, useId, useRef, useState } from "react";
import { Check, ImagePlus, Upload, X } from "lucide-react";
import { formatSize, SelectedImage, validateImage } from "@/lib/files";

export function ImageDropzone({ value, onChange, compact = false }: { value: SelectedImage | null; onChange: (image: SelectedImage | null) => void; compact?: boolean }) {
  const input = useRef<HTMLInputElement>(null);
  const currentUrl = useRef<string | null>(null);
  const request = useRef(0);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState("");
  const id = useId();

  useEffect(() => () => { request.current++; if (currentUrl.current) URL.revokeObjectURL(currentUrl.current); }, []);
  useEffect(() => { if (!value && currentUrl.current) { URL.revokeObjectURL(currentUrl.current); currentUrl.current = null; } }, [value]);

  async function select(file?: File) {
    if (!file) return;
    const token = ++request.current;
    const issue = validateImage(file);
    if (issue) { setError(issue); return; }
    const url = URL.createObjectURL(file);
    const picture = new Image();
    picture.src = url;
    try {
      await picture.decode();
      if (token !== request.current) { URL.revokeObjectURL(url); return; }
      if (currentUrl.current) URL.revokeObjectURL(currentUrl.current);
      currentUrl.current = url;
      setError("");
      onChange({ file, url, width: picture.naturalWidth, height: picture.naturalHeight });
    } catch { URL.revokeObjectURL(url); if (token === request.current) setError("Impossible de lire cette image. Le fichier est peut-être endommagé."); }
  }

  return <div className={`upload-wrapper ${compact ? "compact" : ""}`}>
    <input ref={input} id={id} type="file" accept="image/jpeg,image/png,image/webp" hidden onChange={e => { void select(e.target.files?.[0]); e.target.value = ""; }} aria-label="Fichier image" />
    {value ? <div className="selected-image"><div className="preview-frame"><img src={value.url} alt="Aperçu de l’image sélectionnée" /></div><div className="file-meta"><span className="file-check"><Check size={17} /></span><div><strong>{value.file.name}</strong><span>{formatSize(value.file.size)} · {value.width} × {value.height} px</span></div><button type="button" className="icon-button" aria-label="Retirer l’image" onClick={() => { request.current++; onChange(null); setError(""); }}><X size={18} /></button></div></div> : <div className={`dropzone ${dragging ? "dragging" : ""}`} onDragOver={e => { e.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={e => { e.preventDefault(); setDragging(false); if (e.dataTransfer.files.length > 1) { setError("Déposez une seule image à la fois."); return; } void select(e.dataTransfer.files[0]); }}>
      <div className="upload-symbol"><ImagePlus size={29} strokeWidth={1.5} /><span className="upload-plus">+</span></div>
      <h3>Glissez votre image ici</h3><p>ou sélectionnez un fichier sur votre appareil</p>
      <button type="button" className="button button-primary" onClick={() => input.current?.click()}><Upload size={16} />Choisir une image</button>
      <span className="file-formats">JPG, PNG ou WebP <span>·</span> 10 Mo maximum</span>
    </div>}
    {error && <p className="error-message" role="alert">{error}</p>}
  </div>;
}
