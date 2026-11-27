---
version: 1
slug: "frontend-src-app-tsx"
primary_target: "frontend/src/App.tsx"
related_targets: ["native/ios/LedgerFlow/LedgerFlowApp.swift","landing/index.html"]
---

# Surface brief: LedgerFlow app shell, iPhone home and onboarding, Mac workspace motion, landing

Scope: the shared web app (Mac shell and iPhone WKWebView), the native iOS first-run screens, and the public landing. Modes: Operate (app), Persuade (landing).
Audience: Swedish small-business owners and their accountants on a Mac; employees snapping receipts on an iPhone. Job: understand in seconds how a receipt becomes a verified, approved edit in their own Excel workbook, then do it.
Constraints: keep the LedgerFlow logo spirit (LF monogram, outlined wordmark; light changes allowed); Orvect ergonomics (numbered steps where the sequence matters, EN/FR/SV language switch, outlined secondary controls, honest states, pause-able motion); the agent answers in English, French or Swedish; no invented metrics or fake progress.

## Direction contract

THESIS: The cell is the brand. LedgerFlow speaks in cell addresses and selection rectangles; every screen shows which cells a receipt will change and whether they are verified. It refuses the fintech dashboard of soft cards and big KPI numbers.

OWN-WORLD: White sheet on a cool grey-green canvas, hairline grid #DCE2DC, ink #121614, forest #0B5A45 as the selection colour, mint #8FE3B8 on dark, amber #B7790F for holds. The selection rectangle with its square fill handle is the one device: logo, focus, active nav, hover, the moving highlight. Unverified values print grey, verified values print black. Schibsted Grotesk for display, system UI for text, Martian Mono only for cell addresses, amounts and hashes.

STORY: The visitor sees a receipt land in a sheet, the exact cells light up, a program is checked, and a person signs the file. They believe nothing changes without proof and their approval, and they press "Scan a receipt" or "Download for Mac".

FIRST VIEWPORT: iPhone home: wordmark and language switch on top; a live mini-sheet (cells A–D, the last receipt's real rows) fills the top half with the selection rectangle on the newest row; a large shutter button sits bottom-centre above the tab bar; "How it works" opens the four-step animated explainer.

FORM: The Ledger Grid, position 1 on the ordered list; seed key 476e2525.

Signature interaction: select → write → verify. The selection rectangle glides to the target cells, values type in grey, and turn black once verified (real state only); reduced motion snaps.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
