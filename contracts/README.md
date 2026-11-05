# Registre Prisme — procédure 100 % Remix

Ce dossier conserve uniquement une copie de référence du contrat à coller dans Remix. Il ne contient aucun outillage blockchain local, script de déploiement, dépendance JavaScript ou clé privée.

Le contrat à déployer est [`PrismeOpenImageRegistry.sol`](PrismeOpenImageRegistry.sol).
L'ancien [`PrismeImageRegistry.sol`](PrismeImageRegistry.sol) est conservé uniquement comme
historique du premier déploiement autorisé.

## 1. Préparer MetaMask et Base Sepolia

Ajouter le réseau suivant dans MetaMask si celui-ci n'est pas déjà disponible :

| Paramètre | Valeur |
| --- | --- |
| Nom du réseau | Base Sepolia |
| URL RPC | `https://sepolia.base.org` |
| Chain ID | `84532` |
| Symbole | `ETH` |
| Explorateur | `https://sepolia.basescan.org` |

Obtenir ensuite une petite quantité d'ETH de test depuis un faucet listé par Base : <https://docs.base.org/get-started/get-funds>.

Utiliser un portefeuille réservé au développement. Ne communiquer ni sa phrase de récupération ni sa clé privée.

## 2. Créer le contrat dans Remix

1. Ouvrir uniquement l'adresse officielle stable <https://app.remix.live>.
2. Créer un workspace vide.
3. Dans `contracts`, créer `PrismeOpenImageRegistry.sol`.
4. Copier exactement le contenu du fichier local du même nom.
5. Ouvrir le plugin **Solidity Compiler**.
6. Choisir un compilateur `0.8.24` ou plus récent appartenant à la branche `0.8.x`.
7. Activer l'optimisation avec `200` runs.
8. Compiler `PrismeOpenImageRegistry.sol` et vérifier l'absence d'erreur rouge.
9. Activer **Solidity Static Analysis** depuis le gestionnaire de plugins et analyser le contrat avant le déploiement.

Noter la version complète du compilateur affichée par Remix et conserver les réglages d'optimisation. Ils seront nécessaires pour vérifier le contrat sur BaseScan.

## 3. Tester dans Remix VM

Dans **Deploy & Run Transactions** :

1. Sélectionner un environnement `Remix VM`.
2. Sélectionner `PrismeOpenImageRegistry`.
3. Laisser `VALUE` à `0`, puis cliquer sur **Deploy**.
4. Déplier le contrat dans **Deployed Contracts**.
5. Vérifier que `registrationOpen` renvoie `true`.
6. Changer de compte dans la Remix VM : chaque compte doit pouvoir appeler `registerImage`.

Tester `registerImage` avec ces valeurs fictives :

| Champ | Valeur de test |
| --- | --- |
| `imageSha256` | `0x1111111111111111111111111111111111111111111111111111111111111111` |
| `perceptualHash` | `123456789` |
| `differenceHash` | `987654321` |
| `waveletHash` | `555555555` |
| `imageCid` | `bafybeiexempleimageprisme` |
| `metadataCid` | `bafybeiexemplemetadonneesprisme` |
| `metadataSha256` | `0x2222222222222222222222222222222222222222222222222222222222222222` |
| `mediaId` | `0x3333333333333333333333333333333333333333333333333333333333333333` |

Après confirmation :

- `totalRegistrations` doit valoir `1` ;
- `exists(imageSha256)` doit renvoyer `true` ;
- `isActive(imageSha256)` doit renvoyer `true` ;
- `getImage(imageSha256)` doit restituer les valeurs saisies ;
- un second appel identique à `registerImage` doit être refusé ;
- seul le compte ayant enregistré la preuve peut appeler `revokeImage` ;
- après `revokeImage(imageSha256)`, `isActive` doit renvoyer `false`.

## 4. Déployer sur Base Sepolia

1. Dans MetaMask, sélectionner **Base Sepolia** et le compte financé en ETH de test.
2. Dans Remix, ouvrir **Deploy & Run Transactions**.
3. Choisir **Browser Extension**, **Injected Provider** ou l'intitulé MetaMask proposé par la version de Remix.
4. Autoriser la connexion dans MetaMask.
5. Vérifier dans Remix que le réseau indiqué possède le chain ID `84532` et que l'adresse affichée est la bonne.
6. Sélectionner `PrismeOpenImageRegistry`.
7. Laisser `VALUE` à `0`. Le constructeur n'attend aucun argument.
8. Activer le plugin **Contract Verification** dans le gestionnaire de plugins.
9. Si l'option **Verify Contract on Explorers** est proposée, l'activer.
10. Cliquer sur **Deploy**, contrôler la demande MetaMask et confirmer.
11. Attendre que le contrat apparaisse dans **Deployed Contracts**.
12. Copier immédiatement son adresse et le hash de la transaction de déploiement.

Ne pas appeler `registerImage` sur Base Sepolia avec les données fictives du test Remix VM.
Les véritables données seront préparées par l'API, puis signées manuellement dans
MetaMask par chaque utilisateur.

## 5. Contrôler et vérifier le déploiement

1. Dans le plugin Remix **Contract Verification**, ouvrir l'onglet **Receipts** et contrôler le résultat de la vérification demandée pendant le déploiement.
2. Si elle n'a pas été lancée, ouvrir l'onglet **Verify**, sélectionner Base Sepolia, le contrat compilé et son adresse.
3. Choisir au minimum Sourcify. Pour Etherscan/BaseScan, ajouter si nécessaire une clé Etherscan dans les paramètres du plugin.
4. Conserver exactement la version du compilateur, l'EVM et l'optimisation `200` runs utilisés au déploiement. Le constructeur ne possède aucun argument.
5. Lancer la vérification depuis Remix et contrôler son reçu.
6. Ouvrir `https://sepolia.basescan.org/address/ADRESSE_DU_CONTRAT` pour vérifier la transaction et le bytecode publiquement.
7. Tester les lectures `registrationOpen` et `totalRegistrations` depuis **Deployed Contracts** dans Remix.

## 6. Relier le nouveau déploiement à Prisme

Après le déploiement, copier la nouvelle adresse du contrat puis configurer Render :

```env
PRISME_BASE_RPC_URL=https://sepolia.base.org
PRISME_BASE_CHAIN_ID=84532
PRISME_BASE_EXPLORER_URL=https://sepolia.basescan.org
PRISME_REGISTRY_CONTRACT_ADDRESS=0xNOUVELLE_ADRESSE
```

Il n'existe plus de variable `PRISME_REGISTRY_PRIVATE_KEY`. FastAPI ne signe et ne paie
aucune transaction : il construit le calldata, puis vérifie le reçu envoyé par MetaMask.
Chaque utilisateur doit disposer d'un peu d'ETH Base Sepolia.

Le premier contrat reste un déploiement historique et ne doit plus être configuré comme
registre actif :

| Information | Valeur |
| --- | --- |
| Réseau | Base Sepolia |
| Chain ID | `84532` |
| Ancien contrat | `0x12DD566159a151Ab14009BC5d7624519C60c3647` |
| Transaction | `0x3b9b7b4eea171537e9f6dffa3d40a4afcac1785dd3459dbde3eaff13025bbd48` |
| Ancien déployeur/propriétaire | `0x9f06FcF98fDB0B374E63FdE559590bF2CA472E81` |
| Bloc | `52962707` |
| Compilateur | `0.8.34+commit.80d5c536` |
| Optimisation | activée, `200` runs |

## 7. Limite du registre ouvert

Le premier portefeuille qui enregistre un SHA-256 en devient le publicateur on-chain. Un
tiers connaissant l'empreinte pourrait donc tenter de la réserver avant le média. Le prototype
affiche clairement le signataire et relie la preuve au compte média, mais un futur contrat de
production devrait ajouter des signatures de domaine, des engagements temporaires ou une
gouvernance contre ce risque de front-running.
