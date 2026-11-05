# Authenticité des images et lutte contre les deepfakes

[![Groupe](https://img.shields.io/badge/Groupe-46-205e4e)](#membres-du-groupe)
[![Réseau](https://img.shields.io/badge/Blockchain-Base%20Sepolia-0052ff)](https://sepolia.basescan.org/address/0x00da0457fA85fb4b1d4632eb2D9397D94eeb9da8)
[![Frontend](https://img.shields.io/badge/Frontend-Vercel-black)](https://a-ideepfake-detector.vercel.app)
[![API](https://img.shields.io/badge/API-Render-46e3b7)](https://aideepfakedetector-2.onrender.com/docs)
[![Tests API](https://img.shields.io/badge/Tests%20API-17%20réussis-success)](#tests)
[![Tests navigateur](https://img.shields.io/badge/Playwright-5%20réussis-success)](#tests)

Une application web de vérification de provenance des images, de recherche d’origine et d’analyse des indices de génération ou de manipulation par intelligence artificielle.

Elle combine :

- des empreintes cryptographiques et perceptuelles ;
- la reconnaissance d’images recadrées ou recompressées ;
- l’analyse IA avec Sightengine ;
- les métadonnées de provenance C2PA ;
- le stockage public sur IPFS ;
- un registre blockchain sur Base Sepolia ;
- la signature manuelle des transactions avec MetaMask.

> Prisme ne déclare pas automatiquement qu’une image est « vraie » ou « fausse ».  
> L’application présente séparément la similarité visuelle, la détection IA, la provenance C2PA et la preuve blockchain.

---

## Sommaire

- [Démonstration en ligne](#démonstration-en-ligne)
- [Membres du groupe](#membres-du-groupe)
- [Contexte et problématique](#contexte-et-problématique)
- [Objectifs](#objectifs)
- [Fonctionnalités](#fonctionnalités)
- [Architecture](#architecture)
- [Technologies utilisées](#technologies-utilisées)
- [Reconnaissance des images](#reconnaissance-des-images)
- [Analyse des images par intelligence artificielle](#analyse-des-images-par-intelligence-artificielle)
- [Provenance C2PA](#provenance-c2pa)
- [Stockage IPFS](#stockage-ipfs)
- [Smart contract](#smart-contract)
- [Cycle de publication](#cycle-de-publication)
- [Structure de la base de données](#structure-de-la-base-de-données)
- [Installation locale](#installation-locale)
- [Configuration](#configuration)
- [Déploiement](#déploiement)
- [Tests](#tests)
- [Analyse de sécurité](#analyse-de-sécurité)
- [Coûts en gas](#coûts-en-gas)
- [Captures d’écran](#captures-décran)
- [Compte de démonstration](#compte-de-démonstration)
- [Limites](#limites)
- [Feuille de route](#feuille-de-route)
- [Ressources et dépendances](#ressources-et-dépendances)

---

## Démonstration en ligne

| Ressource | Adresse |
|---|---|
| Application web | [https://a-ideepfake-detector.vercel.app](https://a-ideepfake-detector.vercel.app) |
| API FastAPI | [https://aideepfakedetector-2.onrender.com](https://aideepfakedetector-2.onrender.com) |
| Documentation Swagger | [https://aideepfakedetector-2.onrender.com/docs](https://aideepfakedetector-2.onrender.com/docs) |
| État de l’API | [Health check](https://aideepfakedetector-2.onrender.com/health/ready) |
| Smart contract | [BaseScan](https://sepolia.basescan.org/address/0x00da0457fA85fb4b1d4632eb2D9397D94eeb9da8) |
| Dépôt GitHub | [AIdeepfakeDetector](https://github.com/Benjitembwa/AIdeepfakeDetector) |

> L’API Render peut prendre quelques secondes pour démarrer après une période d’inactivité.

---

## Membres du groupe

**Groupe 46 — Blockchain et intelligence artificielle**

| Numéro | Étudiant |
|---:|---|
| 1 | SHOPO SHOPO HERITIER |
| 2 | SILASI NORI ALEXANDRE |
| 3 | TEMBE ZATEMBE RICHRIS |
| 4 | TEMBWA NGENGO BENJI |

Projet réalisé dans le cadre du cours de **Blockchain et cryptomonnaies**, Master 1, mention Mathématiques, Statistiques et Informatique, Faculté des Sciences et Technologies, Université de Kinshasa.

---

## Contexte et problématique

Les images publiées sur Internet peuvent être :

- copiées sans indication de leur origine ;
- recompressées par les réseaux sociaux ;
- redimensionnées ou recadrées ;
- sorties de leur contexte ;
- retouchées par intelligence artificielle ;
- entièrement générées par un modèle d’IA ;
- accompagnées de fausses informations.

Une analyse visuelle ne permet généralement pas de déterminer avec certitude :

- quel média a publié l’image ;
- si le fichier a été modifié ;
- si une preuve de provenance existe ;
- si les métadonnées présentées correspondent à un enregistrement public ;
- si l’image contient des indices de génération artificielle.

La problématique du projet est donc la suivante :

> Comment concevoir une plateforme capable de rechercher l’origine d’une image, même après certaines transformations, de conserver des preuves de provenance publiquement vérifiables et de présenter les différents indices sans produire un verdict trompeur ?

---

## Objectifs

### Objectif général

Concevoir une application web permettant aux médias partenaires simulés d’enregistrer les preuves de provenance de leurs images et aux visiteurs de vérifier publiquement une image partagée sur Internet.

### Objectifs spécifiques

- calculer une empreinte cryptographique SHA-256 ;
- calculer plusieurs empreintes perceptuelles ;
- reconnaître une image identique, recompressée ou recadrée ;
- analyser les indices de génération ou de retouche par IA ;
- ajouter des métadonnées de provenance C2PA ;
- publier l’image et ses métadonnées sur IPFS ;
- enregistrer les preuves minimales sur Base Sepolia ;
- permettre à chaque média de signer avec son propre portefeuille ;
- demander une confirmation MetaMask pour chaque transaction ;
- vérifier la cohérence entre PostgreSQL, IPFS et la blockchain ;
- permettre la révocation publique d’une preuve ;
- produire un rapport compréhensible et transparent.

---

## Fonctionnalités

### Pour les visiteurs

- téléversement d’une image sans création de compte ;
- validation du format et de la taille ;
- recherche d’une copie exacte avec SHA-256 ;
- recherche d’une image visuellement proche ;
- reconnaissance de certaines recompressions et de certains recadrages ;
- analyse des indices IA et deepfake ;
- inspection des métadonnées C2PA ;
- vérification de la preuve Base Sepolia ;
- consultation des fichiers IPFS ;
- accès à la transaction sur BaseScan.

### Pour les médias partenaires

- création d’un compte média ;
- authentification par JWT ;
- connexion d’un portefeuille MetaMask ;
- sélection automatique de Base Sepolia ;
- publication d’une image et de ses informations éditoriales ;
- confirmation manuelle de la transaction ;
- consultation de la bibliothèque des publications ;
- recherche par titre, auteur ou nom de fichier ;
- export des preuves au format JSON ;
- reprise d’une transaction en attente ;
- révocation avec le portefeuille publicateur.

---

## Architecture

### Architecture générale

```mermaid
flowchart LR
    V[Visiteur] --> W[Application Next.js]
    M[Média partenaire] --> W

    W <--> MM[MetaMask]
    W --> API[API FastAPI]

    API --> DB[(PostgreSQL Neon)]
    API --> SE[Sightengine]
    API --> IPFS[Pinata / IPFS]
    API --> C2PA[c2pa-python]
    API --> RPC[RPC Base Sepolia]

    MM --> BASE[Base Sepolia]
    BASE --> SC[PrismeOpenImageRegistry]

    W --> BS[BaseScan]
    W --> GW[Gateway IPFS]
```

### Partie off-chain

La partie hors chaîne comprend :

- l’interface Next.js ;
- l’API FastAPI ;
- PostgreSQL Neon ;
- les empreintes perceptuelles ;
- les descripteurs ORB ;
- l’analyse Sightengine ;
- la création et l’inspection C2PA ;
- Pinata et IPFS ;
- les états temporaires des transactions.

### Partie on-chain

Le smart contract conserve uniquement les preuves nécessaires :

- SHA-256 de l’image ;
- pHash ;
- dHash ;
- wHash ;
- CID IPFS de l’image ;
- CID IPFS des métadonnées ;
- SHA-256 du document JSON ;
- identifiant haché du média ;
- adresse du portefeuille publicateur ;
- bloc et date d’enregistrement ;
- état de révocation.

Les images et les données personnelles ne sont pas enregistrées directement sur la blockchain.

---

## Technologies utilisées

| Domaine | Technologies |
|---|---|
| Frontend | Next.js 16, React 19, TypeScript |
| Interface | CSS, Tailwind CSS, Lucide React |
| Backend | Python 3.12, FastAPI, Uvicorn, Pydantic |
| SGBD | PostgreSQL Neon |
| ORM et migrations | SQLAlchemy 2, psycopg 3, Alembic |
| Authentification | JWT, Argon2 |
| Traitement des images | Pillow, NumPy, imagehash, OpenCV |
| Détection IA | Sightengine |
| Provenance | c2pa-python 0.38 |
| Stockage distribué | IPFS public via Pinata |
| Blockchain | Solidity, Base Sepolia |
| Portefeuille | MetaMask, EIP-1193 |
| Interaction blockchain | web3.py 7 |
| Déploiement du contrat | Remix IDE |
| Tests API | pytest, pytest-asyncio, HTTPX |
| Tests web | Playwright |
| Frontend en ligne | Vercel |
| API en ligne | Render |
| Versionnement | Git et GitHub |

---

## Reconnaissance des images

Prisme combine plusieurs méthodes complémentaires.

### SHA-256

SHA-256 produit une empreinte cryptographique de 256 bits.

Il permet de reconnaître une copie strictement identique du fichier. Une modification d’un seul octet entraîne normalement une empreinte différente.

### pHash

Le perceptual hash décrit la structure visuelle globale de l’image. Il résiste partiellement :

- à la recompression ;
- au redimensionnement ;
- aux changements légers de qualité.

### dHash

Le difference hash représente les variations de luminosité entre les pixels voisins.

### wHash

Le wavelet hash utilise une transformation en ondelettes pour produire une représentation compacte multi-échelle.

### ORB et RANSAC

OpenCV est utilisé pour détecter des points caractéristiques locaux avec ORB.

RANSAC vérifie ensuite que les correspondances respectent une transformation géométrique cohérente.

Cette approche permet de reconnaître certaines images :

- recadrées ;
- redimensionnées ;
- recompressées ;
- légèrement transformées.

### Types de correspondances

| Type | Description |
|---|---|
| `exact` | Même SHA-256 |
| `perceptual` | Hachages perceptuels suffisamment proches |
| `local_features` | Correspondance locale validée avec ORB et RANSAC |

---

## Analyse des images par intelligence artificielle

### Approche initialement envisagée

Le projet prévoyait initialement :

- un modèle ResNet-18 ;
- le jeu de données CIFAKE ;
- le jeu de données GenImage ;
- un entraînement sur Google Colab.

### Approche finalement retenue

Pour le prototype final, l’entraînement local a été remplacé par l’intégration de l’API Sightengine.

Cette décision réduit :

- les besoins en GPU ;
- la durée d’entraînement ;
- la consommation Internet ;
- les coûts d’hébergement ;
- la complexité MLOps ;
- les risques de surapprentissage sur un seul jeu de données.

### Données et modèle

Sightengine utilise ses propres modèles et jeux de données, qui ne sont pas entièrement publics. Prisme n’entraîne donc pas directement un modèle et ne revendique pas la propriété des modèles Sightengine.

Les sorties utilisées sont notamment :

- `ai_generated_score` ;
- `deepfake_score` ;
- le générateur probable ;
- la confiance associée ;
- l’identifiant de la requête.

### Métriques

Les scores sont normalisés entre `0` et `1`.

Ils représentent une probabilité ou un indice statistique et non une preuve absolue.

### Lien entre l’IA et la blockchain

Les scores Sightengine ne sont pas enregistrés sur la blockchain.

La blockchain conserve les preuves de provenance et d’intégrité, tandis que Sightengine fournit une analyse probabiliste indépendante.

Cette séparation évite de rendre permanent un score susceptible d’évoluer avec les modèles.

---

## Provenance C2PA

C2PA est un standard de provenance des contenus numériques.

Lors de la publication, Prisme ajoute à l’image un manifeste contenant notamment :

- le nom du média ;
- le titre ;
- l’auteur ;
- l’URL source ;
- l’identifiant de la publication ;
- l’empreinte du fichier source ;
- le générateur du manifeste.

### États C2PA

| État | Signification |
|---|---|
| `valid` | Manifeste valide et certificat reconnu |
| `valid_untrusted` | Signature valide mais certificat non approuvé |
| `invalid` | Manifeste ou signature invalide |
| `absent` | Aucun manifeste trouvé |
| `unavailable` | Analyse techniquement impossible |

Le prototype utilise un certificat de test. L’état généralement attendu est donc `valid_untrusted`.

> Une signature C2PA valide prouve l’intégrité d’une déclaration, pas la vérité de la scène photographiée.

---

## Stockage IPFS

Prisme publie deux fichiers sur IPFS avec Pinata :

1. l’image contenant le manifeste C2PA ;
2. un fichier JSON canonique contenant les preuves et les métadonnées.

Le document JSON contient notamment :

- l’identité publique du média ;
- l’adresse du portefeuille ;
- les informations éditoriales ;
- les dimensions ;
- SHA-256 ;
- pHash, dHash et wHash ;
- la version des empreintes ;
- le CID de l’image ;
- les informations C2PA.

Chaque fichier possède un CID dérivé de son contenu.

### Limite du désépinglage

Le désépinglage retire le fichier du compte Pinata, mais ne garantit pas son effacement total. D’autres nœuds IPFS peuvent conserver une copie.

---

## Smart contract

### Contrat actif

| Information | Valeur |
|---|---|
| Nom | `PrismeOpenImageRegistry` |
| Réseau | Base Sepolia |
| Chain ID | `84532` |
| Adresse | `0x00da0457fA85fb4b1d4632eb2D9397D94eeb9da8` |
| Bloc | `54922239` |
| Compilateur | Solidity `0.8.34` |
| Optimisation | Activée, `200 runs` |
| Déploiement | Remix IDE |

### Liens

- [Contrat sur BaseScan](https://sepolia.basescan.org/address/0x00da0457fA85fb4b1d4632eb2D9397D94eeb9da8)
- [Transaction de déploiement](https://sepolia.basescan.org/tx/0x1c3e5a975d0452fc82972993047cf40f063294e640d68eef065a2974a64aa861)
- [Code Solidity](contracts/PrismeOpenImageRegistry.sol)
- [Procédure Remix](contracts/README.md)

### Fonctions principales

```solidity
function registerImage(
    bytes32 imageSha256,
    uint64 perceptualHash,
    uint64 differenceHash,
    uint64 waveletHash,
    string calldata imageCid,
    string calldata metadataCid,
    bytes32 metadataSha256,
    bytes32 mediaId
) external;
```

```solidity
function revokeImage(bytes32 imageSha256) external;
```

```solidity
function getImage(
    bytes32 imageSha256
) external view returns (ImageRegistration memory);
```

### Registre ouvert

Tout portefeuille peut enregistrer une nouvelle image.

Une empreinte SHA-256 ne peut être enregistrée qu’une seule fois.

Seul le portefeuille ayant créé l’enregistrement peut ensuite le révoquer.

### Événements

```solidity
event ImageRegistered(
    bytes32 indexed imageSha256,
    bytes32 indexed mediaId,
    address indexed publisher,
    uint64 registeredAt
);
```

```solidity
event ImageRevoked(
    bytes32 indexed imageSha256,
    address indexed revokedBy,
    uint64 revokedAt
);
```

---

## Cycle de publication

```mermaid
sequenceDiagram
    participant M as Média
    participant W as Interface web
    participant A as FastAPI
    participant I as IPFS / Pinata
    participant MM as MetaMask
    participant B as Base Sepolia
    participant P as PostgreSQL

    M->>W: Image et informations éditoriales
    W->>A: Image, métadonnées et portefeuille
    A->>A: Validation et empreintes
    A->>A: Signature C2PA
    A->>I: Publication de l’image
    I-->>A: CID de l’image
    A->>I: Publication du JSON
    I-->>A: CID des métadonnées
    A->>P: Sauvegarde de l’état IPFS
    A-->>W: Calldata de registerImage
    W->>MM: Demande de transaction
    MM->>M: Confirmation manuelle
    MM->>B: Transaction signée
    B-->>W: Hash de transaction
    W->>A: Hash de transaction
    A->>B: Vérification du reçu
    A->>B: Lecture avec getImage
    A->>P: Statut registered
```

### Vérifications effectuées après la transaction

FastAPI vérifie :

- le Chain ID ;
- l’existence du bytecode ;
- la propriété `registrationOpen` ;
- l’adresse du contrat ciblé ;
- l’adresse du portefeuille émetteur ;
- le calldata ABI ;
- le statut du reçu ;
- les valeurs retournées par `getImage()`.

---

## Structure de la base de données

### `media_organizations`

Cette table contient :

- UUID du média ;
- nom ;
- slug ;
- adresse e-mail ;
- mot de passe haché avec Argon2 ;
- état du compte ;
- dates de création et de modification.

### `image_records`

Cette table contient notamment :

- média propriétaire ;
- informations éditoriales ;
- dimensions et format ;
- SHA-256 ;
- pHash, dHash et wHash ;
- descripteurs ORB ;
- informations C2PA ;
- CID et identifiants Pinata ;
- contrat et Chain ID ;
- portefeuille publicateur ;
- hash de transaction ;
- bloc d’enregistrement ;
- hash de révocation ;
- état de publication.

### États possibles

| État | Description |
|---|---|
| `draft` | Brouillon |
| `fingerprinted` | Empreintes calculées |
| `ipfs_stored` | Fichiers publiés sur IPFS |
| `blockchain_pending` | Transaction en attente |
| `registration_failed` | Transaction échouée ou à reprendre |
| `registered` | Preuve confirmée |
| `revoked` | Preuve révoquée |

---

## Structure du dépôt

```text
AIdeepfakeDetector/
├── apps/
│   └── web/                    # Frontend Next.js
├── contracts/
│   ├── PrismeOpenImageRegistry.sol
│   ├── PrismeImageRegistry.sol # Ancien contrat historique
│   └── README.md               # Procédure Remix
├── docs/
│   ├── architecture.md
│   ├── demo.md
│   └── validation-etape-6.md
├── services/
│   └── api/
│       ├── app/                # API FastAPI
│       ├── migrations/         # Migrations Alembic
│       ├── scripts/            # Validation Pinata et blockchain
│       └── tests/              # Tests pytest
├── tests/
│   └── interface.spec.ts       # Tests Playwright
├── package.json
└── README.md
```

---

## Installation locale

### Prérequis

- Git ;
- Node.js 22 ou supérieur ;
- npm ;
- Python 3.12 ;
- MetaMask ;
- une base PostgreSQL ;
- un compte Pinata ;
- un compte Sightengine.

### Cloner le dépôt

```bash
git clone https://github.com/Benjitembwa/AIdeepfakeDetector.git
cd AIdeepfakeDetector
```

### Installer le frontend

```bash
npm install
```

### Installer l’API sous Windows

```powershell
py -3.12 -m venv services/api/.venv
services\api\.venv\Scripts\python.exe -m pip install -r services/api/requirements-dev.txt
```

### Installer l’API sous Linux ou macOS

```bash
python3.12 -m venv services/api/.venv
source services/api/.venv/bin/activate
pip install -r services/api/requirements-dev.txt
```

### Configurer les variables

Copier les fichiers d’exemple :

```bash
cp services/api/.env.example services/api/.env
cp apps/web/.env.example apps/web/.env.local
```

Sous PowerShell :

```powershell
Copy-Item services/api/.env.example services/api/.env
Copy-Item apps/web/.env.example apps/web/.env.local
```

### Appliquer les migrations

```powershell
npm.cmd run api:migrate
```

### Lancer l’API

```powershell
npm.cmd run api:dev
```

L’API locale sera accessible sur :

```text
http://127.0.0.1:8000
```

Swagger sera disponible sur :

```text
http://127.0.0.1:8000/docs
```

### Lancer le frontend

Dans un autre terminal :

```powershell
npm.cmd run dev
```

Le frontend sera accessible sur :

```text
http://127.0.0.1:3000
```

---

## Configuration

### Variables FastAPI

```dotenv
PRISME_APP_ENV=development
PRISME_DATABASE_URL=postgresql://USER:PASSWORD@HOST/DATABASE?sslmode=require
PRISME_JWT_SECRET_KEY=GENERER_UN_SECRET_ALEATOIRE
PRISME_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

PRISME_SIGHTENGINE_API_USER=VOTRE_IDENTIFIANT
PRISME_SIGHTENGINE_API_SECRET=VOTRE_SECRET

PRISME_PINATA_JWT=VOTRE_JWT_PINATA
PRISME_PINATA_GATEWAY=VOTRE_GATEWAY.mypinata.cloud

PRISME_BASE_RPC_URL=https://sepolia.base.org
PRISME_BASE_CHAIN_ID=84532
PRISME_BASE_EXPLORER_URL=https://sepolia.basescan.org
PRISME_REGISTRY_CONTRACT_ADDRESS=0x00da0457fA85fb4b1d4632eb2D9397D94eeb9da8
```

### Variable frontend

```dotenv
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

> Ne jamais placer de mot de passe, de clé privée, de phrase de récupération, de JWT Pinata ou de secret Sightengine dans GitHub.

L’application n’utilise plus `PRISME_REGISTRY_PRIVATE_KEY`. Les transactions sont signées manuellement avec MetaMask.

---

## Déploiement

### Frontend sur Vercel

- connecter le dépôt GitHub à Vercel ;
- sélectionner l’application Next.js ;
- configurer `NEXT_PUBLIC_API_URL` avec l’URL Render ;
- lancer le déploiement.

### API sur Render

Configuration recommandée :

| Paramètre | Valeur |
|---|---|
| Environnement | Python |
| Root Directory | `services/api` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `python -m alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT` |

Ajouter toutes les variables `PRISME_*` dans les variables d’environnement Render.

### Base de données

PostgreSQL est hébergé sur Neon.

Les migrations sont gérées par Alembic.

### Smart contract

Le contrat a été :

- compilé avec Remix ;
- optimisé avec `200 runs` ;
- déployé sur Base Sepolia ;
- connecté à l’application avec web3.py et MetaMask.

### IPFS

Les images et les documents JSON sont publiés sur IPFS avec Pinata.

---

## Tests

### Tests de l’API

```powershell
npm.cmd run api:test
```

Résultat final :

```text
17 tests réussis
```

Les tests couvrent notamment :

- inscription et connexion ;
- isolation entre médias ;
- validation des images ;
- publication IPFS simulée ;
- préparation du calldata ;
- confirmation des reçus ;
- rejet d’un mauvais portefeuille ;
- détection des doublons ;
- reprise idempotente ;
- révocation ;
- inspection C2PA ;
- analyse Sightengine simulée ;
- copie exacte ;
- recompression ;
- recadrage.

### Tests TypeScript

```powershell
npm.cmd run typecheck
```

### Build de production

```powershell
npm.cmd run build
```

### Tests navigateur

```powershell
npm.cmd run test:e2e
```

Résultat final :

```text
5 parcours Playwright réussis
```

Les parcours simulent notamment :

- l’API ;
- MetaMask ;
- la connexion du portefeuille ;
- l’enregistrement ;
- la révocation ;
- l’affichage mobile ;
- l’accessibilité clavier ;
- l’expiration d’une session.

### Tests blockchain automatisés

Le fichier suivant teste l’intégration blockchain :

```text
services/api/tests/test_blockchain.py
```

Il couvre :

- la conversion des empreintes vers les types Solidity ;
- l’encodage ABI ;
- la normalisation des reçus ;
- la vérification du portefeuille émetteur ;
- le rejet d’une transaction provenant d’une autre adresse.

Les fonctions du contrat ont également été testées dans Remix VM avant le déploiement.

---

## Analyse de sécurité

### Contrôle d’accès

- `registerImage()` est volontairement public ;
- `revokeImage()` est limité au publicateur initial ;
- une image ne peut être enregistrée qu’une seule fois ;
- les comptes PostgreSQL sont isolés par média.

### Réentrance

Le contrat n’effectue aucun appel externe et ne transfère aucun fonds.

La surface de réentrance est donc fortement limitée.

### Validation des entrées

Le contrat rejette :

- un SHA-256 nul ;
- un identifiant média nul ;
- un hash de métadonnées nul ;
- un CID d’image vide ;
- un CID de métadonnées vide ;
- un doublon ;
- une révocation par une adresse différente ;
- une seconde révocation.

### Traçabilité

Les opérations importantes génèrent des événements :

- `ImageRegistered` ;
- `ImageRevoked`.

### Données personnelles

Aucune donnée personnelle n’est enregistrée directement sur la blockchain.

Le contrat conserve uniquement :

- des empreintes ;
- des CID ;
- un identifiant média haché ;
- une adresse publique ;
- des informations de bloc.

### Sécurité des clés

- aucune clé privée MetaMask dans FastAPI ;
- aucune phrase de récupération dans le dépôt ;
- confirmation manuelle des transactions ;
- secrets stockés dans Render et Vercel ;
- fichiers `.env` exclus de Git.

### Menaces identifiées

| Menace | Mesure actuelle | Amélioration future |
|---|---|---|
| Front-running du SHA-256 | Premier enregistrement conservé publiquement | Mécanisme commit-reveal |
| Vol du mot de passe | Argon2 et JWT temporaire | MFA et limitation des tentatives |
| Fausse transaction | Vérification du contrat, du signataire et du calldata | Surveillance d’événements |
| Fuite de secrets | Variables d’environnement | Coffre-fort de secrets |
| Faux positif IA | Résultats présentés comme probabilités | Comparaison de plusieurs modèles |
| Perte d’une clé MetaMask | Aucune récupération intégrée | Portefeuille multisignature ou social recovery |
| Indisponibilité RPC | État `unavailable` sans bloquer les autres analyses | Plusieurs fournisseurs RPC |
| Copie IPFS persistante | Avertissement lors du désépinglage | Politique de rétention et chiffrement selon l’usage |

---

## Coûts en gas

Les transactions sont réalisées uniquement avec de l’ETH de test Base Sepolia.

| Opération | Gas observé ou estimé |
|---|---:|
| Déploiement du contrat | `669 856 gas` |
| `registerImage()` | Variable selon la longueur des CID — à relever pendant la démonstration |
| `revokeImage()` | Variable — à relever pendant la démonstration |
| `getImage()` | Lecture, aucun gas payé par l’utilisateur |
| `exists()` | Lecture, aucun gas payé par l’utilisateur |
| `isActive()` | Lecture, aucun gas payé par l’utilisateur |

Le projet ne réalise aucune transaction avec des fonds réels.

---

## Tokenomics

Le projet ne crée aucun jeton et ne possède donc pas de tokenomics.

L’ETH utilisé est uniquement de l’ETH de test obtenu auprès d’un faucet Base Sepolia et sert au paiement du gas.

---

## Captures d’écran

> Ajouter les fichiers dans `docs/screenshots/` avant la remise.

### Page d’accueil

![Page d’accueil](docs/screenshots/accueil.png)

### Rapport de vérification

![Rapport de vérification](docs/screenshots/rapport-verification.png)

### Espace média

![Espace média](docs/screenshots/espace-media.png)

### Connexion MetaMask

![Connexion MetaMask](docs/screenshots/metamask.png)

### Confirmation de transaction

![Confirmation de transaction](docs/screenshots/confirmation-transaction.png)

### Contrat sur BaseScan

![Contrat BaseScan](docs/screenshots/basescan-contrat.png)

### Fichiers sur IPFS

![Fichiers IPFS](docs/screenshots/ipfs.png)

---

## Compte de démonstration

La page publique de vérification ne nécessite aucun compte.

Pour tester l’espace média, créer avant la remise un compte réservé à la démonstration :

| Information | Valeur |
|---|---|
| URL | [Espace média](https://a-ideepfake-detector.vercel.app/medias) |
| E-mail | `demo.groupe46@example.com` |
| Mot de passe | `Prisme-G46-Demo!` |
| Réseau MetaMask | Base Sepolia |
| Chain ID | `84532` |

> Ce compte doit être créé dans l’application avant la remise.  
> Il ne doit contenir aucune donnée personnelle ou image sensible.  
> Aucune clé privée ou phrase de récupération MetaMask ne doit être communiquée.

---

## Limites

### Détection IA

Sightengine est un service externe. Ses données d’entraînement et son architecture complète ne sont pas publiques.

Les scores restent probabilistes et peuvent produire des faux positifs ou des faux négatifs.

### Reconnaissance visuelle

Les transformations trop importantes peuvent empêcher la reconnaissance.

Les images simples ou peu détaillées peuvent produire des similarités accidentelles.

### C2PA

Le certificat du prototype est un certificat de test non reconnu par une autorité de confiance.

Une signature valide ne prouve pas que la scène photographiée est vraie.

### IPFS

Le désépinglage ne garantit pas l’effacement du fichier sur tous les nœuds IPFS.

### Blockchain

La blockchain prouve qu’une adresse a enregistré des données à un instant donné. Elle ne garantit pas l’exactitude journalistique de ces données.

### Registre ouvert

Le premier portefeuille qui enregistre un SHA-256 devient son publicateur. Cette propriété crée un risque de front-running.

### Performance

La recherche perceptuelle parcourt actuellement un nombre limité de candidats PostgreSQL. Une indexation spécialisée serait nécessaire à très grande échelle.

---

## Feuille de route

### Court terme

- vérifier publiquement le code source du contrat sur BaseScan ;
- compléter les captures d’écran ;
- ajouter un rapport Slither ;
- ajouter des tests Solidity avec Foundry ou Hardhat ;
- relever les coûts réels de `registerImage()` et `revokeImage()` ;
- créer et tester le compte de démonstration.

### Moyen terme

- ajouter une validation administrative des médias ;
- ajouter une limitation des requêtes ;
- utiliser plusieurs fournisseurs RPC ;
- obtenir un certificat C2PA reconnu ;
- ajouter un mécanisme de récupération de session ;
- améliorer l’indexation des empreintes.

### Long terme

- mécanisme commit-reveal contre le front-running ;
- signatures de domaine reliant un média à son portefeuille ;
- portefeuille multisignature pour les rédactions ;
- prise en charge des vidéos et des fichiers audio ;
- comparaison de plusieurs fournisseurs de détection IA ;
- modèle open source local évalué sur plusieurs jeux de données ;
- déploiement sur un réseau principal après audit.

---

## Conformité éthique

Le projet respecte les principes suivants :

- utilisation exclusive d’un réseau de test ;
- aucune transaction avec des fonds réels ;
- aucun mécanisme de levée de fonds ;
- aucun jeton vendu au public ;
- aucune promesse de rendement ;
- utilisation d’images non sensibles pour la démonstration ;
- aucune donnée personnelle en clair sur la blockchain ;
- secrets exclus du dépôt GitHub ;
- portefeuille dédié au développement ;
- présentation explicite des limites de la détection IA.

---

## Ressources et dépendances

Le projet utilise notamment :

- [FastAPI](https://fastapi.tiangolo.com/)
- [Next.js](https://nextjs.org/)
- [React](https://react.dev/)
- [PostgreSQL](https://www.postgresql.org/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [OpenCV](https://opencv.org/)
- [ImageHash](https://github.com/JohannesBuchner/imagehash)
- [C2PA](https://c2pa.org/)
- [IPFS](https://ipfs.tech/)
- [Pinata](https://pinata.cloud/)
- [Solidity](https://soliditylang.org/)
- [Remix IDE](https://remix.ethereum.org/)
- [Base](https://base.org/)
- [web3.py](https://web3py.readthedocs.io/)
- [MetaMask](https://metamask.io/)
- [Sightengine](https://sightengine.com/)
- [Playwright](https://playwright.dev/)
- [pytest](https://pytest.org/)

Les bibliothèques, services externes et standards restent la propriété de leurs auteurs et sont utilisés conformément à leurs licences respectives.

---

## Licence

Projet académique réalisé par le groupe 46 dans le cadre du cours de Blockchain et cryptomonnaies à l’Université de Kinshasa.

L’utilisation du code en dehors du cadre académique nécessite l’accord des membres du groupe.

---

## Avertissement

Prisme est un prototype académique.

Il ne doit pas être utilisé comme unique moyen de décision journalistique, judiciaire ou administrative.

Une correspondance visuelle, un score IA, une signature C2PA ou une preuve blockchain constitue un indice technique, pas une preuve absolue de la vérité d’une image.
