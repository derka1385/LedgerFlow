---
name: LedgerFlow
description: The cell is the brand. Every screen shows which cells a receipt will change and whether they are verified.
colors:
  forest: "#0B5A45"
  forest-hover: "#084839"
  forest-wash: "#E2EFE8"
  mint: "#8FE3B8"
  mint-tint: "#BFEBD3"
  deep: "#06291F"
  canvas: "#F2F5F3"
  panel: "#E9EEEA"
  sheet: "#FFFFFF"
  grid: "#DCE2DC"
  grid-strong: "#B5C0B8"
  ink: "#121614"
  ink-secondary: "#47514B"
  ink-muted: "#5F6A64"
  ink-faint: "#8C968F"
  amber: "#8F5E07"
  amber-wash: "#F6EDD6"
  error: "#B42318"
  night: "#0C1210"
  dark-sheet: "#16201B"
  dark-grid: "#24302A"
  dark-ink: "#EEF3EF"
  dark-amber: "#E5C27A"
typography:
  display:
    fontFamily: "Schibsted Grotesk Variable, Schibsted Grotesk, -apple-system, system-ui, sans-serif"
    fontSize: "clamp(44px, 6.3vw, 86px)"
    fontWeight: 760
    lineHeight: 0.96
    letterSpacing: "-0.045em"
  headline:
    fontFamily: "Schibsted Grotesk Variable, Schibsted Grotesk, -apple-system, system-ui, sans-serif"
    fontSize: "clamp(34px, 4.4vw, 58px)"
    fontWeight: 740
    lineHeight: 1
    letterSpacing: "-0.04em"
  title:
    fontFamily: "Schibsted Grotesk Variable, Schibsted Grotesk, -apple-system, system-ui, sans-serif"
    fontSize: "clamp(26px, 3.4vw, 40px)"
    fontWeight: 700
    lineHeight: 1.04
    letterSpacing: "-0.035em"
  body:
    fontFamily: "-apple-system, BlinkMacSystemFont, Segoe UI, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.5
  body-large:
    fontFamily: "-apple-system, BlinkMacSystemFont, Segoe UI, system-ui, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: "-apple-system, BlinkMacSystemFont, Segoe UI, system-ui, sans-serif"
    fontSize: "12px"
    fontWeight: 600
    lineHeight: 1.2
  data:
    fontFamily: "Martian Mono, ui-monospace, SF Mono, Menlo, monospace"
    fontSize: "12.5px"
    fontWeight: 400
    lineHeight: 1.4
    fontFeature: "tnum"
  data-strong:
    fontFamily: "Martian Mono, ui-monospace, SF Mono, Menlo, monospace"
    fontSize: "11px"
    fontWeight: 600
    lineHeight: 1
    fontFeature: "tnum"
rounded:
  handle: "1px"
  frame: "3px"
  control: "6px"
  button: "8px"
  sheet: "10px"
  stage: "14px"
spacing:
  xs: "6px"
  sm: "12px"
  md: "18px"
  lg: "40px"
  section: "112px"
components:
  button-primary:
    backgroundColor: "{colors.forest}"
    textColor: "{colors.sheet}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "8px 12px"
    height: "34px"
  button-primary-hover:
    backgroundColor: "{colors.forest-hover}"
  button-secondary:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "8px 12px"
    height: "34px"
  button-ghost:
    textColor: "{colors.ink-secondary}"
    rounded: "{rounded.control}"
    padding: "8px 12px"
  button-landing-mint:
    backgroundColor: "{colors.mint}"
    textColor: "{colors.deep}"
    rounded: "{rounded.button}"
    padding: "13px 18px"
  language-switch-active:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.canvas}"
    typography: "{typography.data-strong}"
    rounded: "{rounded.control}"
    padding: "7px 8px"
  sheet:
    backgroundColor: "{colors.sheet}"
    rounded: "{rounded.sheet}"
  sheet-header:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ink-muted}"
    typography: "{typography.data-strong}"
  cell-unverified:
    textColor: "{colors.ink-faint}"
    typography: "{typography.data}"
  cell-verified:
    textColor: "{colors.ink}"
    typography: "{typography.data}"
  cell-proposed:
    backgroundColor: "{colors.forest-wash}"
    typography: "{typography.data}"
  shutter:
    backgroundColor: "{colors.forest}"
    textColor: "{colors.sheet}"
    size: "76px"
---

# Design System: LedgerFlow

## Overview

**Creative North Star: "The Ledger Grid"**

LedgerFlow speaks in cell addresses and selection rectangles. A white sheet with hairline rules sits on a cool grey-green canvas; the forest selection rectangle with its square fill handle marks what a receipt will change. Values arrive grey while unverified and turn ink-black once the verifier has re-read the real file. The world is a spreadsheet seen up close, not a fintech dashboard: no soft KPI cards, no big floating numbers, no gradients.

Density is close to a working spreadsheet: 46px rows, column letters and row numbers on a pale header rail, tabular numerals. Display type is a tight, heavy grotesk that sits on top of that grid; everything else is plain system UI so the data layer stays the loudest thing on screen. The landing drenches its hero and download sections in deep forest with mint accents; the product stays on the light canvas, with a full dark mode in which mint becomes the selection colour.

Motion follows one grammar on every surface: select, write, verify. The rectangle glides to the target cells, values type in grey, then ink in black. Every looping sequence has a pause control, and reduced motion settles on a still, final state.

**Key Characteristics:**
- One device: a selection rectangle (2px forest stroke, 3px corners) with a square fill handle at its bottom-right corner.
- Grey means unverified, ink means verified, and colour state follows real run state only.
- Visible hairline grids, column letters, row numbers, tabular numerals.
- Schibsted Grotesk for display, system UI for text, Martian Mono only for data.
- Flat sheets. Shadows appear only under paper (receipts) and the lifted, selected item.
- EN, FR and SV on every surface, switched by a three-code segmented control.

## Colors

A restrained grey-green sheet palette with a single forest accent, a mint counterpart for dark ground, and amber reserved for holds.

### Primary
- **Ledger Forest** (forest): the selection colour. Selection frames and handles, the active nav cell, primary buttons, the shutter, focus rings, progress bars, the "to approve" status and the app icon tile. Hover deepens to Forest Hover; proposed cells sit on Forest Wash.
- **Fill-Handle Mint** (mint): the selection colour on dark ground. The fill handle on the brand mark, the landing's primary CTA on deep forest, focus rings on the landing, and the accent in app dark mode. Mint Tint is the F of the monogram.

### Secondary
- **Hold Amber** (amber, with amber-wash and dark-amber): only for runs held for review, needing a detail, or a stale base. Never decorative.

### Neutral
- **Cool Canvas** (canvas): the page ground behind every sheet.
- **Sheet White** (sheet): the sheet itself, cards, inputs, secondary buttons.
- **Header Rail** (panel): column-letter and row-number rails, sidebars.
- **Hairline Grid** (grid): every cell rule and divider; Grid Strong outlines sheets and controls.
- **Verified Ink** (ink): verified values, headings, the "booked" status, the active language code.
- **Ink Secondary / Ink Muted**: body copy and quiet labels, in that order.
- **Unverified Grey** (ink-faint): values that are written but not yet verified, and pending rows. Not a body text colour.
- **Deep Forest** (deep): landing hero, nav and download drench. Night (night) is the code log, landing footer and dark-mode canvas.
- **Error Red** (error): failed, rejected, expired and cancelled runs only.

### Named Rules
**The Grey Is A State Rule.** Grey (ink-faint) on a value means "written, not yet verified"; ink means "verified". The switch follows real state only. Never fake it for decoration or as a loading flourish.

**The One Accent Rule.** Forest (mint on dark) is the only accent. It marks selection, the primary action and progress. Amber and red are state colours, never accents.

## Typography

**Display Font:** Schibsted Grotesk Variable (self-hosted via @fontsource-variable/schibsted-grotesk; landing ships the same woff2 files), falling back to -apple-system, system-ui
**Body Font:** the system UI stack (-apple-system, BlinkMacSystemFont, Segoe UI, system-ui)
**Data Font:** Martian Mono 400 and 600 (self-hosted via @fontsource/martian-mono), falling back to ui-monospace, SF Mono, Menlo

**Character:** A heavy, tightly tracked newspaper grotesk for the statement, a neutral system face for reading and controls, and a wide, square-shouldered mono that makes every address and amount look like a cell value.

### Hierarchy
- **Display** (760, clamp 44 to 86px, 0.96, -0.045em): landing hero only, max 11ch.
- **Headline** (740, clamp 34 to 58px, 1, -0.04em): landing section headings, max 16ch.
- **Title** (700, clamp 26 to 40px, 1.04, -0.035em): explainer step headings, phone home greeting (clamp 26 to 34px), with balanced wrapping.
- **Body** (400, 14px, 1.5): app text. Body Large (16 to 17px, 1.55) on the landing and explainer copy, held to 38 to 46ch.
- **Label** (600, 12 to 13px): status words, captions, table heads, the shutter label. Sentence case, no tracking.
- **Data** (Martian Mono, 11 to 13px, tabular numerals): cell addresses, amounts, dates, hashes, check identifiers, column letters, row numbers, step ordinals 01 to 04 and the EN/FR/SV codes.

### Named Rules
**The Mono Is Data Rule.** Martian Mono sets only what would sit in a cell or a log: addresses, amounts, dates, hashes, identifiers, ordinals and language codes. Labels, buttons, captions and table headings are set in the system face. The landing's own review pass moved its captions, pause control and table heads off mono for this reason.

**The No Eyebrow Rule.** No small uppercase or tracked label above a heading. A step number sits on the heading line, inline, at half size.

**The 11px Floor Rule.** No rendered text below 11px (11pt native). Data that needs to be small is set at 11px with tabular numerals, not shrunk further.

## Layout

The product is built from sheets. A sheet is a white grid with a 24 to 34px row-number column, a pale header rail of column letters, and 46px rows (34px for header and filler rows) separated by 1px grid rules. On the phone home, a five-column live sheet (row number, name, date, SEK, status) fills the upper half, followed by a tally line, the "How it works" link and a round shutter fixed bottom-centre above the tab bar (78px plus the safe-area inset). From 761px the shutter returns to the flow.

The explainer is a four-row grid (head, numbered progress, stage, foot) up to 980px wide; the stage splits 1.15fr scene to 1fr copy with a 40px gap and stacks below 760px. Scenes carry their own 34 by 26px hairline grid background.

The landing runs a 1180px wrap with 24px minimum gutters and 112px section padding (80px below 900px). The "How it works" section pairs a step rail with a sticky stage sheet; below 900px the stage sticks on top and steps follow. Gaps step 6, 12, 18, 22 and 40px; section rhythm is 112px.

## Elevation & Depth

Flat by default. Depth comes from tonal layers (canvas, rail, sheet) and hairlines, not shadow. Shadows are reserved for two cases: physical paper (the receipt, which casts a long soft drop) and lift on selection or the primary action.

### Shadow Vocabulary
- **Paper drop** (`box-shadow: 0 24px 40px -22px rgba(0,0,0,.6)`): receipts lying on the sheet.
- **Selected lift** (`box-shadow: inset 0 0 0 1.5px var(--accent), 0 10px 22px -16px rgba(10,40,30,.45)`): the run under review, raised 1px while the rest of the queue dims to 62%.
- **Primary press** (`box-shadow: 0 1px 0 rgba(0,0,0,.06), 0 6px 14px -10px color-mix(in srgb, var(--accent) 70%, transparent)`): primary buttons.
- **Shutter** (`box-shadow: 0 12px 28px -14px rgba(10,40,30,.55)`): the camera button.
- **Hero sheet** (`box-shadow: 0 40px 80px -40px rgba(0,0,0,.6)`): the landing sheet on deep forest.

### Named Rules
**The Paper Casts, Sheets Don't Rule.** Only receipts, the selected item, the shutter and the primary action may cast a shadow. Sheets, panels and cards stay flat on hairlines.

## Shapes

Square and spreadsheet-true. The selection frame has 3px corners, the fill handle 1px, status squares 1px (8 by 8px squares, not dots). Controls are 6px, landing buttons 8px, sheets 10px, explainer scenes and download cards 14px. Round forms are reserved for the camera: the shutter lens (76px circle with a 62px forest core) and the viewfinder ring. Receipts are the only irregular silhouette, with a zigzag tear edge cut by a CSS mask.

The brand mark is the LF monogram as a selected cell: a forest tile (12/64 corner radius) with a white L, a Mint Tint F, and a mint fill handle ringed in the ground colour at the bottom-right. The wordmark is a fixed SVG path in currentColor and is never re-set in a live font. The app icon (native/assets/generate_identity.py) is the same monogram on a forest field with a faint 8 by 8 grid and a mint selection rectangle around the letters.

## Components

### Selection Frame (signature)
- **Shape:** 2px forest stroke, 3px corners, inset -1px over its cells; a fill handle 8px square (10px on the landing) at bottom-right, -5px offset, forest with a 2px ring in the sheet colour.
- **Uses:** the newest row on the phone home, the changed range in Review, the travelling highlight in the explainer, the landing stage, the active sidebar item (inset 1.5px ring plus a 7px handle).
- **Range rule:** in Review, one frame is measured around the bounding box of all changed cells in a T-account group (SelectedRange), recomputed on resize. One rectangle per selected range, never one per cell.
- **Motion:** enters with lf-select; on the landing it glides between ranges with the selection easing.

### Buttons
- **Shape:** 6px corners in the app (8px on the landing), 34px minimum height on desktop, 44px on phones.
- **Primary:** forest fill, white text, primary press shadow; hover to Forest Hover; press translates 1px down.
- **Secondary:** outlined, sheet fill, 1px Grid Strong border. Secondary actions are always outlined.
- **Ghost:** no border, Ink Secondary text; used for Skip and the pause toggle.
- **Landing:** mint fill with deep text on deep forest, forest fill on light, outlined (on-deep at 45%) for the second action.

### Language Switch
- **Style:** a 1px Grid Strong outlined group, 6px corners, 2px inner padding; three codes EN, FR, SV in Martian Mono 600 11 to 12px.
- **State:** the active code is ink-filled with canvas text (on the landing, on-deep fill with deep text); inactive codes are muted, hovering to ink.

### Live Sheet (phone home)
- **Structure:** header rail with column letters A to D, a head row, up to five real runs, filler rows to keep three visible.
- **State:** pending rows print name and amounts in Unverified Grey; approve and booked rows ink in with lf-ink. The newest row carries the selection frame.
- **Status:** an 8px square plus a word: forest "to approve", ink "booked", amber "held", red "failed"; reading and writing squares pulse.

### Shutter
- **Style:** 76px circle, 3px forest ring on canvas, 62px forest core with a 26px camera icon, label below at 12.5px 650. Press scales to 0.96 and the core to 0.92.

### Explainer
- **Structure:** four numbered steps (Snap, Read, Prove, Approve) with segmented progress bars, a scene, copy, a "sample values" note and a foot with pause, Back and Next.
- **Behaviour:** auto-advances every 5.2s and stops on step 04; arrows, swipe (48px threshold) and Escape work; the pause toggle freezes every scene animation in place.

### Inputs
- **Style:** sheet fill, 1px Grid Strong border, 6px corners, 40px minimum (44px on phones, 16px text to prevent zoom), forest caret.
- **Focus:** 2px forest outline, border turns forest.

### Navigation
- **Desktop sidebar:** the active destination is the selected cell (inset forest ring, sheet fill, fill handle, forest icon).
- **Phone:** a five-item bottom tab bar, active item in forest.
- **Landing:** sticky deep-forest bar at 92% with blur, links in on-deep secondary, language switch and mint CTA at the end; links hide below 900px.

### Native iOS
- **Grid colours** mirror forest, mint, grid, canvas, ink and faint exactly. BrandMarkView draws the monogram in a Canvas; the wordmark is the Wordmark image asset (SVG).
- **WelcomeView** runs GridStoryView through four phases every 3.4s with a spring (response 0.5, damping 0.86), with a 44pt pause button and 44pt step targets; with Reduce Motion it starts on the final phase, paused, without springs. Copy comes from the L10n table in EN, FR and SV.

## Do's and Don'ts

### Do:
- **Do** mark every changed range with exactly one selection rectangle and its fill handle (2px forest, 3px corners).
- **Do** print unverified values in ink-faint and switch them to ink only when the real run state is verified.
- **Do** set addresses, amounts, dates, hashes, identifiers, ordinals and language codes in Martian Mono with tabular numerals, and everything else in Schibsted Grotesk (headings) or the system face.
- **Do** keep every rendered text at 11px (11pt) or above.
- **Do** make every touch target at least 44 by 44pt on phones.
- **Do** give every looping or auto-advancing sequence a visible pause control, and settle reduced motion on a still final state.
- **Do** use SVG icons from the shared icon set (web) and SF Symbols (native).
- **Do** ship EN, FR and SV for every user-facing string.

### Don't:
- **Don't** add eyebrows or kickers: no small uppercase labels above headings.
- **Don't** use unicode glyphs (arrows, check marks, bullets, stars) as icons.
- **Don't** draw a frame per cell or stack several rectangles on one range.
- **Don't** use mono for labels, buttons, captions or prose.
- **Don't** build soft KPI cards or big floating metric numbers; show figures in a ledger or sheet.
- **Don't** add a second accent colour, or use amber or red decoratively.
- **Don't** put shadows on sheets, panels or cards.
- **Don't** animate progress or verification that is not happening; explainer figures are labelled as sample values.

## Limits

- The Mac shell chrome and the Mac icon output (macicon) were not captured or reviewed against this system.
- Review, Capture and Settings are only partly translated; parts of them are still English-only.
