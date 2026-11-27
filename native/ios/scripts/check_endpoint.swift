import Foundation

// Portable policy checks, compiled on this Mac without importing any iOS UI framework.
@main
struct EndpointPolicyChecks {
    static func main() throws {
        var checks = 0
        func expect(_ value: Bool, _ label: String) {
            precondition(value, label)
            checks += 1
        }
        let origin = try WorkspaceEndpoint("https://ledger.example")
        expect(origin.homeURL.absoluteString == "https://ledger.example/#/home", "normalized hash route")
        expect(origin.contains(URL(string: "https://ledger.example:443/api/v1/runs")!), "default TLS port")
        for address in ["http://ledger.example", "http://localhost:5174", "file:///tmp/private", "javascript:alert(1)", "https://u:p@ledger.example", "https://ledger.example/api", "https://ledger.example/?invite=secret", "https://ledger.example/#/pair/token"] {
            do { _ = try WorkspaceEndpoint(address); preconditionFailure("accepted invalid origin: \(address)") }
            catch { checks += 1 }
        }
        let simulator = try WorkspaceEndpoint("http://127.0.0.1:5174", allowingSimulatorLoopback: true)
        expect(simulator.url.port == 5174, "explicit simulator loopback")
        do { _ = try WorkspaceEndpoint("http://192.168.1.2:5174", allowingSimulatorLoopback: true); preconditionFailure("accepted LAN HTTP") }
        catch { checks += 1 }
        expect(!origin.contains(URL(string: "https://attacker.example/")!), "foreign host")
        expect(!origin.contains(URL(string: "https://ledger.example:8443/")!), "different port")
        expect(!origin.contains(URL(string: "http://ledger.example/")!), "TLS downgrade")
        expect(origin.permitsDownload(URL(string: "https://ledger.example/api/v1/artifacts/a/download")!), "scoped artifact")
        expect(!origin.permitsDownload(URL(string: "https://ledger.example/api/v1/auth/session")!), "auth is not a download")
        expect(!origin.permitsDownload(URL(string: "https://attacker.example/api/v1/artifacts/a/download")!), "no external artifact")
        let pin = String(repeating: "a", count: 64)
        let token = String(repeating: "x", count: 43)
        let link = "ledgerflow://connect?origin=https%3A%2F%2F192.168.1.3%3A8766&pin=\(pin)&mode=workspace#\(token)"
        let association = try WorkspaceAssociation(URL(string: link)!)
        expect(association.endpoint.url.host == "192.168.1.3", "association extracts origin")
        expect(association.fingerprint == pin && association.token == token, "certificate pin and one-use fragment")
        for invalid in [link.replacingOccurrences(of: "ledgerflow:", with: "https:"), link.replacingOccurrences(of: "https%3A", with: "http%3A"), link.replacingOccurrences(of: pin, with: "bad"), link.replacingOccurrences(of: "#\(token)", with: ""), link.replacingOccurrences(of: "&mode=workspace", with: "&pin=\(pin)")] {
            do { _ = try WorkspaceAssociation(URL(string: invalid)!); preconditionFailure("accepted invalid association") }
            catch { checks += 1 }
        }
        print("\(checks) endpoint policy checks passed; iOS app compilation still requires Xcode and its SDK.")
    }
}
