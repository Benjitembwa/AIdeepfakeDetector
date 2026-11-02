export const MAX_FILE_SIZE = 10 * 1024 * 1024;
export const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp"];

export function validateImage(file: File): string | null {
  if (!ALLOWED_TYPES.includes(file.type)) return "Format non accepté. Choisissez une image JPG, PNG ou WebP.";
  if (file.size === 0) return "Ce fichier est vide. Choisissez une autre image.";
  if (file.size > MAX_FILE_SIZE) return "Cette image dépasse 10 Mo. Choisissez un fichier plus léger.";
  return null;
}

export function formatSize(bytes: number) {
  return bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} Ko` : `${(bytes / 1024 / 1024).toFixed(1)} Mo`;
}

export type SelectedImage = { file: File; url: string; width: number; height: number };
