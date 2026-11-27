import ImageIO
import PhotosUI
import SwiftUI
import Vision
import VisionKit

struct MobileRoot: View {
    private enum Sheet: String, Identifiable {
        case pairing, account
        var id: String { rawValue }
    }

    @State private var workspace = MobileWorkspace()
    @State private var sheet: Sheet?
    @State private var showingLaunch = true
    @Environment(\.scenePhase) private var scenePhase
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    var body: some View {
        ZStack {
            if showingLaunch {
                ReceiptLaunch(finish: finishLaunch).transition(.opacity)
            } else if workspace.canEnter {
                MobileTabs(workspace: workspace, pair: { present(.pairing) }, account: { present(.account) })
            } else {
                MobileWelcome(workspace: workspace, pair: { present(.pairing) }, account: { present(.account) })
            }
        }
        .tint(MobilePalette.forest)
        .sheet(item: $sheet) { view in
            switch view {
            case .pairing: PairingSheet(workspace: workspace)
            case .account: AccountSheet(workspace: workspace)
            }
        }
        .alert("LedgerFlow", isPresented: Binding(
            get: { workspace.notice != nil && sheet == nil },
            set: { if !$0 { workspace.notice = nil } }
        )) {
            Button("OK") { workspace.notice = nil }
        } message: { Text(workspace.notice ?? "") }
        .onOpenURL { url in
            Task {
                if await workspace.pair(url.absoluteString) { await workspace.refresh() }
            }
        }
        .task(id: scenePhase) {
            guard scenePhase == .active else { return }
            while !Task.isCancelled {
                await workspace.refresh()
                do { try await Task.sleep(for: .seconds(8)) } catch { break }
            }
        }
    }

    private func present(_ value: Sheet) {
        workspace.notice = nil
        sheet = value
    }

    private func finishLaunch() {
        withAnimation(reduceMotion ? nil : .easeOut(duration: 0.2)) { showingLaunch = false }
    }
}

private struct MobileTabs: View {
    let workspace: MobileWorkspace
    let pair: () -> Void
    let account: () -> Void
    @State private var selection = 0

    var body: some View {
        TabView(selection: $selection) {
            NavigationStack {
                WorkbookScreen(workspace: workspace, pair: pair, account: account, openQueue: { selection = 2 })
            }.tabItem { Label("Workbooks", systemImage: "tablecells") }.tag(0)
            NavigationStack { CaptureScreen(workspace: workspace, openQueue: { selection = 2 }) }
                .tabItem { Label("Scan", systemImage: "viewfinder") }.tag(1)
            NavigationStack { HistoryScreen(workspace: workspace) }
                .tabItem { Label("History", systemImage: "clock") }.badge(workspace.pending.count).tag(2)
            NavigationStack { AgentScreen(workspace: workspace, pair: pair) }
                .tabItem { Label("Agent", systemImage: "bubble.left.and.text.bubble.right") }.tag(3)
            NavigationStack { ExpensesScreen(workspace: workspace) }
                .tabItem { Label("Expenses", systemImage: "list.bullet.rectangle") }.tag(4)
        }
    }
}

private struct WorkbookScreen: View {
    let workspace: MobileWorkspace
    let pair: () -> Void
    let account: () -> Void
    let openQueue: () -> Void

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 24) {
                connectionPanel
                if !workspace.pending.isEmpty {
                    Button(action: openQueue) {
                        HStack(spacing: 13) {
                            Image(systemName: "tray.full").font(.title3).foregroundStyle(MobilePalette.forest)
                            VStack(alignment: .leading, spacing: 3) {
                                Text(workspace.pending.count == 1 ? "1 receipt pending" : "\(workspace.pending.count) receipts pending").font(.subheadline.weight(.semibold))
                                Text("Saved on this iPhone").font(.footnote).foregroundStyle(.secondary)
                            }
                            Spacer()
                            Image(systemName: "chevron.right").font(.footnote).foregroundStyle(.secondary)
                        }.padding(16).background(.white, in: .rect(cornerRadius: 16))
                    }.buttonStyle(.plain)
                }
                VStack(alignment: .leading, spacing: 0) {
                    Text("Linked workbooks").font(.headline).padding(.bottom, 12)
                    if workspace.snapshot.workbooks.isEmpty {
                        Text(workspace.connection == nil ? "Connect a workspace to see its Excel files here." : "No workbooks are available yet. Link a workbook in LedgerFlow on your Mac.")
                            .font(.subheadline).foregroundStyle(.secondary).padding(.vertical, 12)
                    }
                    ForEach(workspace.snapshot.workbooks) { workbook in
                        Divider().overlay(MobilePalette.rule)
                        NavigationLink { WorkbookDetail(workspace: workspace, workbook: workbook) } label: {
                            HStack(spacing: 12) {
                                Image(systemName: "tablecells").foregroundStyle(MobilePalette.forest)
                                    .frame(width: 38, height: 38).background(MobilePalette.moss.opacity(0.42), in: .rect(cornerRadius: 10))
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(workbook.display_name).font(.subheadline.weight(.semibold)).foregroundStyle(MobilePalette.ink)
                                    Text(workbook.status == "ready" ? "Ready to receive receipts" : workbook.status.replacingOccurrences(of: "_", with: " ").capitalized)
                                        .font(.footnote).foregroundStyle(.secondary)
                                }
                                Spacer()
                                Image(systemName: "chevron.right").font(.footnote).foregroundStyle(.secondary)
                            }.padding(.vertical, 13)
                        }.buttonStyle(.plain)
                    }
                }
                if let updated = workspace.snapshot.updated {
                    Text("Last synced \(updated, format: .relative(presentation: .named))").font(.footnote).foregroundStyle(.secondary)
                }
            }.padding(22).frame(maxWidth: 650).frame(maxWidth: .infinity)
        }
        .background(MobilePalette.paper.ignoresSafeArea())
        .navigationTitle("Workbooks")
        .refreshable { await workspace.refresh() }
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Menu {
                    Button("Connect to your Mac", systemImage: "qrcode.viewfinder", action: pair)
                    Button("Account and sign-in", systemImage: "person.crop.circle", action: account)
                    Button("Refresh workspace", systemImage: "arrow.clockwise") { Task { await workspace.refresh() } }
                } label: { Image(systemName: "ellipsis.circle").accessibilityLabel("Workspace options") }
            }
        }
    }

    private var connectionPanel: some View {
        VStack(alignment: .leading, spacing: 12) {
            Label(connectionTitle, systemImage: workspace.connected ? "checkmark.circle.fill" : "laptopcomputer")
                .font(.headline)
            Text(connectionDescription).font(.subheadline).foregroundStyle(MobilePalette.moss)
            if [.unlinked, .expired].contains(workspace.availability) {
                Button(workspace.availability == .expired ? "Reconnect" : "Connect to your Mac", action: workspace.macLinked || workspace.connection == nil ? pair : account)
                    .font(.subheadline.weight(.semibold)).foregroundStyle(.white).frame(minHeight: 44)
            }
        }
        .foregroundStyle(.white).padding(20).frame(maxWidth: .infinity, alignment: .leading)
        .background {
            WaveBackdrop().overlay(MobilePalette.forest.opacity(0.38)).clipShape(.rect(cornerRadius: 19))
        }
    }

    private var connectionTitle: String {
        switch workspace.availability {
        case .unlinked: "On this iPhone"
        case .checking: "Connecting…"
        case .connected: workspace.macLinked ? "Mac connected" : "Workspace connected"
        case .unreachable: workspace.macLinked ? "Mac unreachable" : "Workspace unreachable"
        case .expired: "Reconnect your workspace"
        }
    }

    private var connectionDescription: String {
        switch workspace.availability {
        case .unlinked: "Scan now and choose a linked workbook when you’re ready."
        case .checking: "Checking access to your workbooks and receipts."
        case .connected: workspace.syncing ? "Sending queued receipts…" : "Your workbooks, receipts and agent are available."
        case .unreachable: "You can keep scanning. Saved receipts will send when this workspace is reachable."
        case .expired: "The receipts on this iPhone are safe. Reconnect to continue syncing."
        }
    }
}

private struct WorkbookDetail: View {
    let workspace: MobileWorkspace
    let workbook: Workbook
    @State private var file: URL?
    @State private var working = false

    var body: some View {
        List {
            Section("Excel file") {
                if let count = workbook.version_count { LabeledContent("Versions", value: String(count)) }
                if workbook.version_count != nil {
                    if let file {
                        ShareLink(item: file) { Label("Share latest Excel", systemImage: "square.and.arrow.up") }
                    } else {
                        Button(working ? "Downloading…" : "Download latest Excel", systemImage: "arrow.down.circle") {
                            working = true
                            Task {
                                defer { working = false }
                                do { file = try await workspace.workbookFile(workbook) }
                                catch { workspace.notice = workspace.message(for: error) }
                            }
                        }.disabled(!workspace.connected || working)
                    }
                }
            }
            Section("Receipts") {
                let items = workspace.snapshot.receipts.filter { $0.workbook_id == workbook.id }
                if items.isEmpty { Text("No receipts yet.").foregroundStyle(.secondary) }
                ForEach(items) { receipt in
                    NavigationLink { ReceiptDetail(workspace: workspace, receipt: receipt) } label: { ReceiptRow(receipt: receipt, workspace: workspace) }
                }
            }
        }.navigationTitle(workbook.display_name).navigationBarTitleDisplayMode(.inline)
    }
}

private struct CaptureScreen: View {
    let workspace: MobileWorkspace
    let openQueue: () -> Void
    @State private var target: String?
    @State private var camera = false
    @State private var photos: [PhotosPickerItem] = []
    @State private var pages: [Data] = []
    @State private var scannedText = ""
    @State private var readingText = false
    @State private var importing = false
    @State private var saving = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 19) {
                ZStack {
                    WaveBackdrop().clipShape(.rect(cornerRadius: 24))
                    if let first = pages.first, let image = UIImage(data: first) {
                        Image(uiImage: image).resizable().scaledToFit().padding(18).accessibilityLabel("Receipt preview")
                    } else {
                        ReceiptGlyph().frame(width: 105).rotationEffect(.degrees(-7))
                    }
                }.frame(height: 222)
                if !pages.isEmpty {
                    Text(pages.count == 1 ? "1 page ready" : "\(pages.count) pages ready").font(.headline)
                    if !scannedText.isEmpty {
                        VStack(alignment: .leading, spacing: 6) {
                            Label("Text read on this iPhone", systemImage: "text.viewfinder").font(.subheadline.weight(.semibold))
                            Text(scannedText).font(.system(.footnote, design: .monospaced)).textSelection(.enabled)
                                .frame(maxWidth: .infinity, alignment: .leading).lineLimit(14)
                        }.padding(12).background(.white, in: .rect(cornerRadius: 12))
                    } else if readingText { ProgressView("Reading the receipt text…").font(.footnote) }
                } else {
                    Text("Scan a receipt").font(.system(.title, design: .serif))
                    Text("Capture the whole receipt in good light. You can scan even when your Mac is out of reach.")
                        .font(.subheadline).foregroundStyle(.secondary)
                }
                Picker("Workbook", selection: $target) {
                    Text("Choose later").tag(Optional<String>.none)
                    ForEach(workspace.snapshot.targets) { workbook in Text(workbook.display_name).tag(Optional(workbook.id)) }
                }.frame(maxWidth: .infinity, minHeight: 44, alignment: .leading)
                if pages.isEmpty {
                    Button { camera = true } label: {
                        Label("Open document scanner", systemImage: "viewfinder").frame(maxWidth: .infinity)
                    }.buttonStyle(.borderedProminent).controlSize(.large).disabled(!VNDocumentCameraViewController.isSupported || importing)
                    PhotosPicker(selection: $photos, maxSelectionCount: 10, matching: .images) {
                        Label("Choose from Photos", systemImage: "photo.on.rectangle").frame(maxWidth: .infinity, minHeight: 44)
                    }.disabled(importing)
                    if importing { ProgressView("Preparing photos…") }
                } else {
                    Button {
                        saving = true
                        Task {
                            let saved = workspace.saveScans(pages, workbookID: target)
                            saving = false
                            pages.removeFirst(saved)
                            if pages.isEmpty { openQueue() }
                        }
                    } label: {
                        Label(saving ? "Saving…" : "Save to receipt queue", systemImage: "tray.and.arrow.down").frame(maxWidth: .infinity)
                    }.buttonStyle(.borderedProminent).controlSize(.large).disabled(saving)
                    Button("Discard preview", role: .destructive) { pages = [] }.frame(minHeight: 44).disabled(saving)
                }
            }.padding(22).frame(maxWidth: 580).frame(maxWidth: .infinity)
        }
        .background(MobilePalette.paper.ignoresSafeArea()).navigationTitle("Scan")
        .fullScreenCover(isPresented: $camera) {
            DocumentCamera { result in
                camera = false
                switch result {
                case .success(let images): pages = images
                case .failure: workspace.notice = "The scanner could not save all pages. Try again or choose a photo."
                }
            }.ignoresSafeArea()
        }
        .task(id: pages) {
            scannedText = ""
            guard let first = pages.first else { return }
            readingText = true
            scannedText = await recognizeText(first)
            readingText = false
        }
        .task(id: photos) {
            guard !photos.isEmpty else { return }
            importing = true
            var selected: [Data] = []
            for item in photos {
                if let data = try? await item.loadTransferable(type: Data.self), let image = downsample(data),
                   let jpeg = receiptJPEG(image) { selected.append(jpeg) }
            }
            guard !Task.isCancelled else { return }
            if selected.count < photos.count { workspace.notice = "Some photos could not be read. Check your selection and try again." }
            pages = selected
            photos = []
            importing = false
        }
        .onChange(of: workspace.connection?.scope) { target = nil }
    }
}

private func downsample(_ data: Data) -> UIImage? {
    guard let source = CGImageSourceCreateWithData(data as CFData, nil),
          let image = CGImageSourceCreateThumbnailAtIndex(source, 0, [
            kCGImageSourceCreateThumbnailFromImageAlways: true,
            kCGImageSourceThumbnailMaxPixelSize: 2400,
            kCGImageSourceCreateThumbnailWithTransform: true
          ] as CFDictionary) else { return nil }
    return UIImage(cgImage: image)
}

private func receiptJPEG(_ image: UIImage) -> Data? {
    guard image.size.width > 0, image.size.height > 0 else { return nil }
    let scale = min(1, 2400 / max(image.size.width, image.size.height))
    let size = CGSize(width: image.size.width * scale, height: image.size.height * scale)
    let format = UIGraphicsImageRendererFormat()
    format.scale = 1
    format.opaque = true
    let data = UIGraphicsImageRenderer(size: size, format: format).jpegData(withCompressionQuality: 0.84) { context in
        UIColor.white.setFill()
        context.fill(CGRect(origin: .zero, size: size))
        image.draw(in: CGRect(origin: .zero, size: size))
    }
    return data.count <= 10 * 1024 * 1024 ? data : nil
}

private struct DocumentCamera: UIViewControllerRepresentable {
    let complete: (Result<[Data], Error>) -> Void

    func makeCoordinator() -> Coordinator { Coordinator(complete: complete) }
    func makeUIViewController(context: Context) -> VNDocumentCameraViewController {
        let camera = VNDocumentCameraViewController()
        camera.delegate = context.coordinator
        return camera
    }
    func updateUIViewController(_ camera: VNDocumentCameraViewController, context: Context) {}

    final class Coordinator: NSObject, VNDocumentCameraViewControllerDelegate {
        let complete: (Result<[Data], Error>) -> Void
        init(complete: @escaping (Result<[Data], Error>) -> Void) { self.complete = complete }

        func documentCameraViewController(_ controller: VNDocumentCameraViewController, didFinishWith scan: VNDocumentCameraScan) {
            var images: [Data] = []
            for index in 0..<scan.pageCount {
                guard let jpeg = autoreleasepool(invoking: { receiptJPEG(scan.imageOfPage(at: index)) }) else {
                    complete(.failure(URLError(.cannotDecodeContentData)))
                    return
                }
                images.append(jpeg)
            }
            complete(.success(images))
        }
        func documentCameraViewControllerDidCancel(_ controller: VNDocumentCameraViewController) { complete(.success([])) }
        func documentCameraViewController(_ controller: VNDocumentCameraViewController, didFailWithError error: Error) { complete(.failure(error)) }
    }
}

private struct HistoryScreen: View {
    let workspace: MobileWorkspace
    @State private var query = ""
    @State private var pendingOnly = false

    var body: some View {
        List {
            Section {
                Toggle("Pending receipts only", isOn: $pendingOnly)
            }
            if !workspace.pending.isEmpty || pendingOnly {
                Section("Pending · \(workspace.pending.count)") {
                    if workspace.pending.isEmpty { Text("The receipt queue is empty.").foregroundStyle(.secondary) }
                    ForEach(workspace.pending) { item in
                        NavigationLink {
                            OutboxDetail(workspace: workspace, id: item.id, created: item.created)
                        } label: {
                            Label {
                                VStack(alignment: .leading, spacing: 5) {
                                    Text(item.issue ?? (item.workbookID == nil ? "Choose a workbook" : "Waiting to sync")).font(.subheadline.weight(.medium))
                                    Text(item.created, format: .dateTime.month().day().hour().minute()).font(.footnote).foregroundStyle(.secondary)
                                }
                            } icon: { Image(systemName: "tray.and.arrow.up").foregroundStyle(MobilePalette.forest) }
                        }
                    }
                }
            }
            if !pendingOnly {
                Section("Submitted receipts") {
                    if matching.isEmpty {
                        Text(query.isEmpty ? "Submitted receipts will appear here." : "No receipts match your search.").foregroundStyle(.secondary)
                    }
                    ForEach(matching) { receipt in
                        NavigationLink { ReceiptDetail(workspace: workspace, receipt: receipt) } label: { ReceiptRow(receipt: receipt, workspace: workspace) }
                    }
                }
            }
        }
        .scrollContentBackground(.hidden).background(MobilePalette.paper)
        .navigationTitle("History").searchable(text: $query, prompt: "Search receipts")
        .refreshable { await workspace.refresh() }
    }

    private var matching: [ReceiptRecord] {
        workspace.snapshot.receipts.filter { row in
            query.isEmpty || (row.merchant_name ?? "Receipt").localizedCaseInsensitiveContains(query)
                || stateTitle(row.state).localizedCaseInsensitiveContains(query)
        }
    }
}

private struct OutboxDetail: View {
    let workspace: MobileWorkspace
    let id: UUID
    let created: Date

    var body: some View {
        List {
            if let data = workspace.queuedImage(id), let image = UIImage(data: data) {
                Image(uiImage: image).resizable().scaledToFit().frame(maxHeight: 380)
                    .frame(maxWidth: .infinity).accessibilityLabel("Queued receipt preview")
            }
            Section {
                LabeledContent("Scanned", value: created.formatted(date: .abbreviated, time: .shortened))
                if let item = workspace.pending.first(where: { $0.id == id }) {
                    if let issue = item.issue { Text(issue).font(.footnote).foregroundStyle(.secondary) }
                    if item.scope == nil && !workspace.snapshot.targets.isEmpty {
                        Menu("Choose linked workbook") {
                            ForEach(workspace.snapshot.targets) { target in
                                Button(target.display_name) { Task { await workspace.assign(id, to: target.id) } }
                            }
                        }.disabled(workspace.syncing)
                    } else if item.scope == nil {
                        Text("Connect to a workspace with a linked workbook to send this receipt.")
                    } else if item.scope != workspace.connection?.scope {
                        Text("Reconnect the workspace that this receipt was assigned to.")
                    } else if item.issue != nil {
                        Button("Retry sync") { Task { await workspace.retryReceipt(id) } }.disabled(workspace.syncing)
                    } else if !workspace.snapshot.targets.contains(where: { $0.id == item.workbookID }) {
                        Text("This receipt will send when its workbook is ready to receive receipts again.")
                    } else {
                        Text("This receipt will send when the workspace is reachable.")
                    }
                } else {
                    Label("Sent to workspace", systemImage: "checkmark.circle")
                }
            }
        }.navigationTitle("Queued receipt").navigationBarTitleDisplayMode(.inline)
    }
}

private func stateTitle(_ value: String) -> String {
    switch value {
    case "COMMITTED": "Recorded"
    case "AWAITING_APPROVAL": "Awaiting approval"
    case "NEEDS_REVIEW", "DUPLICATE_REVIEW", "STALE_BASE": "Needs review"
    case "FAILED", "CANCELLED", "REJECTED", "EXPIRED": value.capitalized
    case "QUEUED": "Submitted"
    default: "Processing"
    }
}

private struct ReceiptRow: View {
    let receipt: ReceiptRecord
    var workspace: MobileWorkspace? = nil

    var body: some View {
        HStack(spacing: 12) {
            ReceiptThumb(receipt: receipt, workspace: workspace)
            VStack(alignment: .leading, spacing: 4) {
                Text(receipt.merchant_name ?? "Reading…").font(.subheadline.weight(.semibold))
                Text("\(stateTitle(receipt.state)) · from \(receipt.source)").font(.footnote).foregroundStyle(.secondary)
            }
            Spacer()
            VStack(alignment: .trailing, spacing: 4) {
                Text(sek(receipt.gross_minor)).font(.subheadline.monospacedDigit().weight(.semibold))
                Text(receipt.document_date ?? String(receipt.created_at.prefix(10)))
                    .font(.footnote.monospacedDigit()).foregroundStyle(.secondary)
            }
        }.padding(.vertical, 5)
    }
}

private struct ReceiptDetail: View {
    let workspace: MobileWorkspace
    let receipt: ReceiptRecord
    @State private var image: UIImage?
    @State private var imageUnavailable = false

    var body: some View {
        let current = workspace.snapshot.receipts.first { $0.id == receipt.id } ?? receipt
        List {
            Section("Receipt") {
                if let image {
                    Image(uiImage: image).resizable().scaledToFit().frame(maxHeight: 420)
                        .frame(maxWidth: .infinity).accessibilityLabel("Original receipt")
                } else if !workspace.connected {
                    Text("Reconnect to view the original receipt.").foregroundStyle(.secondary)
                } else if imageUnavailable {
                    Text("The original receipt is unavailable.").foregroundStyle(.secondary)
                } else {
                    ProgressView("Opening receipt…")
                }
                LabeledContent("Status", value: stateTitle(current.state))
                LabeledContent("Date", value: current.document_date ?? String(current.created_at.prefix(10)))
                if let workbook = workspace.snapshot.workbooks.first(where: { $0.id == current.workbook_id }) {
                    LabeledContent("Workbook", value: workbook.display_name)
                }
                if let minor = current.gross_minor {
                    LabeledContent("Amount", value: (Decimal(minor) / 100).formatted(.number.precision(.fractionLength(2))))
                }
            }
        }
        .navigationTitle(current.merchant_name ?? "Receipt").navigationBarTitleDisplayMode(.inline)
        .task(id: workspace.connected) {
            guard workspace.connected else { return }
            imageUnavailable = false
            do { image = downsample(try await workspace.receiptImage(receipt)); imageUnavailable = image == nil }
            catch { if !Task.isCancelled { imageUnavailable = true } }
        }
    }
}

private struct AgentScreen: View {
    let workspace: MobileWorkspace
    let pair: () -> Void
    @State private var question = ""
    @State private var draft: String?
    @FocusState private var focused: Bool
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    var body: some View {
        ScrollViewReader { scroll in
            ScrollView {
                VStack(alignment: .leading, spacing: 23) {
                    if workspace.snapshot.messages.isEmpty && draft == nil {
                        HStack(alignment: .top, spacing: 13) {
                            ReceiptGlyph().frame(width: 38).padding(5).background(MobilePalette.forest, in: .rect(cornerRadius: 12))
                            VStack(alignment: .leading, spacing: 7) {
                                Text("Ask about your receipts.").font(.system(.title2, design: .serif))
                                Text("LedgerFlow answers using the receipts and workbooks you can access.").font(.subheadline).foregroundStyle(.secondary)
                            }
                        }.padding(.bottom, 8)
                        Button("Which receipts need my attention?") { send("Which receipts need my attention?") }
                            .buttonStyle(.bordered).controlSize(.large).disabled(!canSend)
                    }
                    ForEach(workspace.snapshot.messages) { message in
                        messageView(message.text, fromUser: message.role == "user")
                    }
                    if let draft {
                        messageView(draft, fromUser: true)
                        ProgressView("Checking your workspace…").font(.footnote)
                    }
                    if !workspace.connected {
                        Text(workspace.connection == nil ? "Connect to your workspace to ask the agent a question." : "Reconnect to send messages. Previous replies are saved on this iPhone.")
                            .font(.footnote).foregroundStyle(.secondary)
                        if workspace.macLinked || workspace.connection == nil { Button("Connect to your Mac", action: pair).frame(minHeight: 44) }
                    } else if !workspace.chatAvailable {
                        Text("The connected workspace does not provide agent chat.").font(.footnote).foregroundStyle(.secondary)
                    }
                    Color.clear.frame(height: 1).id("latest")
                }.padding(22).frame(maxWidth: 650).frame(maxWidth: .infinity, alignment: .center)
            }
            .scrollDismissesKeyboard(.interactively)
            .onChange(of: workspace.snapshot.messages.last?.id) { withAnimation(reduceMotion ? nil : .easeOut(duration: 0.2)) { scroll.scrollTo("latest", anchor: .bottom) } }
            .onChange(of: draft) { if draft != nil { scroll.scrollTo("latest", anchor: .bottom) } }
        }
        .background(MobilePalette.paper.ignoresSafeArea())
        .safeAreaInset(edge: .bottom) {
            HStack(alignment: .bottom, spacing: 12) {
                TextField("Message LedgerFlow", text: $question, axis: .vertical).lineLimit(1...5)
                    .padding(12).focused($focused)
                Button { send(question) } label: {
                    Image(systemName: "arrow.up").font(.body.weight(.semibold)).foregroundStyle(.white)
                        .frame(width: 44, height: 44).background(MobilePalette.forest, in: .circle)
                }.accessibilityLabel("Send message")
                    .disabled(!canSend || question.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                    .opacity(canSend && !question.isEmpty ? 1 : 0.5)
            }.padding(9).background(.white, in: .rect(cornerRadius: 20))
                .overlay { RoundedRectangle(cornerRadius: 20).strokeBorder(MobilePalette.rule) }
                .padding(.horizontal, 16).padding(.vertical, 9).background(MobilePalette.paper)
        }
        .navigationTitle("Agent").refreshable { await workspace.refresh() }
    }

    // Tappable whenever there is text; ask() explains why it cannot send (offline, receipts-only pairing).
    private var canSend: Bool { !workspace.asking && draft == nil }

    private func send(_ text: String) {
        guard canSend else { return }
        draft = text
        focused = false
        Task {
            if await workspace.ask(text) { question = "" }
            else { question = text }
            draft = nil
        }
    }

    private func messageView(_ text: String, fromUser: Bool) -> some View {
        VStack(alignment: .leading, spacing: 7) {
            Text(fromUser ? "You" : "LedgerFlow").font(.caption.weight(.semibold)).foregroundStyle(.secondary)
            Text(text).font(.body).textSelection(.enabled)
        }.padding(fromUser ? 13 : 0)
            .background(fromUser ? MobilePalette.moss.opacity(0.37) : .clear, in: .rect(cornerRadius: 15))
            .frame(maxWidth: .infinity, alignment: fromUser ? .trailing : .leading)
    }
}


/// On-device OCR (Vision, accurate, sv/fr/en) so the receipt text is read, not only photographed.
func recognizeText(_ jpeg: Data) async -> String {
    await Task.detached(priority: .userInitiated) {
        guard let image = UIImage(data: jpeg)?.cgImage else { return "" }
        let request = VNRecognizeTextRequest()
        request.recognitionLevel = .accurate
        request.usesLanguageCorrection = true
        request.recognitionLanguages = ["sv-SE", "fr-FR", "en-US"]
        try? VNImageRequestHandler(cgImage: image).perform([request])
        return (request.results ?? []).compactMap { $0.topCandidates(1).first?.string }.joined(separator: "\n")
    }.value
}


func sek(_ minor: Int?) -> String {
    guard let minor else { return "–" }
    return (Double(minor) / 100).formatted(.currency(code: "SEK").presentation(.narrow))
}

/// Small image of the scanned receipt, fetched from the Mac.
private struct ReceiptThumb: View {
    let receipt: ReceiptRecord
    let workspace: MobileWorkspace?
    @State private var image: UIImage?
    var body: some View {
        Group {
            if let image { Image(uiImage: image).resizable().scaledToFill() }
            else { Image(systemName: "doc.text").foregroundStyle(MobilePalette.forest) }
        }
        .frame(width: 40, height: 52).clipShape(.rect(cornerRadius: 6))
        .background(MobilePalette.paper, in: .rect(cornerRadius: 6))
        .task(id: receipt.id) {
            if image == nil, let workspace, let data = try? await workspace.receiptImage(receipt) { image = UIImage(data: data) }
        }
    }
}

/// The firm's expense tracker: every receipt the Mac knows, totals by month.
private struct ExpensesScreen: View {
    let workspace: MobileWorkspace
    private var months: [(String, [ReceiptRecord])] {
        Dictionary(grouping: workspace.snapshot.receipts) { String(($0.document_date ?? $0.created_at).prefix(7)) }
            .sorted { $0.key > $1.key }
    }
    var body: some View {
        List {
            if workspace.snapshot.receipts.isEmpty {
                Text("No expenses yet. Scan a receipt to start.").foregroundStyle(.secondary)
            }
            ForEach(months, id: \.0) { month, items in
                let booked = items.filter { $0.state == "COMMITTED" }.compactMap(\.gross_minor).reduce(0, +)
                let open = items.filter { $0.state != "COMMITTED" }.compactMap(\.gross_minor).reduce(0, +)
                Section {
                    ForEach(items) { receipt in NavigationLink { ReceiptDetail(workspace: workspace, receipt: receipt) } label: { ReceiptRow(receipt: receipt, workspace: workspace) } }
                } header: {
                    HStack { Text(month); Spacer(); Text("Booked \(sek(booked)) · Open \(sek(open))").monospacedDigit() }
                }
            }
        }
        .navigationTitle("Expenses").refreshable { await workspace.refresh() }
    }
}
