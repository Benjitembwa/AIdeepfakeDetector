# Validation réelle des étapes 6 et 7

Cette validation doit être effectuée après avoir créé le compte Pinata et ajouté les secrets localement. Ne jamais copier le JWT Pinata, la clé privée MetaMask ou la phrase de récupération dans Git, une capture d'écran ou une conversation.

## 1. Préparer Pinata

1. Créer une clé API limitée aux opérations de lecture, téléversement et suppression des fichiers publics.
2. Copier le JWT au moment de sa création.
3. Relever le domaine de gateway sous la forme `nom.mypinata.cloud`.

## 2. Préparer le compte Base Sepolia

1. Dans MetaMask, sélectionner le compte déployeur `0x9f06FcF98fDB0B374E63FdE559590bF2CA472E81`.
2. Vérifier qu'il possède de l'ETH Base Sepolia.
3. Exporter sa clé privée uniquement vers `services/api/.env`.

## 3. Compléter `.env`

```dotenv
PRISME_PINATA_JWT=...
PRISME_PINATA_GATEWAY=nom.mypinata.cloud
PRISME_BASE_RPC_URL=https://sepolia.base.org
PRISME_BASE_CHAIN_ID=84532
PRISME_BASE_EXPLORER_URL=https://sepolia.basescan.org
PRISME_REGISTRY_CONTRACT_ADDRESS=0x12DD566159a151Ab14009BC5d7624519C60c3647
PRISME_REGISTRY_PRIVATE_KEY=...
PRISME_C2PA_SIGN_CERT_PATH=tests/fixtures/c2pa/es256_certs.pem
PRISME_C2PA_PRIVATE_KEY_PATH=tests/fixtures/c2pa/es256_private.key
```

Relancer ensuite l'API avec un seul worker :

```powershell
npm.cmd run api:dev
```

## 4. Valider deux images non sensibles

### Image active de démonstration

1. Publier une image depuis `/medias`.
2. Vérifier le statut **Preuve on-chain vérifiable**.
3. Ouvrir le lien IPFS de l'image et celui du JSON, puis confirmer que le fichier contient un manifeste C2PA.
4. Ouvrir la transaction BaseScan et relever le bloc.
5. Vérifier le même fichier depuis `/` : la blockchain doit indiquer `verified` et C2PA `valid_untrusted` avec le certificat de test.
6. Conserver cette image active pour la démonstration.

### Image jetable

1. Publier une seconde image différente.
2. Vérifier les deux liens IPFS et la transaction.
3. Cliquer sur **Révoquer**, puis confirmer.
4. Vérifier que PostgreSQL conserve la ligne avec le statut `revoked` et le hash de révocation.
5. Vérifier depuis `/` que la preuve indique `revoked`.

Le désépinglage Pinata retire les fichiers du compte et de sa gateway, mais ne garantit pas l'effacement des copies conservées par d'autres nœuds IPFS.

Le certificat et la clé présents dans `tests/fixtures/c2pa` sont des données publiques de démonstration. Avant un déploiement de production, les remplacer par un certificat C2PA de confiance et une clé privée protégée hors du système de fichiers applicatif.
