const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");
const AUTH_KEY = "prisme:auth:v1";

export type MediaAccount = {
  id: string;
  name: string;
  slug: string;
  email: string;
  is_active: boolean;
  created_at: string;
};

export type AuthSession = {
  accessToken: string;
  expiresAt: number;
  media: MediaAccount;
};

export type ApiImage = {
  id: string;
  media_id: string;
  title: string;
  author: string;
  source_url: string | null;
  license: string;
  description: string | null;
  original_filename: string;
  media_type: string;
  size_bytes: number;
  width: number;
  height: number;
  status: "draft" | "fingerprinted" | "ipfs_stored" | "blockchain_pending" | "registration_failed" | "registered" | "revoked";
  sha256: string | null;
  perceptual_hash: string | null;
  difference_hash: string | null;
  wavelet_hash: string | null;
  fingerprint_version: number | null;
  orb_descriptor_count: number | null;
  ipfs_cid: string | null;
  ipfs_url: string | null;
  metadata_cid: string | null;
  metadata_sha256: string | null;
  metadata_url: string | null;
  blockchain_tx_hash: string | null;
  blockchain_chain_id: number | null;
  blockchain_contract_address: string | null;
  blockchain_publisher_address: string | null;
  blockchain_block_number: number | null;
  blockchain_registered_at: string | null;
  blockchain_explorer_url: string | null;
  revocation_tx_hash: string | null;
  revoked_at: string | null;
  registration_error: string | null;
  c2pa_status: string | null;
  c2pa_active_manifest: string | null;
  c2pa_claim_generator: string | null;
  c2pa_issuer: string | null;
  c2pa_validation_codes: string | null;
  c2pa_asset_sha256: string | null;
  c2pa_asset_size_bytes: number | null;
  created_at: string;
  updated_at: string;
};

type TokenResponse = {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  media: MediaAccount;
};

type ImagePage = { items: ApiImage[]; total: number; limit: number; offset: number };

export type VerificationMatch = {
  matched_by: "exact" | "perceptual" | "local_features";
  confidence: number;
  perceptual_distance: number | null;
  difference_distance: number | null;
  wavelet_distance: number | null;
  good_matches: number;
  inliers: number;
  media: { id: string; name: string; slug: string };
  image: {
    id: string;
    title: string;
    author: string;
    source_url: string | null;
    license: string;
    original_filename: string;
    width: number;
    height: number;
    created_at: string;
  };
  registry: {
    status: "verified" | "revoked" | "mismatch" | "not_registered" | "unavailable";
    chain_id: number;
    contract_address: string;
    transaction_hash: string | null;
    block_number: number | null;
    publisher_address: string | null;
    image_cid: string | null;
    metadata_cid: string | null;
    image_url: string | null;
    metadata_url: string | null;
    explorer_url: string | null;
    registered_at: string | null;
  };
};

export type VerificationReport = {
  query: { filename: string; size_bytes: number; width: number; height: number; sha256: string };
  match_count: number;
  matches: VerificationMatch[];
  ai_detection: {
    status: "evaluated" | "unavailable";
    provider: "sightengine";
    ai_generated_score: number | null;
    deepfake_score: number | null;
    likely_generator: string | null;
    likely_generator_score: number | null;
    request_id: string | null;
    operations: number | null;
  };
  c2pa_provenance: {
    status: "valid" | "valid_untrusted" | "invalid" | "absent" | "unavailable";
    active_manifest: string | null;
    claim_generator: string | null;
    issuer: string | null;
    validation_codes: string[];
  };
  limitation: string;
};

export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message); }
}

async function request<T>(path: string, init: RequestInit = {}, token?: string): Promise<T> {
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  let response: Response;
  try { response = await fetch(`${API_URL}${path}`, { ...init, headers }); }
  catch { throw new ApiError("L’API Prisme est inaccessible. Vérifiez qu’elle fonctionne sur le port 8000.", 0); }
  if (!response.ok) {
    let message = `La requête a échoué (${response.status}).`;
    try {
      const payload = await response.json() as { detail?: string | Array<{ msg?: string }> };
      if (typeof payload.detail === "string") message = payload.detail;
      else if (Array.isArray(payload.detail)) message = payload.detail.map(item => item.msg).filter(Boolean).join(" ") || message;
    } catch { /* The fallback message is enough. */ }
    throw new ApiError(message, response.status);
  }
  if (response.status === 204) return undefined as T;
  const body = await response.text();
  if (!body) return undefined as T;
  return JSON.parse(body) as T;
}

function toSession(payload: TokenResponse): AuthSession {
  return { accessToken: payload.access_token, expiresAt: Date.now() + payload.expires_in * 1000, media: payload.media };
}

export async function registerMedia(organizationName: string, email: string, password: string) {
  return toSession(await request<TokenResponse>("/api/v1/auth/register", { method: "POST", body: JSON.stringify({ organization_name: organizationName, email, password }) }));
}

export async function loginMedia(email: string, password: string) {
  const form = new URLSearchParams({ username: email, password });
  return toSession(await request<TokenResponse>("/api/v1/auth/token", { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body: form }));
}

export function storeSession(session: AuthSession) { sessionStorage.setItem(AUTH_KEY, JSON.stringify(session)); }
export function clearSession() { sessionStorage.removeItem(AUTH_KEY); }
export function readSession(): AuthSession | null {
  try {
    const session = JSON.parse(sessionStorage.getItem(AUTH_KEY) ?? "null") as AuthSession | null;
    if (!session || typeof session.accessToken !== "string" || typeof session.expiresAt !== "number" || !session.media?.id || session.expiresAt <= Date.now()) { clearSession(); return null; }
    return session;
  } catch { clearSession(); return null; }
}

export function getCurrentMedia(token: string) { return request<MediaAccount>("/api/v1/media/me", {}, token); }
export function listImages(token: string, search = "") {
  const query = search.trim() ? `?search=${encodeURIComponent(search.trim())}` : "";
  return request<ImagePage>(`/api/v1/images${query}`, {}, token);
}
export function createImage(token: string, form: FormData) { return request<ApiImage>("/api/v1/images", { method: "POST", body: form }, token); }
export function retryImageRegistration(token: string, id: string) { return request<ApiImage>(`/api/v1/images/${encodeURIComponent(id)}/retry-registration`, { method: "POST" }, token); }
export function deleteImage(token: string, id: string) { return request<void>(`/api/v1/images/${encodeURIComponent(id)}`, { method: "DELETE" }, token); }
export function verifyImage(file: File) {
  const form = new FormData();
  form.set("image", file);
  return request<VerificationReport>("/api/v1/verify", { method: "POST", body: form });
}

export function exportImage(image: ApiImage) {
  const url = URL.createObjectURL(new Blob([JSON.stringify({
    ...image,
    c2pa_validation_codes: image.c2pa_validation_codes ? JSON.parse(image.c2pa_validation_codes) : [],
    notice: "Preuves C2PA, IPFS et Base Sepolia. Une signature C2PA valide atteste l’intégrité d’une déclaration, pas la vérité de la scène. Le désépinglage Pinata ne supprime pas les copies éventuellement conservées par d’autres nœuds IPFS.",
  }, null, 2)], { type: "application/json" }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `prisme-preuve-${image.id}.json`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
