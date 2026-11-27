import SwiftUI
import WebKit
import UIKit

@MainActor
struct WorkspaceWebView: UIViewRepresentable {
    let endpoint: WorkspaceEndpoint
    let session: WorkspaceSession

    func makeCoordinator() -> Coordinator { Coordinator(endpoint: endpoint, session: session) }

    func makeUIView(context: Context) -> WKWebView {
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .default()
        // The shared app owns auth, uploads and approval. No native execution bridge.
        let webView = WKWebView(frame: .zero, configuration: configuration)
        webView.navigationDelegate = context.coordinator
        webView.uiDelegate = context.coordinator
        webView.allowsBackForwardNavigationGestures = true
        webView.scrollView.contentInsetAdjustmentBehavior = .never
        webView.isOpaque = false
        webView.backgroundColor = .systemBackground
        webView.load(URLRequest(url: session.launchURL ?? endpoint.url))
        return webView
    }

    func updateUIView(_ uiView: WKWebView, context: Context) {}

    static func dismantleUIView(_ uiView: WKWebView, coordinator: Coordinator) {
        uiView.navigationDelegate = nil
        uiView.uiDelegate = nil
        uiView.stopLoading()
        coordinator.cancelDownloads()
    }

    @MainActor
    final class Coordinator: NSObject, WKNavigationDelegate, WKUIDelegate, WKDownloadDelegate {
        let endpoint: WorkspaceEndpoint
        let session: WorkspaceSession
        private var downloads: [ObjectIdentifier: (WKDownload, URL, URL)] = [:]
        private let downloadLimit: Int64 = 16 * 1024 * 1024

        init(endpoint: WorkspaceEndpoint, session: WorkspaceSession) { self.endpoint = endpoint; self.session = session }

        func webView(_ webView: WKWebView, didReceive challenge: URLAuthenticationChallenge, completionHandler: @escaping @MainActor @Sendable (URLSession.AuthChallengeDisposition, URLCredential?) -> Void) {
            guard session.fingerprint != nil else { completionHandler(.performDefaultHandling, nil); return }
            if let credential = WorkspaceTrust.credential(for: challenge, host: endpoint.url.host, fingerprint: session.fingerprint) { completionHandler(.useCredential, credential) }
            else { completionHandler(.cancelAuthenticationChallenge, nil) }
        }

        func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction, decisionHandler: @escaping @MainActor @Sendable (WKNavigationActionPolicy) -> Void) {
            guard let url = action.request.url else { decisionHandler(.cancel); return }
            if endpoint.contains(url) {
                decisionHandler(action.shouldPerformDownload ? (endpoint.permitsDownload(url) ? .download : .cancel) : .allow)
            } else {
                // External user-selected links open outside the authenticated app window.
                if action.navigationType == .linkActivated, url.scheme == "https" { UIApplication.shared.open(url) }
                decisionHandler(.cancel)
            }
        }

        func webView(_ webView: WKWebView, decidePolicyFor response: WKNavigationResponse, decisionHandler: @escaping @MainActor @Sendable (WKNavigationResponsePolicy) -> Void) {
            guard let url = response.response.url, endpoint.contains(url) else { decisionHandler(.cancel); return }
            decisionHandler(response.canShowMIMEType ? .allow : (endpoint.permitsDownload(url) ? .download : .cancel))
        }

        func webView(_ webView: WKWebView, didStartProvisionalNavigation navigation: WKNavigation!) { session.loading = true }
        func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) { session.loading = false; session.failure = nil; session.launchURL = nil }
        func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: any Error) { navigationFailed(error) }
        func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: any Error) { navigationFailed(error) }
        func webViewWebContentProcessDidTerminate(_ webView: WKWebView) {
            session.loading = false
            session.failure = "The workspace was interrupted. Reload to reconnect; your submitted receipts stay on the server."
        }

        private func navigationFailed(_ error: any Error) {
            guard (error as NSError).code != NSURLErrorCancelled else { return }
            session.loading = false
            session.failure = "The workspace could not be reached. Check your connection and the workspace address, then try again."
        }

        func webView(_ webView: WKWebView, navigationAction: WKNavigationAction, didBecome download: WKDownload) { download.delegate = self }
        func webView(_ webView: WKWebView, navigationResponse: WKNavigationResponse, didBecome download: WKDownload) { download.delegate = self }

        func download(_ download: WKDownload, willPerformHTTPRedirection response: HTTPURLResponse, newRequest request: URLRequest, decisionHandler: @escaping @MainActor @Sendable (WKDownload.RedirectPolicy) -> Void) {
            decisionHandler(request.url.map(endpoint.permitsDownload) == true ? .allow : .cancel)
        }

        func download(_ download: WKDownload, decideDestinationUsing response: URLResponse, suggestedFilename: String, completionHandler: @escaping @MainActor @Sendable (URL?) -> Void) {
            guard let source = response.url, endpoint.permitsDownload(source), response.expectedContentLength <= downloadLimit else {
                session.downloadError = "This download is unavailable or exceeds the 16 MB file limit."
                completionHandler(nil); return
            }
            do {
                let directory = FileManager.default.temporaryDirectory.appendingPathComponent("LedgerFlow-\(UUID().uuidString)", isDirectory: true)
                try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
                let name = URL(fileURLWithPath: suggestedFilename).lastPathComponent
                let file = directory.appendingPathComponent(name.isEmpty || name == "." || name == ".." ? "workbook.xlsx" : name)
                downloads[ObjectIdentifier(download)] = (download, file, directory)
                completionHandler(file)
            } catch { session.downloadError = "A temporary file could not be created for this download."; completionHandler(nil) }
        }

        func downloadDidFinish(_ download: WKDownload) {
            guard let (_, file, directory) = downloads.removeValue(forKey: ObjectIdentifier(download)) else { return }
            do {
                let attributes = try FileManager.default.attributesOfItem(atPath: file.path)
                guard let size = attributes[.size] as? NSNumber, size.int64Value > 0, size.int64Value <= downloadLimit else {
                    throw CocoaError(.fileReadTooLarge)
                }
                session.sharedFile = SharedWorkbook(url: file, directory: directory)
            } catch { try? FileManager.default.removeItem(at: directory); session.downloadError = "The downloaded file could not be shared. Please try again." }
        }

        func download(_ download: WKDownload, didFailWithError error: any Error, resumeData: Data?) {
            if let (_, _, directory) = downloads.removeValue(forKey: ObjectIdentifier(download)) { try? FileManager.default.removeItem(at: directory) }
            session.downloadError = "The download was interrupted. Reconnect and try again."
        }

        func cancelDownloads() {
            for (_, (download, _, directory)) in downloads {
                download.cancel { _ in try? FileManager.default.removeItem(at: directory) }
            }
            downloads.removeAll()
        }
    }
}

@MainActor
struct WorkbookShareSheet: UIViewControllerRepresentable {
    let url: URL
    func makeUIViewController(context: Context) -> UIActivityViewController { UIActivityViewController(activityItems: [url], applicationActivities: nil) }
    func updateUIViewController(_ uiViewController: UIActivityViewController, context: Context) {}
}
