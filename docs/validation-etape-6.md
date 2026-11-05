# Validation réelle des étapes 6 et 7

Cette validation doit être effectuée après avoir créé le compte Pinata et déployé le registre ouvert. Ne jamais copier le JWT Pinata, une clé privée MetaMask ou une phrase de récupération dans Git, une capture d'écran ou une conversation. Prisme n'a besoin d'aucune clé privée blockchain.

## 1. Préparer Pinata

1. Créer une clé API limitée aux opérations de lecture, téléversement et suppression des fichiers publics.
2. Copier le JWT au moment de sa création.
3. Relever le domaine de gateway sous la forme `nom.mypinata.cloud`.

## 2. Déployer le registre ouvert

1. Suivre [`contracts/README.md`](../contracts/README.md) pour compiler et déployer `PrismeOpenImageRegistry.sol` dans Remix.
2. Confirmer que le réseau affiche le Chain ID `84532` et que `registrationOpen()` renvoie `true`.
3. Copier uniquement l'adresse publique du nouveau contrat.
4. Approvisionner en ETH Base Sepolia chaque portefeuille qui effectuera les tests.

## 3. Compléter `.env`

```dotenv
PRISME_PINATA_JWT=...
PRISME_PINATA_GATEWAY=nom.mypinata.cloud
PRISME_BASE_RPC_URL=https://sepolia.base.org
PRISME_BASE_CHAIN_ID=84532
PRISME_BASE_EXPLORER_URL=https://sepolia.basescan.org
PRISME_REGISTRY_CONTRACT_ADDRESS=0xNOUVELLE_ADRESSE_DU_REGISTRE_OUVERT
PRISME_C2PA_SIGN_CERT_PATH=tests/fixtures/c2pa/es256_certs.pem
PRISME_C2PA_PRIVATE_KEY_PATH=tests/fixtures/c2pa/es256_private.key
```

Relancer ensuite l'API :

```powershell
npm.cmd run api:dev
```

## 4. Valider deux images non sensibles

### Image active de démonstration

1. Connecter MetaMask depuis `/medias`, puis publier une image.
2. Contrôler le contrat, le réseau et les frais affichés par MetaMask, puis confirmer.
3. Vérifier le statut **Preuve on-chain vérifiable**.
4. Ouvrir le lien IPFS de l'image et celui du JSON, puis confirmer que le fichier contient un manifeste C2PA.
5. Ouvrir la transaction BaseScan et relever le bloc et le portefeuille publicateur.
6. Vérifier le même fichier depuis `/` : la blockchain doit indiquer `verified` et C2PA `valid_untrusted` avec le certificat de test.
7. Conserver cette image active pour la démonstration.

### Image jetable

1. Publier une seconde image différente.
2. Vérifier les deux liens IPFS et la transaction.
3. Cliquer sur **Révoquer**, puis confirmer manuellement la transaction MetaMask avec le même portefeuille.
4. Vérifier que PostgreSQL conserve la ligne avec le statut `revoked` et le hash de révocation.
5. Vérifier depuis `/` que la preuve indique `revoked`.

Le désépinglage Pinata retire les fichiers du compte et de sa gateway, mais ne garantit pas l'effacement des copies conservées par d'autres nœuds IPFS.

Le certificat et la clé présents dans `tests/fixtures/c2pa` sont des données publiques de démonstration. Avant un déploiement de production, les remplacer par un certificat C2PA de confiance et une clé privée protégée hors du système de fichiers applicatif.
