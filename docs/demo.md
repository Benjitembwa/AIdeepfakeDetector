# Parcours de démonstration — étapes 1 à 9

## Démarrage

1. Exécuter `npm.cmd run api:dev` dans un terminal.
2. Exécuter `npm.cmd run dev` dans un second terminal.
3. Ouvrir `http://127.0.0.1:3000`.
4. Vérifier `http://127.0.0.1:8000/health/ready` : la réponse doit indiquer `database: connected`.

## Parcours visiteur

1. Sur l'accueil, cliquer sur **Essayer un exemple** : le rapport reste explicitement fictif.
2. Choisir ou glisser une image JPG, PNG ou WebP de moins de 10 Mo.
3. Vérifier son aperçu, ses dimensions et son nom.
4. Cliquer sur **Vérifier cette image** : le rapport affiche l'origine partenaire trouvée ou indique qu'aucune empreinte ne correspond.
5. Vérifier séparément la preuve Base Sepolia, les probabilités IA/deepfake et la provenance C2PA (`valid`, `valid_untrusted`, `invalid`, `absent` ou `unavailable`).
6. Essayer un fichier texte ou une image illisible : l'interface doit le refuser.

## Parcours média connecté

1. Ouvrir **Espace média**, cliquer sur **Connecter MetaMask** et accepter Base Sepolia.
2. Créer un compte média avec un mot de passe d'au moins 12 caractères.
3. Ajouter une image, son titre, le photographe, la licence et, si nécessaire, son URL et son contexte.
4. Confirmer les droits, cliquer sur **Préparer et signer avec MetaMask**, puis contrôler et confirmer la transaction MetaMask.
5. Vérifier le statut C2PA, les deux liens IPFS, la transaction BaseScan, le bloc, le contrat et le portefeuille signataire.
6. Si la transaction est partielle, utiliser **Réessayer l'enregistrement** : la reprise vérifie d'abord le reçu et le contrat.
7. Recharger la page : la session et les preuves PostgreSQL restent accessibles.
8. Rechercher le titre, ouvrir le détail et exporter le JSON.
9. Révoquer la preuve et confirmer la seconde transaction dans MetaMask : le désépinglage Pinata ne commence qu'après le reçu et la ligne PostgreSQL reste archivée.
10. Rappeler qu'un désépinglage n'efface pas les copies IPFS conservées ailleurs.
11. Se déconnecter et vérifier que l'espace média demande une nouvelle authentification.

## Démontrer la robustesse

1. Enregistrer une photo riche en détails depuis l'espace média.
2. Vérifier le même fichier sur l'accueil : le type doit être **Copie exacte**.
3. Recompresser la photo en JPEG ou la redimensionner, puis la vérifier : une similarité perceptuelle doit être proposée.
4. Recadrer une zone suffisamment détaillée et la vérifier : les caractéristiques locales peuvent retrouver l'origine.
5. Tester une image sans rapport : aucune correspondance ne doit être inventée.

## Documentation API

Ouvrir `http://127.0.0.1:8000/docs`. Le bouton **Authorize** accepte le jeton obtenu par la route `/api/v1/auth/token`.

Les comptes créés sont des comptes de prototype auto-inscrits. La validation d'un média par un administrateur sera ajoutée avant toute ouverture publique. Pour la validation réelle des étapes 6 et 7, conserver une image non sensible active et enregistrer puis révoquer une seconde image jetable. Le certificat C2PA du prototype doit apparaître valide mais non approuvé.
