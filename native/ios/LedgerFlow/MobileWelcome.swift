import SwiftUI
import VisionKit

nonisolated enum MobilePalette {
    static let forest = Color(red: 0.06, green: 0.24, blue: 0.19)
    static let moss = Color(red: 0.80, green: 0.88, blue: 0.68)
    static let paper = Color(red: 0.96, green: 0.96, blue: 0.93)
    static let ink = Color(red: 0.08, green: 0.16, blue: 0.13)
    static let rule = Color(red: 0.85, green: 0.88, blue: 0.83)
}

struct ReceiptGlyph: View {
    var body: some View {
        Canvas { context, size in
            let unit = size.width / 100
            func point(_ x: Double, _ y: Double) -> CGPoint { CGPoint(x: x * unit, y: y * unit) }
            func polygon(_ list: [CGPoint]) -> Path {
                var path = Path(); path.addLines(list); path.closeSubpath(); return path
            }
            let sheet = polygon([point(13, 5), point(69, 5), point(87, 23), point(87, 101), point(75, 93), point(63, 101), point(51, 93), point(39, 101), point(27, 93), point(13, 101)])
            context.fill(sheet, with: .linearGradient(Gradient(colors: [Color.white, MobilePalette.moss]), startPoint: .zero, endPoint: point(92, 114)))
            context.fill(polygon([point(69, 5), point(69, 23), point(87, 23)]), with: .color(Color(red: 0.56, green: 0.71, blue: 0.57)))
            func line(_ x1: Double, _ y1: Double, _ x2: Double, _ y2: Double, width: Double = 1, opacity: Double = 1) {
                var path = Path(); path.move(to: point(x1, y1)); path.addLine(to: point(x2, y2))
                context.stroke(path, with: .color(MobilePalette.forest.opacity(opacity)), style: StrokeStyle(lineWidth: unit * width, lineCap: .round))
            }
            line(25, 25, 51, 25, width: 4)
            line(25, 37, 58, 37, width: 2, opacity: 0.42)
            for y in [51.0, 62.0, 73.0] { line(25, y, 74, y, opacity: 0.35) }
            line(49, 48, 49, 75, opacity: 0.35)
            line(55, 83, 61, 88, width: 3)
            line(61, 88, 73, 77, width: 3)
        }
        .aspectRatio(100.0 / 110.0, contentMode: .fit)
        .accessibilityHidden(true)
    }
}

struct WaveBackdrop: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @Environment(\.scenePhase) private var scenePhase

    var body: some View {
        TimelineView(.animation(minimumInterval: 1.0 / 30, paused: reduceMotion || scenePhase != .active)) { timeline in
            let phase = reduceMotion ? 0 : timeline.date.timeIntervalSinceReferenceDate.truncatingRemainder(dividingBy: 12) * .pi / 6
            Canvas { context, size in
                let scale = min(size.width, size.height)
                for row in 0..<12 {
                    var path = Path()
                    let index = Double(row)
                    for sample in 0...80 {
                        let x = Double(sample) / 80
                        let wave = sin(x * .pi * 2.2 + sin(phase) * 0.38 + index * 0.035)
                        let fold = sin(x * .pi * 3.6 - 0.6 + cos(phase) * 0.25)
                        let spacing = 0.017 + 0.005 * cos(x * .pi * 2)
                        let y = size.height * 0.69 + scale * (index * spacing - wave * 0.14 + fold * 0.03)
                        let point = CGPoint(x: x * size.width, y: y)
                        if sample == 0 { path.move(to: point) } else { path.addLine(to: point) }
                    }
                    context.stroke(path, with: .color(MobilePalette.moss.opacity(0.23)), lineWidth: 0.7)
                }
            }
        }
        .background(RadialGradient(colors: [Color(red: 0.19, green: 0.36, blue: 0.27), MobilePalette.forest], center: .topTrailing, startRadius: 10, endRadius: 520))
        .accessibilityHidden(true)
        .allowsHitTesting(false)
    }
}

struct ReceiptLaunch: View {
    let finish: () -> Void
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var settled = false

    var body: some View {
        ZStack {
            WaveBackdrop().ignoresSafeArea()
            VStack(spacing: 22) {
                ReceiptGlyph().frame(width: 108)
                    .rotationEffect(.degrees(settled || reduceMotion ? -7 : -16))
                    .scaleEffect(settled || reduceMotion ? 1 : 0.94)
                    .offset(y: settled || reduceMotion ? 0 : 22)
                Image("Wordmark").renderingMode(.template).resizable().scaledToFit()
                    .frame(width: 160, height: 35)
                    .opacity(settled || reduceMotion ? 1 : 0)
                    .accessibilityLabel("LedgerFlow")
            }
            .foregroundStyle(.white)
        }
        .safeAreaInset(edge: .bottom) {
            Button("Skip introduction", action: finish)
                .font(.footnote.weight(.medium)).foregroundStyle(.white)
                .frame(minHeight: 44)
        }
        .task {
            guard !reduceMotion else { finish(); return }
            withAnimation(.timingCurve(0.23, 1, 0.32, 1, duration: 0.65)) { settled = true }
            do { try await Task.sleep(for: .milliseconds(2100)); finish() }
            catch { return }
        }
    }
}

struct MobileWelcome: View {
    let workspace: MobileWorkspace
    let pair: () -> Void
    let account: () -> Void

    var body: some View {
        GeometryReader { geometry in
            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    Image("Wordmark").renderingMode(.template).resizable().scaledToFit()
                        .frame(width: 132, height: 30).accessibilityLabel("LedgerFlow")
                    ZStack {
                        WaveBackdrop().clipShape(.rect(cornerRadius: 24))
                        ReceiptGlyph().frame(width: 118)
                            .rotationEffect(.degrees(-9))
                            .shadow(color: .black.opacity(0.24), radius: 12, x: 5, y: 14)
                    }
                    .frame(height: max(190, min(320, geometry.size.height * 0.38)))
                    .padding(.top, 28).padding(.bottom, 26)
                    Text("A place for every receipt.")
                        .font(.system(.largeTitle, design: .serif).weight(.medium))
                        .accessibilityAddTraits(.isHeader)
                    Text("Scan on your iPhone. Keep working in the same LedgerFlow workspace on your Mac.")
                        .font(.subheadline).foregroundStyle(.secondary).padding(.top, 10)
                    Button(action: pair) {
                        Label("Connect to your Mac", systemImage: "qrcode.viewfinder")
                            .frame(maxWidth: .infinity).padding(.vertical, 7)
                    }
                    .buttonStyle(.borderedProminent).controlSize(.large)
                    .disabled(workspace.busy).padding(.top, 24)
                    Button(action: account) {
                        Text("Create an account or sign in").frame(maxWidth: .infinity, minHeight: 44)
                    }.font(.subheadline.weight(.semibold)).disabled(workspace.busy).padding(.top, 6)
                    if workspace.busy { ProgressView("Connecting…").padding(.top, 12) }
                }
                .frame(maxWidth: 480)
                .padding(.horizontal, 24).padding(.vertical, 24)
                .frame(maxWidth: .infinity)
            }
        }
        .background(MobilePalette.paper.ignoresSafeArea())
    }
}

struct PairingSheet: View {
    let workspace: MobileWorkspace
    @Environment(\.dismiss) private var dismiss
    @State private var showCamera = false
    @State private var link = ""

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    ZStack {
                        WaveBackdrop().clipShape(.rect(cornerRadius: 24))
                        Image(systemName: "qrcode.viewfinder").font(.system(size: 73, weight: .light))
                            .foregroundStyle(MobilePalette.moss).accessibilityHidden(true)
                    }.frame(height: 205)
                    Text("Connect to your Mac").font(.system(.largeTitle, design: .serif))
                    Text("Open LedgerFlow on your Mac and choose ‘Scan with iPhone’. Generate a pairing code, then point this iPhone at the code.")
                        .font(.body).foregroundStyle(.secondary)
                    if DataScannerViewController.isSupported {
                        Button { showCamera = true } label: {
                            Label("Scan pairing code", systemImage: "camera").frame(maxWidth: .infinity)
                        }.buttonStyle(.borderedProminent).controlSize(.large).disabled(workspace.busy)
                    } else {
                        Text("Camera scanning is unavailable on this device. You can paste a pairing link below.")
                            .font(.footnote).foregroundStyle(.secondary)
                    }
                    DisclosureGroup("Use a pairing link") {
                        TextField("Pairing link", text: $link).textInputAutocapitalization(.never).autocorrectionDisabled()
                            .textFieldStyle(.roundedBorder).padding(.vertical, 7)
                        Button("Connect") { connect(link) }.disabled(link.isEmpty || workspace.busy).frame(minHeight: 44)
                    }
                    if workspace.busy { ProgressView("Connecting…") }
                    if let error = workspace.notice { Text(error).font(.footnote).foregroundStyle(.red) }
                }.padding(24).frame(maxWidth: 530).frame(maxWidth: .infinity)
            }
            .background(MobilePalette.paper.ignoresSafeArea())
            .toolbar { ToolbarItem(placement: .cancellationAction) { Button("Close") { dismiss() } } }
            .fullScreenCover(isPresented: $showCamera) {
                ZStack(alignment: .top) {
                    AssociationScanner(onRead: { value in showCamera = false; connect(value) }, onFailure: { error in showCamera = false; workspace.notice = error })
                        .ignoresSafeArea()
                    VStack(spacing: 9) {
                        HStack {
                            Text("Pair your Mac").font(.headline)
                            Spacer()
                            Button("Close") { showCamera = false }.frame(minHeight: 44)
                        }
                        Text("Hold the QR code inside the frame.").font(.subheadline).frame(maxWidth: .infinity, alignment: .leading)
                    }
                    .padding(16).background(.regularMaterial, in: .rect(cornerRadius: 19)).padding(18)
                    Image(systemName: "viewfinder").font(.system(size: 239, weight: .ultraLight))
                        .foregroundStyle(.white).frame(maxWidth: .infinity, maxHeight: .infinity)
                        .allowsHitTesting(false).accessibilityHidden(true)
                }
            }
        }
        .tint(MobilePalette.forest)
    }

    private func connect(_ value: String) {
        workspace.notice = nil
        Task {
            if await workspace.pair(value) {
                dismiss()
                await workspace.refresh()
            }
        }
    }
}

struct AccountSheet: View {
    let workspace: MobileWorkspace
    @Environment(\.dismiss) private var dismiss
    @State private var name = ""
    @State private var address = ""
    @State private var invite = ""

    var body: some View {
        NavigationStack {
            Form {
                if workspace.connection != nil {
                    Section("Connected workspace") {
                        ConnectionBadge(workspace: workspace)
                        Button("Sign out", role: .destructive) { Task { await workspace.signOut(); dismiss() } }
                    }
                }
                Section("Start on this iPhone") {
                    Text("Create a local profile to scan and keep receipts until you connect a workspace.")
                        .font(.subheadline).foregroundStyle(.secondary)
                    TextField("Your name", text: $name).textContentType(.name)
                    Button("Create local profile") { workspace.createProfile(name); dismiss() }
                        .disabled(name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                }
                Section("Sign in with an invitation") {
                    TextField("Workspace HTTPS address", text: $address).textContentType(.URL).keyboardType(.URL)
                        .textInputAutocapitalization(.never).autocorrectionDisabled()
                    SecureField("Invitation code", text: $invite).textContentType(.oneTimeCode)
                    Button("Sign in") {
                        workspace.notice = nil
                        Task {
                            if await workspace.signIn(origin: address, invite: invite.trimmingCharacters(in: .whitespacesAndNewlines)) {
                                dismiss()
                                await workspace.refresh()
                            }
                        }
                    }.disabled(address.isEmpty || invite.isEmpty || workspace.busy)
                    if workspace.busy { ProgressView("Signing in…") }
                    if let error = workspace.notice { Text(error).font(.footnote).foregroundStyle(.red) }
                }
            }
            .navigationTitle("Your account")
            .toolbar { ToolbarItem(placement: .cancellationAction) { Button("Close") { dismiss() } } }
            .onAppear { address = workspace.legacyOrigin ?? "" }
        }
        .tint(MobilePalette.forest)
    }
}
