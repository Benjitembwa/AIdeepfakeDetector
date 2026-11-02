# Prisme — Authenticité et provenance des images

Prototype académique de vérification de provenance et de détection d'images générées par IA.

## État actuel : étapes 1 à 9

- **Visiteur (`/`)** : envoi d'une image et recherche publique d'une origine partenaire exacte ou visuellement proche.
- **Média (`/medias`)** : publication automatique sur IPFS et Base Sepolia, reprise idempotente et révocation.
- **API FastAPI** : authentification JWT, validation des images et route publique `POST /api/v1/verify`.
- **Reconnaissance** : SHA-256, pHash, dHash, wHash et caractéristiques ORB validées géométriquement par RANSAC.
- **Détection IA** : analyse Sightengine des indices de génération ou retouche par IA et des manipulations faciales de type deepfake.
- **PostgreSQL Neon** : comptes, métadonnées et empreintes persistants, gérés par migrations Alembic.
- **IPFS public** : image et JSON canonique téléversés via Pinata avec CIDv1.
- **Registre** : contrat `PrismeImageRegistry` déployé sur Base Sepolia (`84532`) et appelé par FastAPI.
- **C2PA** : manifeste signé lors de la publication et contrôlé lors de la vérification publique.
- **Rapport** : origine visuelle, preuve on-chain, C2PA et probabilités IA présentés séparément pour éviter un score global trompeur.
- **Documentation API** : Swagger sur `http://127.0.0.1:8000/docs`.

Les images partenaires signées C2PA sont publiques sur IPFS. PostgreSQL conserve les CID, les identifiants Pinata nécessaires au désépinglage, le manifeste C2PA et le reçu blockchain. Le rapport distingue la correspondance visuelle, la preuve on-chain, la provenance signée et les probabilités IA/deepfake. Un désépinglage ne garantit pas la disparition des copies IPFS conservées par d'autres nœuds.

## Lancer le projet

Prérequis installés : Node.js 22+, npm et Python 3.12.

Dans un premier terminal :

```powershell
npm.cmd run api:dev
```

Dans un second terminal :

```powershell
npm.cmd run dev
```

Ouvrir `http://127.0.0.1:3000`. L'API écoute sur `http://127.0.0.1:8000`.

Dans VS Code, **Terminal → Exécuter la tâche → Prisme : lancer le projet** démarre les deux services.

## Installer ou réinstaller

```powershell
npm.cmd ci
py -3.12 -m venv services/api/.venv
services\api\.venv\Scripts\python.exe -m pip install -r services/api/requirements-dev.txt
npm.cmd run api:migrate
```

La connexion PostgreSQL, le JWT Pinata et la clé privée Base Sepolia se trouvent dans `services/api/.env`, exclu de Git. Le fichier `services/api/.env.example` contient uniquement un modèle sans secret. L'API doit être lancée avec un seul worker afin de sérialiser les nonces du compte signataire.

## Vérifier le projet

```powershell
npm.cmd run typecheck
npm.cmd run build
npm.cmd run api:test
npm.cmd run test:e2e
```

Les tests API utilisent SQLite et des doubles Pinata/Base Sepolia. Ils couvrent publication, reprise, doublons, révocation, C2PA et preuve publique, ainsi que copie exacte, recompression et recadrage. Les tests Playwright simulent l'API pour vérifier l'interface indépendamment du réseau.

## Structure

```text
apps/web/                 Site Next.js, React, TypeScript et Tailwind CSS
services/api/app/         API FastAPI, sécurité, routes et modèles SQLAlchemy
services/api/migrations/  Historique Alembic du schéma PostgreSQL
services/api/tests/       Tests de l'API
contracts/                Contrat Solidity et procédure de déploiement 100 % Remix
docs/                     Architecture et scénario de démonstration
tests/                    Tests navigateur Playwright
```

## Secrets

Ne jamais publier de mot de passe PostgreSQL, JWT Pinata, secret Sightengine, phrase de récupération ou clé privée. Les variables `NEXT_PUBLIC_*` sont visibles dans le navigateur et ne doivent contenir aucun secret. Les fichiers `.env` sont exclus de Git.

Le jeton d'accès du média reste dans `sessionStorage` et expire après 30 minutes. Pour un futur service public, il faudra ajouter une politique d'approbation des médias, une limitation des tentatives de connexion et une stratégie de renouvellement de session.

## Suite du projet

4. ~~SHA-256, hachage perceptuel et recherche de caractéristiques locales.~~ Terminé.
5. ~~Intégration de Sightengine pour l'analyse IA et deepfake.~~ Terminée.
6. ~~Contrat Solidity, Base Sepolia et IPFS public.~~ Implémentée.
7. ~~Provenance C2PA et certificat de test.~~ Implémentée ; un certificat de confiance sera requis en production.
8. ~~Rapport fondé sur les analyses réelles.~~ Implémenté sous forme d’indices séparés et documentés.
9. ~~Validation automatisée de l'ensemble.~~ Implémentée ; le test on-chain réel requiert la clé du déployeur dans `.env`.
10. Déploiements : site sur Vercel, API sur Hugging Face Spaces, registre sur Base Sepolia et fichiers IPFS via Pinata.

Voir [l'architecture](docs/architecture.md), [le scénario de démonstration](docs/demo.md), [la validation réelle des étapes 6 et 7](docs/validation-etape-6.md) et [la documentation de l'API](services/api/README.md).
