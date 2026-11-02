# Registre Prisme — procédure 100 % Remix

Ce dossier conserve uniquement une copie de référence du contrat à coller dans Remix. Il ne contient aucun outillage blockchain local, script de déploiement, dépendance JavaScript ou clé privée.

Le contrat à utiliser est [`PrismeImageRegistry.sol`](PrismeImageRegistry.sol).

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
3. Dans `contracts`, créer `PrismeImageRegistry.sol`.
4. Copier exactement le contenu du fichier local du même nom.
5. Ouvrir le plugin **Solidity Compiler**.
6. Choisir un compilateur `0.8.24` ou plus récent appartenant à la branche `0.8.x`.
7. Activer l'optimisation avec `200` runs.
8. Compiler `PrismeImageRegistry.sol` et vérifier l'absence d'erreur rouge.
9. Activer **Solidity Static Analysis** depuis le gestionnaire de plugins et analyser le contrat avant le déploiement.

Noter la version complète du compilateur affichée par Remix et conserver les réglages d'optimisation. Ils seront nécessaires pour vérifier le contrat sur BaseScan.

## 3. Tester dans Remix VM

Dans **Deploy & Run Transactions** :

1. Sélectionner un environnement `Remix VM`.
2. Sélectionner `PrismeImageRegistry`.
3. Laisser `VALUE` à `0`, puis cliquer sur **Deploy**.
4. Déplier le contrat dans **Deployed Contracts**.
5. Vérifier que `owner` correspond au compte Remix choisi.
6. Vérifier que `authorizedPublishers(owner)` renvoie `true`.

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
- après `revokeImage(imageSha256)`, `isActive` doit renvoyer `false`.

## 4. Déployer sur Base Sepolia

1. Dans MetaMask, sélectionner **Base Sepolia** et le compte financé en ETH de test.
2. Dans Remix, ouvrir **Deploy & Run Transactions**.
3. Choisir **Browser Extension**, **Injected Provider** ou l'intitulé MetaMask proposé par la version de Remix.
4. Autoriser la connexion dans MetaMask.
5. Vérifier dans Remix que le réseau indiqué possède le chain ID `84532` et que l'adresse affichée est la bonne.
6. Sélectionner `PrismeImageRegistry`.
7. Laisser `VALUE` à `0`. Le constructeur n'attend aucun argument.
8. Activer le plugin **Contract Verification** dans le gestionnaire de plugins.
9. Si l'option **Verify Contract on Explorers** est proposée, l'activer.
10. Cliquer sur **Deploy**, contrôler la demande MetaMask et confirmer.
11. Attendre que le contrat apparaisse dans **Deployed Contracts**.
12. Copier immédiatement son adresse et le hash de la transaction de déploiement.

Ne pas appeler `registerImage` sur Base Sepolia avec les données fictives du test Remix VM. Les véritables données seront enregistrées plus tard par l'API Prisme après l'intégration IPFS.

## 5. Contrôler et vérifier le déploiement

1. Dans le plugin Remix **Contract Verification**, ouvrir l'onglet **Receipts** et contrôler le résultat de la vérification demandée pendant le déploiement.
2. Si elle n'a pas été lancée, ouvrir l'onglet **Verify**, sélectionner Base Sepolia, le contrat compilé et son adresse.
3. Choisir au minimum Sourcify. Pour Etherscan/BaseScan, ajouter si nécessaire une clé Etherscan dans les paramètres du plugin.
4. Conserver exactement la version du compilateur, l'EVM et l'optimisation `200` runs utilisés au déploiement. Le constructeur ne possède aucun argument.
5. Lancer la vérification depuis Remix et contrôler son reçu.
6. Ouvrir `https://sepolia.basescan.org/address/ADRESSE_DU_CONTRAT` pour vérifier la transaction et le bytecode publiquement.
7. Tester les lectures `owner`, `totalRegistrations` et `authorizedPublishers` depuis **Deployed Contracts** dans Remix.

## 6. Déploiement retenu par Prisme

Le déploiement définitif de ce prototype est :

| Information | Valeur |
| --- | --- |
| Réseau | Base Sepolia |
| Chain ID | `84532` |
| Contrat | `0x12DD566159a151Ab14009BC5d7624519C60c3647` |
| Transaction | `0x3b9b7b4eea171537e9f6dffa3d40a4afcac1785dd3459dbde3eaff13025bbd48` |
| Déployeur/propriétaire | `0x9f06FcF98fDB0B374E63FdE559590bF2CA472E81` |
| Bloc | `52962707` |
| Compilateur | `0.8.34+commit.80d5c536` |
| Optimisation | activée, `200` runs |

FastAPI utilise le compte déployeur comme signataire, conformément au choix du prototype. Sa clé privée reste uniquement dans `services/api/.env` et ne doit jamais être placée dans Remix, Git, une capture ou une conversation. L'API vérifie avant publication que la clé correspond au propriétaire, que le Chain ID vaut `84532`, que le contrat possède du bytecode et que l'adresse est autorisée.
