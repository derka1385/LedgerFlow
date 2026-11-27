// LedgerFlow landing: EN/FR/SV, the hero sheet loop, the scroll-driven steps, "Pause effects". No dependencies.
const T = {
  fr: {
    "platform.macBadge": "LedgerFlow pour Mac",
    "platform.iosBadge": "LedgerFlow pour iPhone",
    "platform.walkthrough": "Voir le parcours",
    "platform.macRecording": "Capture de LedgerFlow",
    "platform.iosRecording": "App iPhone native · association",
    "platform.browserRecording": "Démo dans le navigateur mobile",
    "mac.headline": "Vos comptes.",
    "mac.headlineAccent": "Entre vos mains.",
    "mac.intro": "Consultez le reçu, interrogez l’agent et validez les cellules exactes du classeur Excel depuis le même espace.",
    "mac.storyTitle": "Voyez chaque étape",
    "mac.storyAccent": "avant l’écriture.",
    "mac.close": "Ouvrez l’espace dans votre navigateur.",
    "mac.closeBody": "Essayez le parcours du reçu au classeur avec des données d’exemple, sans code.",
    "iphone.headline": "De votre poche.",
    "iphone.headlineAccent": "À vos comptes.",
    "iphone.intro": "Photographiez le reçu pendant que vous l’avez en main, puis retrouvez-le dans le même espace que sur votre Mac.",
    "iphone.storyTitle": "Un reçu.",
    "iphone.storyAccent": "Trois étapes.",
    "iphone.close": "Essayez la capture dans votre navigateur.",
    "iphone.closeBody": "La démo guidée s’ouvre depuis n’importe quel téléphone. L’application web fonctionne aussi sur Android.",
    "cta.browserApp": "Ouvrir l’application web", "cta.demoCamera": "Tester la caméra du téléphone",
    "try.live": "La démo s’ouvre directement, sans code. Utilisez des données d’exemple dans cet espace partagé.",
    "nav.home": "Accueil",
    "nav.workflow": "Parcours",
    "shot.mac": "Espace LedgerFlow sur Mac",
    "shot.capture": "Aperçu du reçu · navigateur mobile",
    "shot.review": "Reçu et données extraites",
    "shot.monitor": "Moniteur d’exécution · démo enregistrée",
    "shot.approve": "Cellules modifiées avant validation",
    "product.macLink": "Découvrir l’app Mac",
    "product.iphoneLink": "Découvrir le parcours iPhone",
    "mac.title": "Votre espace comptable sur Mac",
    "mac.lead": "Connectez un classeur Excel, vérifiez les écritures proposées et validez les cellules exactes à modifier.",
    "mac.step1": "Connectez un classeur",
    "mac.detail1": "Importez le fichier Excel et confirmez la correspondance des comptes avant la première écriture.",
    "mac.step2": "Inspectez l’exécution",
    "mac.detail2": "Consultez le reçu et voyez ce que l’agent a exécuté dans la sandbox.",
    "mac.step3": "Validez les cellules",
    "mac.detail3": "Vérifiez les changements proposés et téléchargez le classeur vérifié après approbation.",
    "iphone.title": "Photographiez vos reçus sur iPhone",
    "iphone.lead": "Associez l’iPhone à LedgerFlow sur Mac, choisissez un classeur et envoyez le reçu vers votre espace.",
    "iphone.browser": "Les captures viennent de la démo dans le navigateur mobile. Le parcours guidé s’ouvre sans installation.",
    "iphone.step1": "Associez l’iPhone",
    "iphone.detail1": "Scannez le QR code affiché sur le Mac. Les deux appareils doivent être sur le même Wi-Fi.",
    "iphone.step2": "Photographiez le reçu",
    "iphone.detail2": "Vérifiez la lisibilité de la date, du fournisseur et du montant avant l’envoi.",
    "iphone.step3": "Suivez son traitement",
    "iphone.detail3": "Le reçu apparaît dans l’espace partagé. Suivez son état, puis validez l’écriture sur le Mac.",
    "cta.try": "Essayer la démo web",
    "try.title": "Essayez LedgerFlow sur votre téléphone",
    "try.lead": "Suivez un reçu d’exemple de la capture sur iPhone jusqu’au classeur Excel mis à jour. Ce parcours reprend une démo enregistrée, sans compte, téléchargement ni Xcode.",
    "try.capture": "Capture", "try.review": "Vérifier", "try.sent": "Envoyer", "try.committed": "Résultat Excel",
    "try.captureText": "Choisissez le classeur et photographiez un reçu.",
    "try.reviewText": "Vérifiez que le reçu est lisible avant de l’envoyer.",
    "try.sentText": "Le reçu arrive dans l’espace de travail et attend d’être traité.",
    "try.committedText": "Après validation sur le Mac, LedgerFlow enregistre une nouvelle version. Voici le fichier Excel produit pendant la démo.",
    "try.download": "Télécharger le classeur d’exemple",
    skip: "Aller au contenu", "nav.how": "Comment ça marche", "nav.proof": "Preuves", "nav.security": "Sécurité", "nav.download": "Télécharger",
    "cta.mac": "Télécharger pour Mac", "cta.how": "Voir comment ça marche",
    "hero.title": "Du reçu à l’écriture Excel vérifiée.",
    "hero.lead": "Photographiez ou importez un reçu depuis votre téléphone ou votre ordinateur. LedgerFlow vérifie les modifications dans un conteneur isolé, puis vous pouvez valider et télécharger le classeur mis à jour.",
    "state.0": "Lecture du reçu", "state.1": "Écriture des cellules prévues", "state.2": "Vérifié · 21/21 contrôles", "state.3": "Validé · version 2", sample: "Montants d’exemple",
    "base.1": "Vultr Serverless Inference", "base.2": "Python dans une sandbox verrouillée", "base.3": "Vérificateur indépendant", "base.4": "Votre accord, lié à l’empreinte du fichier",
    "how.title": "Suivez un reçu dans LedgerFlow.", pause: "Mettre les effets en pause", play: "Relancer les effets",
    "s1.t": "Photographiez le reçu", "s1.b": "Sur l’iPhone, ou déposez un PDF ou une photo sur le Mac. L’original est conservé, intact.",
    "s2.t": "Un modèle le lit, des règles décident", "s2.b": "Un modèle hébergé chez Vultr lit fournisseur, date, total et TVA. Ce sont les règles suédoises, pas le modèle, qui choisissent débit et crédit, et qui s’arrêtent quand le paiement ou la TVA ne sont pas prouvés.",
    "s3.t": "Le code écrit, la sandbox exécute, le vérificateur contrôle", "s3.b": "Le modèle écrit un petit programme Python pour les seules cellules prévues. Il tourne sans réseau dans un conteneur jetable. Un vérificateur sans IA relit le vrai fichier.",
    "s4.t": "Vous validez le fichier exact", "s4.b": "Chaque cellule modifiée est sous vos yeux. Votre accord est lié à l’empreinte de ce fichier. La version précédente reste intacte.",
    "l.supplier": "Fournisseur", "l.date": "Date", "l.total": "Total", "l.vat": "TVA 25 %", "l.entry": "Écriture", "l.approve": "Valider 8 cellules",
    "proof.title": "Mesuré, pas promis.", "proof.lead": "Résultats du 27 novembre 2026. Chaque ligne dit ce qui a été mesuré et comment. Reçus synthétiques, entreprises fictives.",
    "proof.h1": "Mesure", "proof.h2": "Résultat", "proof.h3": "Échantillon", "proof.h4": "Méthode",
    "proof.r1": "Résultat attendu atteint sur notre benchmark synthétique", "proof.r1s": "22 reçus", "proof.r2": "Faits critiques inventés par le modèle", "proof.r2s": "12 champs × 22 reçus",
    "proof.r3": "Programmes générés validés du premier coup", "proof.r3s": "11 plans", "proof.r4": "Validations de données conservées après écriture", "proof.r4s": "une sauvegarde openpyxl classique en garde 0/66",
    "proof.r5": "Tentatives d’évasion de la sandbox contenues", "proof.r5s": "réseau, fichiers, secrets, mémoire, temps, disque", "proof.r6": "Coût d’inférence par reçu", "proof.r6s": "moyenne par reçu, 22 reçus et 11 plans de code · tokens × prix catalogue",
    "proof.live": "Vultr en direct", "proof.det": "Déterministe", "proof.docker": "Docker local",
    "proof.fine": "22/22 est un taux de bons résultats sur un benchmark synthétique, pas une précision comptable générale. Un mauvais compte de charge pourtant autorisé ne peut pas être détecté par des règles : c’est pour cela que vous validez chaque écriture.",
    "sec.title": "Le code tourne là où il ne peut pas nuire.", "sec.b1": "Chaque programme écrit par le modèle tourne dans un conteneur neuf : pas de réseau, système en lecture seule, aucun secret, un CPU, 512 Mo, une échéance. Puis le conteneur est détruit.",
    "sec.b2": "Les instructions imprimées sur un reçu sont traitées comme des données. Le traitement est retenu pour un humain, et le texte du reçu n’atteint jamais le prompt de code.",
    "dl.title": "LedgerFlow vit sur votre Mac.", "dl.lead": "Le Mac fait tourner l’agent et garde votre classeur. Votre iPhone s’y associe pour capturer les reçus.",
    "dl.mac": "LedgerFlow pour Mac", "dl.macb": "Version bêta pour macOS. Non signée pendant la bêta : ouvrez-la avec clic droit, puis Ouvrir.", "dl.store": "Mac App Store · prévu",
    "dl.phone": "iPhone", "dl.p1": "Ouvrez LedgerFlow sur le Mac et choisissez « Scanner avec l’iPhone ».", "dl.p2": "Scannez le code avec l’app LedgerFlow pour iPhone (bêta, TestFlight prévu).", "dl.p3": "Photographiez vos reçus et vérifiez les modifications proposées sur le Mac.", "dl.ios": "App Store · prévu",
    foot: "Conçu à Stockholm pour le Vultr Agent Runtime Hackathon, 2026. Données de démonstration synthétiques uniquement.", top: "Haut de page",
  },
  sv: {
    "platform.macBadge": "LedgerFlow för Mac",
    "platform.iosBadge": "LedgerFlow för iPhone",
    "platform.walkthrough": "Se hur det fungerar",
    "platform.macRecording": "Inspelad LedgerFlow-vy",
    "platform.iosRecording": "iPhone-appen · parkoppling",
    "platform.browserRecording": "Demo i mobil webbläsare",
    "mac.headline": "Din bokföring.",
    "mac.headlineAccent": "I dina händer.",
    "mac.intro": "Se kvittot, fråga agenten och godkänn de exakta ändringarna i Excel från samma arbetsyta.",
    "mac.storyTitle": "Se varje steg",
    "mac.storyAccent": "innan något skrivs.",
    "mac.close": "Öppna arbetsytan i webbläsaren.",
    "mac.closeBody": "Prova hela flödet med exempeldata, utan inbjudningskod.",
    "iphone.headline": "Från fickan.",
    "iphone.headlineAccent": "Till bokföringen.",
    "iphone.intro": "Fota kvittot när du har det i handen och följ det i samma arbetsyta som på Macen.",
    "iphone.storyTitle": "Ett kvitto.",
    "iphone.storyAccent": "Tre enkla steg.",
    "iphone.close": "Prova kvittoflödet i webbläsaren.",
    "iphone.closeBody": "Öppna demon från valfri mobil. Webbappen fungerar även på Android.",
    "cta.browserApp": "Öppna webbappen", "cta.demoCamera": "Prova mobilkameran",
    "try.live": "Demon öppnas direkt utan kod. Använd exempeldata i den delade arbetsytan.",
    "nav.home": "Startsida",
    "nav.workflow": "Arbetsflöde",
    "shot.mac": "LedgerFlow på Mac",
    "shot.capture": "Förhandsvisning · mobil webbläsare",
    "shot.review": "Kvitto och avlästa uppgifter",
    "shot.monitor": "Körningslogg · inspelad demo",
    "shot.approve": "Celländringar före godkännande",
    "product.macLink": "Utforska Mac-appen",
    "product.iphoneLink": "Utforska iPhone-flödet",
    "mac.title": "Din bokföringsyta på Mac",
    "mac.lead": "Anslut en Excel-arbetsbok, granska föreslagna verifikationer och godkänn exakt vilka celler som skrivs.",
    "mac.step1": "Anslut arbetsboken",
    "mac.detail1": "Importera Excel-filen och bekräfta kontomappningen innan du bokför.",
    "mac.step2": "Granska körningen",
    "mac.detail2": "Läs kvittot och se vad agenten körde i sandlådan.",
    "mac.step3": "Godkänn cellerna",
    "mac.detail3": "Granska ändringarna och ladda ner den verifierade arbetsboken efter godkännande.",
    "iphone.title": "Fota kvitton med din iPhone",
    "iphone.lead": "Koppla din iPhone till LedgerFlow på Mac, välj arbetsbok och skicka kvittot till arbetsytan.",
    "iphone.browser": "Bilderna visar den inspelade demon i mobil webbläsare. Den guidade demon kräver ingen installation.",
    "iphone.step1": "Parkoppla en gång",
    "iphone.detail1": "Skanna QR-koden på Macen. Båda enheterna måste vara på samma Wi-Fi.",
    "iphone.step2": "Fota kvittot",
    "iphone.detail2": "Kontrollera att datum, leverantör och totalbelopp går att läsa innan du skickar.",
    "iphone.step3": "Följ behandlingen",
    "iphone.detail3": "Kvittot visas i den delade arbetsytan. Följ status och godkänn på Macen.",
    "cta.try": "Prova demon i webbläsaren",
    "try.title": "Prova LedgerFlow på mobilen",
    "try.lead": "Följ ett exempelkvitto från iPhone till den uppdaterade Excel-filen. Den interaktiva demon visar en inspelad körning utan konto, nedladdning eller Xcode.",
    "try.capture": "Fota", "try.review": "Granska", "try.sent": "Skicka", "try.committed": "Excel-resultat",
    "try.captureText": "Välj arbetsbok och fotografera ett kvitto.",
    "try.reviewText": "Kontrollera att kvittot är läsbart innan du skickar det.",
    "try.sentText": "Kvittot når arbetsytan och väntar på behandling.",
    "try.committedText": "Efter godkännandet på Macen sparar LedgerFlow en ny version. Här är Excel-filen från den inspelade demon.",
    "try.download": "Ladda ner exempelarbetsboken",
    skip: "Hoppa till innehållet", "nav.how": "Så fungerar det", "nav.proof": "Bevis", "nav.security": "Säkerhet", "nav.download": "Ladda ner",
    "cta.mac": "Ladda ner för Mac", "cta.how": "Se hur det fungerar",
    "hero.title": "Från kvitto till verifierad Excel-post.",
    "hero.lead": "Fota eller ladda upp ett kvitto från telefonen eller datorn. LedgerFlow kontrollerar ändringarna i en isolerad container. Sedan kan du godkänna och ladda ner den uppdaterade arbetsboken.",
    "state.0": "Läser kvittot", "state.1": "Skriver de planerade cellerna", "state.2": "Verifierad · 21/21 kontroller", "state.3": "Godkänd · version 2", sample: "Exempelbelopp",
    "base.1": "Vultr Serverless Inference", "base.2": "Python i en låst sandlåda", "base.3": "Oberoende kontroll", "base.4": "Ditt godkännande, bundet till filens hash",
    "how.title": "Följ ett kvitto genom LedgerFlow.", pause: "Pausa effekter", play: "Spela effekter",
    "s1.t": "Fota kvittot", "s1.b": "Med iPhone, eller släpp en PDF eller bild på Macen. Originalet sparas orört.",
    "s2.t": "En modell läser, regler bestämmer", "s2.b": "En modell hos Vultr läser leverantör, datum, belopp och moms. Svenska regler, inte modellen, väljer debet och kredit och stoppar när betalning eller moms inte är styrkt.",
    "s3.t": "Koden skriver, sandlådan kör, kontrollen granskar", "s3.b": "Modellen skriver ett litet Python-program för exakt de planerade cellerna. Det körs utan nätverk i en engångscontainer. En kontroll utan AI läser om den riktiga filen.",
    "s4.t": "Du godkänner exakt den filen", "s4.b": "Varje ändrad cell syns. Ditt godkännande är bundet till filens hash. Föregående version finns kvar.",
    "l.supplier": "Leverantör", "l.date": "Datum", "l.total": "Totalt", "l.vat": "Moms 25 %", "l.entry": "Verifikation", "l.approve": "Godkänn 8 celler",
    "proof.title": "Uppmätt, inte utlovat.", "proof.lead": "Resultat från 27 november 2026. Varje rad säger vad som mättes och hur. Syntetiska kvitton, fiktiva företag.",
    "proof.h1": "Mätning", "proof.h2": "Resultat", "proof.h3": "Urval", "proof.h4": "Metod",
    "proof.r1": "Förväntat utfall i vårt syntetiska test", "proof.r1s": "22 kvitton", "proof.r2": "Kritiska uppgifter som modellen hittat på", "proof.r2s": "12 fält × 22 kvitton",
    "proof.r3": "Genererade program godkända på första försöket", "proof.r3s": "11 planer", "proof.r4": "Datavalideringar kvar efter en skrivning", "proof.r4s": "en vanlig openpyxl-sparning behåller 0/66",
    "proof.r5": "Utbrytningsförsök ur sandlådan stoppade", "proof.r5s": "nätverk, filer, hemligheter, minne, tid, disk", "proof.r6": "Inferenskostnad per kvitto", "proof.r6s": "medel per kvitto, 22 kvitton och 11 kodplaner · tokens × listpris",
    "proof.live": "Vultr live", "proof.det": "Deterministisk", "proof.docker": "Lokal Docker",
    "proof.fine": "22/22 är andelen rätta utfall i ett syntetiskt test, inte allmän bokföringsprecision. Ett fel men tillåtet kostnadskonto kan inte fångas av regler: därför godkänner du varje verifikation.",
    "sec.title": "Koden körs där den inte kan göra skada.", "sec.b1": "Varje program som modellen skriver körs i en ny container: inget nätverk, skrivskyddat system, inga hemligheter, en CPU, 512 MB, en deadline. Sedan förstörs containern.",
    "sec.b2": "Instruktioner tryckta på ett kvitto behandlas som data. Ärendet stoppas för en människa, och kvittots text når aldrig kodprompten.",
    "dl.title": "LedgerFlow bor på din Mac.", "dl.lead": "Macen kör agenten och har din arbetsbok. Din iPhone kopplas till den för att fånga kvitton.",
    "dl.mac": "LedgerFlow för Mac", "dl.macb": "Betaversion för macOS. Osignerad under betan: öppna med högerklick och Öppna.", "dl.store": "Mac App Store · planerad",
    "dl.phone": "iPhone", "dl.p1": "Öppna LedgerFlow på Macen och välj ”Skanna med iPhone”.", "dl.p2": "Skanna koden med LedgerFlow-appen för iPhone (beta, TestFlight planerad).", "dl.p3": "Fota kvitton och granska de föreslagna ändringarna på Macen.", "dl.ios": "App Store · planerad",
    foot: "Byggd i Stockholm för Vultr Agent Runtime Hackathon, 2026. Endast syntetisk demodata.", top: "Till toppen",
  },
};
const EN = {};
document.querySelectorAll("[data-i18n]").forEach(el => { EN[el.dataset.i18n] = el.textContent; });
if (location.pathname.startsWith("/welcome/")) {
  document.querySelectorAll("[data-browser-app]").forEach(element => { element.hidden = false; });
}

const demoControls = document.querySelector(".try-controls");
if (demoControls) {
  const buttons = demoControls.querySelectorAll("[data-demo-step]");
  const panels = document.querySelectorAll("[data-demo-panel]");
  for (const button of buttons) {
    button.addEventListener("click", () => {
      for (const item of buttons) item.setAttribute("aria-pressed", String(item === button));
      for (const panel of panels) panel.hidden = panel.dataset.demoPanel !== button.dataset.demoStep;
    });
  }
  demoControls.hidden = false;
}

function setLang(lang) {
  const dict = lang === "en" ? EN : T[lang];
  document.querySelectorAll("[data-i18n]").forEach(el => { const v = dict[el.dataset.i18n] ?? EN[el.dataset.i18n]; if (v) el.textContent = v; });
  document.documentElement.lang = lang;
  document.querySelectorAll("[data-lang]").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.lang === lang)));
  try { localStorage.setItem("ledgerflow.lang", lang); } catch { /* fine */ }
}
const saved = (() => { try { return localStorage.getItem("ledgerflow.lang"); } catch { return null; } })();
const device = (navigator.languages || [navigator.language]).map(l => l.slice(0, 2)).find(l => ["en", "fr", "sv"].includes(l));
setLang(["en", "fr", "sv"].includes(saved) ? saved : device || "en");
document.querySelectorAll("[data-lang]").forEach(b => b.addEventListener("click", () => setLang(b.dataset.lang)));

// Pause effects (also honours reduced motion)
const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
let paused = reduce;
const pauseBtn = document.querySelector(".pause");
const applyPause = () => { document.documentElement.classList.toggle("paused", paused); pauseBtn?.setAttribute("aria-pressed", String(paused)); };
pauseBtn?.addEventListener("click", () => { paused = !paused; applyPause(); });
applyPause();

// Show the recorded screen that matches the current workflow step.
const workflow = document.querySelector(".how-stage");
if (workflow) {
  const steps = [...document.querySelectorAll(".steps li")];
  const screens = [...workflow.querySelectorAll("[data-workflow-panel]")];
  let frame = 0;
  let active = -1;

  function updateWorkflow() {
    frame = 0;
    const marker = matchMedia("(max-width: 900px)").matches
      ? Math.min(innerHeight * .72, workflow.getBoundingClientRect().bottom + 45)
      : innerHeight * .5;
    let next = 0;
    steps.forEach((step, index) => {
      if (step.getBoundingClientRect().top <= marker) next = index;
    });
    if (next === active) return;
    active = next;
    steps.forEach((step, index) => step.classList.toggle("on", index === active));
    screens.forEach((screen, index) => { screen.hidden = index !== active; });
  }

  function scheduleWorkflow() {
    if (!frame) frame = requestAnimationFrame(updateWorkflow);
  }

  workflow.dataset.interactive = "";
  updateWorkflow();
  addEventListener("scroll", scheduleWorkflow, { passive: true });
  addEventListener("resize", scheduleWorkflow);
}


// Unfold the paper toward the workbook as the visitor scrolls through the hero.
const receipt = document.querySelector(".hero-receipt-depth");
const receiptHero = receipt?.closest(".hero");
if (receipt && receiptHero && !reduce) {
  let pendingFrame = 0;
  const placeReceipt = () => {
    pendingFrame = 0;
    if (paused) return;
    const { top, height } = receiptHero.getBoundingClientRect();
    if (top > innerHeight || top + height < 0) return;
    const progress = Math.min(1, Math.max(0, -top / Math.max(height * .64, 1)));
    receipt.style.setProperty("--receipt-progress", progress.toFixed(3));
  };
  const scheduleReceipt = () => {
    if (!pendingFrame) pendingFrame = requestAnimationFrame(placeReceipt);
  };
  addEventListener("scroll", scheduleReceipt, { passive: true });
  addEventListener("resize", scheduleReceipt);
  pauseBtn?.addEventListener("click", scheduleReceipt);
  placeReceipt();
}

const platformSequence = document.querySelector(".platform-sequence");
if (platformSequence) {
  const beats = [...platformSequence.querySelectorAll("[data-platform-beat]")];
  const stage = platformSequence.querySelector(".platform-screen");
  const frames = beats.map(beat => beat.querySelector("[data-platform-frame]"));
  const art = document.querySelector(".platform-opening-art");
  const opening = art?.closest(".platform-opening");
  const desktop = matchMedia("(min-width: 901px)");
  let current = -1;
  let pending = 0;

  function updatePlatform() {
    pending = 0;
    if (!paused && art && opening) {
      const box = opening.getBoundingClientRect();
      const progress = Math.min(1, Math.max(0, -box.top / Math.max(1, box.height * .75)));
      art.style.setProperty("--paper-shift", progress.toFixed(3));
    }
    if (!platformSequence.hasAttribute("data-pinned")) return;
    const marker = innerHeight * .52;
    let next = 0;
    for (const [index, beat] of beats.entries()) {
      if (beat.getBoundingClientRect().top <= marker) next = index;
    }
    if (next === current) return;
    current = next;
    for (const [index, frame] of frames.entries()) {
      const active = index === current;
      frame.toggleAttribute("data-active", active);
      frame.setAttribute("aria-hidden", String(!active));
      beats[index].toggleAttribute("data-active", active);
    }
  }

  function schedulePlatform() {
    if (!pending) pending = requestAnimationFrame(updatePlatform);
  }

  function arrangePlatform() {
    const pinned = desktop.matches;
    platformSequence.toggleAttribute("data-pinned", pinned);
    stage.hidden = !pinned;
    frames.forEach((frame, index) => {
      frame.removeAttribute("aria-hidden");
      frame.removeAttribute("data-active");
      (pinned ? stage : beats[index]).append(frame);
    });
    if (pauseBtn) pauseBtn.hidden = !pinned || reduce;
    current = -1;
    updatePlatform();
  }
  desktop.addEventListener("change", arrangePlatform);
  addEventListener("scroll", schedulePlatform, { passive: true });
  addEventListener("resize", schedulePlatform);
  pauseBtn?.addEventListener("click", schedulePlatform);
  arrangePlatform();
}
