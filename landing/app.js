// LedgerFlow landing: EN/FR/SV, the hero sheet loop, the scroll-driven steps, "Pause effects". No dependencies.
const T = {
  fr: {
    skip: "Aller au contenu", "nav.how": "Comment ça marche", "nav.proof": "Preuves", "nav.security": "Sécurité", "nav.download": "Télécharger",
    "cta.mac": "Télécharger pour Mac", "cta.how": "Voir comment ça marche",
    "hero.title": "Chaque reçu arrive dans les bonnes cellules. Avec la preuve.",
    "hero.lead": "LedgerFlow lit un reçu, l’écrit dans le classeur Excel que vous utilisez déjà, prouve la modification dans une sandbox et attend votre accord sur ce fichier exact.",
    "state.0": "Lecture du reçu", "state.1": "Écriture des cellules prévues", "state.2": "Vérifié · 21/21 contrôles", "state.3": "Validé · version 2", sample: "Montants d’exemple",
    "base.1": "Vultr Serverless Inference", "base.2": "Python dans une sandbox verrouillée", "base.3": "Vérificateur indépendant", "base.4": "Votre accord, lié à l’empreinte du fichier",
    "how.title": "Quatre étapes. Une vingtaine de secondes.", pause: "Mettre les effets en pause", play: "Relancer les effets",
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
    "dl.phone": "iPhone", "dl.p1": "Ouvrez LedgerFlow sur le Mac et choisissez « Scanner avec l’iPhone ».", "dl.p2": "Scannez le code avec l’app LedgerFlow pour iPhone (bêta, TestFlight prévu).", "dl.p3": "Photographiez vos reçus. Ils arrivent sur le Mac, dans les bonnes cellules.", "dl.ios": "App Store · prévu",
    foot: "Conçu à Stockholm pour le Vultr Agent Runtime Hackathon, 2026. Données de démonstration synthétiques uniquement.", top: "Haut de page",
  },
  sv: {
    skip: "Hoppa till innehållet", "nav.how": "Så fungerar det", "nav.proof": "Bevis", "nav.security": "Säkerhet", "nav.download": "Ladda ner",
    "cta.mac": "Ladda ner för Mac", "cta.how": "Se hur det fungerar",
    "hero.title": "Varje kvitto hamnar i rätt celler. Med bevis.",
    "hero.lead": "LedgerFlow läser ett kvitto, skriver in det i Excel-arbetsboken du redan använder, bevisar ändringen i en sandlåda och väntar på ditt godkännande av exakt den filen.",
    "state.0": "Läser kvittot", "state.1": "Skriver de planerade cellerna", "state.2": "Verifierad · 21/21 kontroller", "state.3": "Godkänd · version 2", sample: "Exempelbelopp",
    "base.1": "Vultr Serverless Inference", "base.2": "Python i en låst sandlåda", "base.3": "Oberoende kontroll", "base.4": "Ditt godkännande, bundet till filens hash",
    "how.title": "Fyra steg. Ungefär tjugo sekunder.", pause: "Pausa effekter", play: "Spela effekter",
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
    "dl.phone": "iPhone", "dl.p1": "Öppna LedgerFlow på Macen och välj ”Skanna med iPhone”.", "dl.p2": "Skanna koden med LedgerFlow-appen för iPhone (beta, TestFlight planerad).", "dl.p3": "Fota kvitton. De hamnar på Macen, i rätt celler.", "dl.ios": "App Store · planerad",
    foot: "Byggd i Stockholm för Vultr Agent Runtime Hackathon, 2026. Endast syntetisk demodata.", top: "Till toppen",
  },
};
const EN = {};
document.querySelectorAll("[data-i18n]").forEach(el => { EN[el.dataset.i18n] = el.textContent; });

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

// Hero loop: read → write → verify → approve
const hero = document.querySelector(".hero-sheet");
let heroStep = reduce ? 3 : 0;
hero?.setAttribute("data-step", String(heroStep));
setInterval(() => { if (paused || !hero) return; heroStep = (heroStep + 1) % 4; hero.setAttribute("data-step", String(heroStep)); }, 2600);

// Scroll-driven steps: the sticky sheet follows the step in view
const stage = document.querySelector(".stage-sheet");
const steps = [...document.querySelectorAll(".steps li")];
const io = new IntersectionObserver(entries => {
  entries.forEach(e => {
    if (!e.isIntersecting) return;
    steps.forEach(s => s.classList.toggle("on", s === e.target));
    stage?.setAttribute("data-step", e.target.dataset.step);
  });
}, { rootMargin: matchMedia("(max-width: 900px)").matches ? "-62% 0px -28% 0px" : "-45% 0px -45% 0px" });
steps.forEach(s => io.observe(s));
steps[0]?.classList.add("on");
