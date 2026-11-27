// English, French and Swedish for the shell, the phone home, the explainer and the agent.
// Language = saved choice, else the device language, else English. No network, no library.
import { useEffect, useState } from "react";

export type Lang = "en" | "fr" | "sv";
export const LANGS: { id: Lang; label: string; short: string }[] = [
  { id: "en", label: "English", short: "EN" }, { id: "fr", label: "Français", short: "FR" }, { id: "sv", label: "Svenska", short: "SV" },
];
const KEY = "ledgerflow.lang";
const EVENT = "ledgerflow:lang";

export function detectLang(saved: string | null, device: readonly string[]): Lang {
  if (saved === "en" || saved === "fr" || saved === "sv") return saved;
  for (const tag of device) { const base = tag.toLowerCase().slice(0, 2); if (base === "fr" || base === "sv" || base === "en") return base; }
  return "en";
}

export function currentLang(): Lang {
  let saved: string | null = null;
  try { saved = localStorage.getItem(KEY); } catch { /* private mode: device language */ }
  return detectLang(saved, typeof navigator === "undefined" ? [] : navigator.languages ?? [navigator.language]);
}

export function setLang(lang: Lang) {
  try { localStorage.setItem(KEY, lang); } catch { /* still applies for this page */ }
  document.documentElement.lang = lang;
  window.dispatchEvent(new CustomEvent(EVENT, { detail: lang }));
}

export function useLang(): [Lang, (l: Lang) => void] {
  const [lang, update] = useState<Lang>(currentLang);
  useEffect(() => {
    document.documentElement.lang = lang;
    const on = (e: Event) => update((e as CustomEvent<Lang>).detail);
    window.addEventListener(EVENT, on); return () => window.removeEventListener(EVENT, on);
  }, [lang]);
  return [lang, setLang];
}

type Dict = Record<string, string>;
const en: Dict = {
  "home.date": "Date", "home.status": "Status",
  "agent.noModel": "Model not configured", "agent.explainPrompt": "Explain how you will work with my workbook and my photos.", "agent.attach": "Attach a document", "agent.enter": "Enter to send", "agent.phoneTitle": "Your iPhone, in the same place.", "agent.phoneBody": "Scan a document or reach the agent.", "agent.isolated": "Isolated execution", "agent.engine": "Engine and sync",
  "agent.explain": "Explain how this works", "agent.ready": "Ready for documents", "agent.checkConn": "Check the connection", "agent.reading": "Reading…", "agent.toReview": "Document to review", "agent.structure": "Structure to confirm", "agent.dockerReady": "Docker ready", "agent.dockerStart": "Start Docker", "agent.vision": "Vision connected", "agent.notConfigured": "Not configured", "agent.openFile": "Open the file", "agent.conversation": "Conversation with LedgerFlow", "agent.messageLabel": "Message to LedgerFlow",
  "how.l.supplier": "Supplier", "how.l.date": "Date", "how.l.total": "Total", "how.l.vat": "VAT 25 %", "how.l.paid": "Paid with", "how.l.card": "Card", "how.l.approve": "Approve 8 cells",
  "nav.agent": "Agent", "nav.overview": "Overview", "nav.transactions": "Transactions", "nav.receipts": "Receipts", "nav.workbook": "Excel Workbooks",
  "nav.activity": "Agent Activity", "nav.security": "Security", "nav.audit": "Audit History", "nav.settings": "Settings", "nav.home": "Home",
  "nav.capture": "Scan", "nav.expenses": "Expenses", "nav.requests": "Requests", "nav.profile": "Profile", "nav.files": "Files",
  "shell.workspace": "Workspace", "shell.scanIphone": "Scan with iPhone", "shell.account": "Account and preferences", "shell.language": "Language",
  "home.hello": "Your books, one receipt at a time.", "home.sub": "Photograph a receipt. LedgerFlow finds the exact cells, proves the change, and waits for your approval.",
  "home.scan": "Scan a receipt", "home.scanSub": "Camera or photo library", "home.how": "How it works", "home.howSub": "Four steps, about 20 seconds per receipt",
  "home.sheet": "Latest receipts", "home.sheetEmpty": "No receipt yet. Your first one appears here, row by row.",
  "home.toApprove": "to approve", "home.needInfo": "need a detail", "home.booked": "booked", "home.seeAll": "See all", "home.open": "Open",
  "state.reading": "Reading", "state.writing": "Writing", "state.verified": "Verified", "state.approve": "Awaiting you", "state.booked": "Booked", "state.held": "Held for review", "state.failed": "Stopped",
  "how.title": "How LedgerFlow works", "how.skip": "Skip", "how.next": "Next", "how.back": "Back", "how.done": "Start", "how.pause": "Pause animation", "how.play": "Play animation",
  "how.s1.t": "Snap the receipt", "how.s1.b": "Take a photo on your iPhone or drop a file on the Mac. The original is kept, untouched.",
  "how.s2.t": "LedgerFlow reads it", "how.s2.b": "A model on Vultr reads supplier, date, total and VAT. Our rules, not the model, decide debit and credit.",
  "how.s3.t": "Code writes, a sandbox runs, a verifier checks", "how.s3.b": "A small program edits only the planned cells in a locked sandbox. An independent verifier re-reads the real file.",
  "how.s4.t": "You approve the exact file", "how.s4.b": "You see every cell that changes. Your approval signs that file's hash; the previous version stays safe.",
  "how.demo": "Illustration with sample figures",
  "agent.title": "Your accounting agent", "agent.sub": "Documents, explanations, then your decision.", "agent.placeholder": "Ask a question or hand me a receipt…",
  "agent.send": "Send", "agent.note": "Entries always wait for your approval, cell by cell.", "agent.you": "You", "agent.thinking": "Reading your workspace…",
  "agent.welcomeReady": "What are we working on?", "agent.welcomeStart": "Let's start with your Excel.",
  "agent.welcomeReadyBody": "Your workbook is ready. Hand me an invoice or a receipt, or ask what is waiting for you.",
  "agent.welcomeStartBody": "Connect the workbook you already use. Then each receipt lands in the right cells, with proof.",
  "agent.dossier": "Your file", "agent.workbook": "Connected workbook", "agent.attention": "Needs your attention", "agent.recent": "Latest documents",
  "agent.a.capture": "Add a document", "agent.a.workbook": "Connect my Excel", "agent.a.transactions": "Review documents", "agent.a.activity": "See the agent's work",
  "agent.a.overview": "Open the files", "agent.a.phone": "Pair my iPhone",
};
const fr: Dict = {
  "home.date": "Date", "home.status": "Statut",
  "agent.noModel": "Modèle non configuré", "agent.explainPrompt": "Explique-moi comment tu vas travailler avec mon classeur et mes photos.", "agent.attach": "Joindre une pièce", "agent.enter": "Entrée pour envoyer", "agent.phoneTitle": "Votre iPhone, au même endroit.", "agent.phoneBody": "Scanner une pièce ou retrouver l’agent.", "agent.isolated": "Exécution isolée", "agent.engine": "Moteur et synchronisation",
  "agent.explain": "Explique-moi comment ça fonctionne", "agent.ready": "Prêt à recevoir des pièces", "agent.checkConn": "Connexion à vérifier", "agent.reading": "Lecture en cours…", "agent.toReview": "Pièce à examiner", "agent.structure": "Structure à confirmer", "agent.dockerReady": "Docker prêt", "agent.dockerStart": "Docker à démarrer", "agent.vision": "Vision connectée", "agent.notConfigured": "Non configurée", "agent.openFile": "Ouvrir le dossier", "agent.conversation": "Conversation avec LedgerFlow", "agent.messageLabel": "Message à LedgerFlow",
  "how.l.supplier": "Fournisseur", "how.l.date": "Date", "how.l.total": "Total", "how.l.vat": "TVA 25 %", "how.l.paid": "Payé par", "how.l.card": "Carte", "how.l.approve": "Valider 8 cellules",
  "nav.agent": "Agent", "nav.overview": "Vue d’ensemble", "nav.transactions": "Transactions", "nav.receipts": "Pièces", "nav.workbook": "Classeurs Excel",
  "nav.activity": "Travail de l’agent", "nav.security": "Sécurité", "nav.audit": "Historique", "nav.settings": "Réglages", "nav.home": "Accueil",
  "nav.capture": "Scanner", "nav.expenses": "Dépenses", "nav.requests": "Demandes", "nav.profile": "Profil", "nav.files": "Dossiers",
  "shell.workspace": "Espace de travail", "shell.scanIphone": "Scanner avec l’iPhone", "shell.account": "Compte et préférences", "shell.language": "Langue",
  "home.hello": "Votre compta, un reçu à la fois.", "home.sub": "Photographiez un reçu. LedgerFlow trouve les cellules exactes, prouve la modification et attend votre accord.",
  "home.scan": "Scanner un reçu", "home.scanSub": "Appareil photo ou photothèque", "home.how": "Comment ça marche", "home.howSub": "Quatre étapes, environ 20 secondes par reçu",
  "home.sheet": "Derniers reçus", "home.sheetEmpty": "Aucun reçu pour l’instant. Le premier apparaîtra ici, ligne par ligne.",
  "home.toApprove": "à valider", "home.needInfo": "à compléter", "home.booked": "comptabilisés", "home.seeAll": "Tout voir", "home.open": "Ouvrir",
  "state.reading": "Lecture", "state.writing": "Écriture", "state.verified": "Vérifié", "state.approve": "Attend votre accord", "state.booked": "Comptabilisé", "state.held": "Retenu pour revue", "state.failed": "Arrêté",
  "how.title": "Comment fonctionne LedgerFlow", "how.skip": "Passer", "how.next": "Suivant", "how.back": "Retour", "how.done": "Commencer", "how.pause": "Mettre l’animation en pause", "how.play": "Lancer l’animation",
  "how.s1.t": "Photographiez le reçu", "how.s1.b": "Une photo sur l’iPhone ou un fichier déposé sur le Mac. L’original est conservé, intact.",
  "how.s2.t": "LedgerFlow le lit", "how.s2.b": "Un modèle hébergé chez Vultr lit fournisseur, date, total et TVA. Ce sont nos règles, pas le modèle, qui décident du débit et du crédit.",
  "how.s3.t": "Le code écrit, la sandbox exécute, le vérificateur contrôle", "how.s3.b": "Un petit programme modifie seulement les cellules prévues, dans une sandbox verrouillée. Un vérificateur indépendant relit le vrai fichier.",
  "how.s4.t": "Vous validez le fichier exact", "how.s4.b": "Vous voyez chaque cellule modifiée. Votre accord signe l’empreinte de ce fichier ; la version précédente reste intacte.",
  "how.demo": "Illustration avec des montants d’exemple",
  "agent.title": "Votre agent comptable", "agent.sub": "Les pièces, les explications, puis votre décision.", "agent.placeholder": "Posez une question ou confiez-moi un reçu…",
  "agent.send": "Envoyer", "agent.note": "Les écritures attendent toujours votre accord, cellule par cellule.", "agent.you": "Vous", "agent.thinking": "Je consulte votre espace…",
  "agent.welcomeReady": "Sur quoi travaille-t-on ?", "agent.welcomeStart": "On commence par votre Excel.",
  "agent.welcomeReadyBody": "Votre classeur est prêt. Confiez-moi une facture ou un reçu, ou demandez ce qui vous attend.",
  "agent.welcomeStartBody": "Connectez le classeur que vous utilisez déjà. Ensuite, chaque reçu arrive dans les bonnes cellules, avec la preuve.",
  "agent.dossier": "Votre dossier", "agent.workbook": "Classeur connecté", "agent.attention": "À votre attention", "agent.recent": "Dernières pièces",
  "agent.a.capture": "Ajouter une pièce", "agent.a.workbook": "Connecter mon Excel", "agent.a.transactions": "Revoir les pièces", "agent.a.activity": "Voir le travail de l’agent",
  "agent.a.overview": "Ouvrir les dossiers", "agent.a.phone": "Associer mon iPhone",
};
const sv: Dict = {
  "home.date": "Datum", "home.status": "Status",
  "agent.noModel": "Ingen modell konfigurerad", "agent.explainPrompt": "Förklara hur du kommer att arbeta med min arbetsbok och mina bilder.", "agent.attach": "Bifoga underlag", "agent.enter": "Enter för att skicka", "agent.phoneTitle": "Din iPhone, på samma ställe.", "agent.phoneBody": "Skanna underlag eller nå agenten.", "agent.isolated": "Isolerad körning", "agent.engine": "Motor och synk",
  "agent.explain": "Förklara hur det fungerar", "agent.ready": "Redo för underlag", "agent.checkConn": "Kontrollera anslutningen", "agent.reading": "Läser…", "agent.toReview": "Underlag att granska", "agent.structure": "Struktur att bekräfta", "agent.dockerReady": "Docker redo", "agent.dockerStart": "Starta Docker", "agent.vision": "Vision ansluten", "agent.notConfigured": "Inte konfigurerad", "agent.openFile": "Öppna underlaget", "agent.conversation": "Konversation med LedgerFlow", "agent.messageLabel": "Meddelande till LedgerFlow",
  "how.l.supplier": "Leverantör", "how.l.date": "Datum", "how.l.total": "Totalt", "how.l.vat": "Moms 25 %", "how.l.paid": "Betalt med", "how.l.card": "Kort", "how.l.approve": "Godkänn 8 celler",
  "nav.agent": "Agent", "nav.overview": "Översikt", "nav.transactions": "Transaktioner", "nav.receipts": "Kvitton", "nav.workbook": "Excel-arbetsböcker",
  "nav.activity": "Agentens arbete", "nav.security": "Säkerhet", "nav.audit": "Historik", "nav.settings": "Inställningar", "nav.home": "Hem",
  "nav.capture": "Skanna", "nav.expenses": "Utlägg", "nav.requests": "Förfrågningar", "nav.profile": "Profil", "nav.files": "Underlag",
  "shell.workspace": "Arbetsyta", "shell.scanIphone": "Skanna med iPhone", "shell.account": "Konto och inställningar", "shell.language": "Språk",
  "home.hello": "Din bokföring, ett kvitto i taget.", "home.sub": "Fotografera ett kvitto. LedgerFlow hittar exakt rätt celler, visar beviset och väntar på ditt godkännande.",
  "home.scan": "Skanna ett kvitto", "home.scanSub": "Kamera eller bildbibliotek", "home.how": "Så fungerar det", "home.howSub": "Fyra steg, cirka 20 sekunder per kvitto",
  "home.sheet": "Senaste kvitton", "home.sheetEmpty": "Inga kvitton ännu. Det första dyker upp här, rad för rad.",
  "home.toApprove": "att godkänna", "home.needInfo": "behöver uppgift", "home.booked": "bokförda", "home.seeAll": "Visa alla", "home.open": "Öppna",
  "state.reading": "Läser", "state.writing": "Skriver", "state.verified": "Verifierad", "state.approve": "Väntar på dig", "state.booked": "Bokförd", "state.held": "Till granskning", "state.failed": "Stoppad",
  "how.title": "Så fungerar LedgerFlow", "how.skip": "Hoppa över", "how.next": "Nästa", "how.back": "Tillbaka", "how.done": "Börja", "how.pause": "Pausa animationen", "how.play": "Spela animationen",
  "how.s1.t": "Fota kvittot", "how.s1.b": "Ta en bild med iPhone eller släpp en fil på Macen. Originalet sparas orört.",
  "how.s2.t": "LedgerFlow läser det", "how.s2.b": "En modell hos Vultr läser leverantör, datum, belopp och moms. Våra regler, inte modellen, bestämmer debet och kredit.",
  "how.s3.t": "Koden skriver, sandlådan kör, kontrollen granskar", "how.s3.b": "Ett litet program ändrar bara de planerade cellerna i en låst sandlåda. En oberoende kontroll läser om den riktiga filen.",
  "how.s4.t": "Du godkänner exakt den filen", "how.s4.b": "Du ser varje cell som ändras. Ditt godkännande signerar filens hash; föregående version finns kvar.",
  "how.demo": "Illustration med exempelbelopp",
  "agent.title": "Din bokföringsagent", "agent.sub": "Underlag, förklaringar och sedan ditt beslut.", "agent.placeholder": "Ställ en fråga eller ge mig ett kvitto…",
  "agent.send": "Skicka", "agent.note": "Verifikationer väntar alltid på ditt godkännande, cell för cell.", "agent.you": "Du", "agent.thinking": "Jag läser din arbetsyta…",
  "agent.welcomeReady": "Vad ska vi jobba med?", "agent.welcomeStart": "Vi börjar med din Excel.",
  "agent.welcomeReadyBody": "Din arbetsbok är redo. Ge mig en faktura eller ett kvitto, eller fråga vad som väntar på dig.",
  "agent.welcomeStartBody": "Koppla arbetsboken du redan använder. Sedan hamnar varje kvitto i rätt celler, med bevis.",
  "agent.dossier": "Ditt underlag", "agent.workbook": "Kopplad arbetsbok", "agent.attention": "Behöver din uppmärksamhet", "agent.recent": "Senaste underlag",
  "agent.a.capture": "Lägg till underlag", "agent.a.workbook": "Koppla min Excel", "agent.a.transactions": "Granska underlag", "agent.a.activity": "Se agentens arbete",
  "agent.a.overview": "Öppna underlagen", "agent.a.phone": "Koppla min iPhone",
};
export const DICTS: Record<Lang, Dict> = { en, fr, sv };

export function translate(lang: Lang, key: string): string {
  return DICTS[lang][key] ?? en[key] ?? key;
}

export function useT(): [(key: string) => string, Lang, (l: Lang) => void] {
  const [lang, set] = useLang();
  return [(key: string) => translate(lang, key), lang, set];
}
