import AppKit
import UniformTypeIdentifiers
import WebKit

@MainActor
final class LedgerFlowDelegate: NSObject, NSApplicationDelegate, WKNavigationDelegate, WKUIDelegate, WKDownloadDelegate {
    private var window: NSWindow?
    private var webView: WKWebView?
    private var origin: URL?
    private var fingerprint: String?
    private var runtime: Process?
    private var startup: Task<Void, Never>?
    private var statusDirectory: URL?
    private var startupLabel: NSTextField?
    private var retryButton: NSButton?

    func applicationDidFinishLaunching(_ notification: Notification) {
        let screen = NSScreen.main?.visibleFrame ?? NSRect(x: 0, y: 0, width: 1440, height: 900)
        let size = NSSize(width: min(1600, screen.width * 0.94), height: min(1040, screen.height * 0.94))
        let win = NSWindow(contentRect: NSRect(origin: .zero, size: size), styleMask: [.titled, .closable, .miniaturizable, .resizable], backing: .buffered, defer: false)
        win.title = "LedgerFlow"
        win.isReleasedWhenClosed = false
        win.minSize = NSSize(width: min(1060, screen.width), height: min(700, screen.height))
        win.center()
        win.setFrameAutosaveName("LedgerFlowAgentWorkspaceV2")
        window = win
        configureMenu()
        showStartup()
        win.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        connect()
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { false }
    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        window?.makeKeyAndOrderFront(nil)
        return true
    }
    func applicationWillTerminate(_ notification: Notification) {
        startup?.cancel()
        if runtime?.isRunning == true { runtime?.terminate() }
        if let statusDirectory { try? FileManager.default.removeItem(at: statusDirectory) }
    }

    private func showStartup(message: String = "Ouverture de votre espace…", retry: Bool = false) {
        guard let window else { return }
        let root = NSView()
        let stack = NSStackView()
        stack.orientation = .vertical; stack.alignment = .centerX; stack.spacing = 18
        stack.translatesAutoresizingMaskIntoConstraints = false
        let image = NSImageView(image: NSApp.applicationIconImage)
        image.imageScaling = .scaleProportionallyUpOrDown
        image.widthAnchor.constraint(equalToConstant: 86).isActive = true
        image.heightAnchor.constraint(equalToConstant: 86).isActive = true
        stack.addArrangedSubview(image)
        let title = NSTextField(labelWithString: "LedgerFlow")
        title.font = .systemFont(ofSize: 26, weight: .semibold)
        stack.addArrangedSubview(title)
        let label = NSTextField(wrappingLabelWithString: message)
        label.alignment = .center; label.textColor = .secondaryLabelColor
        label.font = .systemFont(ofSize: 14)
        label.widthAnchor.constraint(lessThanOrEqualToConstant: 460).isActive = true
        startupLabel = label; stack.addArrangedSubview(label)
        if retry {
            let button = NSButton(title: "Réessayer", target: self, action: #selector(restartRuntime))
            button.bezelStyle = .rounded
            retryButton = button; stack.addArrangedSubview(button)
        } else {
            let progress = NSProgressIndicator()
            progress.style = .spinning; progress.startAnimation(nil)
            stack.addArrangedSubview(progress)
        }
        root.addSubview(stack)
        NSLayoutConstraint.activate([stack.centerXAnchor.constraint(equalTo: root.centerXAnchor), stack.centerYAnchor.constraint(equalTo: root.centerYAnchor), stack.leadingAnchor.constraint(greaterThanOrEqualTo: root.leadingAnchor, constant: 24)])
        window.contentView = root
    }

    private func connect() {
        if let configured = Bundle.main.object(forInfoDictionaryKey: "LedgerFlowOrigin") as? String, let url = URL(string: configured), url.scheme == "https" || (url.scheme == "http" && ["localhost","127.0.0.1","::1"].contains(url.host ?? "")) {
            origin = url; loadWorkspace(url); return
        }
        guard let repository = Bundle.main.object(forInfoDictionaryKey: "LedgerFlowRepository") as? String else {
            showStartup(message: "Le dossier de l’application est introuvable. Reconstruisez LedgerFlow depuis son projet.", retry: true); return
        }
        let root = URL(fileURLWithPath: repository)
        let python = root.appendingPathComponent(".venv/bin/python")
        let script = root.appendingPathComponent("native/desktop/server.py")
        guard FileManager.default.isExecutableFile(atPath: python.path), FileManager.default.fileExists(atPath: script.path) else {
            showStartup(message: "Le moteur local est introuvable. Conservez l’application et son projet sur ce Mac.", retry: true); return
        }
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent("LedgerFlow-\(UUID().uuidString)")
        let data = root.appendingPathComponent(".ledgerflow-local", isDirectory: true)
        let status = directory.appendingPathComponent("ready.json")
        do {
            try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true, attributes: [.posixPermissions: 0o700])
            try FileManager.default.createDirectory(at: data, withIntermediateDirectories: true, attributes: [.posixPermissions: 0o700])
            let process = Process()
            process.executableURL = python
            process.arguments = [script.path, "--data-dir", data.path, "--status-file", status.path, "--parent-pid", String(ProcessInfo.processInfo.processIdentifier), "--allow-samples"]
            process.currentDirectoryURL = root
            var environment = ProcessInfo.processInfo.environment
            environment["PATH"] = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
            process.environment = environment
            let log = data.appendingPathComponent("runtime.log")
            FileManager.default.createFile(atPath: log.path, contents: nil, attributes: [.posixPermissions: 0o600])
            process.standardError = try FileHandle(forWritingTo: log)
            process.standardOutput = FileHandle.nullDevice
            runtime = process; statusDirectory = directory
            try process.run()
            startup = Task { [weak self] in
                for _ in 0..<150 {
                    guard !Task.isCancelled, let self else { return }
                    if let bytes = try? Data(contentsOf: status),
                       let value = try? JSONSerialization.jsonObject(with: bytes) as? [String: Any],
                       let address = value["origin"] as? String, let url = URL(string: address),
                       let pin = value["pin"] as? String, pin.count == 64,
                       let token = value["bootstrap"] as? String {
                        self.origin = url; self.fingerprint = pin
                        var parts = URLComponents(url: url, resolvingAgainstBaseURL: false)!
                        parts.fragment = "/bootstrap/\(token)"
                        self.loadWorkspace(parts.url!); return
                    }
                    if !process.isRunning { break }
                    try? await Task.sleep(for: .milliseconds(200))
                }
                guard !Task.isCancelled else { return }
                self?.showStartup(message: "Le moteur local n’a pas démarré. Le diagnostic est conservé dans .ledgerflow-local/runtime.log, dans le projet.", retry: true)
            }
        } catch { showStartup(message: "LedgerFlow n’a pas pu ouvrir son moteur local. Vérifiez que le projet est accessible.", retry: true) }
    }

    private func loadWorkspace(_ url: URL) {
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .default()
        let view = WKWebView(frame: .zero, configuration: configuration)
        view.navigationDelegate = self; view.uiDelegate = self
        view.allowsBackForwardNavigationGestures = true
        webView = view; window?.contentView = view
        view.load(URLRequest(url: url))
    }

    @objc private func restartRuntime() {
        startup?.cancel()
        if runtime?.isRunning == true { runtime?.terminate() }
        showStartup(); connect()
    }
    @objc private func reloadWorkspace() { if let webView { webView.reload() } else { restartRuntime() } }
    @objc private func openProject() {
        if let path = Bundle.main.object(forInfoDictionaryKey: "LedgerFlowRepository") as? String { NSWorkspace.shared.open(URL(fileURLWithPath: path)) }
    }
    @objc private func showWorkspace() { window?.makeKeyAndOrderFront(nil) }
    private func configureMenu() {
        let main = NSMenu()
        let app = NSMenuItem(); let menu = NSMenu()
        menu.addItem(withTitle: "Quitter LedgerFlow", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        app.submenu = menu; main.addItem(app)
        let file = NSMenuItem(); let fileMenu = NSMenu(title: "Fichier")
        let close = fileMenu.addItem(withTitle: "Fermer la fenêtre", action: #selector(NSWindow.performClose(_:)), keyEquivalent: "w"); close.target = window
        file.submenu = fileMenu; main.addItem(file)
        let edit = NSMenuItem(); let editMenu = NSMenu(title: "Édition")
        for (title, selector, key) in [("Annuler", "undo:", "z"), ("Couper", "cut:", "x"), ("Copier", "copy:", "c"), ("Coller", "paste:", "v"), ("Tout sélectionner", "selectAll:", "a")] {
            editMenu.addItem(withTitle: title, action: Selector(selector), keyEquivalent: key)
        }
        edit.submenu = editMenu; main.addItem(edit)
        let view = NSMenuItem(); let viewMenu = NSMenu(title: "Présentation")
        let show = viewMenu.addItem(withTitle: "Afficher l’espace", action: #selector(showWorkspace), keyEquivalent: "0"); show.target = self
        let reload = viewMenu.addItem(withTitle: "Recharger l’espace", action: #selector(reloadWorkspace), keyEquivalent: "r"); reload.target = self
        let project = viewMenu.addItem(withTitle: "Ouvrir le dossier du projet", action: #selector(openProject), keyEquivalent: ""); project.target = self
        view.submenu = viewMenu; main.addItem(view); NSApp.mainMenu = main
    }

    private func isApplicationURL(_ url: URL) -> Bool {
        guard let origin else { return false }
        return url.scheme == origin.scheme && url.host == origin.host && (url.port ?? 443) == (origin.port ?? 443) && url.user == nil && url.password == nil
    }
    private func isDownload(_ url: URL) -> Bool { isApplicationURL(url) && url.path.hasPrefix("/api/v1/artifacts/") && url.path.hasSuffix("/download") }

    func webView(_ webView: WKWebView, didReceive challenge: URLAuthenticationChallenge, completionHandler: @escaping @MainActor @Sendable (URLSession.AuthChallengeDisposition, URLCredential?) -> Void) {
        guard fingerprint != nil else { completionHandler(.performDefaultHandling, nil); return }
        if let credential = WorkspaceTrust.credential(for: challenge, host: origin?.host, fingerprint: fingerprint) { completionHandler(.useCredential, credential) }
        else { completionHandler(.cancelAuthenticationChallenge, nil) }
    }
    func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction, decisionHandler: @escaping @MainActor @Sendable (WKNavigationActionPolicy) -> Void) {
        guard let url = action.request.url else { decisionHandler(.cancel); return }
        if isApplicationURL(url) { decisionHandler(action.shouldPerformDownload ? (isDownload(url) ? .download : .cancel) : .allow) }
        else { if url.scheme == "https", action.navigationType == .linkActivated { NSWorkspace.shared.open(url) }; decisionHandler(.cancel) }
    }
    func webView(_ webView: WKWebView, decidePolicyFor response: WKNavigationResponse, decisionHandler: @escaping @MainActor @Sendable (WKNavigationResponsePolicy) -> Void) {
        guard let url = response.response.url, isApplicationURL(url) else { decisionHandler(.cancel); return }
        decisionHandler(response.canShowMIMEType ? .allow : (isDownload(url) ? .download : .cancel))
    }
    func webView(_ webView: WKWebView, navigationAction: WKNavigationAction, didBecome download: WKDownload) { download.delegate = self }
    func webView(_ webView: WKWebView, navigationResponse: WKNavigationResponse, didBecome download: WKDownload) { download.delegate = self }
    func download(_ download: WKDownload, willPerformHTTPRedirection response: HTTPURLResponse, newRequest request: URLRequest, decisionHandler: @escaping @MainActor @Sendable (WKDownload.RedirectPolicy) -> Void) {
        decisionHandler(request.url.map(isDownload) == true ? .allow : .cancel)
    }
    func download(_ download: WKDownload, decideDestinationUsing response: URLResponse, suggestedFilename: String, completionHandler: @escaping @MainActor @Sendable (URL?) -> Void) {
        guard let window, let url = response.url, isDownload(url) else { completionHandler(nil); return }
        let panel = NSSavePanel(); panel.nameFieldStringValue = URL(fileURLWithPath: suggestedFilename).lastPathComponent
        let local = URL(fileURLWithPath: NSHomeDirectory()).appendingPathComponent("Document", isDirectory: true)
        panel.directoryURL = FileManager.default.fileExists(atPath: local.path) ? local : URL(fileURLWithPath: NSHomeDirectory()).appendingPathComponent("Coding", isDirectory: true)
        panel.beginSheetModal(for: window) { result in completionHandler(result == .OK ? panel.url : nil) }
    }
    func webView(_ webView: WKWebView, runOpenPanelWith parameters: WKOpenPanelParameters, initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping @MainActor @Sendable ([URL]?) -> Void) {
        guard let window else { completionHandler(nil); return }
        let panel = NSOpenPanel(); panel.canChooseDirectories = false; panel.allowsMultipleSelection = false
        panel.allowedContentTypes = [.jpeg, .png, .pdf] + [UTType(filenameExtension: "xlsx")].compactMap { $0 }
        panel.beginSheetModal(for: window) { result in completionHandler(result == .OK ? panel.urls : nil) }
    }
    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: any Error) {
        guard (error as NSError).code != NSURLErrorCancelled else { return }
        showStartup(message: "La connexion au moteur a été interrompue. Vos dossiers restent enregistrés sur ce Mac.", retry: true)
    }
}

@main @MainActor struct LedgerFlowApp {
    static func main() {
        let app = NSApplication.shared; let delegate = LedgerFlowDelegate()
        app.setActivationPolicy(.regular); app.delegate = delegate
        withExtendedLifetime(delegate) { app.run() }
    }
}
