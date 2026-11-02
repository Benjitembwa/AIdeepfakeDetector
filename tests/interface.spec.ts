import { expect, test, type Page } from "@playwright/test";

const png = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aX1sAAAAASUVORK5CYII=", "base64");
async function upload(page: Page) { await page.locator('input[type="file"]').setInputFiles({ name: "photo-test.png", mimeType: "image/png", buffer: png }); }

const media = { id: "11111111-1111-4111-8111-111111111111", name: "Le Journal Horizon", slug: "le-journal-horizon", email: "redaction@prisme.fr", is_active: true, created_at: "2026-10-31T10:00:00Z" };
const image = { id: "22222222-2222-4222-8222-222222222222", media_id: media.id, title: "Le marché au matin", author: "Camille Test", source_url: "https://example.org/reportage", license: "Tous droits réservés", description: "Une image de test pour le prototype.", original_filename: "photo-test.png", media_type: "image/png", size_bytes: png.length, width: 1, height: 1, status: "registered", sha256: "a".repeat(64), perceptual_hash: "0123456789abcdef", difference_hash: "0123456789abcdef", wavelet_hash: "0123456789abcdef", fingerprint_version: 1, orb_descriptor_count: 24, ipfs_cid: "bafy-image", ipfs_url: "https://demo.mypinata.cloud/ipfs/bafy-image", metadata_cid: "bafy-json", metadata_sha256: "b".repeat(64), metadata_url: "https://demo.mypinata.cloud/ipfs/bafy-json", blockchain_tx_hash: `0x${"c".repeat(64)}`, blockchain_chain_id: 84532, blockchain_contract_address: "0x12DD566159a151Ab14009BC5d7624519C60c3647", blockchain_publisher_address: "0x9f06FcF98fDB0B374E63FdE559590bF2CA472E81", blockchain_block_number: 52962708, blockchain_registered_at: "2026-10-31T10:06:00Z", blockchain_explorer_url: `https://sepolia.basescan.org/tx/0x${"c".repeat(64)}`, revocation_tx_hash: null, revoked_at: null, registration_error: null, c2pa_status: "valid_untrusted", c2pa_active_manifest: "urn:c2pa:test", c2pa_claim_generator: "Prisme", c2pa_issuer: "C2PA Test Signing Cert", c2pa_validation_codes: '["signingCredential.untrusted"]', c2pa_asset_sha256: "e".repeat(64), c2pa_asset_size_bytes: png.length + 1024, created_at: "2026-10-31T10:05:00Z", updated_at: "2026-10-31T10:05:00Z" };

async function mockMediaApi(page: Page) {
  let images: typeof image[] = [];
  await page.route("http://127.0.0.1:8000/**", async route => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.pathname === "/api/v1/auth/register" || url.pathname === "/api/v1/auth/token") return route.fulfill({ status: url.pathname.endsWith("register") ? 201 : 200, contentType: "application/json", body: JSON.stringify({ access_token: "test-token", token_type: "bearer", expires_in: 1800, media }) });
    if (url.pathname === "/api/v1/media/me") return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(media) });
    if (url.pathname === "/api/v1/images" && request.method() === "POST") { images = [image, ...images]; return route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify(image) }); }
    if (url.pathname === "/api/v1/images" && request.method() === "GET") {
      const search = (url.searchParams.get("search") ?? "").toLocaleLowerCase("fr");
      const filtered = search && !` ${image.title} ${image.author} ${image.original_filename}`.toLocaleLowerCase("fr").includes(search) ? [] : images;
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ items: filtered, total: filtered.length, limit: 25, offset: 0 }) });
    }
    if (url.pathname.startsWith("/api/v1/images/") && request.method() === "DELETE") { images = images.map(item => url.pathname.endsWith(item.id) ? { ...item, status: "revoked", revocation_tx_hash: `0x${"d".repeat(64)}`, revoked_at: "2026-10-31T10:10:00Z" } : item); return route.fulfill({ status: 204, body: "" }); }
    return route.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ detail: "Not found" }) });
  });
}

test("le visiteur voit un exemple explicite puis un vrai rapport de reconnaissance", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
  await page.route("http://127.0.0.1:8000/api/v1/verify", route => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      query: { filename: "photo-test.png", size_bytes: png.length, width: 1, height: 1, sha256: "a".repeat(64) },
      match_count: 1,
      matches: [{ matched_by: "perceptual", confidence: 0.94, perceptual_distance: 2, difference_distance: 3, wavelet_distance: 2, good_matches: 14, inliers: 10, media: { id: media.id, name: media.name, slug: media.slug }, image: { id: image.id, title: image.title, author: image.author, source_url: image.source_url, license: image.license, original_filename: image.original_filename, width: image.width, height: image.height, created_at: image.created_at }, registry: { status: "verified", chain_id: 84532, contract_address: image.blockchain_contract_address, transaction_hash: image.blockchain_tx_hash, block_number: image.blockchain_block_number, publisher_address: image.blockchain_publisher_address, image_cid: image.ipfs_cid, metadata_cid: image.metadata_cid, image_url: image.ipfs_url, metadata_url: image.metadata_url, explorer_url: image.blockchain_explorer_url, registered_at: image.blockchain_registered_at } }],
      ai_detection: { status: "evaluated", provider: "sightengine", ai_generated_score: 0.87, deepfake_score: 0.08, likely_generator: "midjourney", likely_generator_score: 0.72, request_id: "req_test", operations: 6 },
      c2pa_provenance: { status: "valid_untrusted", active_manifest: "urn:c2pa:test", claim_generator: "Prisme", issuer: "C2PA Test Signing Cert", validation_codes: ["signingCredential.untrusted"] },
      limitation: "Une correspondance visuelle ne prouve pas le contexte de la scène.",
    }),
  }));
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Chaque image a une histoire");
  await page.screenshot({ path: "test-results/accueil-desktop.png", fullPage: true, caret: "initial" });
  await page.getByRole("button", { name: "Essayer un exemple" }).click();
  await expect(page.getByText("Exemple fictif", { exact: true })).toBeVisible();
  await expect(page.getByText("Rapport entièrement fictif", { exact: false })).toBeVisible();
  await upload(page);
  await expect(page.getByAltText("Aperçu de l’image sélectionnée")).toBeVisible();
  await expect(page.getByText("Exemple fictif", { exact: true })).toHaveCount(0);
  await page.getByRole("button", { name: "Vérifier cette image", exact: true }).click();
  await expect(page.getByText("Une image partenaire semble correspondre.", { exact: true })).toBeVisible();
  await expect(page.getByText("Similarité perceptuelle", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("94 %", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("Image générée ou retouchée par IA", { exact: true })).toBeVisible();
  await expect(page.getByText("Preuve Base Sepolia vérifiée", { exact: true })).toBeVisible();
  await expect(page.getByText("Content Credential C2PA valide, certificat de test", { exact: true })).toBeVisible();
  await expect(page.getByText("87 %", { exact: true })).toBeVisible();
  await expect(page.getByText("8 %", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Retirer l’image" }).click();
  await expect(page.getByRole("button", { name: "Choisir une image" })).toBeVisible();
  expect(errors).toEqual([]);
});

test("les fichiers incompatibles, trop lourds et illisibles sont refusés", async ({ page }) => {
  await page.goto("/");
  const input = page.locator('input[type="file"]');
  await input.setInputFiles({ name: "texte.txt", mimeType: "text/plain", buffer: Buffer.from("hello") });
  await expect(page.getByRole("main").getByRole("alert")).toContainText("Format non accepté");
  await input.setInputFiles({ name: "trop-lourd.png", mimeType: "image/png", buffer: Buffer.alloc(10 * 1024 * 1024 + 1) });
  await expect(page.getByRole("main").getByRole("alert")).toContainText("dépasse 10 Mo");
  await input.setInputFiles({ name: "illisible.png", mimeType: "image/png", buffer: Buffer.from("not an image") });
  await expect(page.getByRole("main").getByRole("alert")).toContainText("Impossible de lire cette image");
  await upload(page);
  await expect(page.getByRole("main").getByRole("alert")).toHaveCount(0);
});

test("un média publie, retrouve, exporte et révoque une preuve", async ({ page }) => {
  await mockMediaApi(page);
  await page.goto("/medias");
  await page.getByRole("button", { name: "Créer un compte" }).click();
  await page.getByLabel("Nom du média").fill("Le Journal Horizon");
  await page.getByLabel("Adresse e-mail").fill("redaction@prisme.fr");
  await page.getByLabel("Mot de passe").fill("mot-de-passe-test-123");
  await page.getByRole("button", { name: "Créer et se connecter" }).click();
  await expect(page.getByText("Compte média créé", { exact: false })).toBeVisible();
  await page.screenshot({ path: "test-results/espace-media-desktop.png", fullPage: true, caret: "initial" });
  await page.getByLabel("Titre de la photo").fill("Le marché au matin");
  await page.getByLabel("Photographe", { exact: false }).fill("Camille Test");
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Enregistrer sur IPFS et Base Sepolia" }).click();
  await expect(page.getByRole("main").getByRole("alert")).toContainText("Ajoutez une image");
  await upload(page);
  await page.getByLabel("URL de publication").fill("https://example.org/reportage");
  await page.getByLabel("Contexte de la photo").fill("Une image de test pour le prototype.");
  await page.getByRole("button", { name: "Enregistrer sur IPFS et Base Sepolia" }).click();
  await expect(page.getByRole("status")).toContainText("enregistrée sur Base Sepolia");
  await expect(page.getByRole("row", { name: /Le marché au matin/ })).toBeVisible();
  await page.reload();
  await expect(page.getByText("Le Journal Horizon", { exact: true })).toBeVisible();
  await page.getByRole("textbox", { name: "Rechercher une image" }).fill("inexistant");
  await page.getByRole("textbox", { name: "Rechercher une image" }).press("Enter");
  await expect(page.getByText("Aucun résultat", { exact: true })).toBeVisible();
  await page.getByRole("textbox", { name: "Rechercher une image" }).fill("marché");
  await page.getByRole("textbox", { name: "Rechercher une image" }).press("Enter");
  await page.getByRole("button", { name: /Le marché au matin photo-test/ }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByRole("dialog")).toContainText("Camille Test");
  await expect(page.getByRole("dialog")).toContainText("Manifeste valide · certificat de test");
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Exporter les preuves" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/^prisme-preuve-.*\.json$/);
  await page.getByRole("button", { name: "Fermer le détail" }).click();
  await page.getByRole("button", { name: "Révoquer Le marché au matin", exact: true }).click();
  await page.getByRole("button", { name: "Annuler", exact: true }).click();
  await expect(page.getByRole("row", { name: /Le marché au matin/ })).toBeVisible();
  await page.getByRole("button", { name: "Révoquer Le marché au matin", exact: true }).click();
  await page.getByRole("button", { name: "Révoquer", exact: true }).click();
  await expect(page.getByRole("row", { name: /Le marché au matin/ })).toContainText("Preuve révoquée");
});

test("les pages sont navigables au clavier et sans débordement sur téléphone", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.screenshot({ path: "test-results/accueil-mobile.png", fullPage: true, caret: "initial" });
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Aller au contenu" })).toBeFocused();
  await page.keyboard.press("Enter");
  for (const path of ["/", "/medias", "/comprendre"]) {
    await page.goto(path);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  }
  await page.getByText("Que signifient les pourcentages affichés ?", { exact: true }).click();
  await expect(page.getByText("Aucun de ces nombres n’est une preuve de vérité", { exact: false })).toBeVisible();
});

test("une session refusée par l’API est supprimée du navigateur", async ({ page }) => {
  await page.addInitScript(({ account }) => sessionStorage.setItem("prisme:auth:v1", JSON.stringify({ accessToken: "expired-token", expiresAt: Date.now() + 60_000, media: account })), { account: media });
  await page.route("http://127.0.0.1:8000/**", route => route.fulfill({ status: 401, contentType: "application/json", body: JSON.stringify({ detail: "Jeton invalide" }) }));
  await page.goto("/medias");
  await expect(page.getByRole("main").getByRole("alert")).toContainText("session a expiré");
  await expect(page.getByRole("button", { name: "Se connecter" })).toBeVisible();
  expect(await page.evaluate(() => sessionStorage.getItem("prisme:auth:v1"))).toBeNull();
});
