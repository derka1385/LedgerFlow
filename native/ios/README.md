# LedgerFlow iOS

Projet iPhone/iPad, iOS 17 minimum, Swift 6. Le conteneur SwiftUI utilise l’interface métier partagée via WKWebView, un scanner QR VisionKit pour associer le Mac et la feuille système pour partager les classeurs. Aucun paquet tiers n’est nécessaire.

## Utilisation avec le Mac

1. Ouvrir `native/macos/build/LedgerFlow.app` sur le Mac. Il démarre son moteur et son espace automatiquement.
2. Choisir **Scan with iPhone** → **Afficher le code d’association**. Laisser LedgerFlow actif et le Mac éveillé.
3. Sur l’iPhone, ouvrir LedgerFlow → **Associer mon Mac**. Autoriser la caméra, puis scanner le code du Mac sur le même réseau Wi-Fi.
4. Le mode **Retrouver tout mon espace** donne accès à l’agent, aux dossiers et aux validations. **Scanner des pièces uniquement** ouvre la capture sans droit d’approbation.

L’adresse et l’identité TLS du Mac passent dans le QR ; aucune adresse n’est demandée dans le parcours normal. Le jeton expire en deux minutes, s’utilise une seule fois et n’est conservé ni dans les réglages ni dans l’URL de la conversation. L’origine et l’empreinte publique du certificat sont mémorisées sur l’appareil. La confiance est limitée à ce certificat exact et à son hôte, avec vérification du nom et de la validité du certificat ; aucune confiance générale ni exception globale TLS n’est ajoutée.

Les sources et photos restent dans le dossier du Mac. La vision utilise le service Vultr configuré sur le Mac ; les programmes comptables tournent dans Docker, avec contrôle indépendant et approbation humaine. Aucun moteur comptable n’est exécuté sur l’iPhone. Aucun relais public n’est déployé : le Mac doit rester accessible sur le réseau local.

Le collage d’un lien d’association et l’adresse d’un serveur HTTPS existant sont dans deux rubriques avancées. Le scanner QR est indisponible dans certains simulateurs ; le collage permet d’y tester l’association. L’option serveur distant nécessite un vrai service déjà déployé et son mode d’authentification ; elle ne crée pas de backend.

## Xcode et signature

Ouvrir :

```sh
open /Users/petrinolann/Coding/vultr/native/ios/LedgerFlow.xcodeproj
```

Le Xcode présent sur ce Mac est **Xcode 27.2 bêta**, dans `/Users/petrinolann/Downloads/Xcode-beta.app`. Le réglage global `xcode-select` pointait encore sur les Command Line Tools ; utiliser l’override ci-dessous en terminal sans modifier ce réglage système :

```sh
DEVELOPER_DIR=/Users/petrinolann/Downloads/Xcode-beta.app/Contents/Developer \
  xcodebuild -project native/ios/LedgerFlow.xcodeproj -scheme LedgerFlow \
  -configuration Debug -destination 'platform=iOS Simulator,name=iPhone 17' \
  -derivedDataPath native/ios/build CODE_SIGNING_ALLOWED=NO test
```

Dans Xcode, choisir le scheme LedgerFlow et l’appareil, puis Run. Conserver le Team déjà sélectionné par l’utilisateur. La compilation pour la destination iPhone connectée, la signature et la validation du binaire ont réussi dans Xcode le 27 novembre 2026 à 14:31, avec SDK iOS 27.2, sans erreur. Cela ne démontre pas encore la caméra, le scan du QR ni le parcours comptable sur un appareil physique. Aucun dépôt App Store n’est effectué.

Les fichiers du projet et son scheme partagé sont livrés directement ; aucune génération n’est nécessaire pour ouvrir Xcode. `scripts/generate_project.py` décrit leur création initiale : ne pas le relancer sans examiner les personnalisations faites depuis dans Xcode, notamment la signature. Les fichiers xcconfig n’embarquent aucune clé. En Debug sur simulateur, une origine loopback peut être définie pour le développement ; les appareils physiques et Release exigent HTTPS.

## Vérification et assets

```sh
python3 native/ios/scripts/validate_project.py
```

Vingt-cinq contrôles portables d’origine/association, les références du projet, les Info.plist et les 21 emplacements d’icône passent. La compilation native a aussi été observée dans Xcode ; cette commande portable seule ne la remplace pas. Les tests hébergés sur simulateur iPhone 17 / iOS 27.2 passent : cinq fonctions de test, onze cas exécutés avec leurs paramètres, aucun échec. Le résultat est dans `artifacts/agent-runtime/ios-tests.xcresult`.

L’icône LF vient de `native/assets/generate_identity.py`. Régénérer les assets avec `.venv/bin/python native/ios/scripts/generate_assets.py` après le générateur d’identité. Les PNG restent sous Coding, hors Documents iCloud.
