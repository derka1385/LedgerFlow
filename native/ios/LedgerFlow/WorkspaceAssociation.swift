import Foundation

/// The fragment contains a one-use token. Persist only the origin and public certificate pin.
nonisolated struct WorkspaceAssociation {
    let endpoint: WorkspaceEndpoint
    let fingerprint: String
    let token: String

    init(_ value: URL) throws {
        guard value.scheme == "ledgerflow", value.host == "connect", value.user == nil, value.password == nil,
              let parts = URLComponents(url: value, resolvingAgainstBaseURL: false),
              let items = parts.queryItems,
              Set(items.map(\.name)).count == items.count,
              Set(items.map(\.name)).isSubset(of: ["origin", "pin", "mode"]),
              let origin = items.first(where: { $0.name == "origin" })?.value,
              let pin = items.first(where: { $0.name == "pin" })?.value,
              pin.range(of: "^[a-f0-9]{64}$", options: .regularExpression) != nil,
              let token = parts.fragment, token.range(of: "^[A-Za-z0-9_-]{32,100}$", options: .regularExpression) != nil else {
            throw WorkspaceEndpoint.InvalidAddress.malformed
        }
        endpoint = try WorkspaceEndpoint(origin)
        fingerprint = pin
        self.token = token
    }
}
