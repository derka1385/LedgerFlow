import AuthenticationServices
import CryptoKit
import Foundation
import Observation
import Security
import UIKit

nonisolated struct OrvectIdentity: Decodable {
    let localId: String
    let email: String
    let displayName: String?
    let emailVerified: Bool?
}

@MainActor @Observable
final class OrvectAccount: NSObject, ASWebAuthenticationPresentationContextProviding {
    private(set) var identity: OrvectIdentity?
    private(set) var busy = false
    var notice: String?
    @ObservationIgnored private var webSession: ASWebAuthenticationSession?
    @ObservationIgnored private let transport = URLSession(configuration: .ephemeral)

    var googleAvailable: Bool { googleConfiguration != nil }

    private var apiKey: String? { configurationValue("LedgerFlowOrvectAPIKey") }
    private var googleConfiguration: (client: String, scheme: String)? {
        guard let id = configurationValue("LedgerFlowGoogleClientID"),
              id.range(of: #"^[A-Za-z0-9-]+\.apps\.googleusercontent\.com$"#, options: .regularExpression) != nil else { return nil }
        let scheme = id.split(separator: ".").reversed().joined(separator: ".")
        let registered = Bundle.main.object(forInfoDictionaryKey: "CFBundleURLTypes") as? [[String: Any]]
        guard registered?.contains(where: { ($0["CFBundleURLSchemes"] as? [String])?.contains(scheme) == true }) == true else { return nil }
        return (id, scheme)
    }

    private func configurationValue(_ key: String) -> String? {
        guard let value = Bundle.main.object(forInfoDictionaryKey: key) as? String, !value.isEmpty else { return nil }
        return value
    }

    func signIn(email: String, password: String) async {
        await perform {
            let session: FirebaseSession = try await self.firebase("signInWithPassword", body: ["email": email, "password": password, "returnSecureToken": true])
            let profile = try await self.lookup(session.idToken)
            if profile.emailVerified != true {
                try await self.sendVerification(session.idToken)
                self.notice = "Check your email for the verification link, then sign in again."
                return
            }
            try self.startSession(profile, refreshToken: session.refreshToken)
        }
    }

    func createAccount(email: String, password: String) async {
        await perform {
            let session: FirebaseSession = try await self.firebase("signUp", body: ["email": email, "password": password, "returnSecureToken": true])
            try await self.sendVerification(session.idToken)
            self.notice = "Account created. Verify your email, then sign in."
        }
    }

    func resetPassword(email: String) async {
        await perform {
            do {
                let _: EmptyResponse = try await self.firebase("sendOobCode", body: ["requestType": "PASSWORD_RESET", "email": email])
            } catch AccountError.provider("EMAIL_NOT_FOUND") {
                // Use the same response for existing and unknown addresses.
            }
            self.notice = "If that address has an account, you’ll receive a reset link."
        }
    }

    func signInWithGoogle() async {
        guard let google = googleConfiguration else {
            notice = "Google sign-in is unavailable in this build."
            return
        }
        await perform {
            let redirect = "\(google.scheme):/oauth2redirect"
            let state = try Self.random()
            let verifier = try Self.random()
            let challenge = Self.base64URL(Data(SHA256.hash(data: Data(verifier.utf8))))
            var authorization = URLComponents()
            authorization.scheme = "https"
            authorization.host = "accounts.google.com"
            authorization.path = "/o/oauth2/v2/auth"
            authorization.queryItems = [
                .init(name: "client_id", value: google.client), .init(name: "redirect_uri", value: redirect),
                .init(name: "response_type", value: "code"), .init(name: "scope", value: "openid email profile"),
                .init(name: "state", value: state), .init(name: "code_challenge", value: challenge),
                .init(name: "code_challenge_method", value: "S256"), .init(name: "prompt", value: "select_account"),
            ]
            guard let url = authorization.url else { throw AccountError.invalidResponse }
            let callback = try await self.authorize(url, scheme: google.scheme)
            guard let parts = URLComponents(url: callback, resolvingAgainstBaseURL: false), parts.scheme == google.scheme,
                  parts.host == nil, parts.path == "/oauth2redirect",
                  let query = parts.queryItems, query.filter({ $0.name == "state" }).count == 1,
                  query.first(where: { $0.name == "state" })?.value == state,
                  query.filter({ $0.name == "code" }).count == 1,
                  let code = query.first(where: { $0.name == "code" })?.value, !code.isEmpty else { throw AccountError.invalidResponse }
            var exchange = URLRequest(url: URL(string: "https://oauth2.googleapis.com/token")!, timeoutInterval: 20)
            exchange.httpMethod = "POST"
            exchange.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")
            exchange.httpBody = Data(Self.form(["client_id": google.client, "redirect_uri": redirect, "code": code,
                                               "code_verifier": verifier, "grant_type": "authorization_code"]).utf8)
            let googleToken: GoogleToken = try await self.send(exchange)
            let session: FirebaseSession = try await self.firebase("signInWithIdp", body: [
                "postBody": Self.form(["id_token": googleToken.id_token, "providerId": "google.com"]),
                "requestUri": "http://localhost", "returnSecureToken": true,
            ])
            try self.startSession(await self.lookup(session.idToken), refreshToken: session.refreshToken)
        }
    }

    func restore() async {
        guard identity == nil, !busy, let token = AccountKeychain.read(), let apiKey else { return }
        await perform {
            var components = URLComponents(string: "https://securetoken.googleapis.com/v1/token")!
            components.queryItems = [.init(name: "key", value: apiKey)]
            var request = URLRequest(url: components.url!, timeoutInterval: 20)
            request.httpMethod = "POST"
            request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")
            request.httpBody = Data(Self.form(["grant_type": "refresh_token", "refresh_token": token]).utf8)
            do {
                let session: RefreshSession = try await self.send(request)
                try self.startSession(await self.lookup(session.id_token), refreshToken: session.refresh_token)
            } catch AccountError.provider(let code) where ["TOKEN_EXPIRED", "INVALID_REFRESH_TOKEN", "USER_DISABLED", "USER_NOT_FOUND", "INVALID_GRANT"].contains(code) {
                AccountKeychain.remove()
                self.notice = "The Orvect session expired. Sign in again."
            }
        }
    }

    func signOut() {
        AccountKeychain.remove()
        identity = nil
        notice = nil
    }

    private func startSession(_ profile: OrvectIdentity, refreshToken: String) throws {
        guard profile.emailVerified == true else { throw AccountError.unverified }
        try AccountKeychain.store(refreshToken)
        identity = profile
    }

    private func lookup(_ idToken: String) async throws -> OrvectIdentity {
        let result: Lookup = try await firebase("lookup", body: ["idToken": idToken])
        guard let account = result.users.first else { throw AccountError.invalidResponse }
        return account
    }

    private func sendVerification(_ idToken: String) async throws {
        let _: EmptyResponse = try await firebase("sendOobCode", body: ["requestType": "VERIFY_EMAIL", "idToken": idToken])
    }

    private func firebase<T: Decodable>(_ endpoint: String, body: [String: Any]) async throws -> T {
        guard let apiKey else { throw AccountError.notConfigured }
        var components = URLComponents(string: "https://identitytoolkit.googleapis.com/v1/accounts:\(endpoint)")!
        components.queryItems = [.init(name: "key", value: apiKey)]
        var request = URLRequest(url: components.url!, timeoutInterval: 20)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: body)
        return try await send(request)
    }

    private func send<T: Decodable>(_ request: URLRequest) async throws -> T {
        let (data, response) = try await transport.data(for: request)
        guard let response = response as? HTTPURLResponse else { throw AccountError.invalidResponse }
        guard (200..<300).contains(response.statusCode) else {
            let error = try? JSONDecoder().decode(FirebaseError.self, from: data)
            let code = error?.error.message.components(separatedBy: " : ").first?.uppercased()
            throw AccountError.provider(code ?? "UNAVAILABLE")
        }
        return try JSONDecoder().decode(T.self, from: data)
    }

    private func perform(_ operation: () async throws -> Void) async {
        guard !busy else { return }
        busy = true
        notice = nil
        defer { busy = false }
        do { try await operation() }
        catch let error as ASWebAuthenticationSessionError where error.code == .canceledLogin { return }
        catch let error as AccountError { notice = error.localizedDescription }
        catch { notice = "Couldn’t reach Orvect. Check your connection and try again." }
    }

    private func authorize(_ url: URL, scheme: String) async throws -> URL {
        defer { webSession = nil }
        return try await withCheckedThrowingContinuation { continuation in
            let session = ASWebAuthenticationSession(url: url, callbackURLScheme: scheme) { callback, error in
                if let callback { continuation.resume(returning: callback) }
                else { continuation.resume(throwing: error ?? AccountError.invalidResponse) }
            }
            session.presentationContextProvider = self
            webSession = session
            if !session.start() { continuation.resume(throwing: AccountError.invalidResponse) }
        }
    }

    func presentationAnchor(for session: ASWebAuthenticationSession) -> ASPresentationAnchor {
        UIApplication.shared.connectedScenes.compactMap { ($0 as? UIWindowScene)?.keyWindow }.first ?? ASPresentationAnchor()
    }

    private static func random() throws -> String {
        var bytes = [UInt8](repeating: 0, count: 32)
        let status = bytes.withUnsafeMutableBytes { buffer in
            guard let address = buffer.baseAddress else { return errSecParam }
            return SecRandomCopyBytes(kSecRandomDefault, buffer.count, address)
        }
        guard status == errSecSuccess else { throw AccountError.invalidResponse }
        return base64URL(Data(bytes))
    }

    private static func base64URL(_ data: Data) -> String {
        data.base64EncodedString().replacingOccurrences(of: "+", with: "-").replacingOccurrences(of: "/", with: "_").replacingOccurrences(of: "=", with: "")
    }

    private static func form(_ values: [String: String]) -> String {
        let allowed = CharacterSet(charactersIn: "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._~")
        return values.map { key, value in "\(key)=\(value.addingPercentEncoding(withAllowedCharacters: allowed) ?? "")" }.joined(separator: "&")
    }
}

private nonisolated struct FirebaseSession: Decodable {
    let idToken: String
    let refreshToken: String

    private enum CodingKeys: String, CodingKey { case idToken, refreshToken, needConfirmation }

    init(from decoder: Decoder) throws {
        let values = try decoder.container(keyedBy: CodingKeys.self)
        if try values.decodeIfPresent(Bool.self, forKey: .needConfirmation) == true {
            throw AccountError.provider("ACCOUNT_EXISTS_WITH_DIFFERENT_CREDENTIAL")
        }
        idToken = try values.decode(String.self, forKey: .idToken)
        refreshToken = try values.decode(String.self, forKey: .refreshToken)
    }
}
private nonisolated struct RefreshSession: Decodable { let id_token: String; let refresh_token: String }
private nonisolated struct GoogleToken: Decodable { let id_token: String }
private nonisolated struct Lookup: Decodable { let users: [OrvectIdentity] }
private nonisolated struct EmptyResponse: Decodable {}
private nonisolated struct FirebaseError: Decodable {
    struct Detail: Decodable { let message: String }
    let error: Detail
}

private nonisolated enum AccountError: LocalizedError {
    case notConfigured, unverified, invalidResponse, keychain
    case provider(String)

    var errorDescription: String? {
        switch self {
        case .notConfigured: "Orvect account sign-in hasn’t been configured."
        case .unverified: "Verify your email before using this account."
        case .invalidResponse: "Sign-in didn’t finish. Try again."
        case .keychain: "This iPhone couldn’t save the account securely."
        case .provider("EMAIL_EXISTS"): "This email already has an Orvect account. Choose Sign in."
        case .provider("WEAK_PASSWORD"): "Choose a stronger password."
        case .provider("TOO_MANY_ATTEMPTS_TRY_LATER"): "Too many attempts. Try again later."
        case .provider("INVALID_LOGIN_CREDENTIALS"), .provider("INVALID_PASSWORD"), .provider("EMAIL_NOT_FOUND"): "Check your email and password."
        case .provider("FEDERATED_USER_ID_ALREADY_LINKED"), .provider("ACCOUNT_EXISTS_WITH_DIFFERENT_CREDENTIAL"): "Sign in with the method already linked to your Orvect account."
        default: "Orvect couldn’t complete sign-in. Try again."
        }
    }
}

private nonisolated enum AccountKeychain {
    private static var entry: [String: Any] {
        [kSecClass as String: kSecClassGenericPassword, kSecAttrService as String: "app.ledgerflow.identity", kSecAttrAccount as String: "orvect-firebase"]
    }

    static func read() -> String? {
        var query = entry
        query[kSecReturnData as String] = true
        query[kSecMatchLimit as String] = kSecMatchLimitOne
        var result: CFTypeRef?
        guard SecItemCopyMatching(query as CFDictionary, &result) == errSecSuccess, let data = result as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }

    static func store(_ token: String) throws {
        let data = Data(token.utf8)
        let result = SecItemUpdate(entry as CFDictionary, [kSecValueData as String: data] as CFDictionary)
        if result == errSecSuccess { return }
        guard result == errSecItemNotFound else { throw AccountError.keychain }
        var query = entry
        query[kSecValueData as String] = data
        query[kSecAttrAccessible as String] = kSecAttrAccessibleWhenUnlockedThisDeviceOnly
        guard SecItemAdd(query as CFDictionary, nil) == errSecSuccess else { throw AccountError.keychain }
    }

    static func remove() { SecItemDelete(entry as CFDictionary) }
}
