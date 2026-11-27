import Foundation
import CryptoKit
import Security

/// Trust only the exact certificate the user associated by scanning their Mac's QR.
nonisolated enum WorkspaceTrust {
    static func credential(for challenge: URLAuthenticationChallenge, host: String?, fingerprint: String?) -> URLCredential? {
        guard let fingerprint, fingerprint.count == 64,
              challenge.protectionSpace.authenticationMethod == NSURLAuthenticationMethodServerTrust,
              challenge.protectionSpace.host == host,
              let trust = challenge.protectionSpace.serverTrust,
              let chain = SecTrustCopyCertificateChain(trust) as? [SecCertificate],
              let certificate = chain.first else { return nil }
        let digest = SHA256.hash(data: SecCertificateCopyData(certificate) as Data).map { String(format: "%02x", $0) }.joined()
        guard digest == fingerprint else { return nil }
        SecTrustSetPolicies(trust, SecPolicyCreateSSL(true, challenge.protectionSpace.host as CFString))
        SecTrustSetAnchorCertificates(trust, [certificate] as CFArray)
        SecTrustSetAnchorCertificatesOnly(trust, true)
        guard SecTrustEvaluateWithError(trust, nil) else { return nil }
        return URLCredential(trust: trust)
    }
}
