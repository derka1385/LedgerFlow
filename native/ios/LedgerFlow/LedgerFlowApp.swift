import SwiftUI
import Observation
import VisionKit

@main
@MainActor
struct LedgerFlowApp: App {
    var body: some Scene { WindowGroup { WorkspaceView() } }
}

struct SharedWorkbook: Identifiable {
    let id = UUID()
    let url: URL
    let directory: URL
}

@Observable
@MainActor
final class WorkspaceSession {
    var endpoint: WorkspaceEndpoint?
    var loading = false
    var failure: String?
    var connectionError: String?
    var downloadError: String?
    var sharedFile: SharedWorkbook?
    var reloadID = UUID()
    var showsConnection = false
    var fingerprint: String?
    var launchURL: URL?

    static var allowsLoopback: Bool {
        #if DEBUG && targetEnvironment(simulator)
        true
        #else
        false
        #endif
    }

    init() {
        let configured = Bundle.main.object(forInfoDictionaryKey: "LedgerFlowOrigin") as? String ?? ""
        let saved = UserDefaults.standard.string(forKey: "ledgerflow.workspaceOrigin") ?? ""
        let value = configured.isEmpty || configured.hasPrefix("$(") ? saved : configured
        if !value.isEmpty {
            do {
                endpoint = try WorkspaceEndpoint(value, allowingSimulatorLoopback: Self.allowsLoopback)
                if saved == endpoint?.url.absoluteString { fingerprint = UserDefaults.standard.string(forKey: "ledgerflow.certificatePin") }
            }
            catch { connectionError = error.localizedDescription }
        }
    }

    func connect(_ address: String) {
        do {
            let next = try WorkspaceEndpoint(address, allowingSimulatorLoopback: Self.allowsLoopback)
            UserDefaults.standard.set(next.url.absoluteString, forKey: "ledgerflow.workspaceOrigin")
            failure = nil
            connectionError = nil
            endpoint = next
            fingerprint = nil
            UserDefaults.standard.removeObject(forKey: "ledgerflow.certificatePin")
            launchURL = next.url
            showsConnection = false
            reloadID = UUID()
        } catch { connectionError = error.localizedDescription }
    }

    func retry() { failure = nil; launchURL = nil; reloadID = UUID() }

    func associate(_ value: String) {
        do {
            guard let url = URL(string: value.trimmingCharacters(in: .whitespacesAndNewlines)) else { throw WorkspaceEndpoint.InvalidAddress.malformed }
            let association = try WorkspaceAssociation(url)
            endpoint = association.endpoint
            fingerprint = association.fingerprint
            UserDefaults.standard.set(association.endpoint.url.absoluteString, forKey: "ledgerflow.workspaceOrigin")
            UserDefaults.standard.set(association.fingerprint, forKey: "ledgerflow.certificatePin")
            var destination = URLComponents(url: association.endpoint.url, resolvingAgainstBaseURL: false)!
            destination.fragment = "/associate/\(association.token)"
            launchURL = destination.url
            failure = nil; connectionError = nil; showsConnection = false; reloadID = UUID()
        } catch { connectionError = L10n.t("badLink") }
    }
}

@MainActor
struct WorkspaceView: View {
    @State private var session = WorkspaceSession()

    var body: some View {
        Group {
            if let endpoint = session.endpoint {
                ZStack {
                    WorkspaceWebView(endpoint: endpoint, session: session)
                        .id(session.reloadID)
                        .ignoresSafeArea(.container, edges: .bottom)
                    if let failure = session.failure {
                        ContentUnavailableView {
                            Label(L10n.t("unavailable"), systemImage: "wifi.exclamationmark")
                        } description: { Text(failure) } actions: {
                            Button(L10n.t("retry")) { session.retry() }.buttonStyle(.borderedProminent)
                            Button(L10n.t("settings")) { session.showsConnection = true }
                        }
                        .background(Color(.systemBackground))
                    }
                }
                .safeAreaInset(edge: .top, spacing: 0) {
                    HStack(spacing: 7) {
                        Image(systemName: endpoint.url.scheme == "https" ? "lock" : "hammer")
                        Text(session.fingerprint == nil ? "LedgerFlow" : L10n.t("linked")).lineLimit(1)
                        Spacer()
                        if session.loading { ProgressView().controlSize(.mini).accessibilityLabel(L10n.t("loading")) }
                        Button { session.showsConnection = true } label: { Image(systemName: "gearshape").frame(minWidth: 36, minHeight: 32) }
                            .accessibilityLabel(L10n.t("settings"))
                    }
                    .font(.caption).foregroundStyle(.secondary)
                    .padding(.leading, 16).padding(.trailing, 8)
                    .background(Color(.systemBackground))
                    .overlay(alignment: .bottom) { Divider() }
                }
            } else { WelcomeView(session: session) }
        }
        .tint(Color("BrandAccent"))
        .onOpenURL { session.associate($0.absoluteString) }
        .sheet(isPresented: $session.showsConnection) { ConnectionView(session: session) }
        .sheet(item: $session.sharedFile) { item in
            WorkbookShareSheet(url: item.url)
                .onDisappear { try? FileManager.default.removeItem(at: item.directory) }
        }
        .alert(L10n.t("downloadUnavailable"), isPresented: Binding(
            get: { session.downloadError != nil },
            set: { if !$0 { session.downloadError = nil } }
        )) {
            Button("OK") { session.downloadError = nil }
        } message: { Text(session.downloadError ?? "") }
    }
}

@MainActor
struct ConnectionView: View {
    let session: WorkspaceSession
    @State private var address = ""
    @State private var associationLink = ""
    @State private var showsScanner = false
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    VStack(alignment: .leading, spacing: 12) {
                        BrandMarkView(size: 64)
                        Text(L10n.t("connTitle")).font(.title2.weight(.semibold))
                        Text(L10n.t("connBody"))
                            .font(.subheadline).foregroundStyle(.secondary)
                    }.padding(.vertical, 12)
                }
                Section {
                    Button { if DataScannerViewController.isSupported { showsScanner = true } else { session.showsConnection = true } } label: { Label(L10n.t("pair"), systemImage: "qrcode.viewfinder").frame(maxWidth: .infinity).padding(.vertical, 8) }
                        .disabled(!DataScannerViewController.isSupported)
                    Text(L10n.t("connHint"))
                        .font(.footnote).foregroundStyle(.secondary)
                }
                Section {
                    DisclosureGroup(L10n.t("paste")) {
                        TextField("ledgerflow://connect…", text: $associationLink).textInputAutocapitalization(.never).autocorrectionDisabled()
                        Button(L10n.t("pairWithLink")) { session.associate(associationLink) }.disabled(associationLink.isEmpty)
                    }
                    DisclosureGroup(L10n.t("advanced")) {
                    TextField("https://votre-espace.example", text: $address)
                        .textContentType(.URL).keyboardType(.URL).textInputAutocapitalization(.never)
                        .autocorrectionDisabled().submitLabel(.go)
                        .onSubmit { session.connect(address) }
                    Button(L10n.t("connect")) { session.connect(address) }
                        .disabled(address.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                    }
                }
                if let error = session.connectionError { Section { Text(error).foregroundStyle(.red).accessibilityAddTraits(.updatesFrequently) } }
                Section {
                    Text(L10n.t("oneTime"))
                        .foregroundStyle(.secondary)
                }
            }
            .navigationTitle("LedgerFlow").navigationBarTitleDisplayMode(.inline)
            .toolbar { if session.endpoint != nil { ToolbarItem(placement: .cancellationAction) { Button(L10n.t("done")) { dismiss() } } } }
            .onAppear { address = session.endpoint?.url.absoluteString ?? "" }
            .sheet(isPresented: $showsScanner) {
                NavigationStack {
                    AssociationScanner(onRead: { value in showsScanner = false; session.associate(value) }, onFailure: { error in showsScanner = false; session.connectionError = error })
                        .ignoresSafeArea(edges: .bottom)
                        .navigationTitle(L10n.t("scanMac")).navigationBarTitleDisplayMode(.inline)
                        .toolbar { ToolbarItem(placement: .cancellationAction) { Button(L10n.t("cancel")) { showsScanner = false } } }
                }
            }
        }
    }
}

// MARK: - Welcome (first launch, not yet paired): the Ledger Grid story, then pairing

enum L10n {
    static var lang: String {
        let code = (Locale.preferredLanguages.first ?? "en").prefix(2)
        return ["fr", "sv"].contains(String(code)) ? String(code) : "en"
    }
    static func t(_ key: String) -> String { table[lang]?[key] ?? table["en"]?[key] ?? key }
    static let table: [String: [String: String]] = [
        "en": ["badLink": "This pairing link is not valid. Create a new code in LedgerFlow on the Mac.", "unavailable": "Workspace unavailable", "retry": "Try again", "settings": "Workspace settings", "loading": "Loading workspace", "linked": "Paired with your Mac", "downloadUnavailable": "Download unavailable", "connTitle": "Your agent, on iPhone too.", "connBody": "The same files as on your Mac. Photograph a document, ask the agent, then approve its proposals.", "connHint": "On the Mac: open LedgerFlow, then “Scan with iPhone”. Both devices must be on the same Wi-Fi.", "pairWithLink": "Pair with this link", "advanced": "Advanced server connection", "connect": "Connect to the server", "oneTime": "Pairing uses a one-time code. Keep LedgerFlow running and the Mac awake to use the workspace from the iPhone.", "scanMac": "Scan the Mac's code", "done": "Done", "pauseStory": "Pause the animation", "playStory": "Play the animation",
               "hello": "Your books, one receipt at a time.", "pair": "Pair with my Mac", "paste": "Paste a pairing link", "more": "Other connection options",
               "hint": "On the Mac: open LedgerFlow, then “Scan with iPhone”. Both devices on the same Wi-Fi.",
               "s1": "Snap the receipt", "b1": "The original is kept, untouched.", "s2": "LedgerFlow reads it", "b2": "Supplier, date, total, VAT. Rules decide debit and credit.",
               "s3": "A sandbox runs, a verifier checks", "b3": "Only the planned cells change. The real file is re-read.", "s4": "You approve the exact file", "b4": "Your approval signs its hash. The old version stays.",
               "sample": "Sample figures", "cancel": "Cancel", "supplier": "Supplier", "date": "Date", "account": "Accounts", "total": "Total", "vat": "VAT", "approve": "Approve"],
        "fr": ["badLink": "Ce lien d’association n’est pas valide. Générez un nouveau code dans LedgerFlow sur le Mac.", "unavailable": "Espace indisponible", "retry": "Réessayer", "settings": "Réglages de l’espace", "loading": "Chargement de l’espace", "linked": "Relié à votre Mac", "downloadUnavailable": "Téléchargement impossible", "connTitle": "Votre agent, aussi sur iPhone.", "connBody": "Retrouvez les mêmes dossiers que sur votre Mac. Prenez une pièce en photo, consultez l’agent, puis validez ses propositions.", "connHint": "Sur le Mac : ouvrez LedgerFlow, puis « Scanner avec l’iPhone ». Les deux appareils doivent être sur le même Wi-Fi.", "pairWithLink": "Associer avec ce lien", "advanced": "Connexion avancée à un serveur", "connect": "Se connecter au serveur", "oneTime": "L’association utilise un code à usage unique. Laissez LedgerFlow actif et le Mac éveillé pour utiliser l’espace depuis l’iPhone.", "scanMac": "Scannez le code du Mac", "done": "Terminé", "pauseStory": "Mettre l’animation en pause", "playStory": "Lancer l’animation",
               "hello": "Votre compta, un reçu à la fois.", "pair": "Associer mon Mac", "paste": "Coller un lien d’association", "more": "Autres options de connexion",
               "hint": "Sur le Mac : ouvrez LedgerFlow, puis « Scanner avec l’iPhone ». Les deux appareils sur le même Wi-Fi.",
               "s1": "Photographiez le reçu", "b1": "L’original est conservé, intact.", "s2": "LedgerFlow le lit", "b2": "Fournisseur, date, total, TVA. Les règles décident débit et crédit.",
               "s3": "La sandbox exécute, le vérificateur contrôle", "b3": "Seules les cellules prévues changent. Le vrai fichier est relu.", "s4": "Vous validez le fichier exact", "b4": "Votre accord signe son empreinte. L’ancienne version reste.",
               "sample": "Montants d’exemple", "cancel": "Annuler", "supplier": "Fournisseur", "date": "Date", "account": "Comptes", "total": "Total", "vat": "TVA", "approve": "Valider"],
        "sv": ["badLink": "Kopplingslänken är ogiltig. Skapa en ny kod i LedgerFlow på Macen.", "unavailable": "Arbetsytan är inte tillgänglig", "retry": "Försök igen", "settings": "Inställningar för arbetsytan", "loading": "Laddar arbetsytan", "linked": "Kopplad till din Mac", "downloadUnavailable": "Nedladdning inte tillgänglig", "connTitle": "Din agent, även på iPhone.", "connBody": "Samma underlag som på din Mac. Fota ett underlag, fråga agenten och godkänn sedan förslagen.", "connHint": "På Macen: öppna LedgerFlow och välj ”Skanna med iPhone”. Båda enheterna måste vara på samma wifi.", "pairWithLink": "Koppla med den här länken", "advanced": "Avancerad serveranslutning", "connect": "Anslut till servern", "oneTime": "Kopplingen använder en engångskod. Låt LedgerFlow vara igång och Macen vaken för att använda arbetsytan från iPhone.", "scanMac": "Skanna Macens kod", "done": "Klar", "pauseStory": "Pausa animationen", "playStory": "Spela animationen",
               "hello": "Din bokföring, ett kvitto i taget.", "pair": "Koppla till min Mac", "paste": "Klistra in en kopplingslänk", "more": "Andra anslutningsalternativ",
               "hint": "På Macen: öppna LedgerFlow och välj ”Skanna med iPhone”. Båda enheterna på samma wifi.",
               "s1": "Fota kvittot", "b1": "Originalet sparas orört.", "s2": "LedgerFlow läser det", "b2": "Leverantör, datum, belopp, moms. Reglerna bestämmer debet och kredit.",
               "s3": "Sandlådan kör, kontrollen granskar", "b3": "Bara de planerade cellerna ändras. Den riktiga filen läses om.", "s4": "Du godkänner exakt den filen", "b4": "Ditt godkännande signerar filens hash. Gamla versionen finns kvar.",
               "sample": "Exempelbelopp", "cancel": "Avbryt", "supplier": "Leverantör", "date": "Datum", "account": "Konton", "total": "Totalt", "vat": "Moms", "approve": "Godkänn"],
    ]
}

enum Grid {
    static let forest = Color(red: 11 / 255, green: 90 / 255, blue: 69 / 255)
    static let mint = Color(red: 143 / 255, green: 227 / 255, blue: 184 / 255)
    static let line = Color(red: 220 / 255, green: 226 / 255, blue: 220 / 255)
    static let canvas = Color(red: 242 / 255, green: 245 / 255, blue: 243 / 255)
    static let ink = Color(red: 18 / 255, green: 22 / 255, blue: 20 / 255)
    static let faint = Color(red: 140 / 255, green: 150 / 255, blue: 143 / 255)
}

/// The LF monogram as a selected cell with its fill handle (same geometry as the web mark).
struct BrandMarkView: View {
    var size: CGFloat = 56
    var body: some View {
        Canvas { ctx, s in
            let k = s.width / 64
            ctx.fill(Path(roundedRect: CGRect(x: 1 * k, y: 1 * k, width: 56 * k, height: 56 * k), cornerRadius: 12 * k), with: .color(Grid.forest))
            func poly(_ pts: [(CGFloat, CGFloat)]) -> Path { var p = Path(); p.addLines(pts.map { CGPoint(x: (1.2 + $0.0 * 0.875) * k, y: (1.2 + $0.1 * 0.875) * k) }); p.closeSubpath(); return p }
            ctx.fill(poly([(16, 14), (24, 14), (24, 41), (34, 41), (34, 49), (16, 49)]), with: .color(.white))
            ctx.fill(poly([(32, 14), (49, 14), (49, 22), (40, 22), (40, 29), (47, 29), (47, 37), (40, 37), (40, 49), (32, 49)]), with: .color(Color(red: 191 / 255, green: 235 / 255, blue: 211 / 255)))
            let handle = Path(roundedRect: CGRect(x: 47 * k, y: 47 * k, width: 15 * k, height: 15 * k), cornerRadius: 3 * k)
            ctx.fill(handle, with: .color(Grid.mint)); ctx.stroke(handle, with: .color(Grid.canvas), lineWidth: 3 * k)
        }
        .frame(width: size, height: size)
        .accessibilityHidden(true)
    }
}

/// A mini sheet that plays the four real steps. Sample figures, labelled.
struct GridStoryView: View {
    let phase: Int
    private let rows: [(String, String)] = [("supplier", "Papperskompaniet"), ("date", "2026-11-27"), ("total", "1 562,50"), ("vat", "312,50"), ("account", "6110 2640 1940")]
    var body: some View {
        VStack(spacing: 0) {
            HStack(spacing: 0) { headerCell("", w: 26); headerCell("A", w: nil); headerCell("B", w: nil) }
            ForEach(Array(rows.enumerated()), id: \.offset) { i, row in
                HStack(spacing: 0) {
                    Text("\(i + 2)").font(.system(size: 11, design: .monospaced)).foregroundStyle(Grid.faint).frame(width: 26, height: 40).background(Grid.canvas)
                    Text(L10n.t(row.0)).font(.system(size: 13)).foregroundStyle(Grid.faint).frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .leading).padding(.leading, 10)
                        .overlay(alignment: .trailing) { Rectangle().fill(Grid.line).frame(width: 1) }
                    Text(phase >= 1 ? row.1 : "")
                        .font(.system(size: 13, weight: .medium, design: .monospaced)).lineLimit(1).minimumScaleFactor(0.65)
                        .padding(.trailing, phase >= 2 ? 26 : 0)
                        .foregroundStyle(phase >= 3 ? Grid.ink : Grid.faint)
                        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .leading).padding(.leading, 10)
                        .overlay { if phase >= 2 { Image(systemName: "checkmark").font(.caption.weight(.bold)).foregroundStyle(Grid.forest).frame(maxWidth: .infinity, alignment: .trailing).padding(.trailing, 10).transition(.scale.combined(with: .opacity)) } }
                }
                .frame(height: 40)
                .overlay(alignment: .top) { Rectangle().fill(Grid.line).frame(height: 1) }
            }
        }
        .background(.white)
        .clipShape(RoundedRectangle(cornerRadius: 10))
        .overlay { RoundedRectangle(cornerRadius: 10).stroke(Grid.line, lineWidth: 1) }
        .overlay(alignment: .topLeading) {
            GeometryReader { g in
                let colW = (g.size.width - 26) / 2
                let top: CGFloat = 24
                let height: CGFloat = phase >= 3 ? 200 : phase == 2 ? 120 : 80
                ZStack(alignment: .bottomTrailing) {
                    RoundedRectangle(cornerRadius: 3).stroke(Grid.forest, lineWidth: 2)
                    RoundedRectangle(cornerRadius: 1.5).fill(Grid.forest).frame(width: 9, height: 9).overlay { RoundedRectangle(cornerRadius: 1.5).stroke(.white, lineWidth: 2) }.offset(x: 4, y: 4)
                }
                .frame(width: colW, height: height)
                .offset(x: 26 + colW, y: top)
                .opacity(phase == 0 ? 0 : 1)
            }
        }
        .overlay(alignment: .center) {
            if phase == 0 {
                VStack(alignment: .leading, spacing: 5) {
                    Text("PAPPERSKOMPANIET").font(.system(size: 11, weight: .bold, design: .monospaced))
                    ForEach(0..<3, id: \.self) { _ in Capsule().fill(Grid.line).frame(height: 4) }
                    Text("TOTALT 1 562,50").font(.system(size: 11, weight: .semibold, design: .monospaced))
                }
                .padding(12).frame(width: 150).background(.white).shadow(color: .black.opacity(0.18), radius: 12, y: 8)
                .rotationEffect(.degrees(-3))
                .transition(.move(edge: .bottom).combined(with: .opacity))
            }
        }
    }
    private func headerCell(_ s: String, w: CGFloat?) -> some View {
        Text(s).font(.system(size: 11, weight: .semibold, design: .monospaced)).foregroundStyle(Grid.faint)
            .frame(maxWidth: w ?? .infinity).frame(width: w, height: 24).background(Grid.canvas)
    }
}

@MainActor
struct WelcomeView: View {
    let session: WorkspaceSession
    @State private var phase = 0
    @State private var paused = false
    @State private var showsScanner = false
    @State private var showsPaste = false
    @State private var link = ""
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    private let titles = ["s1", "s2", "s3", "s4"], bodies = ["b1", "b2", "b3", "b4"]

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            HStack(spacing: 10) { BrandMarkView(size: 34); Image("Wordmark").renderingMode(.template).resizable().scaledToFit().frame(height: 21).foregroundStyle(Grid.ink).accessibilityLabel("LedgerFlow"); Spacer() }
            Text(L10n.t("hello")).font(.system(size: 34, weight: .bold)).tracking(-1.2).foregroundStyle(Grid.ink).fixedSize(horizontal: false, vertical: true)
            GridStoryView(phase: phase).frame(height: 224)
                .animation(reduceMotion ? nil : .spring(response: 0.5, dampingFraction: 0.86), value: phase)
            HStack(spacing: 8) {
                ForEach(0..<4, id: \.self) { i in
                    Button { phase = i } label: {
                        VStack(alignment: .leading, spacing: 6) {
                            Text(String(format: "%02d", i + 1)).font(.system(size: 11, weight: .semibold, design: .monospaced))
                            Capsule().fill(i <= phase ? Grid.forest : Grid.line).frame(height: 3)
                        }.foregroundStyle(i == phase ? Grid.forest : Grid.faint)
                    }.buttonStyle(.plain).frame(minHeight: 44).contentShape(Rectangle()).accessibilityLabel(L10n.t(titles[i]))
                }
                Button { paused.toggle() } label: { Image(systemName: paused ? "play.fill" : "pause.fill").font(.footnote).frame(width: 44, height: 44) }
                    .buttonStyle(.plain).foregroundStyle(Grid.forest).accessibilityLabel(L10n.t(paused ? "playStory" : "pauseStory"))
            }
            VStack(alignment: .leading, spacing: 8) {
                Text(L10n.t(titles[phase])).font(.title2.weight(.bold)).tracking(-0.6).foregroundStyle(Grid.ink)
                Text(L10n.t(bodies[phase])).font(.body).foregroundStyle(.secondary)
                Text(L10n.t("sample")).font(.caption2).foregroundStyle(Grid.faint)
            }
            .fixedSize(horizontal: false, vertical: true)
            .id(phase)
            .transition(.asymmetric(insertion: .opacity.combined(with: .offset(y: 8)).animation(.easeOut(duration: 0.28).delay(0.14)),
                                    removal: .opacity.animation(.easeIn(duration: 0.1))))
            Spacer(minLength: 8)
            Button { if DataScannerViewController.isSupported { showsScanner = true } else { session.showsConnection = true } } label: {
                Label(L10n.t("pair"), systemImage: "qrcode.viewfinder").font(.headline).frame(maxWidth: .infinity).padding(.vertical, 16)
            }
            .buttonStyle(.borderedProminent).tint(Grid.forest).clipShape(RoundedRectangle(cornerRadius: 12))
            Text(L10n.t("hint")).font(.footnote).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
            HStack {
                Button(L10n.t("paste")) { showsPaste = true }
                Spacer()
                Button(L10n.t("more")) { session.showsConnection = true }
            }.font(.footnote.weight(.semibold)).tint(Grid.forest)
            if let error = session.connectionError { Text(error).font(.footnote).foregroundStyle(.red) }
        }
        .padding(.horizontal, 22).padding(.top, 12).padding(.bottom, 8)
        .background(Grid.canvas.ignoresSafeArea())
        .task {
            if reduceMotion { phase = 3; paused = true }  // starts still; Play runs the loop without spring
            while !Task.isCancelled {
                try? await Task.sleep(for: .seconds(3.4))
                if paused { continue }
                withAnimation(reduceMotion ? nil : .spring(response: 0.5, dampingFraction: 0.86)) { phase = (phase + 1) % 4 }
            }
        }
        .sheet(isPresented: $showsScanner) {
            NavigationStack {
                AssociationScanner(onRead: { value in showsScanner = false; session.associate(value) }, onFailure: { error in showsScanner = false; session.connectionError = error })
                    .ignoresSafeArea(edges: .bottom)
                    .navigationTitle(L10n.t("pair")).navigationBarTitleDisplayMode(.inline)
                    .toolbar { ToolbarItem(placement: .cancellationAction) { Button(L10n.t("cancel")) { showsScanner = false } } }
            }
        }
        .alert(L10n.t("paste"), isPresented: $showsPaste) {
            TextField("ledgerflow://connect…", text: $link).textInputAutocapitalization(.never).autocorrectionDisabled()
            Button("OK") { session.associate(link) }
            Button(L10n.t("cancel"), role: .cancel) { }
        }
    }
}
