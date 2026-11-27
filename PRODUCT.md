# LedgerFlow

LedgerFlow is accounting software led by a Mac agent, with an iPhone able to access the same workspace and capture receipts. The confirmed goal is a premium interface that is easy to use while keeping the agent's technical work inspectable. The user explicitly rejected the previous basic, AI-looking design, the receipt tile icon and a server-address-first launch.

The local entry is LedgerFlow.app. It starts the local HTTPS service and opens an owner session through a single-use bootstrap. Closing the Mac window leaves the app and service running: the native lifecycle check observed a successful health response while closed, then reopening at the same origin and port with the conversation preserved. The implemented Mac shell depends on the repository and its Python environment remaining in place; delivery is not a standalone notarized installer.

The conversation is the local entry surface. It reads authoritative workspace facts and can offer navigation; a chat response cannot approve an accounting entry or execute an arbitrary tool. Receipt upload uses the real vision and accounting pipeline. Source documents, proposed entries, exact workbook changes, execution events and version history remain inspectable. Financial changes require the existing protected human approval tuple and independent verifier.

iPhone association starts with “Associer mon Mac” and the Mac's QR. The association carries the exact TLS certificate fingerprint and a single-use bearer in the URL fragment, expires after 120 seconds, and can grant full-workspace or capture-only access. Both devices need the same network and the Mac must stay on; no public relay is implemented. An associated phone has a direct capture path. Role restrictions continue to apply.

The visual system preserves the outlined LedgerFlow wordmark and replaces the receipt mark with a folded LF monogram. Warm paper, a quiet forest sidebar and system UI fonts are the implemented direction. No approved visual comp is recorded; see DESIGN.md for the actual tokens and component rules.

Evidence in `artifacts/agent-runtime/experience-spec.md` and its referenced verification files records real model vision, Docker execution, independent verification, protected approval, an exact XLSX hash, shared conversation and restart persistence. Interface evidence includes desktop, narrow desktop, light/dark and phone-sized browser views. Those phone views are browser tests, not physical-device evidence.

A native Xcode build for the connected iPhone destination succeeded, including compilation of the current association scanner and app entry, signing and validation (Xcode 27.2, iOS 27.2 SDK). Hosted tests on iPhone 17 Simulator passed all eleven parameterized cases. Launch of the latest binary on the connected device awaits unlocking the phone; physical QR scanning, native camera capture and end-to-end hardware behavior remain unverified. No public deployment or App Store distribution is claimed.
