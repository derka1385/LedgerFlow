import CryptoKit
import Foundation
import Observation

nonisolated struct MobileIdentity: Codable, Equatable {
    let user_id: String
    let tenant_id: String
    let role: String
    let csrf_token: String
    let backend: String?
}

nonisolated struct Workbook: Codable, Identifiable {
    let workbook_id: String
    let display_name: String
    let status: String
    let version_count: Int?
    var id: String { workbook_id }
}

nonisolated struct CaptureTarget: Codable, Identifiable {
    let workbook_id: String
    let display_name: String
    let base_version_id: String
    let base_sha256: String
    let mapping_id: String
    let mapping_version: Int
    var id: String { workbook_id }
}

nonisolated struct ReceiptRecord: Codable, Identifiable {
    let run_id: String
    let document_id: String
    let workbook_id: String
    let merchant_name: String?
    let gross_minor: Int?
    let document_date: String?
    let created_at: String
    let state: String
    var id: String { run_id }
}

nonisolated struct AgentMessage: Codable, Identifiable {
    let id: String
    let role: String
    let text: String
    let created_at: String
}

nonisolated struct MobileSnapshot: Codable {
    var workbooks: [Workbook] = []
    var targets: [CaptureTarget] = []
    var receipts: [ReceiptRecord] = []
    var messages: [AgentMessage] = []
    var updated: Date?
}

nonisolated struct SavedConnection: Codable {
    let origin: String
    let pin: String?
    let scope: String
}

nonisolated struct PendingReceipt: Codable, Identifiable {
    let id: UUID
    let created: Date
    var workbookID: String?
    var scope: String?
    var documentID: String?
    var submission: CaptureTarget?
    var issue: String?
}

nonisolated struct MobileAPIError: LocalizedError {
    let status: Int
    let code: String?

    var errorDescription: String? {
        switch (status, code) {
        case (_, "PAIRING_INVALID"): "This code has expired. Generate a new one on your Mac."
        case (_, "INVITE_INVALID"): "This invitation could not be accepted. Check the code and try again."
        case (_, "ALREADY_COMMITTED"): "This receipt has already been recorded."
        case (_, "MAPPING_REQUIRED"): "This workbook needs to be set up before it can receive receipts."
        case (401, _): "Your session has ended. Reconnect to continue."
        case (403, _): "Your account does not have access to this action."
        case (404, _): "This feature is unavailable on the connected workspace."
        case (409, _): "The workspace has changed. Refresh and try again."
        case (413, _): "The receipt is too large to upload."
        case (429, _): "The workspace is busy. Try again in a moment."
        case (503, _): "The service is temporarily unavailable."
        default: "The workspace could not complete this request."
        }
    }
}

private nonisolated final class MobileTransport: NSObject, URLSessionDelegate, URLSessionTaskDelegate {
    let endpoint: WorkspaceEndpoint
    let pin: String?

    init(endpoint: WorkspaceEndpoint, pin: String?) {
        self.endpoint = endpoint
        self.pin = pin
    }

    func urlSession(_ session: URLSession, didReceive challenge: URLAuthenticationChallenge,
                    completionHandler: @escaping @Sendable (URLSession.AuthChallengeDisposition, URLCredential?) -> Void) {
        guard challenge.protectionSpace.authenticationMethod == NSURLAuthenticationMethodServerTrust, pin != nil else {
            completionHandler(.performDefaultHandling, nil)
            return
        }
        if let credential = WorkspaceTrust.credential(for: challenge, host: endpoint.url.host, fingerprint: pin) {
            completionHandler(.useCredential, credential)
        } else {
            completionHandler(.cancelAuthenticationChallenge, nil)
        }
    }

    func urlSession(_ session: URLSession, task: URLSessionTask, willPerformHTTPRedirection response: HTTPURLResponse,
                    newRequest request: URLRequest, completionHandler: @escaping @Sendable (URLRequest?) -> Void) {
        completionHandler(nil)
    }
}

private struct MobileAPI {
    let endpoint: WorkspaceEndpoint
    let transport: URLSession

    init(endpoint: WorkspaceEndpoint, pin: String?) {
        self.endpoint = endpoint
        let configuration = URLSessionConfiguration.default
        configuration.urlCache = nil
        configuration.requestCachePolicy = .reloadIgnoringLocalCacheData
        configuration.timeoutIntervalForRequest = 8
        transport = URLSession(configuration: configuration, delegate: MobileTransport(endpoint: endpoint, pin: pin), delegateQueue: nil)
    }

    func request<T: Decodable>(_ path: String, method: String = "GET", body: Data? = nil,
                               contentType: String = "application/json", csrf: String? = nil,
                               key: String? = nil, timeout: TimeInterval = 8) async throws -> T {
        let data = try await bytes(path, method: method, body: body, contentType: contentType, csrf: csrf, key: key, timeout: timeout)
        return try JSONDecoder().decode(T.self, from: data)
    }

    func bytes(_ path: String, method: String = "GET", body: Data? = nil,
               contentType: String = "application/json", csrf: String? = nil,
               key: String? = nil, timeout: TimeInterval = 8) async throws -> Data {
        guard let url = URL(string: path, relativeTo: endpoint.url)?.absoluteURL, endpoint.contains(url) else {
            throw WorkspaceEndpoint.InvalidAddress.originOnly
        }
        var request = URLRequest(url: url, timeoutInterval: timeout)
        request.httpMethod = method
        request.httpBody = body
        request.setValue("en", forHTTPHeaderField: "Accept-Language")
        if body != nil { request.setValue(contentType, forHTTPHeaderField: "Content-Type") }
        if let csrf { request.setValue(csrf, forHTTPHeaderField: "X-CSRF-Token") }
        if let key { request.setValue(key, forHTTPHeaderField: "Idempotency-Key") }
        let (data, response) = try await transport.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw URLError(.badServerResponse) }
        guard (200..<300).contains(http.statusCode) else {
            struct Envelope: Decodable {
                struct Detail: Decodable { let code: String? }
                let error: Detail
            }
            let code = (try? JSONDecoder().decode(Envelope.self, from: data))?.error.code
            throw MobileAPIError(status: http.statusCode, code: code)
        }
        return data
    }
}

struct WorkbookVersion: Decodable {
    let artifact_id: String
    let sha256: String
    let is_current: Bool
}

private nonisolated struct Items<T: Decodable>: Decodable { let items: [T] }
private nonisolated struct RemoteDocument: Decodable { let document_id: String; let status: String?; let image_url: String? }
private nonisolated struct CreatedRun: Decodable { let run_id: String }

@Observable
final class MobileWorkspace {
    enum Availability: Equatable { case unlinked, checking, connected, unreachable, expired }

    private(set) var snapshot = MobileSnapshot()
    private(set) var pending: [PendingReceipt] = []
    private(set) var connection: SavedConnection?
    private(set) var availability: Availability = .unlinked
    private(set) var busy = false
    private(set) var syncing = false
    private(set) var asking = false
    private(set) var chatAvailable = true
    var notice: String?
    var profile: String? = UserDefaults.standard.string(forKey: "ledgerflow.mobile.profile")
    @ObservationIgnored private var api: MobileAPI?
    @ObservationIgnored private var identity: MobileIdentity?
    @ObservationIgnored private var refreshing = false
    @ObservationIgnored private var generation = UUID()
    @ObservationIgnored private var chatRetry: (text: String, key: String)?
    @ObservationIgnored private let root: URL

    init(storageURL: URL = URL.applicationSupportDirectory.appending(path: "LedgerFlowMobile", directoryHint: .isDirectory)) {
        root = storageURL
        pending = read([PendingReceipt].self, "outbox.json") ?? []
        if let saved = read(SavedConnection.self, "connection.json"),
           let endpoint = try? WorkspaceEndpoint(saved.origin, allowingSimulatorLoopback: Self.allowsLoopback) {
            connection = saved
            snapshot = read(MobileSnapshot.self, cacheName(saved.scope)) ?? MobileSnapshot()
            availability = .checking
            api = MobileAPI(endpoint: endpoint, pin: saved.pin)
        } else if let origin = UserDefaults.standard.string(forKey: "ledgerflow.workspaceOrigin"),
                  let cachedEndpoint = try? WorkspaceEndpoint(origin, allowingSimulatorLoopback: Self.allowsLoopback) {
            // A previous build signed in via WebKit. Keep the address only as a sign-in hint.
            legacyOrigin = cachedEndpoint.url.absoluteString
        }
    }

    private(set) var legacyOrigin: String?

    static var allowsLoopback: Bool {
        #if DEBUG && targetEnvironment(simulator)
        true
        #else
        false
        #endif
    }

    var canEnter: Bool { connection != nil || profile != nil }
    var connected: Bool { availability == .connected }
    var macLinked: Bool { connection?.pin != nil }

    func createProfile(_ name: String) {
        let clean = name.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !clean.isEmpty else { return }
        profile = clean
        UserDefaults.standard.set(clean, forKey: "ledgerflow.mobile.profile")
    }

    func pair(_ link: String) async -> Bool {
        guard !busy, !syncing, !asking else {
            notice = "Wait for the current workspace activity to finish, then try again."
            return false
        }
        do {
            guard let url = URL(string: link.trimmingCharacters(in: .whitespacesAndNewlines)) else { throw WorkspaceEndpoint.InvalidAddress.malformed }
            let association = try WorkspaceAssociation(url)
            try await open(association.endpoint, pin: association.fingerprint, path: "/api/v1/desktop/pairings/exchange", payload: ["token": association.token])
            return true
        } catch {
            notice = message(for: error)
            return false
        }
    }

    func signIn(origin: String, invite: String) async -> Bool {
        guard !busy, !syncing, !asking else {
            notice = "Wait for the current workspace activity to finish, then try again."
            return false
        }
        do {
            let endpoint = try WorkspaceEndpoint(origin, allowingSimulatorLoopback: Self.allowsLoopback)
            try await open(endpoint, pin: nil, path: "/api/v1/auth/session", payload: ["invite_token": invite])
            return true
        } catch {
            notice = message(for: error)
            return false
        }
    }

    private func open(_ endpoint: WorkspaceEndpoint, pin: String?, path: String, payload: [String: String]) async throws {
        busy = true
        defer { busy = false }
        let candidate = MobileAPI(endpoint: endpoint, pin: pin)
        do {
            let info: MobileIdentity = try await candidate.request(path, method: "POST", body: encode(payload), key: UUID().uuidString)
            let scope = scopeFor(endpoint: endpoint, pin: pin, identity: info)
            let saved = SavedConnection(origin: endpoint.url.absoluteString, pin: pin, scope: scope)
            try write(saved, "connection.json")
            api?.transport.invalidateAndCancel()
            generation = UUID()
            api = candidate
            identity = info
            connection = saved
            snapshot = read(MobileSnapshot.self, cacheName(scope)) ?? MobileSnapshot()
            availability = .checking
            chatAvailable = true
            chatRetry = nil
        } catch {
            candidate.transport.invalidateAndCancel()
            throw error
        }
        // A foreground refresh may still be unwinding after replacing the connection.
    }

    func refresh() async {
        guard !busy, !refreshing, !syncing, let api, let connection else { return }
        refreshing = true
        defer { refreshing = false }
        let epoch = generation
        do {
            let info: MobileIdentity = try await api.request("/api/v1/auth/session")
            guard epoch == generation else { return }
            guard scopeFor(endpoint: api.endpoint, pin: connection.pin, identity: info) == connection.scope else {
                identity = nil
                availability = .expired
                return
            }
            identity = info
            availability = .connected
            let targets: Items<CaptureTarget> = try await api.request("/api/v1/upload-targets")
            let receipts: Items<ReceiptRecord> = try await api.request("/api/v1/runs")
            let workbooks: [Workbook]
            if info.role == "employee" {
                workbooks = targets.items.map { Workbook(workbook_id: $0.id, display_name: $0.display_name, status: "ready", version_count: nil) }
            } else {
                let result: Items<Workbook> = try await api.request("/api/v1/workbooks")
                workbooks = result.items
            }
            guard epoch == generation else { return }
            snapshot.workbooks = workbooks
            snapshot.targets = targets.items
            snapshot.receipts = receipts.items
            snapshot.updated = .now
            if !asking {
                do {
                    let result: Items<AgentMessage> = try await api.request("/api/v1/assistant/messages")
                    guard epoch == generation else { return }
                    chatAvailable = true
                    if !asking { snapshot.messages = result.items }
                } catch let error as MobileAPIError where [403, 404].contains(error.status) {
                    if epoch == generation { chatAvailable = false }
                }
            }
            guard epoch == generation else { return }
            try write(snapshot, cacheName(connection.scope))
            await sync()
        } catch is CancellationError {
            return
        } catch {
            guard epoch == generation, !Task.isCancelled else { return }
            if let failure = error as? MobileAPIError {
                if failure.status == 401 { availability = .expired; identity = nil }
                else { notice = message(for: error) }
            } else if error is URLError {
                availability = .unreachable
            } else {
                notice = message(for: error)
            }
        }
    }

    func saveScans(_ images: [Data], workbookID: String?) -> Int {
        var saved = 0
        do {
            for image in images {
                let receipt = PendingReceipt(id: UUID(), created: .now, workbookID: workbookID,
                                             scope: workbookID == nil ? nil : connection?.scope)
                try writeBytes(image, photoName(receipt.id))
                do { try updateQueue(pending + [receipt]) }
                catch { try? FileManager.default.removeItem(at: root.appending(path: photoName(receipt.id))); throw error }
                saved += 1
            }
        } catch {
            notice = "Saved \(saved) of \(images.count) scans. Check available iPhone storage before trying again."
        }
        Task { await sync() }
        return saved
    }

    func assign(_ id: UUID, to workbookID: String) async {
        guard !syncing, var row = pending.first(where: { $0.id == id && $0.scope == nil }),
              let scope = connection?.scope else { return }
        row.workbookID = workbookID
        row.scope = scope
        do { try replace(row); await sync() }
        catch { notice = message(for: error) }
    }

    func retryReceipt(_ id: UUID) async {
        guard !syncing, var row = pending.first(where: { $0.id == id && $0.scope == connection?.scope }) else { return }
        row.issue = nil
        do { try replace(row); await refresh() }
        catch { notice = message(for: error) }
    }

    private func sync() async {
        guard !busy, !syncing, connected, let api, let identity, let connection else { return }
        syncing = true
        defer { syncing = false }
        var submitted = false
        for receipt in pending where receipt.scope == connection.scope && receipt.issue == nil {
            if Task.isCancelled { break }
            var row = receipt
            guard let workbook = snapshot.targets.first(where: { $0.id == row.workbookID }) else { continue }
            do {
                try await submit(&row, to: workbook, with: api, csrf: identity.csrf_token)
                try finish(row)
                submitted = true
            } catch let error as MobileAPIError {
                if error.code == "ALREADY_COMMITTED" {
                    do { try finish(row); submitted = true }
                    catch { notice = message(for: error) }
                } else if error.status == 401 {
                    availability = .expired
                    break
                } else if error.code == "STALE_BASE" {
                    // A definitive rejection lets the next retry capture a fresh workbook version.
                    row.submission = nil
                    row.issue = "The workbook was updated. Refresh and retry this receipt."
                    do { try replace(row) } catch { notice = message(for: error) }
                } else if error.status < 500 && error.status != 429 {
                    row.issue = message(for: error)
                    do { try replace(row) } catch { notice = message(for: error) }
                } else { break }
            } catch {
                if !Task.isCancelled {
                    if error is URLError { availability = .unreachable }
                    else { notice = message(for: error) }
                }
                break
            }
        }
        if submitted, let result: Items<ReceiptRecord> = try? await api.request("/api/v1/runs") {
            snapshot.receipts = result.items
            do { try write(snapshot, cacheName(connection.scope)) }
            catch { notice = message(for: error) }
        }
    }

    private func submit(_ row: inout PendingReceipt, to workbook: CaptureTarget, with api: MobileAPI, csrf: String) async throws {
        let id = row.id.uuidString.lowercased()
        if row.documentID == nil {
            let photo = try Data(contentsOf: root.appending(path: photoName(row.id)))
            let boundary = "LedgerFlow-\(id)"
            var body = Data("--\(boundary)\r\nContent-Disposition: form-data; name=\"client_upload_id\"\r\n\r\n\(id)\r\n--\(boundary)\r\nContent-Disposition: form-data; name=\"file\"; filename=\"receipt-\(id).jpg\"\r\nContent-Type: image/jpeg\r\n\r\n".utf8)
            body.append(photo)
            body.append(Data("\r\n--\(boundary)--\r\n".utf8))
            let doc: RemoteDocument = try await api.request("/api/v1/workbooks/\(try component(workbook.id))/documents", method: "POST",
                body: body, contentType: "multipart/form-data; boundary=\(boundary)", csrf: csrf, key: "upload_\(id)", timeout: 90)
            row.documentID = doc.document_id
            try replace(row)
        }
        guard let documentID = row.documentID else { return }
        let document: RemoteDocument = try await api.request("/api/v1/documents/\(try component(documentID))")
        guard ["ready", "normalized"].contains(document.status ?? "") else {
            if ["failed", "rejected", "unreadable"].contains(document.status ?? "") {
                throw MobileAPIError(status: 422, code: "IMAGE_UNREADABLE")
            }
            throw MobileAPIError(status: 503, code: nil)
        }
        let target = row.submission ?? workbook
        row.submission = target
        try replace(row)
        struct RunInput: Encodable {
            let workbook_id: String; let document_id: String; let expected_base_version_id: String
            let expected_base_sha256: String; let mapping_id: String; let mapping_version: Int; let client_request_id: String
        }
        let input = RunInput(workbook_id: target.id, document_id: documentID, expected_base_version_id: target.base_version_id,
                             expected_base_sha256: target.base_sha256, mapping_id: target.mapping_id,
                             mapping_version: target.mapping_version, client_request_id: id)
        let _: CreatedRun = try await api.request("/api/v1/runs", method: "POST", body: encode(input), csrf: csrf, key: "run_\(id)")
    }

    func ask(_ text: String) async -> Bool {
        let clean = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !asking, !clean.isEmpty else { return false }
        guard connected, let api, let identity, let connection else {
            notice = "Not connected to your Mac. Open LedgerFlow on the Mac, same Wi-Fi, then pull to refresh or pair again."
            return false
        }
        guard chatAvailable else {
            notice = "This iPhone is paired for receipts only. On the Mac, pair again with workspace access to chat."
            return false
        }
        let lang = ["en", "fr", "sv"].first { $0 == Locale.preferredLanguages.first?.prefix(2).lowercased() } ?? "en"
        asking = true
        defer { asking = false }
        let key = chatRetry?.text == clean ? chatRetry?.key ?? UUID().uuidString : UUID().uuidString
        chatRetry = (clean, key)
        do {
            let messages: Items<AgentMessage> = try await api.request("/api/v1/assistant/messages", method: "POST",
                body: encode(["text": clean, "language": lang]), csrf: identity.csrf_token, key: key, timeout: 120)
            for message in messages.items where !snapshot.messages.contains(where: { $0.id == message.id }) { snapshot.messages.append(message) }
            chatRetry = nil
            try write(snapshot, cacheName(connection.scope))
            return true
        } catch {
            notice = message(for: error)
            return false
        }
    }

    func receiptImage(_ receipt: ReceiptRecord) async throws -> Data {
        guard connected, let api else { throw URLError(.notConnectedToInternet) }
        let document: RemoteDocument = try await api.request("/api/v1/documents/\(try component(receipt.document_id))")
        guard let path = document.image_url, let url = URL(string: path, relativeTo: api.endpoint.url)?.absoluteURL,
              api.endpoint.permitsDownload(url) else { throw URLError(.badServerResponse) }
        return try await api.bytes(path)
    }

    func workbookFile(_ workbook: Workbook) async throws -> URL {
        guard connected, let api else { throw URLError(.notConnectedToInternet) }
        let versions: Items<WorkbookVersion> = try await api.request("/api/v1/workbooks/\(try component(workbook.id))/versions")
        guard let version = versions.items.first(where: \.is_current) else { throw URLError(.resourceUnavailable) }
        let data = try await api.bytes("/api/v1/artifacts/\(try component(version.artifact_id))/download", timeout: 45)
        guard !data.isEmpty, data.count <= 16 * 1024 * 1024,
              SHA256.hash(data: data).map({ String(format: "%02x", $0) }).joined() == version.sha256 else {
            throw URLError(.cannotDecodeContentData)
        }
        let directory = URL.temporaryDirectory.appending(path: "LedgerFlow-\(UUID())", directoryHint: .isDirectory)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let file = directory.appending(path: "LedgerFlow.xlsx")
        do { try data.write(to: file, options: [.atomic, .completeFileProtection]); return file }
        catch { try? FileManager.default.removeItem(at: directory); throw error }
    }

    func queuedImage(_ id: UUID) -> Data? { try? Data(contentsOf: root.appending(path: photoName(id))) }

    private func finish(_ row: PendingReceipt) throws {
        try updateQueue(pending.filter { $0.id != row.id })
        try? FileManager.default.removeItem(at: root.appending(path: photoName(row.id)))
    }

    private func replace(_ row: PendingReceipt) throws {
        try updateQueue(pending.map { $0.id == row.id ? row : $0 })
    }

    private func updateQueue(_ next: [PendingReceipt]) throws {
        try write(next, "outbox.json")
        pending = next
    }

    private func scopeFor(endpoint: WorkspaceEndpoint, pin: String?, identity: MobileIdentity) -> String {
        let parts = [pin ?? endpoint.url.absoluteString, identity.tenant_id, identity.user_id, identity.role]
        return SHA256.hash(data: Data(parts.joined(separator: "\n").utf8)).map { String(format: "%02x", $0) }.joined()
    }

    private func component(_ value: String) throws -> String {
        guard value.range(of: "^[A-Za-z0-9_-]+$", options: .regularExpression) != nil else { throw URLError(.badServerResponse) }
        return value
    }

    private func cacheName(_ scope: String) -> String { "workspace-\(scope).json" }
    private func photoName(_ id: UUID) -> String { "\(id).jpg" }

    private func read<T: Decodable>(_ type: T.Type, _ filename: String) -> T? {
        guard let data = try? Data(contentsOf: root.appending(path: filename)) else { return nil }
        return try? JSONDecoder().decode(type, from: data)
    }

    private func encode<T: Encodable>(_ value: T) throws -> Data {
        let encoder = JSONEncoder()
        encoder.outputFormatting = .sortedKeys
        return try encoder.encode(value)
    }

    private func write<T: Encodable>(_ value: T, _ filename: String) throws { try writeBytes(encode(value), filename) }

    private func writeBytes(_ data: Data, _ filename: String) throws {
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        var directory = root
        var values = URLResourceValues()
        values.isExcludedFromBackup = true
        try directory.setResourceValues(values)
        try data.write(to: root.appending(path: filename), options: [.atomic, .completeFileProtection])
    }

    func message(for error: Error) -> String {
        if let apiError = error as? MobileAPIError { return apiError.localizedDescription }
        if let address = error as? WorkspaceEndpoint.InvalidAddress { return address.localizedDescription }
        if error is URLError { return "The workspace could not be reached. Check the connection and try again." }
        return "LedgerFlow could not complete this action. Try again."
    }
}
