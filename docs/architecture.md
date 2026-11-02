# Architecture et périmètre

## Composants

| Composant | Technologie | État |
| --- | --- | --- |
| Interface | Next.js, React, TypeScript, Tailwind CSS | Implémentée |
| API et comptes | Python 3.12, FastAPI, JWT, Argon2 | Implémentés |
| Base de données | PostgreSQL Neon, SQLAlchemy, Alembic, psycopg 3 | Connectée |
| Analyse IA | Sightengine (`genai`, `deepfake`) | Intégrée à la vérification publique |
| Images similaires | Pillow, imagehash, OpenCV ORB et RANSAC | Implémentées |
| Registre | Solidity, Remix IDE, web3.py, Base Sepolia | Contrat déployé et intégré à FastAPI |
| Fichiers | IPFS public via Pinata | Intégré |
| Provenance | c2pa-python 0.38 | Intégrée avec certificat de test |

## Flux actuel

```text
Navigateur
   │  compte/JWT (média) ou vérification publique, formulaire multipart
   ▼
FastAPI :8000
   ├─ validation, SHA-256, pHash/dHash/wHash, ORB + RANSAC
   ├─ C2PA : signature à la publication et lecture à la vérification
   ├─ Pinata/IPFS : image signée et JSON canonique publics
   ├─ Base Sepolia : registre de preuves et révocations
   ├─ PostgreSQL Neon : comptes, preuves, reçus et états de reprise
   └─ Sightengine : probabilités genai et deepfake
```

Le navigateur conserve le jeton dans `sessionStorage`. FastAPI vérifie le jeton et limite chaque requête média à son propriétaire. PostgreSQL conserve les comptes, métadonnées et empreintes. Lors d'une vérification publique, FastAPI soumet aussi l'image à Sightengine avec les modèles `genai` et `deepfake`, puis normalise les probabilités renvoyées dans son propre contrat d'API.

La vérification publique compare d'abord SHA-256, puis trois hachages perceptuels. ORB et une homographie RANSAC complètent la recherche pour les recadrages. Le prototype parcourt au maximum 1 000 candidats récents ; un index spécialisé sera nécessaire à grande échelle.

## Schéma de données

### `media_organizations`

Identifiant UUID, nom et slug uniques, adresse e-mail unique, mot de passe haché, statut actif et dates de création/modification.

### `image_records`

Identifiant UUID, média propriétaire, informations éditoriales, dimensions et statut. Les empreintes SHA-256, pHash, dHash, wHash et ORB sont persistées avec les CID/identifiants Pinata, le SHA-256 du JSON, le Chain ID, le contrat, le signataire, le hash de transaction, le bloc et les informations de révocation.

Les migrations `20261031_01`, `20261031_02`, `20261031_03` et `20261101_04` ajoutent successivement le modèle initial, la reconnaissance, les preuves IPFS/blockchain et la provenance C2PA.

## Frontières de confiance

- Le mot de passe brut n'est jamais stocké ; Argon2 produit le hachage.
- Le navigateur ne reçoit jamais la connexion PostgreSQL ni la clé de signature JWT.
- Les identifiants Sightengine restent uniquement dans les variables d'environnement de FastAPI.
- Le JWT Pinata et la clé privée Base Sepolia restent uniquement dans FastAPI.
- L'API vérifie Chain ID, bytecode, propriétaire et autorisation avant toute publication.
- Un verrou applicatif sérialise les nonces ; le prototype fonctionne avec un seul worker.
- L'API valide de nouveau type, taille, décodage et dimensions, même si le site les contrôle déjà.
- Un média ne peut pas lire, reprendre ou révoquer la preuve d'un autre média.
- L'inscription est ouverte pour ce prototype. Une validation administrative des médias sera nécessaire avant une utilisation publique.
- Le jeton d'accès expire après 30 minutes et n'est pas placé dans `localStorage`.
- La blockchain enregistrera une déclaration et son auteur autorisé, pas la vérité d'une scène.
- Une signature C2PA valide et la confiance accordée au signataire restent deux questions distinctes.

## API

| Méthode et route | Authentification | Rôle |
| --- | --- | --- |
| `GET /health` | Non | Santé du processus |
| `GET /health/ready` | Non | Connexion PostgreSQL |
| `POST /api/v1/auth/register` | Non | Créer un média de prototype |
| `POST /api/v1/auth/token` | Non | Obtenir un jeton |
| `GET /api/v1/media/me` | JWT | Lire le compte courant |
| `GET /api/v1/images` | JWT | Rechercher ses publications |
| `POST /api/v1/images` | JWT | Publier sur IPFS et Base Sepolia |
| `POST /api/v1/verify` | Non | Rechercher une origine exacte ou visuellement proche |
| `GET /api/v1/images/{id}` | JWT | Consulter ses preuves |
| `POST /api/v1/images/{id}/retry-registration` | JWT | Reprendre une transaction idempotemment |
| `DELETE /api/v1/images/{id}` | JWT | Révoquer puis désépingler |

## Configuration

- `services/api/.env` contient les valeurs locales et n'est pas suivi par Git.
- `services/api/.env.example` décrit les variables sans secret.
- `apps/web/.env.example` indique l'adresse publique de l'API.
- Alembic est la seule source de création et d'évolution du schéma.

## Interprétation du rapport

Le résultat Sightengine, la correspondance visuelle, la preuve blockchain et la provenance C2PA sont des indices distincts. Prisme ne les fusionne pas en un score universel d’« authenticité » : leurs significations et limites sont différentes. Le certificat C2PA fourni avec le prototype est volontairement non approuvé (`valid_untrusted`) ; un certificat de confiance est requis avant un usage de production.
