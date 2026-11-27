import Foundation
import Testing
@testable import LedgerFlow

struct WorkspaceEndpointTests {
    @Test func offlineReceiptsSurviveWorkspaceRelaunch() throws {
        let directory = URL.temporaryDirectory.appending(path: UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: directory) }
        let original = MobileWorkspace(storageURL: directory)
        let scannedPages = [Data([0xff, 0xd8, 1]), Data([0xff, 0xd8, 2]), Data([0xff, 0xd8, 3])]
        #expect(original.saveScans(scannedPages, workbookID: nil) == 3)
        let reopened = MobileWorkspace(storageURL: directory)
        #expect(reopened.pending.count == 3)
        #expect(reopened.pending.allSatisfy { $0.workbookID == nil && $0.scope == nil })
        #expect(reopened.pending.compactMap { reopened.queuedImage($0.id) } == scannedPages)
        #expect(reopened.availability == .unlinked)
    }
    @Test func httpsWorkspaceAndHashRoute() throws {
        let endpoint = try WorkspaceEndpoint("https://ledger.example")
        #expect(endpoint.url.absoluteString == "https://ledger.example/")
        #expect(endpoint.homeURL.fragment == "/home")
        #expect(endpoint.contains(URL(string: "https://ledger.example:443/api/v1/runs")!))
    }

    @Test(arguments: ["http://ledger.example", "http://127.0.0.1:5174", "file:///tmp/workbook", "javascript:alert(1)"])
    func releaseRejectsInsecureOrigins(_ input: String) {
        #expect(throws: (any Error).self) { try WorkspaceEndpoint(input) }
    }

    @Test(arguments: ["https://user:secret@ledger.example", "https://ledger.example/api/v1", "https://ledger.example/?invite=secret", "https://ledger.example/#/pair/token"])
    func configurationNeverContainsCredentialsOrPairingTokens(_ input: String) {
        #expect(throws: (any Error).self) { try WorkspaceEndpoint(input) }
    }

    @Test func onlySimulatorCanOptIntoHTTPLoopback() throws {
        #expect(try WorkspaceEndpoint("http://127.0.0.1:5174", allowingSimulatorLoopback: true).url.port == 5174)
        #expect(throws: (any Error).self) { try WorkspaceEndpoint("http://192.168.1.10:5174", allowingSimulatorLoopback: true) }
    }

    @Test func navigationAndDownloadsStayScoped() throws {
        let endpoint = try WorkspaceEndpoint("https://ledger.example")
        #expect(!endpoint.contains(URL(string: "https://attacker.example")!))
        #expect(!endpoint.contains(URL(string: "https://ledger.example:8443")!))
        #expect(!endpoint.contains(URL(string: "http://ledger.example")!))
        #expect(endpoint.permitsDownload(URL(string: "https://ledger.example/api/v1/artifacts/art_1/download")!))
        #expect(!endpoint.permitsDownload(URL(string: "https://attacker.example/api/v1/artifacts/art_1/download")!))
        #expect(!endpoint.permitsDownload(URL(string: "https://ledger.example/api/v1/auth/session")!))
    }
}
