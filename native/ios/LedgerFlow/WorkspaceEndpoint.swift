import Foundation

/// A workspace is an origin, never an API credential or an arbitrary page URL.
nonisolated struct WorkspaceEndpoint: Equatable, Sendable {
    let url: URL

    enum InvalidAddress: Error, LocalizedError {
        case malformed, secureOriginRequired, originOnly
        var errorDescription: String? {
            switch self {
            case .malformed: "Enter a valid workspace address."
            case .secureOriginRequired: "Use the HTTPS address provided by your team."
            case .originOnly: "Enter the workspace origin without a path, query, fragment or credentials."
            }
        }
    }

    init(_ address: String, allowingSimulatorLoopback: Bool = false) throws {
        guard var parts = URLComponents(string: address.trimmingCharacters(in: .whitespacesAndNewlines)),
              let scheme = parts.scheme?.lowercased(), let host = parts.host, !host.isEmpty,
              parts.port.map({ (1...65535).contains($0) }) ?? true else {
            throw InvalidAddress.malformed
        }
        let loopback = ["localhost", "127.0.0.1", "::1"].contains(Self.normalizedHost(host))
        guard scheme == "https" || (allowingSimulatorLoopback && loopback && scheme == "http") else {
            throw InvalidAddress.secureOriginRequired
        }
        guard parts.user == nil, parts.password == nil, parts.query == nil, parts.fragment == nil,
              parts.path.isEmpty || parts.path == "/" else { throw InvalidAddress.originOnly }
        parts.scheme = scheme
        parts.host = host.lowercased()
        parts.path = "/"
        guard let url = parts.url else { throw InvalidAddress.malformed }
        self.url = url
    }

    var homeURL: URL {
        var parts = URLComponents(url: url, resolvingAgainstBaseURL: false)!
        parts.fragment = "/home"
        return parts.url! // Validated origin plus a constant fragment.
    }

    func contains(_ other: URL) -> Bool {
        guard let host = other.host, let expected = url.host,
              other.user == nil, other.password == nil else { return false }
        return other.scheme?.lowercased() == url.scheme && Self.normalizedHost(host) == Self.normalizedHost(expected)
            && Self.effectivePort(other) == Self.effectivePort(url)
    }

    func permitsDownload(_ other: URL) -> Bool {
        contains(other) && other.path.hasPrefix("/api/v1/artifacts/") && other.path.hasSuffix("/download")
    }

    private static func normalizedHost(_ host: String) -> String {
        host.lowercased().trimmingCharacters(in: CharacterSet(charactersIn: "[]"))
    }

    private static func effectivePort(_ url: URL) -> Int { url.port ?? (url.scheme == "https" ? 443 : 80) }
}
