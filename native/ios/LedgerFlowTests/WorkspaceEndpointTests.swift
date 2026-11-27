import Foundation
import Testing
@testable import LedgerFlow

struct WorkspaceEndpointTests {
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
