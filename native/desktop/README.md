# LedgerFlow — utilisation du Mac et de l’iPhone

Ouvrir `native/macos/build/LedgerFlow.app`. Le Mac démarre son moteur, retrouve ses dossiers et ouvre l’agent automatiquement. Au premier lancement, donnez un nom à l’agent et créez son espace local. Après le sélecteur de classeurs, le guide présente la lecture, la vérification et l’approbation d’une pièce. L’association iPhone est la dernière étape et peut être passée. La configuration reprend à l’étape enregistrée. Pour revoir le guide, choisissez **Account & settings → Open setup walkthrough**. Aucune adresse de serveur ni invitation de démonstration à saisir.

## Le principe

Le Mac conserve le dossier : classeurs Excel, photos, propositions, versions validées et conversation. L’agent répond à partir de ce dossier. Pour traiter une pièce, il lit l’image avec le modèle de vision Vultr configuré, prépare l’écriture, génère un programme exécuté dans Docker et fait vérifier les modifications par le vérificateur indépendant. L’utilisateur examine le document et le diff avant d’approuver. Une réponse dans la conversation n’approuve jamais une écriture.

1. Dans la configuration initiale ou dans **Workbooks**, choisissez un fichier Excel sur le Mac ou déposez-le dans la zone d’import. Examinez la structure et confirmez le mapping.
2. Choisissez **Add receipt** pour importer un JPEG, un PNG ou un PDF d’une page de 10 Mo maximum. Le Mac conserve le PDF original et produit une image pour la lecture. L’iPhone peut aussi envoyer une photo.
3. Suivez les étapes de lecture. Si un champ important est incertain, le modèle relit la pièce une fois en ciblant ce champ. Les valeurs encore absentes ou contradictoires sont laissées à vérifier.
4. Ouvrir la pièce dans **Receipts** et utiliser les filtres pour retrouver l’historique ou les validations en attente, contrôler les écritures et les cellules proposées, puis approuver explicitement.
5. Télécharger la nouvelle version du classeur. **Workbook checks** affiche la structure, le mapping, les soldes et l’intégrité de la version. **Expenses** reprend les mêmes justificatifs que l’iPhone, avec les totaux par semaine ou par mois, une répartition par catégorie et un graphique d’évolution. **Demo expenses** affiche uniquement des exemples synthétiques pour le walkthrough.

Le moteur comptable actuel applique les règles et formats déjà présents dans ce projet, notamment le classeur en comptes en T et la politique Nordvik. Ce n’est pas une promesse de compatibilité avec tout fichier comptable ni toutes les juridictions.

## Associer l’iPhone

Dans la configuration initiale ou dans **Account & settings → iPhone**, cliquez sur **Connect iPhone**. Sur l’iPhone, choisissez **Connect to your Mac** et scannez le code.

Le code associe le téléphone à l’identité TLS exacte du Mac. Il expire après deux minutes, s’utilise une seule fois et se révoque si la fenêtre d’association est fermée avant son utilisation. Le code relie votre iPhone personnel à l’espace complet, avec l’agent, les justificatifs et les dépenses.

Les appareils doivent être sur le même réseau. Laissez **LedgerFlow actif et le Mac éveillé**. Fermer seulement la fenêtre garde le moteur actif ; cliquer à nouveau sur l’application ou choisir Présentation → Afficher l’espace la rouvre. Quitter LedgerFlow arrête le moteur. Le téléphone garde les nouveaux reçus en attente lorsque le Mac est indisponible. Un changement d’adresse sur le réseau ou l’expiration de la session peut nécessiter une nouvelle association.

Le projet iOS à ouvrir dans Xcode est `native/ios/LedgerFlow.xcodeproj`. Les sources incluent le scanner QR VisionKit, le lien d’association, l’identité TLS, la navigation partagée et le partage des classeurs. Le build signé pour la destination iPhone connectée a réussi dans Xcode 27.2 bêta, présent dans Téléchargements. La caméra et l’association sur un vrai iPhone ne sont pas confirmées par cette compilation. Une seconde session HTTP et un viewport mobile ont aussi été testés ; ils ne remplacent pas ces essais physiques.

## Ce qui reste installé sur le Mac

Cette version locale dépend du projet et de son environnement Python. Conserver le dossier du projet à sa place. Les dossiers sont enregistrés dans `.ledgerflow-local/workspace.sqlite3`, avec des permissions privées. La clé d’inférence reste dans la configuration locale `.env`, jamais dans le QR, le classeur ou le programme isolé. Ne pas partager `.ledgerflow-local` ni `.env`.

Docker Desktop et l’image `python:3.12-slim` servent à exécuter les programmes comptables. Réglages → **Connexion du modèle** montre l’état réel et propose une aide de configuration. Si une session est fermée ou expirée, relancer l’application Mac ; sur l’iPhone, associer de nouveau le Mac. Les dossiers ne sont pas effacés.

Pour reconstruire après une modification du code, depuis la racine du projet :

```sh
UV_CACHE_DIR=/tmp/ledgerflow-uv-cache uv sync --extra dev
npm --prefix frontend ci
npm --prefix frontend run build
python3 native/macos/build.py
```

L’application est signée localement, sans notarisation ni installation App Store. Le paramètre optionnel `--url https://HOTE-REEL` configure un service distant existant ; il ne déploie pas un backend.

## Preuves de vérification

Les rapports et captures sont dans `artifacts/agent-runtime`, sur le stockage local sous Coding.

- `live-verification.json` : nouveau JPEG synthétique lu par le vrai modèle Qwen configuré sur Vultr ; code généré exécuté dans Docker ; vérification indépendante ; refus des approbations sans droit ou avec hash modifié ; XLSX équilibré téléchargé et hash vérifié ; conversation commune ; état conservé après redémarrage. Sept contrôles passent.
- `browser-verification.json` : connexion automatique, vraie réponse du modèle, QR réel, formats 1512/1280/393 px, capture directe sur téléphone, réglages locaux et apparence sombre. Sept contrôles passent, aucune erreur JavaScript non capturée.
- Sept tests spécifiques couvrent origine/Host/CSRF, bootstrap unique, droits de capture, réutilisation/révocation/expiration des QR, sauvegarde binaire et refus d’une base corrompue.
- Quinze tests frontend et onze parcours navigateur existants passent. Soixante tests comptables, de référence API et de sandbox passent ; dix-huit tests du squelette PostgreSQL sont ignorés en l’absence de base de test. Le moteur local utilise SQLite, pas ce squelette de déploiement.
- Vingt-cinq contrôles Swift portables, les références Xcode, les assets et les Info.plist passent. Le Mac compile ; fermeture/réouverture de fenêtre et maintien du service ont été vérifiés directement. Le build iOS pour la destination iPhone, la signature et la validation ont réussi dans Xcode avec SDK iOS 27.2 ; onze cas de test passent aussi sur simulateur iPhone 17. La caméra et l’association physique ne sont pas encore confirmées.

Commandes de reproduction, depuis la racine :

```sh
.venv/bin/python native/desktop/verify_live.py
.venv/bin/python -m pytest native/desktop/test_local_runtime.py -q
npm --prefix frontend run test:agent
python3 native/ios/scripts/validate_project.py
```

`verify_live.py` et `test:agent` utilisent le vrai modèle et nécessitent la configuration Vultr déjà renseignée. Les documents des tests sont synthétiques ; le document SSE original n’est pas utilisé par ces scénarios.
