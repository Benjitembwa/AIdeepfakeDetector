# API Prisme

API FastAPI des étapes 3 à 9. Elle authentifie les médias, calcule les empreintes, signe la provenance C2PA, publie les images sur IPFS, inscrit leurs preuves sur Base Sepolia et combine reconnaissance d'origine, preuve on-chain, C2PA et analyse Sightengine.

## Installation locale

Depuis `services/api` :

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000 --workers 1
```

Swagger est disponible sur `http://127.0.0.1:8000/docs` et la disponibilité PostgreSQL sur `http://127.0.0.1:8000/health/ready`.

## Configuration des étapes 6 et 7

Copier les valeurs suivantes dans `.env`, jamais dans Git ou le navigateur :

```dotenv
PRISME_PINATA_JWT=...
PRISME_PINATA_GATEWAY=votre-domaine.mypinata.cloud
PRISME_BASE_RPC_URL=https://sepolia.base.org
PRISME_BASE_CHAIN_ID=84532
PRISME_BASE_EXPLORER_URL=https://sepolia.basescan.org
PRISME_REGISTRY_CONTRACT_ADDRESS=0x12DD566159a151Ab14009BC5d7624519C60c3647
PRISME_REGISTRY_PRIVATE_KEY=...
PRISME_C2PA_SIGN_CERT_PATH=tests/fixtures/c2pa/es256_certs.pem
PRISME_C2PA_PRIVATE_KEY_PATH=tests/fixtures/c2pa/es256_private.key
```

La clé Pinata doit autoriser l'envoi, la lecture et la suppression de fichiers publics. Le compte Base Sepolia doit être le propriétaire du contrat et posséder de l'ETH de test. Un seul worker API est requis : un verrou applicatif sérialise les transactions et protège les nonces de ce compte. Les identifiants C2PA inclus dans `tests/fixtures/c2pa` sont publics et réservés au prototype : le déploiement de production devra employer un certificat approuvé et protéger sa clé dans un KMS ou HSM.

## Cycle de publication

`POST /api/v1/images` valide le fichier et les métadonnées, calcule SHA-256, pHash, dHash, wHash et ORB, bloque les doublons, puis :

1. signe un manifeste C2PA déclarant le média, l'auteur et l'empreinte du fichier source ;
2. téléverse l'image signée publiquement sur Pinata avec CIDv1 ;
3. crée un JSON canonique et téléverse celui-ci ;
4. appelle `registerImage()` et attend le reçu ;
5. conserve le manifeste, les CID, identifiants Pinata, preuves et reçu dans PostgreSQL.

La route renvoie `201` si le reçu est confirmé, `202` si l'état est récupérable et `409` pour un doublon. `POST /api/v1/images/{id}/retry-registration` vérifie le reçu et `getImage()` avant tout nouvel envoi. La reprise est idempotente.

`DELETE /api/v1/images/{id}` appelle `revokeImage()` avant de désépingler une publication enregistrée. La ligne PostgreSQL est conservée avec le statut `revoked`. Une publication jamais inscrite peut être supprimée définitivement. Un désépinglage Pinata ne supprime pas les copies éventuellement conservées par d'autres nœuds IPFS.

## Routes principales

| Méthode et route | Rôle |
| --- | --- |
| `POST /api/v1/auth/register` | Créer un compte média |
| `POST /api/v1/auth/token` | Obtenir un jeton JWT |
| `GET /api/v1/media/me` | Lire le média authentifié |
| `GET /api/v1/images` | Rechercher ses publications |
| `POST /api/v1/images` | Publier sur IPFS et Base Sepolia |
| `GET /api/v1/images/{id}` | Lire les preuves d'une publication |
| `POST /api/v1/images/{id}/retry-registration` | Reprendre sans doublon |
| `DELETE /api/v1/images/{id}` | Révoquer/désépingler ou supprimer |
| `POST /api/v1/verify` | Reconnaissance, Sightengine, C2PA et preuve on-chain |

La preuve publique vaut `verified`, `revoked`, `mismatch`, `not_registered` ou `unavailable`. La provenance C2PA vaut `valid`, `valid_untrusted`, `invalid`, `absent` ou `unavailable`. Une panne RPC ou C2PA ne bloque ni la reconnaissance d'origine ni Sightengine.

## Migrations et tests

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m pytest
```

Les tests utilisent des doubles Pinata et Base Sepolia et ne consomment ni quota, ni ETH. Ne jamais journaliser `PRISME_DATABASE_URL`, `PRISME_JWT_SECRET_KEY`, `PRISME_SIGHTENGINE_API_SECRET`, `PRISME_PINATA_JWT` ou `PRISME_REGISTRY_PRIVATE_KEY`.
